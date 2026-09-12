"""Uygulama loglama — uvicorn logger'ına bağlanır.

Kurallar:
- Tüm izler `uvicorn.error` taşıyıcı logger'larına yazılır (uvicorn kendi
  handler'larıyla `docker logs`'a akıtır).
- Uvicorn dışında (test/script) root için `basicConfig` fallback'i kurulur —
  kayıtlar daima görünür kalır, çift basılmaz (uvicorn'da root handler yok).

Kullanım: `LOG = get_logger("jobs.recover")`
"""

import logging


def get_logger(scope: str = "app") -> logging.Logger:
    """`uvicorn.error.<scope>` kayıtçısı; uvicorn yoksa root fallback."""
    uvicorn_err = logging.getLogger("uvicorn.error")
    if not uvicorn_err.handlers and not logging.getLogger().handlers:
        # Uvicorn loglama yapılandırmamış: tek seferlik kök fallback.
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)-5.5s [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        )
    return logging.getLogger(f"uvicorn.error.{scope}")