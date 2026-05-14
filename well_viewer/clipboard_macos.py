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

    Uses the modern :class:`NSPasteboardItem` + ``writeObjects:`` API
    instead of the legacy ``setData:forType:``. The legacy path
    registers data with NSPasteboard's dynamic-type translators, and
    some consumers (Keynote in particular) read the translated /
    rasterised representation when a vector PDF is the only declared
    type — even though Illustrator / Affinity / Preview read the raw
    PDF bytes correctly. ``NSPasteboardItem`` bypasses the dynamic
    translators: only the exact types we set are advertised, no
    PDF-to-image conversion happens, and Keynote's paste path falls
    through to handling ``com.adobe.pdf`` as vector.

    Deliberately writes *only* the PDF slot. A PNG fallback in the
    same item would let iWork pick the raster path; raster-only
    consumers (Slack, Mail, Linux Qt clipboard) are served by the
    QMimeData fallback in callers when the native path returns False.
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
        from Foundation import NSData
    except Exception as exc:
        last_failure_reason = (
            "PyObjC framework not installed — "
            "`pip install pyobjc-framework-Cocoa` "
            f"({exc.__class__.__name__}: {exc})"
        )
        return False

    pdf_data = NSData.dataWithBytes_length_(pdf_bytes, len(pdf_bytes))
    item = NSPasteboardItem.alloc().init()
    if not bool(item.setData_forType_(pdf_data, _UTI_PDF)):
        last_failure_reason = "NSPasteboardItem rejected PDF data"
        return False

    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    if not bool(pb.writeObjects_([item])):
        last_failure_reason = "NSPasteboard.writeObjects: returned NO"
        return False
    return True
