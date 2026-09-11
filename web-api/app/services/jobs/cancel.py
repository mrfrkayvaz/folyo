import asyncio


class EmbeddingCancelled(Exception):
    pass


_cancel_events: dict[str, asyncio.Event] = {}


def request_cancel(document_id: str) -> None:
    _cancel_events.setdefault(document_id, asyncio.Event()).set()


async def is_cancelled(document_id: str) -> bool:
    ev = _cancel_events.get(document_id)
    return bool(ev and ev.is_set())


def clear(document_id: str) -> None:
    _cancel_events.pop(document_id, None)