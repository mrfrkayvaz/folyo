"""document_logs tablosu — doküman bazlı işlem günlüğü (panel "Loglar" sekmesi).

web-api (yükleme/iptal/silme) ve worker (embed/özet) süreçlerinin kilit adımları
buraya yazılır; panel-api içerikleri okur. `documents.id` silinince loglar
CASCADE ile temizlenir.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("level", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_document_logs_document_id", "document_logs", ["document_id"])
    op.create_index("ix_document_logs_workspace_id", "document_logs", ["workspace_id"])
    op.create_index("ix_document_logs_created_at", "document_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_document_logs_created_at", table_name="document_logs")
    op.drop_index("ix_document_logs_workspace_id", table_name="document_logs")
    op.drop_index("ix_document_logs_document_id", table_name="document_logs")
    op.drop_table("document_logs")