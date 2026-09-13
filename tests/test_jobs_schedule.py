"""shared.services.jobs.schedule — workspace özeti planlama (kuyruğa atma)."""

import uuid

import pytest

from shared.services.jobs import schedule


@pytest.mark.anyio
async def test_schedule_enqueues_deferred_job(monkeypatch):
    calls = []

    async def fake_enqueue(name, *args, **kwargs):
        calls.append((name, args, kwargs))

    monkeypatch.setattr(schedule, "taskq_enqueue", fake_enqueue)

    wid = uuid.uuid4()
    await schedule.schedule_workspace_summary(wid)

    assert len(calls) == 1
    name, (arg,), kwargs = calls[0]
    assert name == "workspace_summary"
    assert arg == str(wid)
    assert kwargs["_defer_by"] == 2  # 2 sn ertelenmiş


@pytest.mark.anyio
async def test_schedule_swallows_enqueue_failure(monkeypatch):
    async def broken_enqueue(*a, **kw):
        raise RuntimeError("redis kapalı")

    monkeypatch.setattr(schedule, "taskq_enqueue", broken_enqueue)

    # Hata çağırana fırlatılmaz — loglanır (idempotent recover sonra halleder)
    await schedule.schedule_workspace_summary(uuid.uuid4())