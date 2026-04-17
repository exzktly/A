from __future__ import annotations

import csv
import io
import json
import logging
import re
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable

import matplotlib
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from skimage.segmentation import find_boundaries
from tifffile import imread

from ui.theme import ACCENT, BG_APP, BG_PANEL, BG_SIDE, FM_BOLD, FM_TINY, TXT_MUT, TXT_PRI, get_color
from well_viewer.image_resolver import resolve_ref_by_fov_tp
from well_viewer.preview_controller import classify_member, read_member_bytes, scan_zip_members
from well_viewer.viewer_state import make_schema_extractor

matplotlib.use("TkAgg")

logger = logging.getLogger("smfish_tab")


@dataclass
class _ImgRef:
    zip_path: Path | None = None
    zip_member: str | None = None
    disk_path: Path | None = None

    @property
    def name(self) -> str:
        if self.disk_path is not None:
            return self.disk_path.name
        return Path(self.zip_member or "").name


class SmfishTab(tk.Frame):
    def __init__(self, parent: tk.Widget, app=None, **kw):
        super().__init__(parent, bg=BG_APP, **kw)
        self._app = app
        self._out_dir: Path | None = None
        self._separator = "_"
        self._fov_tp_extractor: Callable[[str], tuple[str, str]] | None = None
        self._smfish_tokens: list[str] = []
        self._well_to_zip: dict[str, Path] = {}
        self._current_log_img: np.ndarray | None = None
        self._current_labels: np.ndarray | None = None
        self._current_sorted_vals: np.ndarray | None = None
        self._hover_annot = None
        self._pan_anchor: tuple[float, float, tuple[float, float], tuple[float, float]] | None = None
        self._fit_on_next_redraw = True
        self._show_overlays = True
        self._cdf_popup: tk.Toplevel | None = None
        self._cdf_canvas: FigureCanvasTkAgg | None = None
        self._cdf_ax = None
        self._cdf_fig = None

        self._build_ui()

    def _build_ui(self) -> None:
        right = tk.Frame(self, bg=BG_APP)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._channel_var = tk.StringVar(value="")
        self._fov_var = tk.StringVar(value="")
        self._tp_var = tk.StringVar(value="")
        self._threshold_var = tk.StringVar(value="1500")
        self._lut_min_var = tk.StringVar(value="")
        self._lut_max_var = tk.StringVar(value="")
        self._status_var = tk.StringVar(value="Select a single well from the global picker.")

        panel_bg = get_color("BG_PANEL")
        txt_pri = get_color("TXT_PRI")
        border = get_color("BORDER")
        accent = get_color("ACCENT")

        ctrl = tk.Frame(right, bg=BG_SIDE, pady=6, padx=10)
        ctrl.pack(fill=tk.X, side=tk.TOP)
        tk.Label(ctrl, text="Channel:", font=FM_BOLD, fg=TXT_PRI, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
        self._channel_cb = ttk.Combobox(ctrl, textvariable=self._channel_var, state="readonly", width=12)
        self._channel_cb.pack(side=tk.LEFT, padx=(0, 10))
        self._channel_cb.bind("<<ComboboxSelected>>", self._on_selection_change)
        tk.Label(ctrl, text="FOV:", font=FM_BOLD, fg=TXT_PRI, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
        self._fov_cb = ttk.Combobox(ctrl, textvariable=self._fov_var, state="readonly", width=10)
        self._fov_cb.pack(side=tk.LEFT, padx=(0, 10))
        self._fov_cb.bind("<<ComboboxSelected>>", self._on_selection_change)
        tk.Label(ctrl, text="Timepoint:", font=FM_BOLD, fg=TXT_PRI, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
        self._tp_cb = ttk.Combobox(ctrl, textvariable=self._tp_var, state="readonly", width=12)
        self._tp_cb.pack(side=tk.LEFT, padx=(0, 10))
        self._tp_cb.bind("<<ComboboxSelected>>", self._on_selection_change)
        tk.Label(ctrl, text="smFISH_Thresh:", font=FM_BOLD, fg=TXT_PRI, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
        thr = tk.Entry(ctrl, textvariable=self._threshold_var, bg=panel_bg, fg=txt_pri,
                       relief=tk.FLAT, highlightthickness=1, highlightbackground=border,
                       highlightcolor=accent)
        thr.pack(side=tk.LEFT, padx=(0, 8))
        thr.bind("<Return>", lambda _e: self._redraw())
        thr.bind("<FocusOut>", lambda _e: self._redraw())
        tk.Label(ctrl, text="LUT Min:", font=FM_BOLD, fg=TXT_PRI, bg=BG_SIDE).pack(side=tk.LEFT, padx=(4, 6))
        lut_min = tk.Entry(ctrl, textvariable=self._lut_min_var, width=8, bg=panel_bg, fg=txt_pri,
                           relief=tk.FLAT, highlightthickness=1, highlightbackground=border,
                           highlightcolor=accent)
        lut_min.pack(side=tk.LEFT, padx=(0, 6))
        lut_min.bind("<Return>", lambda _e: self._redraw())
        tk.Label(ctrl, text="LUT Max:", font=FM_BOLD, fg=TXT_PRI, bg=BG_SIDE).pack(side=tk.LEFT, padx=(0, 6))
        lut_max = tk.Entry(ctrl, textvariable=self._lut_max_var, width=8, bg=panel_bg, fg=txt_pri,
                           relief=tk.FLAT, highlightthickness=1, highlightbackground=border,
                           highlightcolor=accent)
        lut_max.pack(side=tk.LEFT, padx=(0, 8))
        lut_max.bind("<Return>", lambda _e: self._redraw())

        btn_row = tk.Frame(right, bg=BG_SIDE, pady=2, padx=10)
        btn_row.pack(fill=tk.X, side=tk.TOP)
        ttk.Button(btn_row, text="Apply Global Threshold", command=self._apply_to_all).pack(side=tk.LEFT, padx=(2, 0))
        ttk.Button(btn_row, text="Refresh", command=self._redraw).pack(side=tk.LEFT, padx=(6, 0))
        self._overlay_btn = ttk.Button(btn_row, text="Hide Overlays", command=self._toggle_overlays)
        self._overlay_btn.pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btn_row, text="This Frame CDF", command=self._open_cdf_popup).pack(side=tk.LEFT, padx=(6, 0))
        tk.Label(right, textvariable=self._status_var, bg=BG_SIDE, fg=TXT_MUT, font=FM_TINY,
                 justify=tk.LEFT, anchor="w").pack(fill=tk.X, padx=10, pady=(0, 6))

        self._fig_img = Figure(figsize=(6, 5), dpi=100)
        self._ax_img = self._fig_img.add_subplot(111)
        self._canvas_img = FigureCanvasTkAgg(self._fig_img, master=right)
        self._canvas_img.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 3))
        self._toolbar = NavigationToolbar2Tk(self._canvas_img, right, pack_toolbar=False)
        self._toolbar.update()
        self._toolbar.pack(fill=tk.X, padx=6, pady=(0, 3))
        self._canvas_img.mpl_connect("motion_notify_event", self._on_img_hover)
        self._canvas_img.mpl_connect("scroll_event", self._on_img_scroll)
        self._canvas_img.mpl_connect("button_press_event", self._on_img_press)
        self._canvas_img.mpl_connect("button_release_event", self._on_img_release)
        self._canvas_img.mpl_connect("motion_notify_event", self._on_img_drag)

    def _toggle_overlays(self) -> None:
        self._show_overlays = not self._show_overlays
        self._overlay_btn.config(text="Hide Overlays" if self._show_overlays else "Show Overlays")
        self._redraw()

    def _open_cdf_popup(self) -> None:
        if self._cdf_popup is not None and self._cdf_popup.winfo_exists():
            self._cdf_popup.lift()
            self._cdf_popup.focus_force()
            self._update_cdf_plot()
            return

        popup = tk.Toplevel(self)
        popup.title("smFISH CDF")
        popup.configure(bg=BG_APP)
        popup.geometry("760x380")
        popup.protocol("WM_DELETE_WINDOW", self._close_cdf_popup)
        self._cdf_popup = popup

        self._cdf_fig = Figure(figsize=(7.2, 3.4), dpi=100)
        self._cdf_ax = self._cdf_fig.add_subplot(111)
        self._cdf_canvas = FigureCanvasTkAgg(self._cdf_fig, master=popup)
        self._cdf_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self._update_cdf_plot()

    def _close_cdf_popup(self) -> None:
        if self._cdf_popup is not None and self._cdf_popup.winfo_exists():
            self._cdf_popup.destroy()
        self._cdf_popup = None
        self._cdf_canvas = None
        self._cdf_ax = None
        self._cdf_fig = None

    def _update_cdf_plot(self) -> None:
        if self._cdf_ax is None:
            return

        log_img = self._current_log_img
        labels = self._current_labels
        thr = self._get_threshold()
        ax = self._cdf_ax
        ax.clear()
        ax.set_facecolor(BG_PANEL)
        if self._cdf_fig is not None:
            self._cdf_fig.patch.set_facecolor(BG_PANEL)

        if log_img is None or labels is None:
            ax.text(0.5, 0.5, "No smFISH image loaded.", transform=ax.transAxes,
                    ha="center", va="center", color=TXT_MUT, fontsize=10)
            if self._cdf_canvas is not None:
                self._cdf_canvas.draw_idle()
            return

        candidate_mask = (log_img > 0) & (labels > 0)
        candidate_ys, candidate_xs = np.where(candidate_mask)
        candidate_vals = log_img[candidate_ys, candidate_xs]
        if candidate_vals.size == 0:
            candidate_mask = labels > 0
            candidate_ys, candidate_xs = np.where(candidate_mask)
            candidate_vals = np.abs(log_img[candidate_ys, candidate_xs])

        debug_limit = min(100, candidate_vals.size)
        logger.debug("smFISH CDF candidate pixel sample (showing %d/%d)", debug_limit, candidate_vals.size)
        for i in range(debug_limit):
            logger.debug(
                "CDF[%03d] x=%d y=%d value=%.6f",
                i,
                int(candidate_xs[i]),
                int(candidate_ys[i]),
                float(candidate_vals[i]),
            )

        vals = np.sort(candidate_vals) if candidate_vals.size else np.array([], dtype=np.float32)
        if vals.size:
            y = np.arange(1, vals.size + 1, dtype=np.float32) / vals.size
            ax.plot(vals, y, color=ACCENT, linewidth=2.0, alpha=0.85)
            ax.fill_between(vals, y, alpha=0.2, color=ACCENT)
        else:
            ax.text(0.5, 0.5, "No candidate values found.", transform=ax.transAxes,
                    ha="center", va="center", color=TXT_MUT, fontsize=10)

        ax.axvline(thr, color="red", linestyle="--", linewidth=2.0, alpha=0.7)
        ax.set_title("CDF of LoG values inside labels", color=TXT_PRI, fontsize=10, fontweight="bold")
        ax.set_xlabel("LoG value", color=TXT_PRI, fontsize=9)
        ax.set_ylabel("Cumulative Probability", color=TXT_PRI, fontsize=9)
        ax.grid(True, alpha=0.2, color=TXT_MUT)
        ax.tick_params(axis="x", colors=TXT_MUT, labelsize=8)
        ax.tick_params(axis="y", colors=TXT_MUT, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(TXT_MUT)
        if self._cdf_canvas is not None:
            self._cdf_canvas.draw_idle()

    def _section_label(self, parent: tk.Widget, text: str) -> None:
        tk.Label(parent, text=text, bg=BG_SIDE, fg=TXT_PRI, font=FM_BOLD).pack(anchor="w", padx=10, pady=(10, 4))

    def _combo(self, parent: tk.Widget, label: str, var: tk.StringVar, callback) -> ttk.Combobox:
        self._section_label(parent, label)
        cb = ttk.Combobox(parent, textvariable=var, state="readonly")
        cb.pack(fill=tk.X, padx=10, pady=(0, 4))
        cb.bind("<<ComboboxSelected>>", callback)
        return cb

    def sync_from_app(self) -> None:
        out_dir = self._app._data_dir if self._app is not None else self._out_dir
        if out_dir is None:
            self._status_var.set("No output loaded.")
            return
        try:
            info_path = out_dir / "pipeline_info.json"
            info = json.loads(info_path.read_text())
            self._smfish_tokens = [str(t).strip() for t in info.get("smfish_tokens", []) if str(t).strip()]
            self._separator = str(info.get("separator", "_"))
            fov_idx = int(info.get("fov_index", -1))
            tp_idx = int(info.get("tp_index", -1))
            if fov_idx >= 0 and tp_idx >= 0:
                self._fov_tp_extractor = make_schema_extractor(self._separator, fov_idx, tp_idx)
            else:
                self._fov_tp_extractor = None
        except Exception as exc:
            messagebox.showerror("Invalid pipeline_info.json", str(exc), parent=self)
            return

        self._out_dir = out_dir
        zips = sorted(out_dir.glob("*_out.zip"))
        self._well_to_zip = {}
        for z in zips:
            m = re.match(r"([A-Ha-h])(\d{1,2})_out\.zip$", z.name)
            if m:
                self._well_to_zip[f"{m.group(1).upper()}{int(m.group(2)):02d}"] = z

        channels = self._smfish_tokens
        self._channel_cb["values"] = channels
        if channels:
            self._channel_var.set(channels[0])
        self._refresh_fov_tp_values()

    def _selected_well_token(self) -> str | None:
        if self._app is None:
            return None
        sels = sorted(self._app._selected_wells, key=lambda lbl: self._app._parse_rc(lbl))
        if len(sels) != 1:
            return None
        tok = self._app._extract_well_token(sels[0]) or sels[0]
        m = re.match(r"([A-Ha-h])(\d{1,2})$", tok.strip())
        if not m:
            return None
        return f"{m.group(1).upper()}{int(m.group(2)):02d}"

    def _selected_well_label(self) -> str | None:
        if self._app is None:
            return None
        sels = sorted(self._app._selected_wells, key=lambda lbl: self._app._parse_rc(lbl))
        return sels[0] if len(sels) == 1 else None

    @staticmethod
    def _norm_well_token(well: str) -> str:
        m = re.match(r"([A-Ha-h])(\d{1,2})$", well.strip())
        if not m:
            return well.strip().upper()
        return f"{m.group(1).upper()}{int(m.group(2)):02d}"

    @staticmethod
    def _norm_id(v: str) -> str:
        t = (v or "").strip()
        if t.isdigit():
            return str(int(t))
        return t

    def _classify_local(self, name: str, fluor_lower: str, fov_tp_extractor=None):
        mask_re = re.compile(r"_labels\.(tif{1,2}|png)$", re.I)
        overlay_re = re.compile(r"_overlay\.(tif{1,2}|png|jpe?g)$", re.I)
        tophat_re = re.compile(r"_tophat_\w+\.tif{1,2}$", re.I)

        def _legacy(stem: str) -> tuple[str, str]:
            parts = stem.split(self._separator)
            if len(parts) >= 2:
                return parts[-2], parts[-1]
            return "unknown", "unknown"

        return classify_member(
            name=name,
            fluor_lower=fluor_lower,
            mask_re=mask_re,
            overlay_re=overlay_re,
            tophat_fluor_re=tophat_re,
            fov_tp_extractor=fov_tp_extractor,
            legacy_extractor=_legacy,
        )

    def _scan_selected_zip(self):
        if self._out_dir is None:
            return {}, {}
        well = self._selected_well_token()
        channel = self._channel_var.get().strip().lower()
        zip_path = self._well_to_zip.get(well)
        if not well or not channel or zip_path is None:
            return {}, {}
        _g, _ov, mask, tophat, smfish = scan_zip_members(
            zip_path=zip_path,
            fluor_lower=channel,
            image_exts={".tif", ".tiff", ".png", ".jpg", ".jpeg"},
            classify_member_fn=self._classify_local,
            imgref_factory=lambda p, m: _ImgRef(zip_path=p, zip_member=m),
            logger=logger,
            fov_tp_extractor=self._fov_tp_extractor,
        )
        source = smfish if smfish else tophat
        return source, mask

    def _refresh_fov_tp_values(self) -> None:
        smfish, mask = self._scan_selected_zip()
        keys = sorted(set(smfish).intersection(mask))
        fovs = sorted({k[0] for k in keys})
        tps = sorted({k[1] for k in keys})
        self._fov_cb["values"] = fovs
        self._tp_cb["values"] = tps
        if fovs:
            self._fov_var.set(fovs[0])
        if tps:
            self._tp_var.set(tps[0])
        self._load_selected_images()

    def _on_selection_change(self, _event=None) -> None:
        if _event is not None and _event.widget == self._channel_cb:
            self._refresh_fov_tp_values()
            return
        self._load_selected_images()

    def _load_selected_images(self) -> None:
        smfish, mask = self._scan_selected_zip()
        fov_raw = self._fov_var.get().strip()
        tp_raw = self._tp_var.get().strip()
        sm_ref = resolve_ref_by_fov_tp(
            smfish,
            fov_raw=fov_raw,
            tp_raw=tp_raw,
            norm_timepoint=lambda value: str(value or "").strip(),
        )
        mk_ref = resolve_ref_by_fov_tp(
            mask,
            fov_raw=fov_raw,
            tp_raw=tp_raw,
            norm_timepoint=lambda value: str(value or "").strip(),
        )
        if sm_ref is None or mk_ref is None:
            self._status_var.set("No smFISH/mask pair found for current selection.")
            return
        sm_raw = read_member_bytes(zip_path=sm_ref.zip_path, member=sm_ref.zip_member, logger=logger)
        mk_raw = read_member_bytes(zip_path=mk_ref.zip_path, member=mk_ref.zip_member, logger=logger)
        if sm_raw is None or mk_raw is None:
            self._status_var.set("Failed to load selected image data.")
            return
        self._current_log_img = imread(io.BytesIO(sm_raw)).astype(np.float32)
        self._current_labels = imread(io.BytesIO(mk_raw))
        vals = self._current_log_img[self._current_labels > 0]
        self._current_sorted_vals = np.sort(vals) if vals.size else np.array([], dtype=np.float32)
        well = self._selected_well_token() or "N/A"
        self._status_var.set(f"Loaded {well} fov={fov_raw} tp={tp_raw}.")
        self._fit_on_next_redraw = True
        self._redraw()

    def _get_threshold(self) -> float:
        try:
            return float(self._threshold_var.get().strip())
        except ValueError:
            return 0.0

    def _redraw(self) -> None:
        if self._current_log_img is None or self._current_labels is None:
            return
        thr = self._get_threshold()
        log_img = self._current_log_img
        labels = self._current_labels
        prev_xlim = self._ax_img.get_xlim()
        prev_ylim = self._ax_img.get_ylim()
        try:
            lut_min = float(self._lut_min_var.get().strip()) if self._lut_min_var.get().strip() else None
        except ValueError:
            lut_min = None
        try:
            lut_max = float(self._lut_max_var.get().strip()) if self._lut_max_var.get().strip() else None
        except ValueError:
            lut_max = None
        spot_mask = (log_img > thr) & (labels > 0)
        ys, xs = np.where(spot_mask)

        self._ax_img.clear()
        self._ax_img.imshow(log_img, cmap="gray", vmin=lut_min, vmax=lut_max)
        bnd = find_boundaries(labels, mode="outer")
        if self._show_overlays:
            self._ax_img.contour(bnd.astype(np.uint8), levels=[0.5], colors="red", linewidths=0.5)
            if xs.size:
                self._ax_img.scatter(xs, ys, s=20, facecolors="none", edgecolors="cyan", linewidths=0.6)
        self._ax_img.set_title(f"Spots above threshold: {int(xs.size)}", color=TXT_PRI, fontsize=10)
        self._ax_img.set_xticks([])
        self._ax_img.set_yticks([])
        if self._fit_on_next_redraw:
            h, w = log_img.shape[:2]
            self._ax_img.set_xlim(-0.5, w - 0.5)
            self._ax_img.set_ylim(h - 0.5, -0.5)
            self._fit_on_next_redraw = False
        else:
            self._ax_img.set_xlim(prev_xlim)
            self._ax_img.set_ylim(prev_ylim)
        if self._hover_annot is None:
            self._hover_annot = self._ax_img.annotate(
                "",
                xy=(0, 0),
                xytext=(8, 8),
                textcoords="offset points",
                color="white",
                fontsize=8,
                bbox=dict(boxstyle="round,pad=0.2", fc="black", ec="white", lw=0.6, alpha=0.8),
            )
            self._hover_annot.set_visible(False)

        self._canvas_img.draw_idle()
        self._update_cdf_plot()

    def _on_img_hover(self, event) -> None:
        if self._current_log_img is None or event.inaxes != self._ax_img:
            if self._hover_annot is not None and self._hover_annot.get_visible():
                self._hover_annot.set_visible(False)
                self._canvas_img.draw_idle()
            return
        if event.xdata is None or event.ydata is None or self._hover_annot is None:
            return
        x = int(round(event.xdata))
        y = int(round(event.ydata))
        h, w = self._current_log_img.shape[:2]
        if not (0 <= x < w and 0 <= y < h):
            self._hover_annot.set_visible(False)
            self._canvas_img.draw_idle()
            return
        if self._current_labels is None or int(self._current_labels[y, x]) <= 0:
            self._hover_annot.set_visible(False)
            self._canvas_img.draw_idle()
            return
        px = float(self._current_log_img[y, x])
        self._hover_annot.xy = (x, y)
        self._hover_annot.set_text(f"({x}, {y}) = {px:.3f}")
        self._hover_annot.set_visible(True)
        self._canvas_img.draw_idle()

    def _on_img_scroll(self, event) -> None:
        if event.inaxes != self._ax_img or event.xdata is None or event.ydata is None:
            return
        scale = 1 / 1.2 if event.button == "up" else 1.2
        xlim = self._ax_img.get_xlim()
        ylim = self._ax_img.get_ylim()
        new_w = (xlim[1] - xlim[0]) * scale
        new_h = (ylim[1] - ylim[0]) * scale
        relx = (event.xdata - xlim[0]) / (xlim[1] - xlim[0]) if xlim[1] != xlim[0] else 0.5
        rely = (event.ydata - ylim[0]) / (ylim[1] - ylim[0]) if ylim[1] != ylim[0] else 0.5
        self._ax_img.set_xlim(event.xdata - new_w * relx, event.xdata + new_w * (1 - relx))
        self._ax_img.set_ylim(event.ydata - new_h * rely, event.ydata + new_h * (1 - rely))
        self._canvas_img.draw_idle()

    def _on_img_press(self, event) -> None:
        if event.inaxes != self._ax_img or event.button != 1 or event.xdata is None or event.ydata is None:
            return
        self._pan_anchor = (event.xdata, event.ydata, self._ax_img.get_xlim(), self._ax_img.get_ylim())

    def _on_img_release(self, _event) -> None:
        self._pan_anchor = None

    def _on_img_drag(self, event) -> None:
        if self._pan_anchor is None or event.inaxes != self._ax_img or event.xdata is None or event.ydata is None:
            return
        x0, y0, xlim0, ylim0 = self._pan_anchor
        dx = event.xdata - x0
        dy = event.ydata - y0
        self._ax_img.set_xlim(xlim0[0] - dx, xlim0[1] - dx)
        self._ax_img.set_ylim(ylim0[0] - dy, ylim0[1] - dy)
        self._canvas_img.draw_idle()

    def _apply_to_all(self) -> None:
        threading.Thread(target=self._apply_to_all_worker, daemon=True).start()

    def _refresh_app_cache(self) -> None:
        if self._app is None:
            return
        for label, path in self._app._well_paths.items():
            if label in self._app._cache:
                self._app._cache[label] = self._app._load_well_csv(path)
        self._app._recalculate_threshold()
        self._app._redraw()

    def _apply_to_all_worker(self) -> None:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        out_dir = self._out_dir
        channel = self._channel_var.get().strip().lower()
        if out_dir is None or not channel:
            self.after(0, lambda: self._status_var.set("Select channel and ensure one well is selected."))
            return
        thr = self._get_threshold()
        col = f"{channel}_smfish_count"
        counts: dict[tuple[str, str, str, str], int] = {}

        def _process_well(well: str, zip_path: Path) -> dict[tuple[str, str, str, str], int]:
            per_well_counts: dict[tuple[str, str, str, str], int] = {}
            g, _ov, mask, _th, smfish = scan_zip_members(
                zip_path=zip_path,
                fluor_lower=channel,
                image_exts={".tif", ".tiff", ".png", ".jpg", ".jpeg"},
                classify_member_fn=self._classify_local,
                imgref_factory=lambda p, m: _ImgRef(zip_path=p, zip_member=m),
                logger=logger,
                fov_tp_extractor=self._fov_tp_extractor,
            )
            _ = g
            for key in sorted(set(smfish).intersection(mask)):
                sm_ref = smfish[key]
                mk_ref = mask[key]
                sm_raw = read_member_bytes(zip_path=sm_ref.zip_path, member=sm_ref.zip_member, logger=logger)
                mk_raw = read_member_bytes(zip_path=mk_ref.zip_path, member=mk_ref.zip_member, logger=logger)
                if sm_raw is None or mk_raw is None:
                    continue
                log_img = imread(io.BytesIO(sm_raw)).astype(np.float32)
                labels = imread(io.BytesIO(mk_raw))
                hits = labels[(labels > 0) & (log_img > thr)].astype(np.int64, copy=False)
                if hits.size:
                    hit_counts = np.bincount(hits)
                    for nid in np.nonzero(hit_counts)[0]:
                        per_well_counts[(well, key[0], key[1], str(int(nid)))] = int(hit_counts[nid])
            return per_well_counts

        wells = sorted(self._well_to_zip.items())
        if wells:
            max_workers = min(8, len(wells))
            self.after(
                0,
                lambda n=len(wells), workers=max_workers: self._status_var.set(
                    f"Applying global threshold across {n} wells using {workers} workers..."
                ),
            )
            completed = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_well = {
                    executor.submit(_process_well, well, zip_path): well
                    for well, zip_path in wells
                }
                for future in as_completed(future_to_well):
                    well = future_to_well[future]
                    completed += 1
                    try:
                        counts.update(future.result())
                    except Exception as e:
                        logger.exception("smFISH global threshold failed for %s: %s", well, e)
                    self.after(
                        0,
                        lambda c=completed, n=len(wells), w=well: self._status_var.set(
                            f"Processed {w} ({c}/{n})..."
                        ),
                    )

        for well in sorted(self._well_to_zip):
            csv_matches = list(out_dir.glob(f"*_{well}.csv"))
            if not csv_matches:
                continue
            csv_path = csv_matches[0]
            with csv_path.open("r", newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
                fieldnames = list(reader.fieldnames or [])
            if col not in fieldnames:
                fieldnames.append(col)

            for row in rows:
                r_well = self._norm_well_token((row.get("well") or well))
                fov = self._norm_id((row.get("fov") or row.get("FOV") or ""))
                tp = self._norm_id((row.get("timepoint") or row.get("tp") or row.get("time") or ""))
                nid = (row.get("nucleus_id") or "").strip()
                key = (r_well, fov, tp, nid)
                row[col] = str(counts.get(key, 0))

            with csv_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

        self.after(0, self._refresh_app_cache)
        self.after(0, lambda: self._status_var.set("Apply to All complete. Line/Bar plots refreshed."))
        self.after(0, lambda: messagebox.showinfo("smFISH", "Apply to All finished.", parent=self))
