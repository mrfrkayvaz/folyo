"""shared.services.jobs.cancel — embed iptal olayları (asyncio.Event tabanlı)."""

import pytest

from shared.services.jobs import cancel


@pytest.mark.anyio
async def test_unknown_document_not_cancelled():
    assert await cancel.is_cancelled("yok") is False


@pytest.mark.anyio
async def test_request_cancel_then_is_cancelled():
    cancel.request_cancel("doc-1")
    assert await cancel.is_cancelled("doc-1") is True
    cancel.clear("doc-1")  # temizlik


@pytest.mark.anyio
async def test_clear_resets_state():
    cancel.request_cancel("doc-1")
    cancel.clear("doc-1")
    assert await cancel.is_cancelled("doc-1") is False


@pytest.mark.anyio
async def test_documents_are_independent():
    cancel.request_cancel("doc-a")
    assert await cancel.is_cancelled("doc-a") is True
    assert await cancel.is_cancelled("doc-b") is False
    cancel.clear("doc-a")


@pytest.mark.anyio
async def test_clear_unknown_is_silent():
    cancel.clear("hic-yok")  # hata fırlatmamalı