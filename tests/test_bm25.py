"""shared.services.bm25 — Türkçe uyumlu tokenizer + BM25Okapi skorlaması.

Odak: Unicode/Türkçe diakritikler, bileşik kelime ayrıştırma, hafif kök (prefix)
eşleşmesi ve tf-idf normalizasyonu. Tamamen saf matematik — dış bağımlılık yok.
"""

import pytest

from shared.services.bm25 import BM25Okapi, tokenize_text


# ── tokenizer ──────────────────────────────────────────────────────────────

def test_tokenize_empty():
    assert tokenize_text("") == []
    assert tokenize_text(None) == []


def test_tokenize_handles_turkish_I_mapping():
    # İ noktalı → i; I noktasız → ı (birleşik üst nokta üretilmemeli, kelime bölünmemeli)
    assert tokenize_text("İSTANBUL") == ["istanbul"]
    assert tokenize_text("ÇEVİRMELİYİM") == ["çevirmeliyim"]
    assert tokenize_text("ILIK") == ["ılık"]
    assert tokenize_text("İLIK") == ["ilık"]  # İ→i, I→ı (Türkçe ayrım korunur)


def test_tokenize_ascii_query_matches_i_doc():
    # Kullanıcı "ismet" yazar (ascii i), dokümanda "İsmet" → ikisi de "ismet"
    assert tokenize_text("İsmet") == ["ismet"]
    assert tokenize_text("ismet") == ["ismet"]


def test_tokenize_keeps_diacritics():
    toks = tokenize_text("ç ş ğ ö ü ı Ç Ş Ğ Ö Ü İ")
    for expected in ("ç", "ş", "ğ", "ö", "ü", "ı"):
        assert expected in toks


def test_tokenize_splits_compounds():
    toks = tokenize_text("fatura-no abc_def a/b c.d")
    assert "fatura-no" in toks
    assert "fatura" in toks
    assert "no" in toks
    assert "abc" in toks
    assert "def" in toks


def test_tokenize_apostrophe_is_separator():
    toks = tokenize_text("Ali'nin")
    assert "'" not in "".join(toks)
    assert set(toks) == {"ali", "nin"}



def test_empty_corpus_safe():
    idx = BM25Okapi([])
    assert idx.corpus_size == 0
    assert idx.get_scores("bir şey") == []


def test_exact_match_ranks_first():
    idx = BM25Okapi(["kırmızı elma ağacı", "mavi gökyüzü", "sarı limon"])
    scores = idx.get_scores("elma")
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]


def test_term_frequency_monotonic():
    idx = BM25Okapi(["a b c elma", "elma elma elma x", "farklı konu"])
    scores = idx.get_scores("elma")
    assert scores[1] > scores[0]  # 3x tekrarlı > 1x


def test_length_normalization_prefers_short():
    short = "elma"
    long_doc = "elma " + "dolgu " * 49
    idx = BM25Okapi([long_doc, short])
    scores = idx.get_scores("elma")
    assert scores[1] > scores[0]  # kısa belge aynı tf ile daha yüksek


def test_rare_term_idf_outranks_frequent():
    idx = BM25Okapi(["elma", "elma", "elma", "muz x"])
    scores = idx.get_scores("muz")
    assert scores[3] > idx.get_scores("elma")[3]


def test_stem_prefix_matches_suffix_variants():
    # "çevirmeliyim" ile "çevirmelisiniz" aynı köke (çevi) sahip — prefix eşleşmesi
    idx = BM25Okapi(["çevirmelisiniz mi", "tamamen alakasız konu"])
    scores = idx.get_scores("çevirmeliyim")
    assert scores[0] > 0.0
    assert scores[1] == 0.0


def test_exact_term_dominates_by_tf():
    # Aynı kökten iki terim: tam eşleşme 2× tekrarlanınca prefix-only eşleşmeyi geçer
    idx = BM25Okapi(["çevirme çevirme nedir", "çevirmelisiniz artık"])
    s_exact, s_prefix = idx.get_scores("çevirme")
    assert s_exact > 0.0 and s_prefix > 0.0
    assert s_exact > s_prefix  # daha yüksek tf → daha yüksek skor


def test_stem_cap_limits_prefix_matches(bind_settings):
    bind_settings()
    corpus = [f"kelime{i}" for i in range(30)]  # hepsi "kelime" önekini paylaşır
    idx = BM25Okapi(corpus, stem_min=4, stem_cap=5)
    terms = idx._matched_terms("kelime")  # exact yok → en çok 5 önekli terim
    assert len(terms) == 5


def test_stem_cap_with_exact_match(bind_settings):
    bind_settings()
    corpus = [f"kelime{i}" for i in range(30)]
    idx = BM25Okapi(corpus, stem_min=4, stem_cap=5)
    terms = idx._matched_terms("kelime3")  # exact 1 + 4 önekli = 5
    assert len(terms) == 5
    assert "kelime3" in terms


def test_stem_cap_default_24():
    corpus = [f"kelime{i}" for i in range(40)]
    idx = BM25Okapi(corpus, stem_min=4)
    terms = idx._matched_terms("kelime")
    assert len(terms) == 24  # varsayılan cap: 24 önekli terim


@pytest.mark.parametrize("k1,b", [(1.5, 0.75), (2.0, 0.5), (0.5, 1.0)])
def test_params_accepted(k1, b):
    idx = BM25Okapi(["a b", "a a c"], k1=k1, b=b)
    assert idx.k1 == k1
    assert idx.b == b
    assert len(idx.get_scores("a")) == 2


def test_short_query_returns_zero_scores():
    idx = BM25Okapi(["bir metin vardı", "başka metin"])
    assert idx.get_scores("") == [0.0, 0.0]
    assert idx.get_scores("   ") == [0.0, 0.0]