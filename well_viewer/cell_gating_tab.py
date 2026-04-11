"""Cell Gating tab widget extracted from runtime_app."""

from __future__ import annotations

import tkinter as tk
from typing import Optional

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from ui.theme import (
    ACCENT,
    BG_APP,
    BG_PANEL,
    BG_SIDE,
    BORDER,
    FM_BOLD,
    FM_MONO,
    FM_TINY,
    FM_UI,
    TXT_MUT,
    TXT_PRI,
    TXT_SEC,
    WARN,
)
from ui.theme import get_color

try:
    import numpy as _np
    _NP_AVAILABLE = True
except ImportError:
    _np = None  # type: ignore[assignment]
    _NP_AVAILABLE = False


class CellGatingTab(tk.Frame):
    """Tab for cell inclusion gating (FluorGating) and per-channel settings."""

    def __init__(self, parent: tk.Widget, app, **kw):
        super().__init__(parent, bg=BG_APP, **kw)
        self._app = app
        self._cell_areas: list[float] = []
        self._cell_area_threshold = tk.StringVar(value="0.0")  # Cell area gating threshold
        self._fluor_gates: dict[str, tk.StringVar] = {}  # channel -> threshold StringVar
        self._thresh_frac_on: dict[str, tk.StringVar] = {}  # channel -> ThreshFracOn StringVar
        self._fluor_data: dict[str, list[float]] = {}  # channel -> list of values
        self._figure: Optional[Figure] = None
        self._canvas: Optional[FigureCanvasTkAgg] = None
        self._ax: Optional[any] = None
        self._axes_stack: list[tuple] = []  # For zoom history
        self._gating_controls_frame: Optional[tk.Frame] = None
        self._plot_canvas: Optional[tk.Canvas] = None
        self._plot_inner: Optional[tk.Frame] = None
        self._plot_canvas_window: Optional[int] = None
        self._plot_scrollbar: Optional[tk.Scrollbar] = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the UI layout."""
        # Main vertical layout
        main_frame = tk.Frame(self, bg=BG_APP)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ── Top: Control panels ────────────────────────────────────────
        control_frame = tk.Frame(main_frame, bg=BG_SIDE, height=100)
        control_frame.pack(fill=tk.X, padx=8, pady=8)

        # Cell area gating threshold
        cell_area_frame = tk.Frame(control_frame, bg=BG_SIDE)
        cell_area_frame.pack(fill=tk.X, padx=4, pady=(4, 8))

        tk.Label(
            cell_area_frame, text="Cell Area Threshold (pixels):",
            font=FM_UI, fg=TXT_PRI, bg=BG_SIDE
        ).pack(side=tk.LEFT, padx=(0, 8))

        cell_area_entry = tk.Entry(
            cell_area_frame,
            textvariable=self._cell_area_threshold,
            font=FM_MONO,
            fg=ACCENT,
            bg=BG_PANEL,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightcolor=ACCENT,
            highlightbackground=BORDER,
            width=10
        )
        cell_area_entry.pack(side=tk.LEFT, padx=(0, 8))
        cell_area_entry.bind("<FocusOut>", self._on_gating_change)
        cell_area_entry.bind("<Return>", self._on_gating_change)

        # Title for FluorGating (cell inclusion)
        tk.Label(
            control_frame, text="FluorGating (Cell Inclusion)",
            font=FM_BOLD, fg=TXT_PRI, bg=BG_SIDE
        ).pack(fill=tk.X, padx=4, pady=(4, 8))

        # Scrollable frame for per-channel gating controls
        canvas = tk.Canvas(control_frame, bg=BG_SIDE, highlightthickness=0, bd=0, height=80)
        scrollbar = tk.Scrollbar(control_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_SIDE)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._gating_controls_frame = scrollable_frame

        # ── Bottom: CDF plot (scrollable) ──────────────────────────────
        plot_frame = tk.Frame(main_frame, bg=BG_APP)
        plot_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        plot_scroll_frame = tk.Frame(plot_frame, bg=BG_APP)
        plot_scroll_frame.pack(fill=tk.BOTH, expand=True)

        self._plot_canvas = tk.Canvas(plot_scroll_frame, bg=BG_APP, highlightthickness=0, bd=0)
        self._plot_scrollbar = tk.Scrollbar(plot_scroll_frame, orient=tk.VERTICAL, command=self._plot_canvas.yview)
        self._plot_canvas.configure(yscrollcommand=self._plot_scrollbar.set)

        self._plot_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._plot_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._plot_inner = tk.Frame(self._plot_canvas, bg=BG_APP)
        self._plot_canvas_window = self._plot_canvas.create_window((0, 0), window=self._plot_inner, anchor="nw")

        self._plot_inner.bind(
            "<Configure>",
            lambda _e: self._plot_canvas.configure(scrollregion=self._plot_canvas.bbox("all"))
        )
        self._plot_canvas.bind(
            "<Configure>",
            lambda e: self._plot_canvas.itemconfigure(self._plot_canvas_window, width=e.width)
        )

        self._figure = Figure(figsize=(8, 5), dpi=100, facecolor=BG_APP)
        self._canvas = FigureCanvasTkAgg(self._figure, master=self._plot_inner)
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Toolbar
        toolbar_frame = tk.Frame(plot_frame, bg=BG_APP)
        toolbar = NavigationToolbar2Tk(self._canvas, toolbar_frame)
        toolbar.update()
        toolbar_frame.pack(fill=tk.X)

        # Status label
        self._status_label = tk.Label(
            main_frame, text="No data loaded",
            font=FM_TINY, fg=TXT_MUT, bg=BG_APP
        )
        self._status_label.pack(fill=tk.X, padx=8, pady=(0, 8))

    def _build_channel_controls(self) -> None:
        """Build per-channel gating controls."""
        # Clear existing controls
        for widget in self._gating_controls_frame.winfo_children():
            widget.destroy()

        channels = self._app._fluor_channels
        if not channels:
            tk.Label(
                self._gating_controls_frame,
                text="No channels loaded",
                font=FM_UI,
                fg=TXT_MUT,
                bg=BG_SIDE
            ).pack(fill=tk.X, padx=4, pady=4)
            # Force redraw
            self._gating_controls_frame.update_idletasks()
            return

        for channel in channels:
            # Channel label
            ch_frame = tk.Frame(self._gating_controls_frame, bg=BG_SIDE)
            ch_frame.pack(fill=tk.X, padx=4, pady=4)

            tk.Label(
                ch_frame,
                text=f"{channel.upper()} Channel:",
                font=FM_BOLD,
                fg=TXT_SEC,
                bg=BG_SIDE,
                width=18,
                anchor="w"
            ).pack(side=tk.LEFT, padx=(0, 8))

            # FluorGating threshold input
            if channel not in self._fluor_gates:
                self._fluor_gates[channel] = tk.StringVar(value="0.0")

            tk.Label(
                ch_frame,
                text="FluorGating:",
                font=FM_UI,
                fg=TXT_MUT,
                bg=BG_SIDE
            ).pack(side=tk.LEFT, padx=(0, 4))

            gate_entry = tk.Entry(
                ch_frame,
                textvariable=self._fluor_gates[channel],
                font=FM_MONO,
                fg=ACCENT,
                bg=BG_PANEL,
                relief=tk.FLAT,
                highlightthickness=1,
                highlightcolor=ACCENT,
                highlightbackground=BORDER,
                width=10
            )
            gate_entry.pack(side=tk.LEFT, padx=(0, 12))
            gate_entry.bind("<FocusOut>", self._on_gating_change)
            gate_entry.bind("<Return>", self._on_gating_change)

            # ThreshFracOn input
            if channel not in self._thresh_frac_on:
                self._thresh_frac_on[channel] = tk.StringVar(value="50.0")

            tk.Label(
                ch_frame,
                text="ThreshFracOn:",
                font=FM_UI,
                fg=TXT_MUT,
                bg=BG_SIDE
            ).pack(side=tk.LEFT, padx=(0, 4))

            thresh_entry = tk.Entry(
                ch_frame,
                textvariable=self._thresh_frac_on[channel],
                font=FM_MONO,
                fg=ACCENT,
                bg=BG_PANEL,
                relief=tk.FLAT,
                highlightthickness=1,
                highlightcolor=ACCENT,
                highlightbackground=BORDER,
                width=10
            )
            thresh_entry.pack(side=tk.LEFT, padx=(0, 8))
            thresh_entry.bind("<FocusOut>", self._on_threshold_frac_on_change)
            thresh_entry.bind("<Return>", self._on_threshold_frac_on_change)

        # Force redraw of the scrollable frame
        self._gating_controls_frame.update_idletasks()

    def _load_cell_areas(self) -> None:
        """Load cell areas and fluorescence values from currently loaded wells."""
        self._cell_areas = []
        self._fluor_data: dict[str, list[float]] = {}  # channel -> list of values

        # Get cell areas and fluorescence values from all loaded wells
        for label in self._app._well_paths:
            rows = self._app._get_rows(label)
            for row in rows:
                # Get cell area
                try:
                    area = float(row.get("area_px", 0))
                    if area > 0:
                        self._cell_areas.append(area)
                except (ValueError, TypeError):
                    pass

                # Get fluorescence values for each channel
                for channel in self._app._fluor_channels:
                    val_col = f"{channel}_mean_intensity"
                    try:
                        val = float(row.get(val_col, 0))
                        if val > 0:
                            if channel not in self._fluor_data:
                                self._fluor_data[channel] = []
                            self._fluor_data[channel].append(val)
                    except (ValueError, TypeError):
                        pass

        # Build per-channel controls
        self._build_channel_controls()

        if self._cell_areas:
            self._axes_stack = []  # Reset zoom history
            self._plot_cdf()
            self._status_label.config(
                text=f"Loaded {len(self._cell_areas)} cells",
                fg=TXT_PRI
            )
        else:
            self._status_label.config(
                text="No cell data found",
                fg=TXT_MUT
            )

    def _plot_cdf(self) -> None:
        """Plot CDFs for cell area and all fluorescence channels."""
        if not self._cell_areas and not self._fluor_data:
            return

        bg_app = get_color("BG_APP")
        bg_panel = get_color("BG_PANEL")
        txt_pri = get_color("TXT_PRI")
        txt_mut = get_color("TXT_MUT")
        accent = get_color("ACCENT")
        warn = get_color("WARN")

        self._figure.clf()
        self._figure.set_facecolor(bg_app)

        # Determine number of plots needed (cell area + channels)
        n_plots = 1 + len(self._fluor_data)  # 1 for cell area, rest for channels

        # Create subplots (2 columns max) and scale figure height so labels do not overlap.
        n_cols = 1 if n_plots == 1 else 2
        n_rows = (n_plots + n_cols - 1) // n_cols
        plot_height_per_row = 3.8
        fig_height = max(5.0, n_rows * plot_height_per_row)
        self._figure.set_size_inches(8.0, fig_height, forward=True)

        axes = []
        for i in range(n_plots):
            ax = self._figure.add_subplot(n_rows, n_cols, i + 1, facecolor=bg_panel)
            axes.append(ax)

        # Plot cell area CDF
        if self._cell_areas:
            areas = _np.array(sorted(self._cell_areas))
            cdf = _np.arange(1, len(areas) + 1) / len(areas)
            axes[0].plot(areas, cdf, linewidth=2, color=accent, alpha=0.8)
            axes[0].fill_between(areas, cdf, alpha=0.2, color=accent)
            axes[0].set_xlabel("Cell Area (pixels)", color=txt_pri, fontsize=9)
            axes[0].set_ylabel("Cumulative Probability", color=txt_pri, fontsize=9)
            axes[0].set_title("Cell Area Distribution", color=txt_pri, fontsize=10, fontweight="bold")
            axes[0].grid(True, alpha=0.2, color=txt_mut)
            axes[0].tick_params(colors=txt_mut, labelsize=8)

            # Add cell area threshold line
            try:
                cell_area_threshold = float(self._cell_area_threshold.get())
                axes[0].axvline(x=cell_area_threshold, color=warn, linestyle="--", linewidth=2, alpha=0.7)
            except ValueError:
                pass

        # Plot CDFs for each fluorescence channel
        colors = [accent, "#FF9500", "#FF3B30", "#34C759"]  # Predefined colors
        for idx, (channel, values) in enumerate(sorted(self._fluor_data.items()), 1):
            if idx < len(axes):
                ax = axes[idx]
                color = colors[idx % len(colors)]
                vals = _np.array(sorted(values))
                cdf = _np.arange(1, len(vals) + 1) / len(vals)
                ax.plot(vals, cdf, linewidth=2, color=color, alpha=0.8)
                ax.fill_between(vals, cdf, alpha=0.2, color=color)
                ax.set_xlabel(f"{channel.upper()} Intensity", color=txt_pri, fontsize=9)
                ax.set_ylabel("Cumulative Probability", color=txt_pri, fontsize=9)
                ax.set_title(f"{channel.upper()} Distribution", color=txt_pri, fontsize=10, fontweight="bold")
                ax.grid(True, alpha=0.2, color=txt_mut)
                ax.tick_params(colors=txt_mut, labelsize=8)

                # Add FluorGating threshold line for this channel
                try:
                    fluor_gate = float(self._fluor_gates[channel].get())
                    ax.axvline(x=fluor_gate, color=warn, linestyle="--", linewidth=2, alpha=0.7)
                except (ValueError, KeyError):
                    pass

        self._ax = axes[0]  # Keep reference to first axis for zoom

        # Save current axis limits for zoom
        if not self._axes_stack:
            limits = [(ax.get_xlim(), ax.get_ylim()) for ax in axes]
            self._axes_stack.append(limits)

        self._figure.tight_layout(pad=1.3)
        self._canvas.draw()

        # Ensure the embedded widget matches figure pixel size so the frame can scroll.
        figure_widget = self._canvas.get_tk_widget()
        dpi = self._figure.get_dpi()
        fig_h_px = max(1, int(self._figure.get_figheight() * dpi))
        figure_widget.configure(height=fig_h_px)
        figure_widget.update_idletasks()
        if self._plot_canvas is not None:
            self._plot_canvas.configure(scrollregion=self._plot_canvas.bbox("all"))

    def _on_gating_change(self, _e=None) -> None:
        """Handle FluorGating threshold change (when focus leaves field)."""
        try:
            # Validate cell area threshold
            float(self._cell_area_threshold.get())
            # Validate all inputs
            for channel in self._fluor_gates:
                float(self._fluor_gates[channel].get())
            # Redraw the CDF with new thresholds
            self._axes_stack = []
            self._plot_cdf()
            # Redraw the app to reflect the new thresholds
            self._app._redraw()
        except ValueError:
            # Invalid input - revert to previous value (do nothing, field keeps old value)
            pass

    def _on_threshold_frac_on_change(self, _e=None) -> None:
        """Handle ThreshFracOn threshold change (when focus leaves field)."""
        try:
            # Validate all inputs
            for channel in self._thresh_frac_on:
                float(self._thresh_frac_on[channel].get())
            # Save the values
            self._save_threshold_frac_on()
            # Redraw the app to reflect the new thresholds
            self._app._redraw()
        except ValueError:
            # Invalid input - revert to previous value (do nothing, field keeps old value)
            pass

    def _save_threshold_frac_on(self) -> None:
        """Save ThreshFracOn values for all channels."""
        # Store in app state for persistence
        if not hasattr(self._app, '_thresh_frac_on_saved'):
            self._app._thresh_frac_on_saved = {}
        for channel, var in self._thresh_frac_on.items():
            try:
                self._app._thresh_frac_on_saved[channel] = float(var.get())
            except ValueError:
                pass

    def _load_threshold_frac_on(self) -> None:
        """Load saved ThreshFracOn values for all channels."""
        if hasattr(self._app, '_thresh_frac_on_saved'):
            for channel, value in self._app._thresh_frac_on_saved.items():
                if channel in self._thresh_frac_on:
                    self._thresh_frac_on[channel].set(str(value))

    def get_fluor_gate(self, channel: str) -> float:
        """Get FluorGating threshold for a channel."""
        if channel in self._fluor_gates:
            try:
                return float(self._fluor_gates[channel].get())
            except ValueError:
                return 0.0
        return 0.0

    def get_thresh_frac_on(self, channel: str) -> float:
        """Get ThreshFracOn threshold for a channel."""
        if channel in self._thresh_frac_on:
            try:
                return float(self._thresh_frac_on[channel].get())
            except ValueError:
                return 50.0
        return 50.0

    def update_theme_colors_rebuild(self, old_theme: str, new_theme: str) -> None:
        """Recolor CDF panel and redraw plots when runtime theme changes."""
        bg_app = get_color("BG_APP")
        self.configure(bg=bg_app)
        if self._figure is not None:
            self._figure.set_facecolor(bg_app)
        if self._canvas is not None:
            self._canvas.get_tk_widget().configure(bg=bg_app)
        if self._cell_areas or self._fluor_data:
            self._plot_cdf()
