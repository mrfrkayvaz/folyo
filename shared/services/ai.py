"""OpenAI-uyumlu sağlayıcılar için ortak HTTP katmanı (LLM / embedding / vision)."""

import asyncio
import json

import httpx


class AIError(Exception):
    pass


def resolve(*, base_url: str, api_key: str, model: str, subject: str, hint: str = "") -> str:
    if not api_key or not base_url:
        raise AIError(f"{subject} ayarları eksik.{hint}")
    if not model:
        raise AIError(f"{subject} ayarları eksik: model tanımsız.{hint}")
    return base_url.rstrip("/")


def _raise_for_http(status: int, model: str, subject: str) -> None:
    if status == 401:
        raise AIError(f"{subject}: API anahtarı geçersiz (401). web-api/.env'i kontrol edin.")
    if status == 404:
        raise AIError(f"{subject}: model bulunamadı (404) — '{model}'.")
    if status == 429:
        raise AIError(f"{subject}: İstek limiti aşıldı (429). Lütfen birkaç saniye sonra tekrar deneyin.")
    raise AIError(f"{subject} servisi yanıt vermedi: {status}")


async def post_json(
    *,
    url: str,
    headers: dict,
    payload: dict,
    model: str,
    subject: str,
    timeout: float = 180.0,
    retries: int = 3,
) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, retries + 1):
            try:
                resp = await client.post(url, json=payload, headers=headers)
            except (httpx.TransportError, httpx.RequestError) as exc:
                if attempt < retries:
                    await asyncio.sleep(attempt * 1.5)
                    continue
                raise AIError(f"{subject} sunucusuna bağlanılamadı: {exc}") from exc

            if resp.status_code in (429, 502, 503) and attempt < retries:
                await asyncio.sleep(attempt * 1.5)
                continue
            if resp.status_code >= 400:
                _raise_for_http(resp.status_code, model, subject)
            return resp.json()

    raise AIError(f"{subject}: yanıt alınamadı.")


async def stream_json(
    *,
    url: str,
    headers: dict,
    payload: dict,
    model: str,
    subject: str,
    retries: int = 3,
):
    """SSE yanıtını satır satır parse edilmiş nesne olarak verir; [DONE]'da biter."""
    async with httpx.AsyncClient(timeout=None) as client:
        for attempt in range(1, retries + 1):
            try:
                async with client.stream("POST", url, json=payload, headers=headers) as resp:
                    if resp.status_code in (429, 502, 503) and attempt < retries:
                        await asyncio.sleep(attempt * 1.5)
                        continue
                    if resp.status_code >= 400:
                        _raise_for_http(resp.status_code, model, subject)
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            return
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            continue
                    return
            except (httpx.TransportError, httpx.RequestError) as exc:
                if attempt < retries:
                    await asyncio.sleep(attempt * 1.5)
                    continue
                raise AIError(f"{subject} sunucusuna bağlanılamadı: {exc}") from exc

    raise AIError(f"{subject}: yanıt alınamadı.")