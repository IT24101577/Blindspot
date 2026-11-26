
from pathlib import Path

import chromadb

from app.embedder import generate_embeddings


# Database configuration
DB_PATH = Path(__file__).resolve().parent.parent / "chroma_db"

COLLECTION_NAME = "blindspot_knowledge"



def search_documents(question, top_k=5, max_distance=0.40):

    if not question.strip():
        raise ValueError("Search question cannot be empty.")

    if top_k <= 0:
        raise ValueError("top_k must be positive.")

    if not 0 <= max_distance <= 2:
        raise ValueError("Invalid cosine distance threshold.")

    # Connect to our persistent database
    client = chromadb.PersistentClient(
        path=str(DB_PATH)
    )

    # Access our existing collection
    collection = client.get_collection(
        name=COLLECTION_NAME
    )

    total_records = collection.count()

    if total_records == 0:
        print("The database is empty.")
        return None

    # Convert the question into an embedding
    query_embedding = generate_embeddings([question])[0]

    # Retrieve the closest document chunks
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, total_records),
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    # Identify chunks that meet the relevance threshold
    distances = results["distances"][0]

    relevant_indices = [
        index
        for index, distance in enumerate(distances)
        if distance <= max_distance
    ]

    # Return nothing when no relevant chunks are found
    if not relevant_indices:
        print("No sufficiently relevant information found.")
        return None

    # Keep only relevant search results
    for field in ("ids", "documents", "metadatas", "distances"):

        results[field][0] = [
            results[field][0][index]
            for index in relevant_indices
        ]

    return results



def main():

    print("\n=== BLINDSPOT SEMANTIC SEARCH ===\n")

    question = input("Enter your question: ").strip()

    results = search_documents(question)

    if results is None:
        return

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    ids = results["ids"][0]

    print(f"\nSearch results: {len(documents)}")

    for index, (doc_id, document, metadata, distance) in enumerate(
        zip(ids, documents, metadatas, distances),
        start=1
    ):

        print(f"\n--- Result {index} ---")
        print(f"ID: {doc_id}")
        print(f"Source: {metadata['source']}")
        print(f"Chunk: {metadata['chunk_index']}")
        print(f"Cosine distance: {distance:.4f}")
        print(f"\nContent:\n{document}")


if __name__ == "__main__":
    main()
