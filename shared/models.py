"""Ortak SQLModel şemaları — üç servis aynı Postgres'i okur/yazar; tablo tanımları tek yerdedir.

Şema DDL'si (migration) panel-api'de yaşar; bu modül yalnızca runtime model tanımlarıdır.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from .core.constants import DEFAULT_WORKSPACE_NAME
from .core.enums import ChatRole, DocumentStatus, EmbeddingStatus, UserType


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


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str = Field(default="", index=True, unique=True)
    password_hash: str = Field(default="", sa_column=Column(Text, nullable=False))
    user_type: UserType = Field(
        default=UserType.user,
        sa_column=Column(Enum(UserType, name="user_type"), nullable=False),
    )
    created_at: datetime = Field(default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class DocumentLog(SQLModel, table=True):
    """Doküman bazlı işlem günlüğü — web-api/worker kilit adımlarını kaydeder; panel okur."""

    __tablename__ = "document_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    workspace_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    # info | warning | error (panel Loglar sekmesinde rozet rengi buna göre)
    level: str = Field(default="info", sa_column=Column(Text, nullable=False))
    scope: str = Field(default="", sa_column=Column(Text, nullable=False))
    message: str = Field(default="", sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(
        default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )


class QaLog(SQLModel, table=True):
    """Cevap (QA) üretim günlüğü — her sahne one row; panel 'Loglar' görünümünde okunur.

    Amaç: canlıda 'cevap gelmedi / hata oluştu' durumlarında pipeline'ın hangi
    aşamada koptuğunu görmek. Tam yanıt/metin SAKLANMAZ — yalnızca olaylar.
    """

    __tablename__ = "qa_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    message_id: uuid.UUID | None = Field(
        sa_column=Column(
            ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=True, index=True
        )
    )
    level: str = Field(default="info", sa_column=Column(Text, nullable=False))
    stage: str = Field(default="", sa_column=Column(Text, nullable=False))
    message: str = Field(default="", sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(
        default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )


__all__ = [
    "Workspace",
    "Document",
    "EmbeddingJob",
    "DocumentQuestion",
    "ChatMessage",
    "User",
    "DocumentLog",
    "QaLog",
]