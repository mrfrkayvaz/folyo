"""Servis-yapılandırma bağlayıcısı (binder).

Shared modüller hangi serviste çalışırsa o servisin `Settings` nesnesini okur —
her servis kendi yapılandırmasını başlangıçta `bind(get_settings())` ile verir
(ayrı container'larda yaşar → global tek değerdir, çakışma yok). Böylece shared
içinde secret/env kalmamış olur; izolasyon korunur.

Bağlanmamış kullanım açık hata verir ("hangi servisten settings bekleniyor?").
"""

_current = None


def bind(settings) -> None:
    """Çalışan servisin Settings nesnesini kaydeder (başlangıçta bir kez çağrılır)."""
    global _current
    _current = settings


def get_settings():
    if _current is None:
        raise RuntimeError(
            "shared.core.config: settings bind edilmedi — servis başlangıcında "
            "`shared.core.config.bind(get_settings())` çağrılmalı."
        )
    return _current