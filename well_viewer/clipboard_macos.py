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

# Hardcoded UTIs (the constants ``NSPasteboardTypePDF`` /
# ``NSPasteboardTypePNG`` aren't exposed by every PyObjC release, so
# we use the canonical UTI strings directly — they're stable Apple
# identifiers, unchanged since macOS 10.6).
_UTI_PDF = "com.adobe.pdf"
_UTI_PNG = "public.png"


def write_vector_pdf_pasteboard(
    *,
    pdf_bytes: bytes,
    png_bytes: bytes | None = None,
) -> bool:
    """Write a PDF (and optional PNG fallback) to the macOS pasteboard.

    Returns ``True`` when the pasteboard was written, ``False`` when
    the platform isn't macOS, PyObjC isn't importable, or the write
    itself failed. The PDF slot uses ``com.adobe.pdf`` (the canonical
    vector-paste UTI iWork / Preview honour); the optional PNG slot
    uses ``public.png`` for raster-only consumers (Slack, Mail).
    ``declareTypes_owner_`` puts PDF first so ``NSImage``-based paste
    targets (Keynote, Pages) read the vector slot instead of the
    raster fallback.
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
            "PyObjC not installed — `pip install pyobjc-framework-Cocoa` "
            f"({exc.__class__.__name__})"
        )
        return False

    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    types = [_UTI_PDF]
    if png_bytes:
        types.append(_UTI_PNG)
    pb.declareTypes_owner_(types, None)

    pdf_data = NSData.dataWithBytes_length_(pdf_bytes, len(pdf_bytes))
    if not bool(pb.setData_forType_(pdf_data, _UTI_PDF)):
        last_failure_reason = "NSPasteboard rejected PDF data"
        return False
    if png_bytes:
        png_data = NSData.dataWithBytes_length_(png_bytes, len(png_bytes))
        pb.setData_forType_(png_data, _UTI_PNG)
    return True
