"""Panel-api test kurulumu — ayrı ortam:

    cd panel-api && uv run --no-sync pytest tests -q

Panel ve web-api aynı `app` paket adını kullandığı için bu suite'te
panel-api/app sys.path'te ÖNCELİKLİ olmalı (web-api suite'inden bağımsız süreç).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # repo kökü
for _p in (str(ROOT / "panel-api"), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402


@pytest.fixture
def anyio_backend():
    return "asyncio"