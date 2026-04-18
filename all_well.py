"""
all_well.py
-----------
Composition root for the All-Well application.

Tabs:
  • Review  — WellViewerApp (from well_viewer package runtime)
  • Analyze — AnalyzeTab (from analyze_tab.py)

Run:
    python all_well.py [--data_dir /path/to/results]
"""

from __future__ import annotations

import argparse
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ui.theme import (
    BG_APP, BG_SIDE, BORDER, apply_all_well_theme, TXT_PRI, TXT_MUT,
    FM_UI, FM_TITLE, ThemeManager, THEMES, set_theme, get_color,
    update_widget_colors
)

# Global tab-scoped debug toggles.
# Toggle these to True for opt-in debug output in each tab.
REVIEW_TAB_DEBUG = False
ANALYZE_TAB_DEBUG = False
REVIEW_BAR_DEBUG = False
REVIEW_SCATTER_DEBUG = False


class AllWellApp(tk.Tk):
    """Root window containing the Review and Analyze notebook tabs."""

    def __init__(self, data_path: Path | None = None) -> None:
        super().__init__()
        self.title("All-Well")
        self.configure(bg=BG_APP)
        self.minsize(1100, 800)
        self.geometry("1640x980")

        self._review = None
        self._analyze = None
        self._theme_manager = ThemeManager("Dark")
        self._cell_threshold = 0.0  # Shared cell area threshold

        self._apply_outer_theme()
        self._build_ui()
        self._install_app_icon()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if data_path is not None and self._review is not None:
            self.after(150, lambda: self._review.after(
                0, lambda: self._review._load_path(data_path)))

    def _apply_outer_theme(self) -> None:
        s = ttk.Style(self)
        apply_all_well_theme(s)

    def _build_ui(self) -> None:
        from analyze_tab import AnalyzeTab
        from well_viewer import WellViewerApp

        container = tk.Frame(self, bg=BG_APP)
        container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # ── App header bar ────────────────────────────────────────────────
        self._theme_frame = tk.Frame(container, bg=BG_SIDE)
        self._theme_frame.pack(side=tk.TOP, fill=tk.X)

        tk.Label(
            self._theme_frame, text="All-Well",
            font=FM_TITLE, fg=TXT_PRI, bg=BG_SIDE,
        ).pack(side=tk.LEFT, padx=(14, 0), pady=7)

        self._theme_var = tk.StringVar(value="Dark")
        self._theme_dropdown = ttk.Combobox(
            self._theme_frame,
            textvariable=self._theme_var,
            values=["Dark", "Light"],
            state="readonly",
            width=8,
        )
        self._theme_dropdown.pack(side=tk.RIGHT, padx=(0, 14), pady=7)
        self._theme_dropdown.bind("<<ComboboxSelected>>", self._on_theme_change)

        self._theme_label = tk.Label(
            self._theme_frame, text="Theme:", bg=BG_SIDE, fg=TXT_MUT, font=FM_UI,
        )
        self._theme_label.pack(side=tk.RIGHT, padx=(0, 6), pady=7)

        tk.Frame(container, bg=BORDER, height=1).pack(fill=tk.X)

        # ── Notebook ──────────────────────────────────────────────────────
        self._nb = ttk.Notebook(container, style="AllWell.TNotebook")
        self._nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        review_frame = tk.Frame(self._nb, bg=BG_APP)
        self._nb.add(review_frame, text="  Review  ")

        self._review = WellViewerApp(review_frame)
        self._review.pack(fill=tk.BOTH, expand=True)

        analyze_frame = tk.Frame(self._nb, bg=BG_APP)
        self._nb.add(analyze_frame, text="  Analyze  ")

        self._analyze = AnalyzeTab(
            analyze_frame,
            on_pipeline_complete=self._on_analyze_pipeline_complete,
        )
        self._analyze.pack(fill=tk.BOTH, expand=True)

        self._nb.select(0)
        self._nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_theme_change(self, _event=None) -> None:
        """Handle theme selection change."""
        from ui.theme import rebuild_widget_colors, get_color

        theme_name = self._theme_var.get()
        old_theme = self._theme_manager.current_theme

        # Switch theme and update module colors
        self._theme_manager.set_theme(theme_name)
        set_theme(theme_name)

        # Apply TTK style changes
        s = ttk.Style(self)
        apply_all_well_theme(s, theme_name)

        # Use smart semantic-aware rebuild that properly handles color name collisions
        # (when multiple color names map to same hex value like BG_APP and BG_PANEL)
        rebuild_widget_colors(self, old_theme, theme_name)

        # Update root window background
        self.configure(bg=get_color("BG_APP"))

        # Update header frame and label backgrounds
        if hasattr(self, "_theme_frame"):
            bg_color = get_color("BG_SIDE")
            self._theme_frame.configure(bg=bg_color)
            self._theme_label.configure(bg=bg_color)

        # Notify child components of theme change
        if self._review is not None and hasattr(self._review, "_on_theme_change"):
            self._review._on_theme_change(theme_name)

        self._install_app_icon()

    def _install_app_icon(self) -> None:
        """Install Option 1 app icon: highlighted well + sparkline."""
        size = 64
        img = tk.PhotoImage(width=size, height=size)
        bg = get_color("BG_APP")
        panel = get_color("BG_SIDE")
        accent = get_color("ACCENT")
        muted = get_color("TXT_MUT")
        white = "#FFFFFF"

        img.put(bg, to=(0, 0, size, size))
        img.put(panel, to=(6, 6, size - 6, size - 6))

        def _disk(cx: int, cy: int, r: int, color: str) -> None:
            for y in range(cy - r, cy + r + 1):
                for x in range(cx - r, cx + r + 1):
                    if 0 <= x < size and 0 <= y < size and ((x - cx) ** 2 + (y - cy) ** 2 <= r * r):
                        img.put(color, (x, y))

        # 2x2 microplate wells
        _disk(22, 22, 7, muted)
        _disk(42, 22, 7, muted)
        _disk(22, 42, 7, muted)
        _disk(42, 42, 7, accent)  # highlighted well

        # Sparkline overlay (simple stepped polyline)
        for x, y in [(12, 46), (18, 42), (24, 44), (30, 36), (36, 38), (42, 30), (48, 28)]:
            img.put(white, to=(x, y, x + 2, y + 2))

        self._app_icon = img  # keep ref alive
        try:
            self.iconphoto(True, self._app_icon)
        except Exception:
            pass

    def _on_tab_change(self, _event=None) -> None:
        if self._review is None:
            return
        try:
            tab_text = self._nb.tab(self._nb.select(), "text").strip()
        except tk.TclError:
            return
        if tab_text == "Review":
            self.after(50, self._nudge_review)

    def _on_analyze_pipeline_complete(self, output_dir: Path) -> None:
        """Switch to Review tab and load the dataset that was just analyzed."""
        if self._review is None:
            return
        dataset_path = output_dir
        if output_dir.name.lower() == "out" and (output_dir.parent / "in").is_dir():
            dataset_path = output_dir.parent
        self._nb.select(0)
        self.after(50, lambda: self._review._load_path(dataset_path))

    def _nudge_review(self) -> None:
        if self._review is None:
            return
        if hasattr(self._review, "_redraw"):
            self._review._redraw()
        if hasattr(self._review, "_redraw_bars"):
            self._review._redraw_bars()

    def _on_close(self) -> None:
        if self._review is not None and hasattr(self._review, "_cleanup_tmp"):
            self._review._cleanup_tmp()
        if self._analyze is not None:
            self._analyze.destroy()
        self.destroy()

    def get_cell_threshold(self) -> float:
        """Get the current cell area threshold from the Analyze tab."""
        if self._analyze is not None and hasattr(self._analyze, "_cell_properties_tab"):
            if self._analyze._cell_properties_tab is not None:
                return self._analyze._cell_properties_tab.get_threshold()
        return 0.0

    def set_cell_threshold(self, value: float) -> None:
        """Set the cell area threshold in the Analyze tab."""
        if self._analyze is not None and hasattr(self._analyze, "_cell_properties_tab"):
            if self._analyze._cell_properties_tab is not None:
                self._analyze._cell_properties_tab._threshold_var.set(str(value))
        self._cell_threshold = value


def main() -> None:
    from well_viewer import debug_flags as _debug_flags

    _debug_flags.REVIEW_TAB_DEBUG = REVIEW_TAB_DEBUG
    _debug_flags.ANALYZE_TAB_DEBUG = ANALYZE_TAB_DEBUG
    _debug_flags.REVIEW_BAR_DEBUG = REVIEW_BAR_DEBUG
    _debug_flags.REVIEW_SCATTER_DEBUG = REVIEW_SCATTER_DEBUG
    _debug_flags.BAR_DEBUG = REVIEW_BAR_DEBUG

    ap = argparse.ArgumentParser(
        description="All-Well: pipeline runner + well viewer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument(
        "--data_dir",
        type=Path,
        default=None,
        help="Pre-load a results directory into the Review tab on startup.",
    )
    args = ap.parse_args()
    AllWellApp(data_path=args.data_dir).mainloop()


if __name__ == "__main__":
    main()
