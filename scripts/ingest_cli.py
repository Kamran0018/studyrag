
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from rag.loader import load_document
from rag.chunker import chunk_pages


def main():
    parser = argparse.ArgumentParser(
        description="Extract and chunk a PDF or DOCX document."
    )
    parser.add_argument("file", help="Path to a PDF or DOCX file")
    args = parser.parse_args()

    file_path = Path(args.file)

    try:
        pages = load_document(file_path)
        chunks = chunk_pages(pages)

        print(f"\nFile: {file_path.name}")
        print(f"Sections/pages extracted: {len(pages)}")
        print(f"Chunks created: {len(chunks)}")

        print("\nPage/section metadata:")
        for page in pages:
            print(f"- {page['page']}: {len(page['text'])} characters")

    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
