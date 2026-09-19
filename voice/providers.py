"""Server-only provider adapters. No API credentials reach the phone."""
import os

import httpx
from fastapi import HTTPException


def capabilities():
    return {
        "stt": "deepgram" if os.getenv("DEEPGRAM_API_KEY") else "browser",
        "tts": "elevenlabs" if (
            os.getenv("ELEVENLABS_API_KEY") and os.getenv("ELEVENLABS_VOICE_ID")
            and os.getenv("ELEVENLABS_VOICE_CONSENT", "").lower() == "true"
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
                params={"model": "nova-3", "smart_format": "true"},
                headers={"Authorization": f"Token {key}", "Content-Type": content_type},
                content=audio,
            )
            response.raise_for_status()
            return response.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
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
    except httpx.HTTPError:
        raise HTTPException(502, "Voice generation failed. Use the phone voice or retry.") from None
