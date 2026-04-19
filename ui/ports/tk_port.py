from __future__ import annotations


class TkUIPort:
    """Legacy Tk UI port removed after PySide6 migration completion."""

    def __init__(self, *args, **kwargs) -> None:
        raise RuntimeError(
            "TkUIPort is no longer available. The application is now PySide6-only."
        )
