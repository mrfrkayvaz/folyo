"""initial schema baseline

Canlı kurulumların şeması eski `create_all + ALTER` ile yaratıldığından bu
migration `upgrade` yerine `stamp` ile işaretlenir (init_db, tablolar zaten
varsa başlığa `stamp head` atar); boş DB'lerde `upgrade head` şemayı kurar.

Revision ID: 0001
Revises:
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE document_status AS ENUM "
        "('uploading','pending','embedding','embedded','failed','cancelled')"
    )
    op.execute(
        "CREATE TYPE embedding_status AS ENUM "
        "('pending','running','completed','failed','cancelled')"
    )
    op.execute("CREATE TYPE chat_role AS ENUM ('user','assistant')")

    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("summary_docs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workspaces_name", "workspaces", ["name"])

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_type", sa.String(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "uploading", "pending", "embedding", "embedded", "failed", "cancelled",
                name="document_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("summary_status", sa.Text(), nullable=True),
        sa.Column("summary_error", sa.Text(), nullable=True),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"],
            name="documents_workspace_id_fkey", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_documents_workspace_id", "documents", ["workspace_id"])

    op.create_table(
        "document_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"],
            name="document_questions_document_id_fkey", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_document_questions_document_id", "document_questions", ["document_id"])

    # ── embeddings ──
    op.create_table(
        "embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending", "running", "completed", "failed", "cancelled",
                name="embedding_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("chunks", sa.Integer(), nullable=True),
        sa.Column("dim", sa.Integer(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"],
            name="embeddings_document_id_fkey", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_embeddings_document_id", "embeddings", ["document_id"], unique=True)

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("user", "assistant", name="chat_role", create_type=False),
            nullable=False,
        ),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"],
            name="chat_messages_workspace_id_fkey", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_chat_messages_workspace_id", "chat_messages", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("embeddings")
    op.drop_table("document_questions")
    op.drop_table("documents")
    op.drop_table("workspaces")
    op.execute("DROP TYPE IF EXISTS chat_role")
    op.execute("DROP TYPE IF EXISTS embedding_status")
    op.execute("DROP TYPE IF EXISTS document_status")