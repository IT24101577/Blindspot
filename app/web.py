
from pathlib import Path

import chromadb

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "chroma_db"
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATE_DIR = BASE_DIR / "app" / "templates"

COLLECTION_NAME = "blindspot_knowledge"


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


# Read actual database statistics
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

    except Exception:

        return {
            "document_count": 0,
            "chunk_count": 0,
            "db_status": "Unavailable",
            "documents": []
        }


# Dashboard homepage
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    dashboard_data = get_dashboard_data()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "stats": dashboard_data,
            "documents": dashboard_data["documents"]
        }
    )


# Backend health check
@app.get("/health")
async def health_check():

    return {
        "status": "operational",
        "application": "Blindspot",
        "version": "0.1.0"
    }
