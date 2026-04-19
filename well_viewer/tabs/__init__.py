"""Tab builder modules for each centre-notebook tab.

Each module exposes a single ``build_*_tab(app, parent)`` function that
fills a pre-created tk.Frame with the controls and figure for that tab.
``centre_view.build_centre`` creates the frames, adds them to the notebook,
and then calls each builder here.
"""

import tkinter as tk
from tkinter import ttk


def _make_action_button(parent: tk.Widget, *, text: str, command, style: str) -> ttk.Button:
    """Primary action button with the shared tab-toolbar style."""
    return ttk.Button(parent, text=text, command=command, style=style, cursor="hand2")


def _make_secondary_button(parent: tk.Widget, *, text: str, command) -> ttk.Button:
    """Neutral toolbar button with the ActionSecondary style."""
    return ttk.Button(parent, text=text, command=command,
                      style="ActionSecondary.TButton", cursor="hand2")
