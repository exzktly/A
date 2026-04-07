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
from tkinter import filedialog, messagebox, ttk
from typing import Callable

import matplotlib
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from skimage.segmentation import find_boundaries
from tifffile import imread

from ui.theme import ACCENT, BG_APP, BG_PANEL, BG_SIDE, BORDER, FM_BOLD, FM_TINY, TXT_MUT, TXT_PRI
from well_viewer.preview_controller import classify_member, read_member_bytes, scan_zip_members
from well_viewer.state import make_schema_extractor

matplotlib.use("TkAgg")


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
    def __init__(self, parent: tk.Widget, **kw):
        super().__init__(parent, bg=BG_APP, **kw)
        self._out_dir: Path | None = None
        self._separator = "_"
        self._fov_tp_extractor: Callable[[str], tuple[str, str]] | None = None
        self._smfish_tokens: list[str] = []
        self._well_to_zip: dict[str, Path] = {}
        self._current_log_img: np.ndarray | None = None
        self._current_labels: np.ndarray | None = None
        self._current_sorted_vals: np.ndarray | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        left = tk.Frame(self, bg=BG_SIDE, width=300)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        l_canvas = tk.Canvas(left, bg=BG_SIDE, highlightthickness=0)
        l_scroll = tk.Scrollbar(left, orient=tk.VERTICAL, command=l_canvas.yview)
        l_inner = tk.Frame(l_canvas, bg=BG_SIDE)
        l_inner.bind("<Configure>", lambda _e: l_canvas.configure(scrollregion=l_canvas.bbox("all")))
        l_canvas.create_window((0, 0), window=l_inner, anchor="nw")
        l_canvas.configure(yscrollcommand=l_scroll.set)
        l_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        l_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        right = tk.Frame(self, bg=BG_APP)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._output_var = tk.StringVar(value="")
        self._channel_var = tk.StringVar(value="")
        self._well_var = tk.StringVar(value="")
        self._fov_var = tk.StringVar(value="")
        self._tp_var = tk.StringVar(value="")
        self._threshold_var = tk.StringVar(value="0.0")
        self._status_var = tk.StringVar(value="Select an output folder.")

        self._section_label(l_inner, "Output folder")
        out_row = tk.Frame(l_inner, bg=BG_SIDE)
        out_row.pack(fill=tk.X, padx=10, pady=(0, 8))
        tk.Entry(out_row, textvariable=self._output_var, state=tk.DISABLED, relief=tk.FLAT,
                 bg=BG_PANEL, fg=TXT_PRI, highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(out_row, text="Browse...", command=self._browse_output).pack(side=tk.LEFT, padx=(6, 0))

        self._channel_cb = self._combo(l_inner, "Channel", self._channel_var, self._on_selection_change)
        self._well_cb = self._combo(l_inner, "Well", self._well_var, self._on_selection_change)
        self._fov_cb = self._combo(l_inner, "FOV", self._fov_var, self._on_selection_change)
        self._tp_cb = self._combo(l_inner, "Timepoint", self._tp_var, self._on_selection_change)

        self._section_label(l_inner, "smFISH_Thresh")
        thr = tk.Entry(l_inner, textvariable=self._threshold_var, bg=BG_PANEL, fg=TXT_PRI,
                       relief=tk.FLAT, highlightthickness=1, highlightbackground=BORDER,
                       highlightcolor=ACCENT)
        thr.pack(fill=tk.X, padx=10, pady=(0, 8))
        thr.bind("<Return>", lambda _e: self._redraw())

        ttk.Button(l_inner, text="Apply to All", command=self._apply_to_all).pack(anchor="w", padx=10, pady=(0, 8))
        tk.Label(l_inner, textvariable=self._status_var, bg=BG_SIDE, fg=TXT_MUT, font=FM_TINY,
                 wraplength=260, justify=tk.LEFT, anchor="w").pack(fill=tk.X, padx=10, pady=(4, 6))

        self._fig_img = Figure(figsize=(6, 5), dpi=100)
        self._ax_img = self._fig_img.add_subplot(111)
        self._canvas_img = FigureCanvasTkAgg(self._fig_img, master=right)
        self._canvas_img.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 3))

        self._fig_cdf = Figure(figsize=(6, 2.7), dpi=100)
        self._ax_cdf = self._fig_cdf.add_subplot(111)
        self._canvas_cdf = FigureCanvasTkAgg(self._fig_cdf, master=right)
        self._canvas_cdf.get_tk_widget().pack(fill=tk.BOTH, expand=False, padx=6, pady=(3, 6))

    def _section_label(self, parent: tk.Widget, text: str) -> None:
        tk.Label(parent, text=text, bg=BG_SIDE, fg=TXT_PRI, font=FM_BOLD).pack(anchor="w", padx=10, pady=(10, 4))

    def _combo(self, parent: tk.Widget, label: str, var: tk.StringVar, callback) -> ttk.Combobox:
        self._section_label(parent, label)
        cb = ttk.Combobox(parent, textvariable=var, state="readonly")
        cb.pack(fill=tk.X, padx=10, pady=(0, 4))
        cb.bind("<<ComboboxSelected>>", callback)
        return cb

    def _browse_output(self) -> None:
        p = filedialog.askdirectory(title="Select output folder")
        if not p:
            return
        out_dir = Path(p)
        info_path = out_dir / "pipeline_info.json"
        if not info_path.exists():
            messagebox.showerror("Missing file", f"pipeline_info.json not found in:\n{out_dir}", parent=self)
            return
        try:
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
        self._output_var.set(str(out_dir))
        zips = sorted(out_dir.glob("*_out.zip"))
        self._well_to_zip = {}
        for z in zips:
            m = re.match(r"([A-Ha-h])(\d{1,2})_out\.zip$", z.name)
            if m:
                self._well_to_zip[f"{m.group(1).upper()}{int(m.group(2)):02d}"] = z

        channels = self._smfish_tokens
        self._channel_cb["values"] = channels
        self._well_cb["values"] = sorted(self._well_to_zip)
        if channels:
            self._channel_var.set(channels[0])
        if self._well_cb["values"]:
            self._well_var.set(self._well_cb["values"][0])
        self._refresh_fov_tp_values()

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
        well = self._well_var.get().strip()
        channel = self._channel_var.get().strip().lower()
        zip_path = self._well_to_zip.get(well)
        if not well or not channel or zip_path is None:
            return {}, {}
        g, _ov, mask, _th, smfish = scan_zip_members(
            zip_path=zip_path,
            fluor_lower=channel,
            image_exts={".tif", ".tiff", ".png", ".jpg", ".jpeg"},
            classify_member_fn=self._classify_local,
            imgref_factory=lambda p, m: _ImgRef(zip_path=p, zip_member=m),
            logger=logging.getLogger("smfish_tab"),
            fov_tp_extractor=self._fov_tp_extractor,
        )
        _ = g
        return smfish, mask

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
        if _event is not None and _event.widget in (self._channel_cb, self._well_cb):
            self._refresh_fov_tp_values()
            return
        self._load_selected_images()

    def _load_selected_images(self) -> None:
        smfish, mask = self._scan_selected_zip()
        key = (self._fov_var.get().strip(), self._tp_var.get().strip())
        sm_ref = smfish.get(key)
        mk_ref = mask.get(key)
        if sm_ref is None or mk_ref is None:
            self._status_var.set("No smFISH/mask pair found for current selection.")
            return
        sm_raw = read_member_bytes(zip_path=sm_ref.zip_path, member=sm_ref.zip_member, logger=logging.getLogger("smfish_tab"))
        mk_raw = read_member_bytes(zip_path=mk_ref.zip_path, member=mk_ref.zip_member, logger=logging.getLogger("smfish_tab"))
        if sm_raw is None or mk_raw is None:
            self._status_var.set("Failed to load selected image data.")
            return
        self._current_log_img = imread(io.BytesIO(sm_raw)).astype(np.float32)
        self._current_labels = imread(io.BytesIO(mk_raw))
        vals = self._current_log_img[self._current_labels > 0]
        self._current_sorted_vals = np.sort(vals) if vals.size else np.array([], dtype=np.float32)
        self._status_var.set(f"Loaded {self._well_var.get()} fov={key[0]} tp={key[1]}.")
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
        spot_mask = (log_img > thr) & (labels > 0)
        ys, xs = np.where(spot_mask)

        self._ax_img.clear()
        self._ax_img.imshow(log_img, cmap="gray")
        bnd = find_boundaries(labels, mode="outer")
        self._ax_img.contour(bnd.astype(np.uint8), levels=[0.5], colors="red", linewidths=0.5)
        if xs.size:
            self._ax_img.scatter(xs, ys, s=10, c="cyan", edgecolors="none")
        self._ax_img.set_title(f"Spots above threshold: {int(xs.size)}", color=TXT_PRI, fontsize=10)
        self._ax_img.set_xticks([])
        self._ax_img.set_yticks([])

        self._ax_cdf.clear()
        vals = self._current_sorted_vals if self._current_sorted_vals is not None else np.array([])
        if vals.size:
            y = np.arange(1, vals.size + 1, dtype=np.float32) / vals.size
            self._ax_cdf.plot(vals, y, color="white", linewidth=1.0)
        self._ax_cdf.axvline(thr, color="red", linestyle="--", linewidth=1.0)
        self._ax_cdf.set_title("CDF of LoG values inside labels", color=TXT_PRI, fontsize=9)
        self._ax_cdf.set_xlabel("LoG value", color=TXT_PRI, fontsize=8)
        self._ax_cdf.set_ylabel("CDF", color=TXT_PRI, fontsize=8)

        self._canvas_img.draw_idle()
        self._canvas_cdf.draw_idle()

    def _apply_to_all(self) -> None:
        threading.Thread(target=self._apply_to_all_worker, daemon=True).start()

    def _apply_to_all_worker(self) -> None:
        out_dir = self._out_dir
        channel = self._channel_var.get().strip().lower()
        if out_dir is None or not channel:
            self.after(0, lambda: self._status_var.set("Select output folder and channel first."))
            return
        thr = self._get_threshold()
        col = f"{channel}_smfish_count"
        counts: dict[tuple[str, str, str, str], int] = {}

        wells = sorted(self._well_to_zip.items())
        for i, (well, zip_path) in enumerate(wells, start=1):
            self.after(0, lambda i=i, n=len(wells), w=well: self._status_var.set(f"Processing {w} ({i}/{n})..."))
            g, _ov, mask, _th, smfish = scan_zip_members(
                zip_path=zip_path,
                fluor_lower=channel,
                image_exts={".tif", ".tiff", ".png", ".jpg", ".jpeg"},
                classify_member_fn=self._classify_local,
                imgref_factory=lambda p, m: _ImgRef(zip_path=p, zip_member=m),
                logger=logging.getLogger("smfish_tab"),
                fov_tp_extractor=self._fov_tp_extractor,
            )
            _ = g
            for key in sorted(set(smfish).intersection(mask)):
                sm_ref = smfish[key]
                mk_ref = mask[key]
                sm_raw = read_member_bytes(zip_path=sm_ref.zip_path, member=sm_ref.zip_member, logger=logging.getLogger("smfish_tab"))
                mk_raw = read_member_bytes(zip_path=mk_ref.zip_path, member=mk_ref.zip_member, logger=logging.getLogger("smfish_tab"))
                if sm_raw is None or mk_raw is None:
                    continue
                log_img = imread(io.BytesIO(sm_raw)).astype(np.float32)
                labels = imread(io.BytesIO(mk_raw))
                for nid in np.unique(labels):
                    if nid == 0:
                        continue
                    nuc_mask = labels == nid
                    counts[(well, key[0], key[1], str(int(nid)))] = int(np.sum(log_img[nuc_mask] > thr))

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
                r_well = (row.get("well") or well).strip().upper()
                fov = (row.get("fov") or row.get("FOV") or "").strip()
                tp = (row.get("timepoint") or row.get("tp") or row.get("time") or "").strip()
                nid = (row.get("nucleus_id") or "").strip()
                key = (r_well, fov, tp, nid)
                row[col] = str(counts.get(key, 0))

            with csv_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

        self.after(0, lambda: self._status_var.set("Apply to All complete."))
        self.after(0, lambda: messagebox.showinfo("smFISH", "Apply to All finished.", parent=self))
