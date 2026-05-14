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

import sys

# Last reason ``write_vector_pdf_pasteboard`` returned ``False``. Kept
# as module state so callers (e.g. the Copy-SVG status bar) can show a
# diagnostic without piping a tuple through every call site.
last_failure_reason: str = ""

# Hardcoded UTI. ``NSPasteboardTypePDF`` isn't exposed by every PyObjC
# release, so we use the canonical UTI string directly — it's a stable
# Apple identifier, unchanged since macOS 10.6.
_UTI_PDF = "com.adobe.pdf"


def write_vector_pdf_pasteboard(*, pdf_bytes: bytes) -> bool:
    """Write a PDF to the macOS pasteboard under ``com.adobe.pdf``.

    Returns ``True`` when the pasteboard was written, ``False`` when
    the platform isn't macOS, PyObjC isn't importable, or the write
    itself failed.

    Deliberately writes *only* the PDF slot. Keynote (and probably
    Pages) reads ``public.png`` ahead of ``com.adobe.pdf`` when both
    are present on the pasteboard — even with ``declareTypes:owner:``
    putting PDF first — so a raster fallback in the same write would
    silently win in iWork and you'd get a PNG paste instead of vector.
    Raster-only consumers (Slack, Mail, Linux Qt clipboard) are
    handled by the QMimeData fallback in callers; the native path is
    reserved for vector-aware targets.
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
        from Foundation import NSData
    except Exception as exc:
        last_failure_reason = (
            "PyObjC framework not installed — "
            "`pip install pyobjc-framework-Cocoa` "
            f"({exc.__class__.__name__}: {exc})"
        )
        return False

    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pdf_data = NSData.dataWithBytes_length_(pdf_bytes, len(pdf_bytes))
    if not bool(pb.setData_forType_(pdf_data, _UTI_PDF)):
        last_failure_reason = "NSPasteboard rejected PDF data"
        return False
    return True
