"""Belge özeti + başlangıç soruları üretimi (rag_arch §4) — tek LLM çağrısı.

Girdi: başlıklar + stratified örnek (ilk/orta/son), ~2500 karakter bütçe.
Çıktı: `{summary, questions}`. Model JSON yerine akıcı metin döndürürse veya
çağrı patlarsa `generate_summary` `None` döndürür → belge `embedded` kalır.
"""

import ast
import json
import re

from ..core.prompts import SUMMARY_PROMPT, WORKSPACE_SUMMARY_PROMPT
from . import llm
from .ai import AIError
from .types import Chunk

_SAMPLE_CHAR_BUDGET = 2500
MAX_QUESTIONS = 6


def build_sample(chunks: list[Chunk]) -> str:
    """Başlıklar + baş/orta/son örneği — çok sayfalı belgede tek sayfaya saplanmaz."""
    headings: list[str] = []
    seen: set[str] = set()
    for c in chunks:
        p = (c.page_context or "").strip()
        if p and p not in seen:
            seen.add(p)
            headings.append(p)
    heading_block = "\n".join(f"- {h}" for h in headings[:12])

    def clip(text: str, n: int = 700) -> str:
        return text[:n] + ("…" if len(text) > n else "")

    parts: list[str] = []
    if heading_block:
        parts.append("BAŞLIKLAR:\n" + heading_block)
    if chunks:
        parts.append("BELGE BAŞI:\n" + clip(chunks[0].text))
        mid = chunks[len(chunks) // 2]
        if mid is not chunks[0] and mid is not chunks[-1]:
            parts.append("BELGE ORTASI:\n" + clip(mid.text))
        if len(chunks) > 1:
            parts.append("BELGE SONU:\n" + clip(chunks[-1].text))
    sample = "\n\n".join(parts)
    return sample[:_SAMPLE_CHAR_BUDGET]


def _try_loads(text: str) -> dict | None:
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except (ValueError, TypeError):
        return None


def _extract_object_region(text: str) -> str | None:
    """İlk `{` ile SON `}` arasındaki bölgeyi döndürür (ön/art yazı tolere)."""
    try:
        start = text.index("{")
        end = text.rindex("}")
    except ValueError:
        return None
    if end <= start:
        return None
    return text[start : end + 1]


def _salvage_fields(text: str) -> dict | None:
    """Tam JSON kurtarılamazsa alan bazlı en iyi çaba (summary/title/questions).

    Modelin özet metni içine kaçışsız `"` koyması gibi durumlarda JSON bozulur;
    burada değer ilk kaçışsız tırnakta kesilir — kısmi ama kullanılabilir özet.
    """
    out: dict = {}

    def unq(s: str) -> str:
        return s.replace('\\"', '"').replace("\\\\", "\\").strip()

    m = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', text, flags=re.DOTALL)
    if m:
        out["summary"] = unq(m.group(1))
    m = re.search(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"', text, flags=re.DOTALL)
    if m:
        out["title"] = unq(m.group(1))
    m = re.search(r'"questions"\s*:\s*\[(.*?)\]', text, flags=re.DOTALL)
    if m:
        out["questions"] = [unq(q) for q in re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))]
    return out or None


def parse_json_blocks(raw: str, *, allow_salvage: bool = True) -> dict | None:
    """Model çıktısından JSON nesnesini kurtarır — çok katmanlı onarım.

    1) Fence/ön-yazı temizliği → ham veya `{...}` bölgesi `json.loads`
    2) `raw_decode` — kuyruk çöpüne rağmen ilk geçerli JSON nesnesi
    3) Python benzeri tek tırnaklı çıktı → `ast.literal_eval`
    4) Hepsi başarısızsa ve `allow_salvage` ise alan bazlı regex kurtarma
       (`summary`/`title`/`questions` — kısmi ama kullanılabilir).
    """
    text = (raw or "").strip()
    if not text:
        return None

    clean = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    clean = re.sub(r"\s*```\s*$", "", clean, flags=re.MULTILINE).strip()

    candidates: list[str] = []
    for src in (clean, text):
        for cand in (src, _extract_object_region(src)):
            if cand is not None and cand not in candidates:
                candidates.append(cand)

    for src in candidates:
        data = _try_loads(src)
        if data is not None:
            return data
        # Kuyrukta ek metin kalmış olabilir → ilk geçerli nesneyi al.
        try:
            decoded, _ = json.JSONDecoder().raw_decode(src.lstrip())
            if isinstance(decoded, dict):
                return decoded
        except (ValueError, json.JSONDecodeError):
            pass
        # Python tarzı tek tırnaklı çıktı: {'summary': '…'}
        try:
            val = ast.literal_eval(src)
            if isinstance(val, dict):
                return val
        except (ValueError, SyntaxError, TypeError):
            pass
    return _salvage_fields(text) if allow_salvage else None


def _strict_nudge() -> str:
    return (
        "Yukarıdaki cevabın JSON ayrıştırılamadı. Yalnızca geçerli JSON döndür; "
        'açıklama, kod çiti veya başlık ekleme: {"summary": "...", "title": "...", '
        '"questions": ["...", "..."]}'
    )


async def generate_summary(chunks: list[Chunk]) -> dict | None:
    """`{"summary": str, "questions": [str, ...]}` döndürür; hata/parse kaybında None."""
    if not chunks:
        return None
    sample = build_sample(chunks)
    messages = [
        {"role": "system", "content": SUMMARY_PROMPT},
        {"role": "user", "content": f"BELGE İÇERİĞİ:\n\n{sample}"},
    ]
    raw = await llm.complete(messages, temperature=0.3, max_tokens=900)
    data = parse_json_blocks(raw, allow_salvage=False)
    if not data:
        # Kırık JSON yaygın → tek katı yeniden deneme (etkin, pahalı değil).
        strict = [*messages, {"role": "user", "content": _strict_nudge()}]
        raw = await llm.complete(strict, temperature=0.5, max_tokens=900)
        # Yeniden deneme de bozuksa en azından kısmi (salvage) kabul et.
        data = parse_json_blocks(raw)
    if not data:
        raise AIError(f"Özet yanıtı JSON değil: {raw[:200]!r}")
    summary = (data.get("summary") or "").strip()
    if not summary:
        raise AIError("Özet yanıtında summary boş döndü.")
    questions = [str(q).strip() for q in (data.get("questions") or []) if str(q).strip()]
    questions = questions[:MAX_QUESTIONS]
    return {"summary": summary, "questions": questions}


async def generate_workspace(entries: list[dict]) -> dict | None:
    """Belge özetlerinden workspace özeti + başlık üretir: `{summary, title}`."""
    if not entries:
        return None
    blocks = "\n".join(f"- {e['name']}: {e['summary']}" for e in entries)
    messages = [
        {"role": "system", "content": WORKSPACE_SUMMARY_PROMPT},
        {"role": "user", "content": f"BELGE ÖZETLERİ:\n\n{blocks}"},
    ]
    raw = await llm.complete(messages, temperature=0.3, max_tokens=900)
    data = parse_json_blocks(raw, allow_salvage=False)
    if not data:
        strict = [*messages, {"role": "user", "content": _strict_nudge()}]
        data = parse_json_blocks(await llm.complete(strict, temperature=0.5, max_tokens=900))
    if not data:
        return None
    summary = (data.get("summary") or "").strip()
    title = (data.get("title") or "").strip()
    if not summary:
        return None
    return {"summary": summary, "title": title}