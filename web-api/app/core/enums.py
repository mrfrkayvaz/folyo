import enum


class DocumentStatus(str, enum.Enum):
    uploading = "uploading"
    pending = "pending"
    embedding = "embedding"
    embedded = "embedded"
    failed = "failed"
    cancelled = "cancelled"


class EmbeddingStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ChatRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class ContentType(str, enum.Enum):
    text = "text"
    table = "table"
    ocr_text = "ocr_text"
    image = "image"
    code = "code"


class ImageKind(str, enum.Enum):
    """Görsel chunk'ının metadata detayı — chunk tipi her zaman `image`'dır."""

    image_caption = "image_caption"
    diagram = "diagram"
    form_data = "form_data"
    scanned_page = "scanned_page"


class SummaryStatus(str, enum.Enum):
    pending = "pending"
    done = "done"
    failed = "failed"