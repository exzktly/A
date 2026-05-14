"""Native macOS pasteboard helpers for vector-PDF copy.

Qt6's QMacMimeRegistry doesn't surface ``application/pdf`` /
``com.adobe.pdf`` from a :class:`QMimeData` to the macOS pasteboard,
so Copy-as-PDF via :meth:`QClipboard.setMimeData` lands as nothing in
Keynote / Pages / Preview. Going through ``NSPasteboard`` directly
via PyObjC reaches the OS pasteboard with the correct UTI, so those
apps paste the figure as editable vector PDF.

The module is import-safe on every OS: ``write_vector_pdf_pasteboard``
returns ``False`` when not running on macOS or when PyObjC isn't
available, and the caller falls back to its in-Qt clipboard path.
``last_failure_reason`` exposes the human-readable reason a write was
skipped so the UI can surface it (e.g. "PyObjC not installed").
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

# Hardcoded UTI. ``NSPasteboardTypePDF`` isn't exposed by every PyObjC
# release, so we use the canonical UTI string directly — it's a stable
# Apple identifier, unchanged since macOS 10.6.
_UTI_PDF = "com.adobe.pdf"
_UTI_FILE_URL = "public.file-url"

# Subdir under the OS temp dir for "live" clipboard PDFs. macOS prunes
# NSTemporaryDirectory periodically, so files here disappear on reboot;
# we also best-effort prune our own entries older than an hour on each
# write so back-to-back copies don't grow the dir without bound.
_TMP_SUBDIR = "allwell-clipboard"
_TMP_MAX_AGE_SEC = 3600


def write_vector_pdf_pasteboard(*, pdf_bytes: bytes) -> bool:
    """Write a PDF to the macOS pasteboard so iWork pastes it as vector.

    Returns ``True`` when the pasteboard was written, ``False`` when
    the platform isn't macOS, PyObjC isn't importable, or the write
    itself failed.

    Strategy: advertise *both* ``com.adobe.pdf`` and ``public.file-url``
    on a single :class:`NSPasteboardItem`. Different consumers walk
    pasteboard types differently:

    - Illustrator / Affinity / Preview read ``com.adobe.pdf`` directly
      and embed the raw PDF bytes as vector (this already worked).
    - Keynote (and likely Pages) rasterise ``com.adobe.pdf`` data on
      their paste path via NSImage — empirically confirmed: same PDF
      bytes paste vector into Illustrator, raster into Keynote.
      Their *file-URL* paste path runs separate code that treats the
      paste like an Insert > PDF and preserves vector. By writing
      the PDF to a temp file and offering its URL alongside the PDF
      data, Keynote's paste-handler reads the URL and embeds vector.

    The temp file lives under ``NSTemporaryDirectory()/allwell-clipboard``
    until macOS prunes it (or the helper prunes its own entries
    older than ``_TMP_MAX_AGE_SEC``). The pasted figure in Keynote
    keeps its own embedded copy, so the temp file only needs to
    outlive the paste itself.
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
        from AppKit import NSPasteboard, NSPasteboardItem
        from Foundation import NSData, NSURL
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

    pdf_data = NSData.dataWithBytes_length_(pdf_bytes, len(pdf_bytes))
    file_url = NSURL.fileURLWithPath_(pdf_path_str)

    item = NSPasteboardItem.alloc().init()
    if not bool(item.setData_forType_(pdf_data, _UTI_PDF)):
        last_failure_reason = "NSPasteboardItem rejected PDF data"
        return False
    if not bool(item.setString_forType_(
        file_url.absoluteString(), _UTI_FILE_URL,
    )):
        last_failure_reason = "NSPasteboardItem rejected file URL"
        return False

    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    if not bool(pb.writeObjects_([item])):
        last_failure_reason = "NSPasteboard.writeObjects: returned NO"
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
