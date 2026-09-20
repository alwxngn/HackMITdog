"""On-demand dog camera — out-of-band URL for Night Watch (no DimOS import)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger("lantern.camera")

router = APIRouter(prefix="/api/camera", tags=["camera"])


def _enabled() -> bool:
    return os.getenv("DOG_CAMERA_ENABLED", "0").strip() in {"1", "true", "True", "yes"}


def _viewer_url() -> str:
    return os.getenv("DOG_CAMERA_URL", "").strip()


def _stream_url() -> str:
    return os.getenv("DOG_CAMERA_STREAM_URL", "").strip()


def camera_status() -> dict[str, Any]:
    enabled = _enabled()
    url = _viewer_url() if enabled else ""
    stream = _stream_url() if enabled else ""
    return {
        "enabled": enabled and bool(url or stream),
        "master_enabled": enabled,
        "url": url or None,
        "stream_url": stream or None,
        "proxy_stream": "/api/camera/stream" if stream else None,
        "hint": (
            "Set DOG_CAMERA_ENABLED=1 and DOG_CAMERA_URL to a DimOS cockpit/teleop page "
            "(see robot/README.md). Camera stays off until the caregiver opens the panel."
            if not (enabled and (url or stream))
            else "Caregiver must open View dog camera — feed is not always-on."
        ),
    }


@router.get("/status")
async def get_status():
    return camera_status()


@router.get("/stream")
async def proxy_stream():
    """Same-origin MJPEG (or similar) proxy for phone tunnels. Optional."""
    if not _enabled():
        raise HTTPException(status_code=404, detail="Dog camera disabled")
    upstream = _stream_url()
    if not upstream:
        raise HTTPException(
            status_code=404,
            detail="DOG_CAMERA_STREAM_URL not set — use DOG_CAMERA_URL iframe instead",
        )

    async def gen():
        async with httpx.AsyncClient(timeout=None) as client:
            try:
                async with client.stream("GET", upstream) as resp:
                    if resp.status_code >= 400:
                        logger.warning("camera upstream %s", resp.status_code)
                        return
                    async for chunk in resp.aiter_bytes():
                        yield chunk
            except Exception:
                logger.exception("camera stream proxy failed")

    # Pass through common MJPEG content type; browsers tolerate octet-stream too
    return StreamingResponse(
        gen(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache, no-store"},
    )
