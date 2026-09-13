"""shared.services.paths — depolama dizini çözümü (web-api + worker ortak)."""

import uuid
from pathlib import Path

from shared.services.paths import storage_dir


def test_storage_dir_uses_bound_settings(bind_settings, tmp_path):
    bind_settings(storage_dir=str(tmp_path))
    did = uuid.uuid4()
    assert storage_dir(did) == Path(tmp_path) / str(did)


def test_storage_dir_roundtrip_through_uuid(bind_settings, tmp_path):
    bind_settings(storage_dir=str(tmp_path))
    did = uuid.uuid4()
    d = storage_dir(did)
    assert d.name == str(did)
    assert d.parent == Path(tmp_path)