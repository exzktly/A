"""PlotRenderer adapter — builds matplotlib Figures from real analysis CSVs."""

from __future__ import annotations
from pathlib import Path
from typing import Optional

import numpy as np


class PlotRenderer:
    """Aggregates per-well CSVs for each sample group and renders kinetics charts.

    Usage::

        renderer = PlotRenderer(data_dir="/path/to/out")
        groups = {
            "ctrl":  {"wells": ["A01","A02"], "color": "#0E6B52", "name": "Control"},
            "dose1": {"wells": ["A05","A06"], "color": "#E25C3A", "name": "PF 100nM"},
        }
        fig = renderer.render_kinetics(groups, metric="Mean", normalize=False)
    """

    def __init__(self, data_dir: str = "") -> None:
        self._data_dir: Optional[Path] = Path(data_dir) if data_dir else None
        self._pipeline_info: dict = {}
        self._well_paths: dict[str, Path] = {}    # well_token -> CSV Path
        self._cache: dict[str, list[dict]] = {}   # well_token -> rows
        self._fluor_channels: list[str] = []

    def set_data_dir(self, path: str) -> None:
        self._data_dir = Path(path)
        self._well_paths.clear()
        self._cache.clear()
        self._fluor_channels.clear()
        self._scan()

    def _scan(self) -> None:
        """Discover and cache all well CSVs in data_dir."""
        if not self._data_dir or not self._data_dir.is_dir():
            return
        try:
            from well_viewer.viewer_state import read_pipeline_info, extract_well_token
            from well_viewer.runtime_app import (
                load_well_csv,
                detect_fluor_channels,
            )
            from well_viewer.load_controller import _looks_like_well_measurement_csv
        except ImportError:
            return

        try:
            _, fluor_tokens, _, info = read_pipeline_info(self._data_dir, logger=None)
            self._pipeline_info = info
        except Exception:
            pass

        csvs = sorted(self._data_dir.glob("*.csv"))
        for p in csvs:
            if p.name.startswith("."):
                continue
            try:
                if not _looks_like_well_measurement_csv(p):
                    continue
            except Exception:
                continue
            tok = extract_well_token(p.stem) or p.stem
            rows = load_well_csv(p)
            self._well_paths[tok] = p
            self._cache[tok] = rows
            if not self._fluor_channels and rows:
                self._fluor_channels = detect_fluor_channels(rows)

    def available_wells(self) -> list[str]:
        return list(self._well_paths.keys())

    def render_kinetics(
        self,
        groups: dict,
        metric: str = "Mean",
        normalize: bool = False,
        channel: str = "",
    ) -> Optional[object]:
        """Return a matplotlib Figure, or None on failure.

        *groups* maps group_id → {"wells": [...], "color": "#hex", "name": "..."}
        """
        if not self._cache:
            return None
        try:
            from well_viewer.runtime_app import aggregate_with_threshold, detect_fluor_channels
            from matplotlib.figure import Figure
        except ImportError:
            return None

        # Determine column to plot
        ch = channel.lower() if channel else (self._fluor_channels[0] if self._fluor_channels else "gfp")
        val_col = f"{ch}_mean_intensity"

        # Try to detect from any cached rows if still empty
        if not self._fluor_channels:
            for rows in self._cache.values():
                if rows:
                    self._fluor_channels = detect_fluor_channels(rows)
                    break
        if self._fluor_channels and ch not in self._fluor_channels:
            ch = self._fluor_channels[0]
            val_col = f"{ch}_mean_intensity"

        series: list[tuple[str, str, np.ndarray, np.ndarray]] = []  # (name, color, t, y)

        for gid, spec in groups.items():
            wells = spec.get("wells", [])
            color = spec.get("color", "#888888")
            name = spec.get("name", gid)

            # Aggregate each well, then average across wells per timepoint
            per_well_agg: dict[float, list[float]] = {}
            for w in wells:
                rows = self._cache.get(w)
                if not rows:
                    continue
                pts = aggregate_with_threshold(rows, threshold=0.0, val_col=val_col)
                for tp, mean, *_ in pts:
                    per_well_agg.setdefault(tp, []).append(mean)

            if not per_well_agg:
                continue

            t_arr = np.array(sorted(per_well_agg.keys()), dtype=float)
            y_arr = np.array([np.mean(per_well_agg[tp]) for tp in t_arr], dtype=float)

            if normalize and len(y_arr) > 0:
                baseline = y_arr[0]
                denom = baseline if abs(baseline) > 1e-9 else 1.0
                y_arr = y_arr / denom

            if metric == "Median":
                # Re-aggregate with median
                t_arr2, y_arr2 = [], []
                for tp in sorted(per_well_agg):
                    t_arr2.append(tp)
                    y_arr2.append(float(np.median(per_well_agg[tp])))
                t_arr = np.array(t_arr2)
                y_arr = np.array(y_arr2)
                if normalize and len(y_arr) > 0:
                    baseline = y_arr[0]
                    denom = baseline if abs(baseline) > 1e-9 else 1.0
                    y_arr = y_arr / denom
            elif metric == "Sum":
                t_arr2, y_arr2 = [], []
                for tp in sorted(per_well_agg):
                    t_arr2.append(tp)
                    y_arr2.append(float(np.sum(per_well_agg[tp])))
                t_arr = np.array(t_arr2)
                y_arr = np.array(y_arr2)

            series.append((name, color, t_arr, y_arr))

        if not series:
            return None

        try:
            from ..theme.manager import ThemeManager
            t_map = ThemeManager.instance().tokens
            spine_color = t_map["line"]
            tick_color = t_map["mut"]
        except Exception:
            spine_color, tick_color = "#DED5C2", "#7C786D"

        fig = Figure(facecolor="none")
        ax = fig.add_subplot(111)
        ax.set_facecolor("none")
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines["bottom"].set_color(spine_color)
        ax.spines["left"].set_color(spine_color)
        ax.tick_params(colors=tick_color, labelsize=9)
        ylabel = f"{ch.upper()} mean intensity" + (" (norm.)" if normalize else "")
        ax.set_xlabel("Time (h)", color=tick_color, fontsize=9)
        ax.set_ylabel(ylabel, color=tick_color, fontsize=9)

        for name, color, t_arr, y_arr in series:
            ax.plot(t_arr, y_arr, color=color, linewidth=1.5, label=name)
            ax.fill_between(t_arr, y_arr, alpha=0.06, color=color)
            if len(t_arr):
                ax.plot(t_arr[-1], y_arr[-1], "o", color=color, markersize=5)

        fig.tight_layout(pad=0.8)
        return fig
