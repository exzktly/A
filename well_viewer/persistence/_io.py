"""Shared I/O helpers for persistence modules.

Centralises the tmp + ``os.replace`` pattern so a crash, signal, or full-disk
condition mid-write can't leave a truncated JSON sidecar.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, data: Any, *, indent: int = 2) -> None:
    """Serialise *data* as JSON to *path*, atomically.

    Writes to ``<path>.tmp`` then ``os.replace`` onto the destination so a
    reader never sees a partial file. Parents are created on demand.

    Raises ``OSError`` on filesystem failure — callers decide whether to
    catch (usually yes, with a logger.warning) or propagate (Save-via-dialog
    paths where the user should see the error).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=indent)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                # fsync isn't supported on every filesystem (e.g. some
                # network mounts). The replace below is still atomic on
                # POSIX and Windows.
                pass
        os.replace(tmp, path)
    finally:
        # If replace didn't run (exception during write), clean up the
        # tmp file rather than leaving it behind.
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def atomic_write_text(path: Path, text: str) -> None:
    """Same shape as ``atomic_write_json`` but for arbitrary text payloads.

    Used by ``smfish_worker`` to write per-well CSVs.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                pass
        os.replace(tmp, path)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
