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
"""

from __future__ import annotations

import sys


def write_vector_pdf_pasteboard(
    *,
    pdf_bytes: bytes,
    png_bytes: bytes | None = None,
) -> bool:
    """Write a PDF (and optional PNG fallback) to the macOS pasteboard.

    Returns ``True`` when the pasteboard was written, ``False`` when
    the platform isn't macOS or PyObjC isn't importable. The PDF slot
    uses the ``com.adobe.pdf`` UTI (the canonical vector-paste type
    that iWork / Preview honour); the optional PNG slot uses
    ``public.png`` for apps that only accept raster.
    """
    if sys.platform != "darwin":
        return False
    if not pdf_bytes:
        return False
    try:
        from AppKit import (
            NSPasteboard,
            NSPasteboardTypePDF,
            NSPasteboardTypePNG,
        )
        from Foundation import NSData
    except Exception:
        return False

    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pdf_data = NSData.dataWithBytes_length_(pdf_bytes, len(pdf_bytes))
    ok = bool(pb.setData_forType_(pdf_data, NSPasteboardTypePDF))
    if not ok:
        return False
    if png_bytes:
        png_data = NSData.dataWithBytes_length_(png_bytes, len(png_bytes))
        pb.setData_forType_(png_data, NSPasteboardTypePNG)
    return True
