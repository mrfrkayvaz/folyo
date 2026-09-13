"""Worker test kurulumu — ayrı ortam:

    cd worker && uv run --no-sync pytest tests -q

Worker testleri worker venv'inde çalışır (pytesseract/pymupdf/pillow burada).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # repo kökü
for _p in (str(ROOT / "worker"), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402


@pytest.fixture
def anyio_backend():
    return "asyncio"