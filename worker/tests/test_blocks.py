"""worker extract.blocks — PyMuPDF bloğundan metin/kod/tablo item toplama.

Saf geometri/metin kuralları; gerçek PDF veya OCR yok. `page_width=0` ile denklem
dallanması atlanır (equations modülüne dokunulmaz → atomik kalır).
"""

from worker_app.services.extract import blocks


def _span(text: str, size: float = 12.0, font: str = "Helvetica", flags: int = 0) -> dict:
    return {"text": text, "size": size, "font": font, "flags": flags}


def _line(*spans) -> dict:
    return {"spans": list(spans)}


def _block(box, lines, type_: int = 0) -> dict:
    return {"bbox": box, "lines": lines, "type": type_}


class FakeTable:
    def __init__(self, bbox, rows):
        self.bbox = bbox
        self._rows = rows

    def extract(self):
        return self._rows


# ── _text_item ────────────────────────────────────────────────────────────

def test_text_item_outside_y_band_is_none():
    b = _block((0, 100, 100, 120), [_line(_span("alt"))])
    assert blocks._text_item(b, top=0, bottom=50, table_list=[]) is None


def test_text_item_empty_text_is_none():
    b = _block((0, 0, 100, 20), [_line(_span("   ")), _line(_span(""))])
    assert blocks._text_item(b, 0, 100, []) is None


def test_text_item_joins_lines_and_keeps_bbox():
    b = _block(
        (1.0, 2.0, 3.0, 4.0),
        [_line(_span("ilk")), _line(_span("satır", size=14.0))],
    )
    item = blocks._text_item(b, 0, 100, [])
    assert item["kind"] == "text"
    assert item["text"] == "ilk\nsatır"
    assert item["bbox"] == (1.0, 2.0, 3.0, 4.0)
    assert item["size"] == 14.0
    assert item["bold"] is False


def test_text_item_detects_bold_via_flags():
    bold_flags = 16
    b = _block((0, 0, 50, 20), [_line(_span("kalın", flags=bold_flags))])
    item = blocks._text_item(b, 0, 100, [])
    assert item["bold"] is True
    assert item["lines"][0]["bold"] is True


def test_code_block_majority_mono_font_is_code():
    mono = lambda t: _span(t, font="Courrier-Bold")  # noqa: E731
    b = _block((0, 0, 50, 20), [_line(mono("def")), _line(mono("x")), _line(_span("not mono"))])
    item = blocks._text_item(b, 0, 100, [])
    assert item["kind"] == "code"
    assert item["text"] == "```\ndef\nx\nnot mono\n```"
    assert item["ctype"] == "code"


def test_minority_mono_font_is_text():
    mono = lambda t: _span(t, font="Consolas")  # noqa: E731
    b = _block((0, 0, 50, 20), [_line(mono("bir")), _line(_span("iki")), _line(_span("üç"))])
    item = blocks._text_item(b, 0, 100, [])
    assert item["kind"] == "text"
    assert "```" not in item["text"]


def test_skip_set_removes_band_header():
    b = _block((0, 0, 100, 10), [_line(_span("Rapor 2026"))])
    assert (
        blocks._text_item(
            b, 0, 100, [], skip={"rapor 2026"}, skip_top=50, skip_bottom=float("inf")
        )
        is None
    )


def test_skip_band_outside_is_kept():
    b = _block((0, 200, 100, 210), [_line(_span("Rapor 2026"))])
    item = blocks._text_item(
        b, 0, 300, [], skip={"rapor 2026"}, skip_top=50, skip_bottom=float("inf")
    )
    assert item is not None  # y-band dışındaki blok budama dışı kalır


def test_overlapping_table_text_is_skipped():
    b = _block((0.0, 0.0, 12.0, 12.0), [_line(_span("tablo metni"))])
    t = FakeTable((0.0, 0.0, 10.0, 10.0), [])
    assert blocks._text_item(b, 0, 100, [t]) is None


def test_slight_table_overlap_is_kept():
    b = _block((0.0, 0.0, 10.0, 10.0), [_line(_span("kenar metni"))])
    t = FakeTable((5.0, 5.0, 15.0, 15.0), [])  # %25 örtüşme
    assert blocks._text_item(b, 0, 100, [t]) is not None


# ── overlaps_table ────────────────────────────────────────────────────────

def test_overlaps_table_zero_area_bbox():
    t = FakeTable((0.0, 0.0, 10.0, 10.0), [])
    assert blocks.overlaps_table((5.0, 5.0, 5.0, 5.0), [t]) is False


def test_overlaps_table_half_area():
    t = FakeTable((0.0, 0.0, 10.0, 10.0), [])
    assert blocks.overlaps_table((0.0, 0.0, 10.0, 5.1), [t]) is True  # %51


# ── collect_items ─────────────────────────────────────────────────────────

def test_collect_items_filters_non_text_blocks():
    blocks_in = [
        _block((0, 0, 50, 20), [_line(_span("metin"))], type_=0),
        _block((0, 30, 50, 40), [_line(_span("resim"))], type_=1),  # görsel → atla
        _block((0, 50, 50, 60), [_line(_span("yine metin"))], type_=0),
    ]
    items = blocks.collect_items(blocks_in, [], top=0, bottom=100, page_width=0)
    assert [i["text"] for i in items] == ["metin", "yine metin"]


def test_collect_items_skips_out_of_band():
    blocks_in = [_block((0, 0, 50, 20), [_line(_span("görünür"))])]
    assert blocks.collect_items(blocks_in, [], top=30, bottom=100, page_width=0) == []


def test_collect_items_appends_tables_with_markdown():
    rows_table = FakeTable((0.0, 0.0, 100.0, 50.0), [["Ad", "Yaş"], ["Ali", "30"]])
    items = blocks.collect_items([], [rows_table], top=0, bottom=100, page_width=0)
    assert len(items) == 1
    it = items[0]
    assert it["kind"] == "table"
    assert "|" in it["text"]
    assert "caption" in it
    assert it["ctype"] == "table"


def test_collect_items_empty():
    assert blocks.collect_items([], [], top=0, bottom=100, page_width=0) == []


def test_collect_items_orders_blocks_before_tables():
    # Tablo bloğu metin bloğuyla ÇAKIŞMAMALI (üst üste binen blok elenir)
    txt = _block((0, 0, 50, 20), [_line(_span("metin"))])
    tbl = FakeTable((0.0, 100.0, 100.0, 150.0), [["h1", "h2"], ["v1", "v2"]])
    items = blocks.collect_items([txt], [tbl], top=0, bottom=200, page_width=0)
    assert items[0]["kind"] == "text"
    assert items[-1]["kind"] == "table"