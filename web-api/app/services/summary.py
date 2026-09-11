"""Belge özeti + başlangıç soruları üretimi (rag_arch §4) — tek LLM çağrısı.

Girdi: başlıklar + stratified örnek (ilk/orta/son), ~2500 karakter bütçe.
Çıktı: `{summary, questions}`. Model JSON yerine akıcı metin döndürürse veya
çağrı patlarsa `generate_summary` `None` döndürür → belge `embedded` kalır.
"""

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


def parse_json_blocks(raw: str) -> dict | None:
    """Model çıktısından JSON bloğunu kurtarır (code fence / ön-yazı tolere)."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE | re.DOTALL)
    try:
        start, end = text.index("{"), text.rindex("}")
        return json.loads(text[start : end + 1])
    except (ValueError, json.JSONDecodeError):
        return None


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
    data = parse_json_blocks(raw)
    if not data:
        return None
    summary = (data.get("summary") or "").strip()
    title = (data.get("title") or "").strip()
    if not summary:
        return None
    return {"summary": summary, "title": title}