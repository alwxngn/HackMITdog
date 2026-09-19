"""Shared Lantern event bus — schemas from docs/04-interfaces.md."""

from .core import Bus, get_bus
from .envelope import SOURCES, make_envelope

__all__ = ["Bus", "SOURCES", "get_bus", "make_envelope"]
