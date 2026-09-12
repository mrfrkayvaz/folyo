import re
from .extract import extract_segments
from .types import Chunk, Segment


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    # Satır sonu tirelemesiyle bölünmüş sözcükleri birleştir (PDF artefaktı: "olu-\nşan").
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    # Ok/glif gürültüsünü (süsleme karakterleri) boşlukla değiştir.
    text = re.sub(r"[➨➔→]", " ", text)
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


def _with_breadcrumb(text: str, breadcrumbs: list[str]) -> str:
    if not breadcrumbs:
        return text
    return f"[Bölüm: {' > '.join(breadcrumbs)}]\n{text}"


def _split_table(text: str, size: int) -> list[str]:
    """Büyük markdown tabloyu satır bazlı böler; her parça ön satırları + başlık/ayırıcıyı korur.

    `[Tablo: etiket]` gibi ön satırlar ve başlık+ayırıcı her parçada tekrarlanır,
    böylece parçalar bağlamdan kopmaz ve embed girdisi sınırda kalmaz.
    """
    lines = text.split("\n")
    prefix: list[str] = []
    while lines and not lines[0].startswith("|"):
        prefix.append(lines.pop(0))
    head: list[str] = []
    while lines and len(head) < 2:
        head.append(lines.pop(0))  # başlık satırı + ```---``` ayırıcı
    if not head:
        return [text]

    chunks: list[str] = []
    buf: list[str] = []

    def body_len() -> int:
        return len("\n".join(buf))

    def flush() -> None:
        nonlocal buf
        if buf:
            chunks.append("\n".join([*prefix, *head, *buf]))
            buf = []

    for ln in lines:
        if buf and body_len() + len(ln) + 1 > size:
            flush()
        buf.append(ln)
    flush()
    return chunks or [text]


def chunk_segments(
    segments: list[Segment],
    size: int,
    overlap: int,
    table_max_chars: int = 0,
) -> list[Chunk]:
    groups: list[list[Segment]] = []
    # `text` ile `equation` aynı grupta birleşebilir — denklemler paragraf bağlamından kopmaz
    # (sayfa başına 20 denklem = 20 mini chunk olmasın). Diğer türler tek başlarına bölünmez.
    mergeable: tuple[str, ...] = ("text", "equation")
    for seg in segments:
        head = groups[-1][0] if groups else None
        joins = (
            seg.content_type in mergeable
            and head is not None
            and head.page_number == seg.page_number
            and head.content_type in mergeable
            and head.page_context == seg.page_context
        )
        if joins:
            groups[-1].append(seg)
        else:
            groups.append([seg])

    chunks: list[Chunk] = []
    idx = 0
    for group in groups:
        head = group[0]
        # Karışık grup (metin + denklem) varsa chunk türü `text`; saf denklem grubu `equation`.
        ctype = "text" if any(s.content_type == "text" for s in group) else head.content_type
        text = "\n".join(s.text for s in group)
        bbox = [box for s in group for box in s.bbox]
        pieces: list[str]
        if ctype == "text":
            pieces = _split(text, size, overlap)
        elif ctype == "table" and table_max_chars > 0 and len(text) > table_max_chars:
            pieces = _split_table(text, size)
        else:
            pieces = [text]
        for piece in pieces:
            chunks.append(
                Chunk(
                    text=_with_breadcrumb(piece, head.breadcrumbs),
                    # Embed metni breadcrumb ön eki olmadan (gürültüsüz vektör; ön ek
                    # gösterim/LLM için `text`'te ve `breadcrumbs` metadata'sında kalır).
                    embed_text=piece,
                    content_type=ctype,
                    page_number=head.page_number,
                    page_context=head.page_context,
                    chunk_index=idx,
                    bbox=bbox,
                    breadcrumbs=head.breadcrumbs,
                    image_path=head.image_path,
                    image_kind=head.image_kind,
                )
            )
            idx += 1
    return chunks


async def extract_segments_for(filename: str, path, crop_dir=None) -> list[Segment]:
    return await extract_segments(filename, path, crop_dir=crop_dir)