"""Server-only provider adapters. No API credentials reach the phone."""
import os

import httpx
from fastapi import HTTPException


def configuration_notes():
    """Safe diagnostics: never return key values or provider response bodies."""
    notes = []
    if not os.getenv("DEEPGRAM_API_KEY"):
        notes.append("Deepgram is not configured; replies use browser recognition.")
    if not os.getenv("ELEVENLABS_API_KEY"):
        notes.append("ElevenLabs is not configured; using the phone voice.")
    elif os.getenv("ELEVENLABS_VOICE_CONSENT", "").strip().lower() != "true":
        notes.append("ElevenLabs is disabled. Set ELEVENLABS_VOICE_CONSENT=true for an approved voice and restart the server.")
    elif not os.getenv("ELEVENLABS_VOICE_ID"):
        notes.append("No default ElevenLabs voice set; clone one during onboarding or set ELEVENLABS_VOICE_ID.")
    return notes


def _upstream_message(error):
    """Best-effort extraction of the provider's own error text, for diagnosis."""
    try:
        body = error.response.json()
    except ValueError:
        return None
    if isinstance(body, dict):
        detail = body.get("detail")
        if isinstance(detail, dict):
            return detail.get("message") or detail.get("status")
        if isinstance(detail, str):
            return detail
        return body.get("message")
    return None


def provider_error(name, error):
    response_status = 502
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        upstream = _upstream_message(error)
        if 400 <= status < 500:
            response_status = status
        if status in {401, 403}:
            detail = f"{name} rejected the credentials or permissions. Check its API key and account access, then restart the server."
        elif status == 429:
            detail = f"{name} has reached a rate or quota limit. Check your account balance and retry later."
        elif status in {400, 404, 422}:
            detail = ("ElevenLabs could not use the selected voice/model. Check the voice ID and your account's access to it."
                      if name == "ElevenLabs" else "Deepgram could not read this recording. Try recording again.")
        else:
            detail = f"{name} is unavailable (HTTP {status}). Please retry later."
        if upstream:
            detail = f"{detail} ({upstream})"
    elif isinstance(error, httpx.TimeoutException):
        detail = f"{name} timed out. Check connectivity and try again."
    else:
        detail = f"Could not reach {name}. Check the server's internet connection."
    return HTTPException(response_status, detail)


def capabilities():
    return {
        "stt": "deepgram" if os.getenv("DEEPGRAM_API_KEY") else "browser",
        "tts": "elevenlabs" if (
            os.getenv("ELEVENLABS_API_KEY")
            and os.getenv("ELEVENLABS_VOICE_CONSENT", "").strip().lower() == "true"
        ) else "browser",
        "dialogue": "scripted",
    }


async def transcribe(audio: bytes, content_type: str) -> str:
    key = os.getenv("DEEPGRAM_API_KEY")
    if not key:
        raise HTTPException(503, "Deepgram is not configured. Use browser recognition or a typed reply.")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen",
                params={"model": os.getenv("DEEPGRAM_MODEL", "nova-3"), "smart_format": "true"},
                headers={"Authorization": f"Token {key}", "Content-Type": content_type},
                content=audio,
            )
            response.raise_for_status()
            return response.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
    except httpx.HTTPError as error:
        raise provider_error("Deepgram", error) from None
    except (KeyError, IndexError, ValueError):
        raise HTTPException(502, "Speech recognition failed. Please retry or type your reply.") from None


async def synthesize(text: str, voice_id: str | None = None, *, output_format: str = "mp3_44100_128") -> bytes:
    # Check consent on every request, including requests for previously prepared text.
    if capabilities()["tts"] != "elevenlabs":
        raise HTTPException(503, "Approved ElevenLabs voice unavailable. Use the phone voice.")
    voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID")
    if not voice_id:
        raise HTTPException(503, "No ElevenLabs voice configured. Clone one during onboarding or set ELEVENLABS_VOICE_ID.")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                params={"output_format": output_format},
                headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
                json={"text": text, "model_id": os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")},
            )
            response.raise_for_status()
            return response.content
    except httpx.HTTPError as error:
        raise provider_error("ElevenLabs", error) from None


_CLONE_EXTENSIONS = {"audio/webm": "webm", "audio/mp4": "mp4", "audio/ogg": "ogg", "audio/wav": "wav"}


async def clone_voice(name: str, audio: bytes, content_type: str) -> str:
    """Instant Voice Cloning: https://api.elevenlabs.io/v1/voices/add"""
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        raise HTTPException(503, "ElevenLabs is not configured. Set ELEVENLABS_API_KEY to clone a voice.")
    ext = _CLONE_EXTENSIONS.get(content_type, "webm")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.elevenlabs.io/v1/voices/add",
                headers={"xi-api-key": key},
                data={"name": name},
                files={"files": (f"sample.{ext}", audio, content_type)},
            )
            response.raise_for_status()
            voice_id = response.json().get("voice_id")
            if not voice_id:
                raise KeyError("voice_id")
            return voice_id
    except httpx.HTTPError as error:
        if isinstance(error, httpx.HTTPStatusError):
            message = str(_upstream_message(error) or "").lower()
            if error.response.status_code == 402 or (
                error.response.status_code in {400, 401, 403}
                and any(word in message for word in ("subscription", "upgrade", "paid plan", "payment"))
            ):
                raise HTTPException(402, "Instant voice cloning requires ElevenLabs Starter or above. Upgrade the account linked to the server's API key, or use a key from an eligible account. You can continue onboarding without cloning.") from None
        raise provider_error("ElevenLabs", error) from None
    except (KeyError, ValueError):
        raise HTTPException(502, "ElevenLabs did not return a voice ID.") from None
