"""Dosya yükleme — istek gövdesini diske akışla yazar, boyut doğrular."""

from dataclasses import dataclass

from fastapi import Request


@dataclass
class UploadResult:
    aborted: bool = False
    incomplete: bool = False


async def stream_to_disk(request: Request, path, expected_size: int) -> UploadResult:
    received = 0
    aborted = False
    try:
        with open(path, "wb") as f:
            async for chunk in request.stream():
                f.write(chunk)
                received += len(chunk)
                if expected_size and received > expected_size:
                    aborted = True
                    break
    except Exception:
        aborted = True
    incomplete = expected_size and received < expected_size
    return UploadResult(aborted=aborted, incomplete=incomplete)