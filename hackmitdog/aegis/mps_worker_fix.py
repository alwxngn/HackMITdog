"""Make DimOS's module workers use `spawn` on macOS so Metal/MPS works.

WHY THIS EXISTS
---------------
DimOS runs every module in its own worker process, created from a
`multiprocessing` **forkserver** context
(`dimos.core.coordination.python_worker.get_forkserver_context`). Its own
comment explains the choice: "Using `forkserver` instead of `fork` because it
avoids CUDA context corruption issues." That is correct on Linux/NVIDIA --
and it is exactly what breaks Apple Metal (MPS) on macOS.

A forkserver child inherits the forkserver template process's already-
initialized Metal XPC connection, which is not valid in the child. The first
attempt to compile a Metal shader there fails with:

    RuntimeError: Failed to created pipeline state object, error:
    Error Domain=AGXMetalG15G_C0 Code=2 "Compiler encountered
    XPC_ERROR_CONNECTION_INVALID (is the OS shutting down?)"

Confirmed directly by running the same tiny conv on the same machine under
three start methods:

    parent process     -> OK
    forkserver child   -> XPC_ERROR_CONNECTION_INVALID   (the error above)
    spawn child        -> OK
    fork child         -> hangs

This is what made `follow_person` fail 100% of the time on this Mac while
`detect_person` kept working: `YoloPersonDetector` runs on CPU, but
`EdgeTAMProcessor` (`dimos.models.segmentation.edge_tam`, the tracker DimOS's
`PersonFollowSkillContainer` starts once following begins) hard-requires a GPU
-- its `_build_model()` raises `RuntimeError("EdgeTAM requires a CUDA or MPS
device")` on CPU -- so on macOS it must use MPS, inside a worker where Metal
cannot compile.

WHAT THIS DOES
--------------
Replaces `python_worker.get_forkserver_context` with one that returns a
**spawn** context, on macOS only. `spawn` starts each worker as a fresh
interpreter with no inherited Metal/XPC state, so shader compilation works
normally. On every other platform this module does nothing at all, leaving
DimOS's CUDA-motivated forkserver behavior exactly as-is.

The swap is safe to do at import time: `_forkserver_ctx` is lazily created
(`None` until first use) and `get_forkserver_context()` has exactly one call
site, `PythonWorker.start_process()`, which runs well after blueprint import.
`hackmitdog.aegis.blueprint` imports this module at its top so the override is
in place before `dimos run` starts any worker.

TRADEOFF: `spawn` workers re-import the world instead of inheriting it, so
startup is somewhat slower than forkserver. That is the cost of having a
working GPU in the worker at all on this platform.
"""

from __future__ import annotations

import multiprocessing
import sys
from typing import Any

from dimos.utils.logging_config import setup_logger

logger = setup_logger()

_spawn_ctx: Any = None


def _get_spawn_context() -> Any:
    """Drop-in replacement for DimOS's `get_forkserver_context`, using spawn."""
    global _spawn_ctx
    if _spawn_ctx is None:
        _spawn_ctx = multiprocessing.get_context("spawn")
    return _spawn_ctx


def apply() -> bool:
    """Force DimOS module workers onto `spawn` when running on macOS.

    Returns True if the override was applied, False if it was skipped
    (non-macOS platform, or DimOS's internals no longer look as expected).
    Idempotent -- calling it more than once is harmless.
    """
    if sys.platform != "darwin":
        return False

    try:
        from dimos.core.coordination import python_worker
    except ImportError:
        logger.warning(
            "mps_worker_fix: could not import dimos.core.coordination.python_worker; "
            "leaving worker start method alone"
        )
        return False

    if getattr(python_worker.get_forkserver_context, "__mps_spawn_override__", False):
        return True

    if python_worker._forkserver_ctx is not None:
        # A forkserver context was already built, so workers may already be
        # bound to it. Say so loudly rather than pretending the fix took.
        logger.warning(
            "mps_worker_fix: a forkserver context already exists; Metal/MPS in "
            "worker processes may still fail. Import hackmitdog.aegis.blueprint "
            "before starting any DimOS worker."
        )

    _get_spawn_context.__mps_spawn_override__ = True  # type: ignore[attr-defined]
    python_worker.get_forkserver_context = _get_spawn_context

    logger.info(
        "mps_worker_fix: DimOS module workers set to 'spawn' (macOS) so Metal/MPS "
        "shader compilation works in worker processes"
    )
    return True
