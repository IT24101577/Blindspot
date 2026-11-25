
from document_loader import load_text_documents, SAMPLES_DIR


def chunk_text(text, chunk_size=60, overlap=12):

    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("Overlap must be smaller than chunk size.")

    words = text.split()
    chunks = []

    step = chunk_size - overlap

    for start in range(0, len(words), step):

        chunk_words = words[start:start + chunk_size]

        if not chunk_words:
            break

        chunks.append(" ".join(chunk_words))

        if start + chunk_size >= len(words):
            break

    return chunks


def main():

    documents = load_text_documents(SAMPLES_DIR)

    for document in documents:

        chunks = chunk_text(document["text"])

        print(f"\nDocument: {document['source']}")
        print(f"Total chunks: {len(chunks)}")

        for index, chunk in enumerate(chunks, start=1):

            print(f"\n--- Chunk {index} ---")
            print(chunk)


if __name__ == "__main__":
    main()
