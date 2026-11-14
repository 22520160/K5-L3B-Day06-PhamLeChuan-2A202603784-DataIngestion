from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    if size <= 0:
        raise ValueError("size must be greater than zero")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and smaller than size")

    text = page.text.strip()
    if not text:
        return []

    chunks: list[Chunk] = []
    step = size - overlap
    start = 0
    index = 0

    while start < len(text):
        chunk_text = text[start:start + size].strip()

        if chunk_text:
            chunks.append(
                Chunk(
                    chunk_id=f"{page.document_id}:p{page.page}:fixed:{index}",
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=chunk_text,
                    metadata={
                        **page.metadata,
                        "chunk_strategy": "fixed",
                        "chunk_index": index,
                        "start_offset": start,
                    },
                )
            )

        index += 1
        start += step

    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    if max_size <= 0:
        raise ValueError("max_size must be greater than zero")

    text = page.text.strip()
    if not text:
        return []

    paragraphs = [
        paragraph.strip()
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    ]

    chunks: list[Chunk] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_size:
            if current:
                chunks.append(_make_chunk(page, current, len(chunks)))
                current = ""

            for start in range(0, len(paragraph), max_size):
                part = paragraph[start:start + max_size].strip()
                if part:
                    chunks.append(_make_chunk(page, part, len(chunks)))
            continue

        candidate = paragraph if not current else f"{current}\n\n{paragraph}"

        if len(candidate) <= max_size:
            current = candidate
        else:
            chunks.append(_make_chunk(page, current, len(chunks)))
            current = paragraph

    if current:
        chunks.append(_make_chunk(page, current, len(chunks)))

    return chunks


def _make_chunk(page: DocumentPage, text: str, index: int) -> Chunk:
    return Chunk(
        chunk_id=f"{page.document_id}:p{page.page}:paragraph:{index}",
        document_id=page.document_id,
        source=page.source,
        page=page.page,
        text=text,
        metadata={
            **page.metadata,
            "chunk_strategy": "paragraph",
            "chunk_index": index,
        },
    )
