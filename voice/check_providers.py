"""Run a short, billable live TTS -> STT check without printing credentials.

Usage: python -m voice.check_providers
"""
import asyncio
from pathlib import Path
import sys

from dotenv import load_dotenv
from fastapi import HTTPException

from voice import providers


async def main():
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    mode = providers.capabilities()
    print(f"Recognition: {mode['stt']}; voice: {mode['tts']}")
    if mode["stt"] != "deepgram" or mode["tts"] != "elevenlabs":
        for note in providers.configuration_notes():
            print(note)
        return 1
    try:
        audio = await providers.synthesize("Hello Arthur. How are you feeling today?")
        print(f"ElevenLabs: received {len(audio)} bytes of MP3 audio.")
        transcript = await providers.transcribe(audio, "audio/mpeg")
        print(f"Deepgram: {transcript}")
        if not transcript.strip():
            print("FAIL: the generated audio produced an empty transcript.")
            return 1
        print("PASS: both live APIs completed the speech round trip.")
        return 0
    except HTTPException as error:
        print(f"FAIL: {error.detail}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
