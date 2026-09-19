"""Zone geometry helpers — metres, SW origin (docs/16-e3-portal.md)."""

from __future__ import annotations

from typing import Any


DEFAULT_ZONES: list[dict[str, Any]] = [
    {
        "id": "bedroom",
        "class": "safe",
        "label": "Bedroom",
        "kind": "door",
        "polygon": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
    },
    {
        "id": "hallway",
        "class": "watch",
        "label": "Hallway",
        "kind": "door",
        "polygon": [[1.0, 0.3], [1.8, 0.3], [1.8, 0.9], [1.0, 0.9]],
    },
    {
        "id": "front_door",
        "class": "exit",
        "label": "Don't go",
        "kind": "door",
        "polygon": [[1.6, 0.0], [2.0, 0.0], [2.0, 0.5], [1.6, 0.5]],
    },
]


def point_in_poly(x: float, y: float, polygon: list[list[float]]) -> bool:
    # Ray casting
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def zone_at(x: float, y: float, zones: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    zones = zones or DEFAULT_ZONES
    # Prefer exit / watch over safe when overlapping
    order = {"exit": 0, "watch": 1, "safe": 2}
    hits = [z for z in zones if point_in_poly(x, y, z.get("polygon") or [])]
    if not hits:
        return None
    hits.sort(key=lambda z: order.get(z.get("class", "safe"), 9))
    return hits[0]


def centroid(polygon: list[list[float]]) -> tuple[float, float]:
    if not polygon:
        return 0.0, 0.0
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return sum(xs) / len(xs), sum(ys) / len(ys)
