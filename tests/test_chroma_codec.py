"""shared.services.chroma_codec — Chroma metadata kodlama/çözme (JSON alanları)."""

import json

from shared.services.chroma_codec import chunk_metadata, parse_get_row, parse_query_row
from shared.services.types import Chunk


def _chunk(**over):
    base = dict(
        text="örnek metin",
        content_type="text",
        page_number=3,
        page_context="bağlam",
        chunk_index=7,
    )
    base.update(over)
    return Chunk(**base)


def test_chunk_metadata_encodes_json_fields():
    c = _chunk(breadcrumbs=["Bölüm", "Alt"], bbox=[(0.0, 1.0, 2.0, 3.0)])
    meta = chunk_metadata("ws-1", "doc-9", "ad.docx", c)
    assert meta["workspace_id"] == "ws-1"
    assert meta["document_id"] == "doc-9"
    assert meta["page_number"] == 3
    assert meta["chunk_index"] == 7
    assert meta["content_type"] == "text"
    assert json.loads(meta["breadcrumbs"]) == ["Bölüm", "Alt"]
    assert meta["section_title"] == "Alt"
    # Chunk.bbox bir kutu LİSTESİDİR → [[x0,y0,x1,y1]] olarak dizilir
    assert json.loads(meta["bbox"]) == [[0.0, 1.0, 2.0, 3.0]]


def test_chunk_metadata_empty_breadcrumbs():
    meta = chunk_metadata("w", "d", "n", _chunk())
    assert meta["breadcrumbs"] == "[]"
    assert meta["section_title"] == ""


def test_parse_query_row_score_and_defaults():
    row = parse_query_row(
        {"document_id": "d1", "chunk_index": "4", "page_number": "2", "name": "x.pdf"},
        "metin",
        0.25,
    )
    assert row["doc_id"] == "d1"
    assert row["chunk_index"] == 4
    assert row["page_number"] == 2
    assert row["score"] == 0.75  # round(1 - 0.25, 4)


def test_parse_query_row_score_absent_means_zero():
    row = parse_query_row({}, "metin", None)
    assert row["score"] == 0.0
    assert row["content_type"] == "text"
    assert row["page_number"] == 1
    assert row["doc_id"] == ""


def test_parse_query_row_malformed_json_breadcrumbs_falls_back():
    row = parse_query_row({"breadcrumbs": "{broken", "bbox": "nope"}, "t", None)
    assert row["breadcrumbs"] == []
    assert row["bbox"] == []


def test_parse_query_row_non_list_json_falls_back():
    row = parse_query_row({"breadcrumbs": '"str"', "bbox": "42"}, "t", None)
    assert row["breadcrumbs"] == []
    assert row["bbox"] == []


def test_chunk_metadata_parse_roundtrip():
    c = _chunk(breadcrumbs=["A"], image_path="d/c.png", image_kind="figure")
    meta = chunk_metadata("w", "d", "n", c)
    row = parse_get_row(meta, c.text)
    assert row["doc_id"] == "d"
    assert row["chunk_index"] == 7
    assert row["page_number"] == 3
    assert row["content_type"] == "text"
    assert row["breadcrumbs"] == ["A"]
    assert row["image_path"] == "d/c.png"
    assert row["text"] == "örnek metin"


def test_parse_get_row_missing_keys_use_defaults():
    row = parse_get_row({}, "")
    assert row["name"] == "?"
    assert row["image_kind"] == ""
    assert row["image_path"] == ""