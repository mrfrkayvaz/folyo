from dataclasses import dataclass, field

BBox = tuple[float, float, float, float]


@dataclass
class Segment:
    content_type: str
    text: str
    page_number: int
    bbox: list[BBox] = field(default_factory=list)
    order: int = 0
    page_context: str = ""
    breadcrumbs: list[str] = field(default_factory=list)
    image_path: str = ""
    image_kind: str = ""


@dataclass
class Chunk:
    text: str
    content_type: str
    page_number: int
    page_context: str
    chunk_index: int
    bbox: list[BBox] = field(default_factory=list)
    breadcrumbs: list[str] = field(default_factory=list)
    image_path: str = ""
    image_kind: str = ""
    # Embed/gösterim ayrımı: `embed_text` breadcrumb ön eki İÇERMEZ (gürültüsüz vektör);
    # `text` gösterim/LLM bağlamı için ön ekli halini korur.
    embed_text: str = ""