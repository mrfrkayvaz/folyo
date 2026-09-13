"""shared.core.enums — durum/rol enum'ları (str tabanlı, DB değerleri)."""

from shared.core.enums import (
    ChatRole,
    ContentType,
    DocumentStatus,
    EmbeddingStatus,
    SummaryStatus,
    UserType,
)


def test_document_status_values():
    assert DocumentStatus.uploading.value == "uploading"
    assert DocumentStatus.pending.value == "pending"
    assert DocumentStatus.embedding.value == "embedding"
    assert DocumentStatus.embedded.value == "embedded"
    assert DocumentStatus.failed.value == "failed"
    assert DocumentStatus.cancelled.value == "cancelled"


def test_document_status_str_is_value():
    # str(member) Python 3.11+ enum adını verir; DB değeri .value'dur
    assert [s.value for s in DocumentStatus] == [
        "uploading", "pending", "embedding", "embedded", "failed", "cancelled",
    ]


def test_embedding_status_flow_values():
    assert [e.value for e in EmbeddingStatus] == [
        "pending", "running", "completed", "failed", "cancelled",
    ]


def test_content_type_values():
    assert [c.value for c in ContentType] == [
        "text", "table", "ocr_text", "image", "code", "equation",
    ]


def test_chat_role_values():
    assert ChatRole.user.value == "user"
    assert ChatRole.assistant.value == "assistant"


def test_summary_status_values():
    assert [s.value for s in SummaryStatus] == ["pending", "done", "failed"]


def test_user_type_values():
    assert UserType.admin.value == "admin"
    assert UserType.user.value == "user"


def test_from_value_string_membership():
    assert "embedded" in {s.value for s in DocumentStatus}
    assert "admin" in {u.value for u in UserType}