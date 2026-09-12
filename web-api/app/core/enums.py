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
    equation = "equation"


class SummaryStatus(str, enum.Enum):
    pending = "pending"
    done = "done"
    failed = "failed"