import hashlib
from pathlib import Path
import re
import uuid

import chromadb

from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.vector_store import (
    store_documents,
    SECURITY_LAB_COLLECTION
)
from pydantic import BaseModel
from app.ask import answer_question
from app.document_loader import SAMPLES_DIR

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "chroma_db"
UPLOADS_DIR = BASE_DIR / "data" / "uploads"
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATE_DIR = BASE_DIR / "app" / "templates"

COLLECTION_NAME = "blindspot_knowledge"

MAX_UPLOAD_SIZE = 2 * 1024 * 1024  # 2 MB


# Initialize FastAPI
app = FastAPI(
    title="Blindspot",
    description="AI Application Security Testing Laboratory",
    version="0.1.0"
)


# Configure frontend resources
app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static"
)

templates = Jinja2Templates(
    directory=str(TEMPLATE_DIR)
)

class AskRequest(BaseModel):
    question: str
    sources: list[str] | None = None

class SecurityLabAskRequest(BaseModel):
    question: str
    source: str


# Dashboard data
def get_dashboard_data():

    try:
        client = chromadb.PersistentClient(
            path=str(DB_PATH)
        )

        collection = client.get_collection(
            name=COLLECTION_NAME
        )

        records = collection.get(
            include=["metadatas"]
        )

        metadata = records.get("metadatas") or []

        documents = sorted({
            item["source"]
            for item in metadata
            if item and item.get("source")
        })

        return {
            "document_count": len(documents),
            "chunk_count": collection.count(),
            "db_status": "Connected",
            "documents": documents
        }

    except Exception as exc:

        print(f"Dashboard database error: {exc}")

        return {
            "document_count": 0,
            "chunk_count": 0,
            "db_status": "Unavailable",
            "documents": []
        }


# Dashboard homepage
@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    upload_status: str | None = None
):

    dashboard_data = get_dashboard_data()

    messages = {
        "success": "Document uploaded and indexed successfully!",
        "invalid_type": "Only TXT files are currently supported.",
        "too_large": "File exceeds the 2 MB upload limit.",
        "invalid_text": "The file must contain valid, non-empty UTF-8 text.",
        "processing_failed": "Document processing failed. Check the server logs.",
        "duplicate": "This document already exists in the knowledge base."
        
    }

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "stats": dashboard_data,
            "documents": dashboard_data["documents"],
            "upload_message": messages.get(upload_status),
            "upload_error": (
                upload_status is not None
                and upload_status != "success"
            )
        }
    )


# Document upload endpoint
@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):

    # Validate filename
    original_name = (
        (file.filename or "")
        .replace("\\", "/")
        .rsplit("/", 1)[-1]
        .strip()
    )

    if not original_name or Path(original_name).suffix.lower() != ".txt":
        await file.close()

        return RedirectResponse(
            "/?upload_status=invalid_type",
            status_code=303
        )

    # Read no more than the allowed size plus one byte
    try:
        content = await file.read(MAX_UPLOAD_SIZE + 1)
    finally:
        await file.close()

    if len(content) > MAX_UPLOAD_SIZE:
        return RedirectResponse(
            "/?upload_status=too_large",
            status_code=303
        )

    # Validate text encoding and content
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return RedirectResponse(
            "/?upload_status=invalid_text",
            status_code=303
        )

    if not text.strip() or "\x00" in text:
        return RedirectResponse(
            "/?upload_status=invalid_text",
            status_code=303
        )
    
    # Calculate SHA-256 hash of uploaded content
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")

    content_hash = hashlib.sha256(
        normalized_text.encode("utf-8")
    ).hexdigest()


    # Check existing documents for identical content
    for directory in (SAMPLES_DIR, UPLOADS_DIR):

        if not directory.exists():
            continue

        for existing_file in directory.glob("*.txt"):

            try:
                existing_text = existing_file.read_text(
                    encoding="utf-8"
                )
            except (OSError, UnicodeDecodeError):
                continue

            existing_text = (
                existing_text
                .replace("\r\n", "\n")
                .replace("\r", "\n")
            )

            existing_hash = hashlib.sha256(
                existing_text.encode("utf-8")
            ).hexdigest()

            if content_hash == existing_hash:

                print(
                    f"Duplicate document detected: "
                    f"{existing_file.name}"
                )

                return RedirectResponse(
                    "/?upload_status=duplicate",
                    status_code=303
                )

    # Generate a safe, unique filename
    stem = Path(original_name).stem

    safe_stem = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        stem
    ).strip("._-") or "document"

    stored_name = (
        f"{safe_stem}_{uuid.uuid4().hex[:8]}.txt"
    )

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    destination = UPLOADS_DIR / stored_name

    # Save and index the uploaded document
    try:
        destination.write_text(
            text,
            encoding="utf-8"
        )

        store_documents(directory=UPLOADS_DIR)

    except Exception as exc:

        print(f"Document upload error: {exc}")

        destination.unlink(missing_ok=True)

        return RedirectResponse(
            "/?upload_status=processing_failed",
            status_code=303
        )

    return RedirectResponse(
        "/?upload_status=success",
        status_code=303
    )
# AI Playground API
@app.post("/api/ask")
def ask_ai(payload: AskRequest):

    try:
        result = answer_question(
            payload.question,
            sources=payload.sources
        )

        if result is None:
            return {
                "answer": "I couldn't find relevant information in the indexed documents.",
                "sources": []
            }

        answer, sources = result

        return {
            "answer": answer,
            "sources": [
                {
                    **source,
                    "distance": float(source["distance"])
                }
                for source in sources
            ]
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception as exc:
        print(f"AI question error: {exc}")

        raise HTTPException(
            status_code=500,
            detail="AI request failed. Check the server logs."
        )

# Security Research Lab API
@app.post("/api/security-lab/ask")
def ask_security_lab(payload: SecurityLabAskRequest):

    if not payload.source.strip():
        raise HTTPException(
            status_code=400,
            detail="Source cannot be empty."
        )

    try:

        result = answer_question(
            payload.question,
            sources=[payload.source],
            collection_name=SECURITY_LAB_COLLECTION
        )

        if result is None:
            return {
                "answer": "No relevant information found in the security lab.",
                "sources": []
            }

        answer, sources = result

        return {
            "answer": answer,
            "sources": [
                {
                    **source,
                    "distance": float(source["distance"])
                }
                for source in sources
            ]
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception as exc:

        print(f"Security lab query error: {exc}")

        raise HTTPException(
            status_code=500,
            detail="Security lab request failed. Check server logs."
        )


# Backend health check
@app.get("/health")
async def health_check():

    return {
        "status": "operational",
        "application": "Blindspot",
        "version": "0.1.0"
    }
