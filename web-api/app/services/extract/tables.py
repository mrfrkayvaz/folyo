"""Tablo → Markdown dönüşümü ve caption çıkarımı."""


def table_to_markdown(table) -> str:
    """PyMuPDF tablo nesnesini Markdown tablosuna çevirir."""
    rows = table.extract()
    if not rows:
        return ""
    rows = [
        [(c or "").replace("\r", " ").replace("\n", " ").replace("|", "\\|").strip() for c in row]
        for row in rows
    ]
    rows = [r for r in rows if any(c for c in r)]
    if not rows:
        return ""
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]

    header = rows[0]
    md = "| " + " | ".join(header) + " |\n"
    md += "| " + " | ".join("---" for _ in header) + " |\n"
    for r in rows[1:]:
        md += "| " + " | ".join(r) + " |\n"
    return md.strip()


def table_caption(block_data: list[dict], tb) -> str | None:
    """Tablo bbox'ının hemen üstündeki kısa metin bloğunun ilk satırını caption olarak döndürür."""
    best: tuple[str, float] | None = None
    for block in block_data:
        if block.get("type") != 0:
            continue
        bx0, by0, bx1, by1 = block["bbox"]
        if not (by1 <= tb[1] and by0 < tb[1] and by1 >= tb[1] - 60):
            continue
        for line in block.get("lines", []):
            text = "".join(sp.get("text", "") for sp in line.get("spans", [])).strip()
            if not text:
                continue
            if len(text) <= 90 and (best is None or by1 > best[1]):
                best = (text, by1)
            break
    return best[0] if best else None