def compute_stats(chunks) -> dict:
    """Embedlenen chunk'lardan özet istatistik (sayfa, parça, tür dağılımı)."""
    types: dict[str, int] = {}
    pages: set[int] = set()
    for c in chunks:
        types[c.content_type] = types.get(c.content_type, 0) + 1
        pages.add(c.page_number)
    return {"pages": len(pages), "chunks": len(chunks), "types": types}