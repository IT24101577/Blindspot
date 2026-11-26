
import ollama

from app.chunker import chunk_text
from app.document_loader import load_text_documents, SAMPLES_DIR


EMBEDDING_MODEL = "qwen3-embedding:0.6b"


def generate_embeddings(text_chunks):

    if not text_chunks:
        return []

    response = ollama.embed(
        model=EMBEDDING_MODEL,
        input=text_chunks
    )

    embeddings = response.embeddings

    if len(embeddings) != len(text_chunks):
        raise RuntimeError(
            "Number of embeddings does not match number of chunks."
        )

    return embeddings


def main():

    documents = load_text_documents(SAMPLES_DIR)

    all_chunks = []

    for document in documents:

        chunks = chunk_text(document["text"])
        all_chunks.extend(chunks)

    if not all_chunks:
        print("No text chunks available.")
        return

    embeddings = generate_embeddings(all_chunks)

    print("\nEmbedding generation successful!")
    print(f"Model: {EMBEDDING_MODEL}")
    print(f"Total chunks: {len(all_chunks)}")
    print(f"Total embeddings: {len(embeddings)}")
    print(f"Vector dimensions: {len(embeddings[0])}")

    for index, embedding in enumerate(embeddings, start=1):

        print(f"\n--- Embedding {index} ---")
        print(f"Vector dimensions: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")


if __name__ == "__main__":
    main()
