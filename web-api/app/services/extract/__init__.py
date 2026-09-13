"""web-api tarafı yalnızca dosya türü allowlist'ini kullanır.

Ayrıştırma (extract) gövdesi ayrı `worker_app.services.extract` paketinde yaşar;
burada yalnızca upload ön-doğrulamasının ihtiyaç duyduğu `SUPPORTED_EXTS` kalır
(kaynak gerçeği: `app/services/extract/constants.py`).
"""

from shared.services.extract.constants import SUPPORTED_EXTS

__all__ = ["SUPPORTED_EXTS"]