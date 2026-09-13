"""shared.core.fs — bloklayıcı dosya işlemlerinin thread havuzu sarmalayıcıları."""

import pytest

from shared.core import fs


@pytest.mark.anyio
async def test_write_bytes_creates_parent_dirs(tmp_path):
    target = tmp_path / "a" / "b" / "f.txt"
    await fs.write_bytes(target, b"hello")
    assert target.read_bytes() == b"hello"


@pytest.mark.anyio
async def test_read_bytes_roundtrip(tmp_path):
    target = tmp_path / "f.bin"
    target.write_bytes(b"\x00\x01\xff")
    assert await fs.read_bytes(target) == b"\x00\x01\xff"


@pytest.mark.anyio
async def test_rmtree_ignore_removes_dir(tmp_path):
    d = tmp_path / "x"
    (d / "deep").mkdir(parents=True)
    (d / "deep" / "f").write_text("a")
    await fs.rmtree_ignore(d)
    assert not d.exists()


@pytest.mark.anyio
async def test_rmtree_ignore_missing_is_silent(tmp_path):
    await fs.rmtree_ignore(tmp_path / "yok")  # hata fırlatmamalı


@pytest.mark.anyio
async def test_write_bytes_overwrites(tmp_path):
    target = tmp_path / "f.txt"
    await fs.write_bytes(target, b"v1")
    await fs.write_bytes(target, b"v2")
    assert target.read_bytes() == b"v2"