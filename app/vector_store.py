
from pathlib import Path

import chromadb

from document_loader import load_text_documents, SAMPLES_DIR
from chunker import chunk_text
from embedder import generate_embeddings


# Database configuration
DB_PATH = Path(__file__).resolve().parent.parent / "chroma_db"

COLLECTION_NAME = "blindspot_knowledge"


def store_documents():

    # Load our documents
    documents = load_text_documents(SAMPLES_DIR)

    if not documents:
        print("No documents found.")
        return

    all_chunks = []
    all_ids = []
    all_metadata = []

    # Split documents into chunks
    for document in documents:

        chunks = chunk_text(document["text"])

        for index, chunk in enumerate(chunks, start=1):

            all_chunks.append(chunk)

            all_ids.append(
                f"{document['source']}_chunk_{index}"
            )

            all_metadata.append({
                "source": document["source"],
                "chunk_index": index
            })

    if not all_chunks:
        print("No text chunks available.")
        return

    # Generate embeddings
    print("Generating embeddings...")

    embeddings = generate_embeddings(all_chunks)

    # Initialize persistent ChromaDB
    DB_PATH.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(DB_PATH)
    )

    # Create or retrieve our collection
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=None
    )

    # Store documents, embeddings and metadata
    collection.upsert(
        ids=all_ids,
        embeddings=embeddings,
        documents=all_chunks,
        metadatas=all_metadata
    )

    print("\nDocuments stored successfully!")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Database location: {DB_PATH}")
    print(f"Chunks processed: {len(all_chunks)}")
    print(f"Total records in database: {collection.count()}")


if __name__ == "__main__":
    store_documents()
