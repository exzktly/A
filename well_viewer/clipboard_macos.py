"""Native macOS pasteboard helper for vector-PDF copy.

Qt6's QMacMimeRegistry doesn't surface ``application/pdf`` /
``com.adobe.pdf`` from a :class:`QMimeData` to the macOS pasteboard,
so Copy-as-PDF via :meth:`QClipboard.setMimeData` lands as nothing in
Keynote / Pages / Preview. Going through ``NSPasteboard`` directly
via PyObjC reaches the OS pasteboard, but raw PDF *data* still
rasterises in Keynote — confirmed empirically over multiple iterations
(PRs #195, #197, #198, #199, #200). The same bytes paste as vector
into Illustrator / Affinity / Preview, so Keynote's paste handler is
choosing to rasterise on a path we can't influence from the data
side.

The recipe that actually works for Keynote is the AppleScript one:

    tell application "Finder"
        set the clipboard to (POSIX file "/path/to/figure.pdf")
    end tell

i.e. the clipboard holds a *file URL*, not raw PDF bytes. Apps that
read ``com.adobe.pdf`` still get it (NSPasteboard advertises the
file's UTI based on its extension and lazily reads the bytes on
demand), so Illustrator / Affinity / Preview keep working. Keynote
sees a "file paste" rather than a "PDF data paste" and embeds the
.pdf as a vector object exactly the way ``Insert > Choose…`` does.

**Scope trade-off.** Because the pasteboard now carries a file URL
instead of raw image data, apps that previously pasted an inline PNG
raster (Slack, Mail, Notes, browser composers) now paste a **PDF
file attachment** instead. This was an explicit user choice — Copy
SVG is being optimised for vector-aware targets.

The module is import-safe on every OS: ``write_vector_pdf_pasteboard``
returns ``False`` when not running on macOS or when PyObjC isn't
available, and the caller falls back to its in-Qt clipboard path.
``last_failure_reason`` exposes the human-readable reason a write was
skipped so the UI can surface it.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

# Last reason ``write_vector_pdf_pasteboard`` returned ``False``. Kept
# as module state so callers (e.g. the Copy-SVG status bar) can show a
# diagnostic without piping a tuple through every call site.
last_failure_reason: str = ""

# Subdir under the OS temp dir for "live" clipboard PDFs. macOS prunes
# NSTemporaryDirectory periodically, so files here disappear on reboot;
# we also best-effort prune our own entries older than an hour on each
# write so back-to-back copies don't grow the dir without bound.
_TMP_SUBDIR = "allwell-clipboard"
_TMP_MAX_AGE_SEC = 3600


def write_vector_pdf_pasteboard(*, pdf_bytes: bytes) -> bool:
    """Write a PDF file URL to the macOS pasteboard.

    Returns ``True`` when the pasteboard was written, ``False`` when
    the platform isn't macOS, PyObjC isn't importable, or the write
    itself failed.

    Writes the PDF bytes to a temp file under
    ``NSTemporaryDirectory()/allwell-clipboard`` and puts the resulting
    file URL on the general pasteboard via
    ``pb.writeObjects_([NSURL])``. This is the AppleScript-equivalent
    recipe Keynote respects for vector paste; see the module docstring
    for the full rationale.

    Deliberately does **not** put raw ``com.adobe.pdf`` bytes on the
    pasteboard. NSPasteboard still advertises ``com.adobe.pdf`` (and
    other UTIs derived from the file's ``.pdf`` extension) as
    promised types, so data-paste consumers (Illustrator, Affinity,
    Preview) read the file content on demand and still receive vector.
    """
    global last_failure_reason
    last_failure_reason = ""

    if sys.platform != "darwin":
        last_failure_reason = "not macOS"
        return False
    if not pdf_bytes:
        last_failure_reason = "no PDF bytes"
        return False
    try:
        from AppKit import NSPasteboard
        from Foundation import NSURL
    except Exception as exc:
        last_failure_reason = (
            "PyObjC framework not installed — "
            "`pip install pyobjc-framework-Cocoa` "
            f"({exc.__class__.__name__}: {exc})"
        )
        return False

    tmp_dir = Path(tempfile.gettempdir()) / _TMP_SUBDIR
    try:
        tmp_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        last_failure_reason = f"temp dir create failed: {exc}"
        return False
    _prune_stale(tmp_dir)

    try:
        fd, pdf_path_str = tempfile.mkstemp(
            suffix=".pdf", prefix="figure-", dir=str(tmp_dir),
        )
        with os.fdopen(fd, "wb") as fp:
            fp.write(pdf_bytes)
    except OSError as exc:
        last_failure_reason = f"temp PDF write failed: {exc}"
        return False

    file_url = NSURL.fileURLWithPath_(pdf_path_str)
    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    if not bool(pb.writeObjects_([file_url])):
        last_failure_reason = "NSPasteboard.writeObjects_([NSURL]) returned NO"
        return False
    return True


def _prune_stale(tmp_dir: Path) -> None:
    """Best-effort cleanup of clipboard PDFs older than the cap.

    Quiet on errors — this is hygiene, not correctness.
    """
    now = time.time()
    try:
        entries = list(tmp_dir.iterdir())
    except OSError:
        return
    for stale in entries:
        try:
            if stale.is_file() and (now - stale.stat().st_mtime) > _TMP_MAX_AGE_SEC:
                stale.unlink()
        except OSError:
            pass
