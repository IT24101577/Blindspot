
from pathlib import Path


# Locate the sample documents directory
SAMPLES_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "samples"
)


def load_text_documents(directory: Path) -> list[dict[str, str]]:

    if not directory.is_dir():
        raise FileNotFoundError(
            f"Document directory not found: {directory}"
        )

    documents = []

    # Find all text files in the directory
    for file_path in sorted(directory.glob("*.txt")):

        # Read the document contents
        content = file_path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            print(f"Skipping empty document: {file_path.name}")
            continue

        # Store the filename and its contents
        documents.append({
            "source": file_path.name,
            "text": content
        })

    return documents


def main():

    documents = load_text_documents(SAMPLES_DIR)

    if not documents:
        print("No documents found.")
        return

    print(f"Successfully loaded {len(documents)} document(s).\n")

    for document in documents:
        print(f"Document: {document['source']}")
        print("-" * 40)
        print(document["text"])
        print()


if __name__ == "__main__":
    main()
