
from pathlib import Path

import chromadb

from app.embedder import generate_embeddings


# Database configuration
DB_PATH = Path(__file__).resolve().parent.parent / "chroma_db"

COLLECTION_NAME = "blindspot_knowledge"




def search_documents(question, top_k=5, max_distance=0.40, sources=None):

    if not question.strip():
        raise ValueError("Search question cannot be empty.")

    if top_k <= 0:
        raise ValueError("top_k must be positive.")

    if not 0 <= max_distance <= 2:
        raise ValueError("Invalid cosine distance threshold.")

    client = chromadb.PersistentClient(
        path=str(DB_PATH)
    )

    collection = client.get_collection(
        name=COLLECTION_NAME
    )

    # Restrict retrieval to selected documents
    where = None

    if sources is not None:

        selected_sources = list(dict.fromkeys(
            source.strip()
            for source in sources
            if isinstance(source, str) and source.strip()
        ))

        if not selected_sources:
            return None

        where = {
            "source": {
                "$in": selected_sources
            }
        }

    if where is not None:
        matching_records = collection.get(
            where=where,
            include=["metadatas"]
        )

        total_records = len(matching_records["ids"])

    else:
        total_records = collection.count()

    if total_records == 0:
        return None

    query_embedding = generate_embeddings([question])[0]

    query_options = {
        "query_embeddings": [query_embedding],
        "n_results": min(top_k, total_records),
        "include": [
            "documents",
            "metadatas",
            "distances"
        ]
    }

    if where is not None:
        query_options["where"] = where

    results = collection.query(**query_options)

    # Apply relevance filtering
    distances = results["distances"][0]

    relevant_indices = [
        index
        for index, distance in enumerate(distances)
        if distance <= max_distance
    ]

    if not relevant_indices:
        return None

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
