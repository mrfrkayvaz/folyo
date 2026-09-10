import math
import re


def tokenize_text(text: str) -> list[str]:
    if not text:
        return []
    cleaned = text.lower()
    compounds = re.findall(r"[a-z0-9_]+(?:[-./][a-z0-9_]+)*", cleaned)
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
    def __init__(self, corpus: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
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

    def _calc_idf(self) -> None:
        n = self.corpus_size
        for word, freq in self.df.items():
            self.idf[word] = math.log((n - freq + 0.5) / (freq + 0.5) + 1.0)

    def get_scores(self, query: str) -> list[float]:
        q_tokens = tokenize_text(query)
        scores = [0.0] * self.corpus_size
        if not q_tokens or self.corpus_size == 0:
            return scores

        for token in q_tokens:
            if token not in self.idf:
                continue
            idf_val = self.idf[token]
            for i, freqs in enumerate(self.doc_freqs):
                tf = freqs.get(token, 0)
                if tf == 0:
                    continue
                num = tf * (self.k1 + 1)
                denom = tf + self.k1 * (1 - self.b + self.b * (self.doc_len[i] / self.avgdl))
                scores[i] += idf_val * (num / denom)

        return scores
