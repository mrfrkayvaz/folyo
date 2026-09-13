"""Workspace özeti planlama sınırı — web-api (API) tarafından da tetiklenir.

Görev gövdesi (`do_workspace_summary`) ayrı `worker_app` servisinde çalışır; bu
fonksiyon yalnızca ARQ kuyruğuna ertelenmiş görevi bırakır (API ve worker ortak).
"""

import uuid

from ...core.logging import get_logger
from ...core.taskq import enqueue as taskq_enqueue

LOG = get_logger("jobs.schedule")


async def schedule_workspace_summary(workspace_id: uuid.UUID) -> None:
    """Workspace özeti görevini 2 sn ertelenmiş kuyruğa bırakır (arq `_defer_by`)."""
    try:
        await taskq_enqueue("workspace_summary", str(workspace_id), _defer_by=2)
    except Exception as exc:
        LOG.warning("[schedule] workspace özeti kuyruğa atılamadı: %s", exc)