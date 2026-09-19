"""Server-only provider adapters. No API credentials reach the phone."""
import os

import httpx
from fastapi import HTTPException


def configuration_notes():
    """Safe diagnostics: never return key values or provider response bodies."""
    notes = []
    if not os.getenv("DEEPGRAM_API_KEY"):
        notes.append("Deepgram is not configured; replies use browser recognition.")
    if not os.getenv("ELEVENLABS_API_KEY") or not os.getenv("ELEVENLABS_VOICE_ID"):
        notes.append("ElevenLabs needs both an API key and a voice ID; using the phone voice.")
    elif os.getenv("ELEVENLABS_VOICE_CONSENT", "").strip().lower() != "true":
        notes.append("ElevenLabs is disabled. Set ELEVENLABS_VOICE_CONSENT=true for an approved voice and restart the server.")
    return notes


def provider_error(name, error):
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        if status in {401, 403}:
            detail = f"{name} rejected the credentials or permissions. Check its API key and account access, then restart the server."
        elif status == 429:
            detail = f"{name} has reached a rate or quota limit. Check your account balance and retry later."
        elif status in {400, 404, 422}:
            detail = ("ElevenLabs could not use the selected voice/model. Check the voice ID and your account's access to it."
                      if name == "ElevenLabs" else "Deepgram could not read this recording. Try recording again.")
        else:
            detail = f"{name} is unavailable (HTTP {status}). Please retry later."
    elif isinstance(error, httpx.TimeoutException):
        detail = f"{name} timed out. Check connectivity and try again."
    else:
        detail = f"Could not reach {name}. Check the server's internet connection."
    return HTTPException(502, detail)


def capabilities():
    return {
        "stt": "deepgram" if os.getenv("DEEPGRAM_API_KEY") else "browser",
        "tts": "elevenlabs" if (
            os.getenv("ELEVENLABS_API_KEY") and os.getenv("ELEVENLABS_VOICE_ID")
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


async def synthesize(text: str) -> bytes:
    # Check consent on every request, including requests for previously prepared text.
    if capabilities()["tts"] != "elevenlabs":
        raise HTTPException(503, "Approved ElevenLabs voice unavailable. Use the phone voice.")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{os.environ['ELEVENLABS_VOICE_ID']}",
                params={"output_format": "mp3_44100_128"},
                headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
                json={"text": text, "model_id": os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")},
            )
            response.raise_for_status()
            return response.content
    except httpx.HTTPError as error:
        raise provider_error("ElevenLabs", error) from None
