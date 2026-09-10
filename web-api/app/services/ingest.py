from .extract import extract_segments
from .types import Chunk, Segment


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    text = "\n".join(" ".join(line.split()) for line in text.split("\n"))
    text = text.replace("\n \n", "\n\n")
    return text.strip()


def _split(text: str, size: int, overlap: int) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    start, n = 0, len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:
            cut = text.rfind("\n", start, end)
            if cut <= start + size * 0.5:
                cut = text.rfind(" ", start, end)
            if cut > start + size * 0.5:
                end = cut

        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break

        start = max(end - overlap, start + 1)
        if start < n:
            nxt = text.find(" ", start, min(start + overlap, n))
            if nxt != -1 and nxt - start < overlap:
                start = nxt + 1

    if len(chunks) > 1 and len(chunks[-1]) < size * 0.3:
        chunks[-2] = f"{chunks[-2]}\n\n{chunks[-1]}"
        chunks.pop()
    return chunks


def chunk_segments(segments: list[Segment], size: int, overlap: int) -> list[Chunk]:
    groups: list[list[Segment]] = []
    for seg in segments:
        joins = (
            seg.content_type != "table"
            and groups
            and groups[-1][0].page_number == seg.page_number
            and groups[-1][0].content_type == seg.content_type
            and groups[-1][0].page_context == seg.page_context
        )
        if joins:
            groups[-1].append(seg)
        else:
            groups.append([seg])

    chunks: list[Chunk] = []
    idx = 0
    for group in groups:
        head = group[0]
        text = "\n".join(s.text for s in group)
        bbox = [box for s in group for box in s.bbox]
        pieces = [text] if head.content_type == "table" else _split(text, size, overlap)
        for piece in pieces:
            chunks.append(
                Chunk(
                    text=piece,
                    content_type=head.content_type,
                    page_number=head.page_number,
                    page_context=head.page_context,
                    chunk_index=idx,
                    bbox=bbox,
                )
            )
            idx += 1
    return chunks


async def extract_segments_for(filename: str, path) -> list[Segment]:
    return await extract_segments(filename, path)