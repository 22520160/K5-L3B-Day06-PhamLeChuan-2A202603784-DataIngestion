import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

from .models import DocumentPage


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = [
        re.sub(r"[ \t]+", " ", line).strip()
        for line in text.split("\n")
    ]

    result = []
    previous_blank = False

    for line in lines:
        if line:
            result.append(line)
            previous_blank = False
        elif not previous_blank:
            result.append("")
            previous_blank = True

    return "\n".join(result).strip()


def load_pdf(path: Path, document_id: str, source: str, page_metadata: dict[int, dict[str, str]] | None = None,) -> list[DocumentPage]:
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    reader = PdfReader(str(path))
    pages = []

    for page_number, pdf_page in enumerate(reader.pages, start=1):
        text = normalize_text(pdf_page.extract_text() or "")

        metadata = {
         "document_type": "book",
         "has_text": bool(text),
         "content_chars": len(text),
        }

        if page_metadata and page_number in page_metadata:
          metadata.update(page_metadata[page_number])

        pages.append(
            DocumentPage(
                document_id=document_id,
                source=source,
                page=page_number,
                text=text,
                metadata=metadata,
            )
        )

    if not pages:
        raise ValueError(f"PDF contains no pages: {path}")

    return pages
