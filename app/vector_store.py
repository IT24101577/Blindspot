
from pathlib import Path

import chromadb

from app.document_loader import load_text_documents, SAMPLES_DIR
from app.chunker import chunk_text
from app.embedder import generate_embeddings


# Database configuration
DB_PATH = Path(__file__).resolve().parent.parent / "chroma_db"

COLLECTION_NAME = "blindspot_knowledge"
SECURITY_LAB_COLLECTION = "blindspot_security_lab"


def store_documents(
    directory=SAMPLES_DIR,
    collection_name=COLLECTION_NAME
):
    
    # Load our documents
    documents = load_text_documents(directory)

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
        name=collection_name,
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
        # Remove outdated chunks from previous indexing versions
    for document in documents:

        source = document["source"]

        # Generate the IDs expected from the current chunker
        expected_ids = {
            f"{source}_chunk_{index}"
            for index, _ in enumerate(
                chunk_text(document["text"]),
                start=1
            )
        }

        # Retrieve existing records for this document
        existing_records = collection.get(
            where={"source": source},
            include=["metadatas"]
        )

        # Identify chunks that no longer exist
        stale_ids = [
            record_id
            for record_id in existing_records["ids"]
            if record_id not in expected_ids
        ]

        # Delete obsolete chunks
        if stale_ids:
            collection.delete(ids=stale_ids)

            print(
                f"Removed {len(stale_ids)} outdated chunks "
                f"from {source}"
            )

    print("\nDocuments stored successfully!")
    print(f"Collection: {collection_name}")
    print(f"Database location: {DB_PATH}")
    print(f"Chunks processed: {len(all_chunks)}")
    print(f"Total records in database: {collection.count()}")


if __name__ == "__main__":
    store_documents()
 