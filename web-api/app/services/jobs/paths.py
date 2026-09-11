import uuid
from pathlib import Path

from ...core.config import get_settings


def storage_dir(document_id: uuid.UUID) -> Path:
    return Path(get_settings().storage_dir) / str(document_id)