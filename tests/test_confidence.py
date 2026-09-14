"""confidence_score — güven skoru kalibrasyonu (varlık-ödüllü, dense doyumu 0.60).

Canlı kullanıcı örneği (09-14): dense 0.448 + bm25 0 → eski (max=0.70) 58/dolaylı;
yeni (max=0.60) 69/orta. Amaç: tek-kanal güçlü dense, bm25 sıfırken bile doyuma
ulaşabilsin; 'varlık' (kesişim) kredisi bm25 gücünden bağımsız kalsın.
"""

from types import SimpleNamespace

import pytest

from shared.core import config as shared_config

# `app.services.rag` import'u `shared.services.embeddings`'i tetikler; embeddings
# modül-top-level'da get_settings() okur — app import'undan ÖNCE minimal bind.
shared_config.bind(SimpleNamespace(embed_max_concurrency=4))

from app.services.rag.retrieval import confidence_score  # noqa: E402


def _settings(**over):
    base = dict(
        confidence_dense_min=0.15,
        confidence_dense_max=0.60,   # yeni kalibrasyon (eski: 0.70)
        confidence_bm25_sat=5.0,
        confidence_path_dense_norm=92.0,
        confidence_path_bm25_norm=64.0,
        confidence_path_kind_bonus=8.0,
        confidence_dense_blind_floor=74.0,
        confidence_min_answered=55.0,
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_kullanici_ornegine_dense_468_bm25_0():
    """Canlı örnek: 0.448/0 → 69 'orta' (eski kalibrasyonda 58 'dolaylı' idi)."""
    s = _settings()
    conf, level = confidence_score(top_dense=0.448, top_bm25=0.0, qualifying=5, context_k=5, settings=s)
    assert conf == 69
    assert level == "orta"


def test_strong_dense_alone_reaches_saturation():
    """Dense 0.60+ tek kanalda (bm25 0) doyuma ulaşıp 'yüksek' alabilir."""
    s = _settings()
    conf, level = confidence_score(top_dense=0.62, top_bm25=0.0, qualifying=5, context_k=5, settings=s)
    assert conf >= 85
    assert level == "yüksek"


def test_strong_bm25_alone_gets_high():
    """BM25 güçlüyken (dense yok) bm25 yolu 'yüksek' üretebilir (varlık kredisiyle)."""
    s = _settings()
    conf, level = confidence_score(top_dense=0.0, top_bm25=9.0, qualifying=5, context_k=5, settings=s)
    assert conf >= 85
    assert level == "yüksek"


def test_consensus_credit_independent_of_bm25_strength():
    """Kesişim (c) kredisi bm25'in GÜCÜNE değil VARLIĞINA bağlıdır:
    bm25=0 ile bm25=3 aynı qualifying'de benzer dense-yolu üretir (dense baskınken)."""
    s = _settings()
    c0, _ = confidence_score(top_dense=0.5, top_bm25=0.0, qualifying=5, context_k=5, settings=s)
    c3, _ = confidence_score(top_dense=0.5, top_bm25=3.0, qualifying=5, context_k=5, settings=s)
    # dense yolu belirleyiciyken bm25'in küçük farkı rozet seviyesini değiştirmemeli
    assert abs(c0 - c3) <= 8


def test_weak_dense_still_floors_at_min_answered():
    """Guard'ı geçen ama zayıf dense (0.2) 'yetersiz'e inemez — min_answered tabanı (55)."""
    s = _settings()
    conf, level = confidence_score(top_dense=0.2, top_bm25=0.0, qualifying=4, context_k=5, settings=s)
    assert conf == 55
    assert level == "dolaylı"


def test_parameter_driven_bands():
    """Doyum parametresi skoru yönlendirir (özelleştirme testi)."""
    s_loose = _settings(confidence_dense_max=0.70)   # eski geniş bant
    s_tight = _settings(confidence_dense_max=0.50)   # dar bant
    c_loose, _ = confidence_score(top_dense=0.448, top_bm25=0.0, qualifying=5, context_k=5, settings=s_loose)
    c_tight, _ = confidence_score(top_dense=0.448, top_bm25=0.0, qualifying=5, context_k=5, settings=s_tight)
    assert c_tight > c_loose
    assert c_loose == 58  # eski kalibrasyonun ürettiği değer — regresyon bekçisi