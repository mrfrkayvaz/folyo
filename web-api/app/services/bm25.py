r"""Saf Python BM25Okapi — Türkçe uyumlu tokenizer + hafif kök (prefix) eşleşmesi.

Sorun (canlı doğrulandı): eski tokenizer `[a-z0-9_]+` ASCII yalnızca harfleriydi —
Türkçe `ç ş ğ ö ü ı` token'lardan düşüyor, "çıktığında" → `kt` + `nda` gibi
parçalanıyordu; "çevirmeliyim" ile "çevirmelisiniz" asla eşleşmiyordu.

Çözüm:
- Tokenizer Unicode: `[\w]+` — Türkçe diakritikler korunur.
- Hafif kök eşleşmesi: sorgu token'inin ilk `stem_min` karakteri, indeksteki
  aynı ön-ekli terimleri de eşleştirir (sınırlı: `stem_cap`). Sonek değişkenliği
  (çevirmeli-çevirmelisiniz, kabarcık-kabarcıklar) yakalanır; tam eşleşme baskın kalır.
"""

import math
import re

_WORD_RE = re.compile(r"[\w]+(?:[-./][\w]+)*")


def tokenize_text(text: str) -> list[str]:
    r"""Metni küçük harfe indirip Unicode kelime token'larına böler.

    `text.lower()` Python yerelinden bağımsız Unicode küçültme kullanır
    (İ → i, I → ı doğru çözülür); `\w` Unicode harfleri (çşğöüı dahil),
    rakamları ve alt çizgiyi kapsar. Kesme işareti ve noktalama ayraçtır.
    """
    if not text:
        return []
    cleaned = text.lower()
    compounds = _WORD_RE.findall(cleaned)
    tokens: list[str] = []
    for token in compounds:
        tokens.append(token)
        sub_parts = re.split(r"[-./_]+", token)
        if len(sub_parts) > 1:
            for part in sub_parts:
                if part and part != token:
                    tokens.append(part)
    return tokens


class BM25Okapi:
    def __init__(
        self,
        corpus: list[str],
        k1: float = 1.5,
        b: float = 0.75,
        stem_min: int = 4,
        stem_cap: int = 24,
    ):
        self.k1 = k1
        self.b = b
        self.stem_min = max(2, int(stem_min))
        self.stem_cap = max(1, int(stem_cap))
        self.corpus_size = len(corpus)
        self.doc_len: list[int] = []
        self.doc_freqs: list[dict[str, int]] = []
        self.df: dict[str, int] = {}
        self.idf: dict[str, float] = {}

        total_len = 0
        for doc in corpus:
            tokens = tokenize_text(doc)
            length = len(tokens)
            self.doc_len.append(length)
            total_len += length

            freqs: dict[str, int] = {}
            for t in tokens:
                freqs[t] = freqs.get(t, 0) + 1
            self.doc_freqs.append(freqs)

            for t in freqs:
                self.df[t] = self.df.get(t, 0) + 1

        self.avgdl = (total_len / self.corpus_size) if self.corpus_size > 0 else 1.0
        self._calc_idf()
        self._build_prefix()

    def _calc_idf(self) -> None:
        n = self.corpus_size
        for word, freq in self.df.items():
            self.idf[word] = math.log((n - freq + 0.5) / (freq + 0.5) + 1.0)

    def _build_prefix(self) -> None:
        """İndeks terimlerinin ön-ek dizini (köklü eşleşme için)."""
        pref: dict[str, list[str]] = {}
        for term in self.idf:
            if len(term) >= self.stem_min:
                pref.setdefault(term[: self.stem_min], []).append(term)
        self._prefix = pref

    def _matched_terms(self, token: str) -> list[str]:
        """Bir sorgu token'ine karşılık gelen indeks terimleri: tam + aynı ön-ekliler."""
        terms: list[str] = []
        if token in self.idf:
            terms.append(token)
        if len(token) >= self.stem_min:
            cand = self._prefix.get(token[: self.stem_min])
            if cand:
                for t in cand:
                    if t != token and len(terms) < self.stem_cap:
                        terms.append(t)
        return terms

    def get_scores(self, query: str) -> list[float]:
        q_tokens = tokenize_text(query)
        scores = [0.0] * self.corpus_size
        if not q_tokens or self.corpus_size == 0:
            return scores

        for token in q_tokens:
            for term in self._matched_terms(token):
                if term not in self.idf:
                    continue
                idf_val = self.idf[term]
                for i, freqs in enumerate(self.doc_freqs):
                    tf = freqs.get(term, 0)
                    if tf == 0:
                        continue
                    num = tf * (self.k1 + 1)
                    denom = tf + self.k1 * (1 - self.b + self.b * (self.doc_len[i] / self.avgdl))
                    scores[i] += idf_val * (num / denom)

        return scores