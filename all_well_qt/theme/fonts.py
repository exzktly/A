"""Register application fonts at boot time."""

from __future__ import annotations
import logging
import os

_logger = logging.getLogger(__name__)
_FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")


def register_fonts() -> None:
    """Load Geist and Instrument Serif from the fonts/ directory.

    Falls back silently to system stack if TTFs are missing — the QSS
    font-family declarations already list appropriate fallbacks.
    """
    try:
        from PySide6.QtGui import QFontDatabase
    except ImportError:
        return

    wanted = [
        "Geist-Regular.ttf",
        "Geist-Medium.ttf",
        "Geist-SemiBold.ttf",
        "Geist-Bold.ttf",
        "GeistMono-Regular.ttf",
        "InstrumentSerif-Regular.ttf",
        "InstrumentSerif-Italic.ttf",
    ]
    missing = []
    for name in wanted:
        path = os.path.join(_FONTS_DIR, name)
        if os.path.isfile(path):
            QFontDatabase.addApplicationFont(path)
        else:
            missing.append(name)

    if missing:
        _logger.warning(
            "Font TTFs not found (falling back to system stack): %s. "
            "Place them in %s to enable custom typography.",
            ", ".join(missing),
            _FONTS_DIR,
        )
