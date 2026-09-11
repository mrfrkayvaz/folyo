import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from .core.constants import DEFAULT_WORKSPACE_NAME
from .core.enums import ChatRole, DocumentStatus, EmbeddingStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Workspace(SQLModel, table=True):
    __tablename__ = "workspaces"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(default=DEFAULT_WORKSPACE_NAME, index=True)
    summary: str | None = Field(default=None, sa_column=Column(Text))
    summary_docs: list | None = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    filename: str = Field(default="")
    file_type: str = Field(default="")
    size: int = Field(default=0)
    status: DocumentStatus = Field(
        default=DocumentStatus.uploading,
        sa_column=Column(Enum(DocumentStatus, name="document_status"), nullable=False),
    )
    chunk_count: int = Field(default=0)
    error: str | None = Field(default=None)
    summary: str | None = Field(default=None, sa_column=Column(Text))
    summary_status: str | None = Field(default=None, sa_column=Column(Text))
    summary_error: str | None = Field(default=None, sa_column=Column(Text))
    stats: dict | None = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class DocumentQuestion(SQLModel, table=True):
    __tablename__ = "document_questions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    question: str = Field(default="")
    position: int = Field(default=0)
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class EmbeddingJob(SQLModel, table=True):
    __tablename__ = "embeddings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
        )
    )
    status: EmbeddingStatus = Field(
        default=EmbeddingStatus.pending,
        sa_column=Column(Enum(EmbeddingStatus, name="embedding_status"), nullable=False),
    )
    chunks: int | None = Field(default=None)
    dim: int | None = Field(default=None)
    progress: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    error: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    role: ChatRole = Field(
        sa_column=Column(Enum(ChatRole, name="chat_role"), nullable=False),
    )
    content: str = Field(default="")
    citations: list | None = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


__all__ = [
    "Workspace",
    "Document",
    "EmbeddingJob",
    "DocumentQuestion",
    "ChatMessage",
]