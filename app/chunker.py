
import re
from app.document_loader import load_text_documents, SAMPLES_DIR





def chunk_text(text, chunk_size=120, overlap=20):

    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("Overlap must be smaller than chunk size.")

    # Separate the document into paragraphs
    paragraphs = re.split(r"\n\s*\n", text.strip())

    chunks = []
    current_heading = None

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        # Clean Markdown heading symbols if present
        clean_paragraph = re.sub(
            r"^#+\s*", "", paragraph
        ).strip()

        words = clean_paragraph.split()

        # Identify Markdown and plain-text headings
        is_markdown_heading = paragraph.startswith("#")

        is_plain_heading = (
            len(words) <= 8
            and not re.search(r"[.!?]$", clean_paragraph)
        )

        if is_markdown_heading or is_plain_heading:

            current_heading = clean_paragraph
            continue

        # Attach the heading to the paragraph
        if current_heading:
            paragraph = f"{current_heading}: {clean_paragraph}"
        else:
            paragraph = clean_paragraph

        words = paragraph.split()

        # Keep shorter paragraphs together
        if len(words) <= chunk_size:
            chunks.append(" ".join(words))
            continue

        # Split longer paragraphs with overlap
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
