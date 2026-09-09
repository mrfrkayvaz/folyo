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
