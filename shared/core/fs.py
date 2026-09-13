"""Event loop dışına taşınan bloklayıcı dosya işlemleri.

`shutil.rmtree` / büyük `write_bytes` / `read_bytes` eşzamanlı sürer ve event loop'u
kilitleyebilir. Tümü iş parçacığına taşınır (`anyio.to_thread` — BM25 rebuild ile
aynı desen); çağıranlar `await` eder, döngü serbest kalır.
"""

import shutil
from pathlib import Path
from typing import Union

import anyio


async def rmtree_ignore(path: Union[str, Path]) -> None:
    """Dizin + içeriğini siler; yoksa/yazılamıyorsa sessizce geçer."""
    await anyio.to_thread.run_sync(shutil.rmtree, str(path), True)


async def write_bytes(path: Union[str, Path], data: bytes) -> None:
    """Dosyaya bayt yazar; üst dizin yoksa oluşturur (forEach path)."""
    await anyio.to_thread.run_sync(_write, path, data)


def _write(path, data: bytes) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


async def read_bytes(path: Union[str, Path]) -> bytes:
    """Dosya içeriğini okur."""
    return await anyio.to_thread.run_sync(_read, path)


def _read(path) -> bytes:
    return Path(path).read_bytes()