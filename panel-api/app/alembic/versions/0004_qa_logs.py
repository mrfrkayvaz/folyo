"""qa_logs tablosu — cevap (QA) üretim sahne günlükleri (panel "Loglar" görünümü).

web-api'nin QA pipeline'ı her aşamada (ismeğil → retrieval → guard → bağlam →
LLM akışı → sonuç) tek satır yazar; panel-api pagination'lı okur. Tam yanıt
metni saklanmaz — yalnızca olaylar. `chat_messages.id` silinince CASCADE.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "qa_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_messages.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("level", sa.Text(), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_qa_logs_workspace_id", "qa_logs", ["workspace_id"])
    op.create_index("ix_qa_logs_message_id", "qa_logs", ["message_id"])
    op.create_index("ix_qa_logs_created_at", "qa_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_qa_logs_created_at", table_name="qa_logs")
    op.drop_index("ix_qa_logs_message_id", table_name="qa_logs")
    op.drop_index("ix_qa_logs_workspace_id", table_name="qa_logs")
    op.drop_table("qa_logs")