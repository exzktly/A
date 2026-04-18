"""
analyze_tab.py
--------------
Standalone AnalyzeTab widget — submission 1 of 2 for all_well.py.

Run this file directly to test the Analyze tab in isolation:
    python analyze_tab.py

In the final all_well.py this module will be imported and embedded inside
the outer "Analyze" notebook tab.

Input-folder resolution rules (applied when Run is pressed):
  1. Folder is named "in"           → input = folder,     output = parent/"out"
  2. Folder contains a sub-dir "in" → input = folder/"in", output = folder/"out"
  3. Folder has >10 TIF files       → move TIFs to folder/"in",
                                       input = folder/"in", output = folder/"out"
  4. Otherwise                      → error; user must supply a valid input folder

process_microscopy_v2.py is located relative to this file (same directory).
The pipeline runs as a subprocess so crashes don't affect the UI.
"""

from __future__ import annotations

import csv
import queue
import shutil
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from services.input_resolution_service import resolve_input_output, tif_files_in
from services.pipeline_service import (
    build_pipeline_args,
    collect_available_fovs,
    collect_available_timepoints,
    find_pipeline_script,
    spawn_pipeline,
    write_pipeline_info,
)

# ---------------------------------------------------------------------------
# Shared visual constants from ui.theme tokens so Analyze and Review tabs use
# the same palette while keeping this file independently runnable.
# ---------------------------------------------------------------------------
import sys as _sys
from ui.theme import (
    ACCENT,
    ACCENT_DARK,
    BG_APP,
    BG_PANEL,
    BG_SIDE,
    BORDER,
    CLR_DANGER,
    CLR_SUCCESS,
    CLR_WHITE,
    SANS as _SANS_TOKEN,
    TXT_MUT,
    TXT_PRI,
    TXT_SEC,
    WARN,
)

_MONO = "Menlo"      if _sys.platform == "darwin" else "Consolas"
_SANS = "SF Pro Text" if _sys.platform == "darwin" else _SANS_TOKEN

FM_MONO  = (_MONO, 9)
FM_UI    = (_SANS, 9)
FM_BOLD  = (_SANS, 9, "bold")
FM_TINY  = (_MONO, 8)
FM_H2    = (_SANS, 10, "bold")

CLR_ACCENT_DARK = ACCENT_DARK

_HERE = Path(__file__).resolve().parent
_PIPELINE_SCRIPT = _HERE / "process_microscopy_v2.py"


# Schema vocabulary — kept in sync with process_microscopy_v2.py
SCHEMA_FIELDS  = ("experiment", "channel", "well", "fov", "timepoint", "ignore")
DEFAULT_SCHEMA = "experiment:channel:well:fov:timepoint"
DEFAULT_SEP    = "_"

# Human-readable labels shown in the dropdowns (same order as SCHEMA_FIELDS).
_SCHEMA_LABELS = ("Experiment", "Channel", "Well", "FOV", "Timepoint", "— ignore —")
# Map label → field name
_LABEL_TO_FIELD = dict(zip(_SCHEMA_LABELS, SCHEMA_FIELDS))
# Map field name → label
_FIELD_TO_LABEL = dict(zip(SCHEMA_FIELDS, _SCHEMA_LABELS))


def _validate_schema_mappings() -> None:
    """
    Defensive consistency check for schema dropdown mappings.

    Keeps _SCHEMA_LABELS, _LABEL_TO_FIELD, and _FIELD_TO_LABEL in sync so
    schema UI labels always round-trip to the expected parser fields.
    """
    if len(_SCHEMA_LABELS) != len(SCHEMA_FIELDS):
        raise RuntimeError("Schema label/field length mismatch.")
    for label in _SCHEMA_LABELS:
        field = _LABEL_TO_FIELD.get(label)
        if field is None:
            raise RuntimeError(f"Missing mapping for schema label: {label!r}")
        if _FIELD_TO_LABEL.get(field) != label:
            raise RuntimeError(
                f"Schema mapping is not invertible for label: {label!r}"
            )


_validate_schema_mappings()

# Representative placeholder tokens shown in the live preview.
_PREVIEW_TOKENS = {
    "experiment": "Exp01",
    "well":       "B03",
    "fov":        "F001",
    "timepoint":  "02d04h30m",
    "ignore":     "X",
}



# Compatibility alias for local call sites
_tif_files_in = tif_files_in

import re as _re_well
_WELL_NAME_RE = _re_well.compile(r"^[A-Ha-h]\d{1,2}$")


def _has_well_content(folder: Path) -> bool:
    """Return True if *folder* contains zip files OR well-named subdirectories."""
    if any(folder.glob("*.zip")):
        return True
    try:
        return any(_WELL_NAME_RE.match(p.name) for p in folder.iterdir() if p.is_dir())
    except OSError:
        return False


def _count_well_content(folder: Path) -> int:
    """Count well zips + well-named subdirectories inside *folder*."""
    zips = list(folder.glob("*.zip"))
    folders = [p for p in folder.iterdir() if p.is_dir() and _WELL_NAME_RE.match(p.name)]
    return len(zips) or len(folders)

# ---------------------------------------------------------------------------
# AnalyzeTab
# ---------------------------------------------------------------------------
class AnalyzeTab(tk.Frame):
    """
    Left: pipeline options form.
    Right: live subprocess log.
    """

    def __init__(
        self,
        parent: tk.Widget,
        *,
        on_pipeline_complete: Callable[[Path], None] | None = None,
        **kw,
    ):
        super().__init__(parent, bg=BG_APP, **kw)
        self._proc:    Optional[subprocess.Popen] = None   # type: ignore[type-arg]
        self._log_q:   queue.Queue[str] = queue.Queue()
        self._running  = False
        self._well_total: int = 0   # total wells expected this run
        self._well_done:  int = 0   # wells completed so far
        self._on_pipeline_complete = on_pipeline_complete
        self._last_output_dir: Path | None = None

        self._build_ui()
        self._poll_log()   # start the Tk-safe log polling loop

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # Top separator line
        tk.Frame(self, bg=BORDER, height=1).pack(fill=tk.X)

        # Main horizontal split: form (left) | log (right)
        pane = tk.PanedWindow(self, orient=tk.HORIZONTAL,
                              bg=BG_APP, sashwidth=5,
                              sashrelief=tk.FLAT, bd=0)
        pane.pack(fill=tk.BOTH, expand=True)

        # ── Left: scrollable form ──────────────────────────────────────
        left_outer = tk.Frame(pane, bg=BG_SIDE, width=340)
        pane.add(left_outer, minsize=280)

        # Canvas + scrollbar for the form
        form_canvas = tk.Canvas(left_outer, bg=BG_SIDE,
                                highlightthickness=0, bd=0)
        vsb = tk.Scrollbar(left_outer, orient=tk.VERTICAL,
                           command=form_canvas.yview,
                           relief=tk.FLAT, width=8,
                           bg=BORDER, troughcolor=BG_SIDE)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        form_canvas.configure(yscrollcommand=vsb.set)

        self._form = tk.Frame(form_canvas, bg=BG_SIDE)
        self._form_win = form_canvas.create_window(
            (0, 0), window=self._form, anchor="nw")

        def _on_configure(_e=None):
            form_canvas.configure(scrollregion=form_canvas.bbox("all"))
        def _on_canvas_resize(e):
            form_canvas.itemconfig(self._form_win, width=e.width)

        self._form.bind("<Configure>", _on_configure)
        form_canvas.bind("<Configure>", _on_canvas_resize)

        # ── Mousewheel scroll (macOS + Linux + Windows) ────────────────
        def _on_mousewheel(event):
            """Scroll the form canvas on trackpad / mousewheel events."""
            # macOS delivers delta in units of 120 per notch on a wheel,
            # or fractional values for trackpad momentum scrolling.
            # Linux uses Button-4/5 instead.
            if event.num == 4:          # Linux scroll up
                form_canvas.yview_scroll(-1, "units")
            elif event.num == 5:        # Linux scroll down
                form_canvas.yview_scroll(1, "units")
            else:                       # macOS / Windows
                form_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(widget):
            """Recursively bind mousewheel events to *widget* and all descendants."""
            widget.bind("<MouseWheel>", _on_mousewheel, add="+")   # macOS / Windows
            widget.bind("<Button-4>",   _on_mousewheel, add="+")   # Linux up
            widget.bind("<Button-5>",   _on_mousewheel, add="+")   # Linux down
            for child in widget.winfo_children():
                _bind_mousewheel(child)

        # Bind to the canvas itself now; after the form is built we re-bind
        # to pick up all the child widgets that don't exist yet.
        form_canvas.bind("<MouseWheel>", _on_mousewheel, add="+")
        form_canvas.bind("<Button-4>",   _on_mousewheel, add="+")
        form_canvas.bind("<Button-5>",   _on_mousewheel, add="+")

        # Store so _build_form can call it after all widgets are created.
        self._bind_form_scroll = lambda: _bind_mousewheel(self._form)

        self._build_form(self._form)

        # Bind scroll to every widget now that the form is fully populated.
        self._bind_form_scroll()

        # ── Right: log panel ───────────────────────────────────────────
        right = tk.Frame(pane, bg=BG_APP)
        pane.add(right, minsize=300)
        self._build_log(right)

    def _section(self, parent: tk.Frame, title: str) -> tk.Frame:
        """Return a labelled section frame."""
        tk.Label(parent, text=title, font=FM_H2,
                 fg=TXT_PRI, bg=BG_SIDE,
                 padx=12).pack(fill=tk.X, anchor="w", pady=(8, 2))
        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=(0, 6))
        body = tk.Frame(parent, bg=BG_SIDE)
        body.pack(fill=tk.X, padx=12, pady=(0, 8))
        return body

    def _row(self, parent: tk.Frame, label: str) -> tk.Frame:
        """Return a two-column label+widget row."""
        row = tk.Frame(parent, bg=BG_SIDE)
        row.pack(fill=tk.X, pady=2)
        tk.Label(row, text=label, font=FM_UI, fg=TXT_SEC,
                 bg=BG_SIDE, width=20, anchor="w").pack(side=tk.LEFT)
        right = tk.Frame(row, bg=BG_SIDE)
        right.pack(side=tk.LEFT, fill=tk.X, expand=True)
        return right

    def _entry(self, parent: tk.Frame, textvariable: tk.StringVar,
               width: int = 10) -> tk.Entry:
        e = tk.Entry(parent, textvariable=textvariable,
                     font=FM_MONO, fg=ACCENT, bg=BG_PANEL,
                     relief=tk.FLAT, highlightthickness=1,
                     highlightcolor=ACCENT, highlightbackground=BORDER,
                     width=width)
        e.pack(side=tk.LEFT)
        return e

    def _build_form(self, parent: tk.Frame) -> None:
        """Populate the left-side form."""
        tk.Frame(parent, bg=BG_SIDE, height=8).pack()
        self._build_schema_section(parent)
        self._build_channel_tokens_section(parent)
        self._build_folders_section(parent)
        # Now that schema/channel/folder widgets exist, run the initial preview.
        self._refresh_schema_preview()
        self._build_tophat_section(parent)
        self._build_output_options_section(parent)
        self._build_compute_options_section(parent)
        self._build_run_controls(parent)

    def _build_schema_section(self, parent: tk.Frame) -> None:
        sec_schema = self._section(parent, "Filename Schema")

        sep_row = self._row(sec_schema, "Separator char")
        self._filename_sep = tk.StringVar(value=DEFAULT_SEP)
        self._entry(sep_row, self._filename_sep, width=3)
        tk.Label(
            sep_row,
            text="character between fields",
            font=FM_TINY,
            fg=TXT_MUT,
            bg=BG_SIDE,
        ).pack(side=tk.LEFT, padx=(6, 0))

        default_fields = DEFAULT_SCHEMA.split(":")
        self._schema_vars = []
        self._schema_cbs = []
        for pos_idx in range(5):
            row = self._row(sec_schema, f"Position {pos_idx + 1}")
            var = tk.StringVar(value=_FIELD_TO_LABEL.get(default_fields[pos_idx], "— ignore —"))
            self._schema_vars.append(var)
            cb = ttk.Combobox(
                row,
                textvariable=var,
                values=list(_SCHEMA_LABELS),
                state="readonly",
                width=14,
                font=FM_UI,
            )
            cb.pack(side=tk.LEFT)
            self._schema_cbs.append(cb)
            cb.bind("<<ComboboxSelected>>", lambda e, v=var, c=cb: self._on_combobox_selected(v, c))
            var.trace_add("write", lambda *_: self._refresh_schema_preview())

        self._filename_sep.trace_add("write", lambda *_: self._refresh_schema_preview())

        schema_str_row = self._row(sec_schema, "Schema string")
        self._schema_str_var = tk.StringVar(value=DEFAULT_SCHEMA)
        self._schema_str_entry = tk.Entry(
            schema_str_row,
            textvariable=self._schema_str_var,
            font=FM_MONO,
            fg=ACCENT,
            bg=BG_PANEL,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightcolor=ACCENT,
            highlightbackground=BORDER,
            width=30,
        )
        self._schema_str_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._schema_str_entry.bind("<Return>", lambda _e: self._sync_dropdowns_from_string())
        self._schema_str_entry.bind("<FocusOut>", lambda _e: self._sync_dropdowns_from_string())
        self._schema_str_entry.bind("<Tab>", lambda _e: self._sync_dropdowns_from_string())

        self._schema_err_lbl = tk.Label(
            sec_schema,
            text="",
            font=FM_TINY,
            fg=CLR_DANGER,
            bg=BG_SIDE,
            anchor="w",
            wraplength=280,
            justify=tk.LEFT,
        )
        self._schema_err_lbl.pack(anchor="w", pady=(2, 0))
        self._schema_preview_lbl = tk.Label(
            sec_schema,
            text="",
            font=FM_MONO,
            fg=TXT_MUT,
            bg=BG_SIDE,
            anchor="w",
            wraplength=280,
            justify=tk.LEFT,
        )
        self._schema_preview_lbl.pack(anchor="w", pady=(0, 2))

    def _build_channel_tokens_section(self, parent: tk.Frame) -> None:
        sec = self._section(parent, "Channel Tokens")
        self._segmentation_method = tk.StringVar(value="stardist_nuclei")
        self._cytoplasm_token = tk.StringVar(value="")
        self._min_nucleus_area_px = tk.StringVar(value="50")

        seg_row = self._row(sec, "Segmentation")
        ttk.Combobox(
            seg_row,
            textvariable=self._segmentation_method,
            values=("stardist_nuclei", "stardist_seeded_watershed_cell"),
            state="readonly",
            width=30,
            font=FM_UI,
        ).pack(side=tk.LEFT)
        self._segmentation_method.trace_add("write", lambda *_: self._refresh_segmentation_hints())

        self._nuclear_token = tk.StringVar(value="NIR")
        nuc_row = self._row(sec, "Nuclear (seg)")
        self._entry(nuc_row, self._nuclear_token)
        tk.Label(
            nuc_row,
            text="segmentation + quantified",
            font=FM_TINY,
            fg=TXT_MUT,
            bg=BG_SIDE,
        ).pack(side=tk.LEFT, padx=(6, 0))
        self._nuclear_token.trace_add("write", lambda *_: self._refresh_schema_preview())
        self._nuclear_token.trace_add("write", lambda *_: self._refresh_segmentation_hints())

        tk.Label(
            sec,
            text="Fluorescent channels",
            font=FM_BOLD,
            fg=TXT_PRI,
            bg=BG_SIDE,
        ).pack(anchor="w", pady=(6, 2))
        tk.Label(
            sec,
            text="Mark smFISH channels with the checkbox on each row.",
            font=FM_TINY,
            fg=TXT_MUT,
            bg=BG_SIDE,
        ).pack(anchor="w", pady=(0, 2))
        self._fluor_frame = tk.Frame(sec, bg=BG_SIDE)
        self._fluor_frame.pack(fill=tk.X)
        self._fluor_vars = []
        self._fluor_smfish_vars: list[tk.BooleanVar] = []
        self._fluor_add_row("GFP")
        self._fluor_add_btn = ttk.Button(sec, text="+ Add channel",
                                         command=self._fluor_add_row,
                                         style="SideAccent.TButton")
        self._fluor_add_btn.pack(anchor="w", pady=(2, 0))

        self._cyto_row = self._row(sec, "Cytoplasm token")
        self._cytoplasm_entry = self._entry(self._cyto_row, self._cytoplasm_token, width=10)
        self._cytoplasm_token.trace_add("write", lambda *_: self._refresh_segmentation_hints())
        self._area_row = self._row(sec, "Min nucleus area")
        self._min_nucleus_area_entry = self._entry(self._area_row, self._min_nucleus_area_px, width=6)
        tk.Label(
            self._area_row,
            text="pixels (watershed)",
            font=FM_TINY,
            fg=TXT_MUT,
            bg=BG_SIDE,
        ).pack(side=tk.LEFT, padx=(6, 0))
        self._min_nucleus_area_px.trace_add("write", lambda *_: self._refresh_segmentation_hints())
        self._segmentation_hint_lbl = tk.Label(
            sec,
            text="",
            font=FM_TINY,
            fg=TXT_MUT,
            bg=BG_SIDE,
            anchor="w",
            wraplength=280,
            justify=tk.LEFT,
        )
        self._segmentation_hint_lbl.pack(anchor="w", pady=(2, 0))
        self._refresh_segmentation_hints()

    def _build_folders_section(self, parent: tk.Frame) -> None:
        sec = self._section(parent, "Folders")
        in_row = tk.Frame(sec, bg=BG_SIDE)
        in_row.pack(fill=tk.X, pady=2)
        tk.Label(in_row, text="Input folder", font=FM_BOLD, fg=TXT_PRI, bg=BG_SIDE).pack(anchor="w")
        in_pick = tk.Frame(sec, bg=BG_SIDE)
        in_pick.pack(fill=tk.X, pady=(0, 2))
        self._input_var = tk.StringVar()
        self._input_entry = tk.Entry(
            in_pick,
            textvariable=self._input_var,
            font=FM_TINY,
            fg=TXT_PRI,
            bg=BG_PANEL,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightcolor=ACCENT,
            highlightbackground=BORDER,
            state=tk.DISABLED,
        )
        self._input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._browse_btn = ttk.Button(in_pick, text="Browse…",
                                      command=self._browse_input,
                                      style="Secondary.TButton",
                                      state="disabled")
        self._browse_btn.pack(side=tk.LEFT, padx=(4, 0))
        self._input_var.trace_add("write", lambda *_: self._refresh_output())

        self._folder_lock_lbl = tk.Label(
            sec,
            text="Define the filename schema above first.",
            font=FM_TINY,
            fg=TXT_MUT,
            bg=BG_SIDE,
            anchor="w",
        )
        self._folder_lock_lbl.pack(anchor="w", pady=(0, 2))

        tk.Label(sec, text="Output folder (auto)", font=FM_BOLD, fg=TXT_PRI, bg=BG_SIDE).pack(
            anchor="w", pady=(6, 0)
        )
        self._output_var = tk.StringVar(value="—")
        self._output_lbl = tk.Label(
            sec,
            textvariable=self._output_var,
            font=FM_TINY,
            fg=TXT_MUT,
            bg=BG_SIDE,
            anchor="w",
            wraplength=280,
            justify=tk.LEFT,
        )
        self._output_lbl.pack(anchor="w")

        self._layout_lbl = tk.Label(
            sec,
            text="",
            font=FM_TINY,
            fg=CLR_DANGER,
            bg=BG_SIDE,
            anchor="w",
            wraplength=280,
            justify=tk.LEFT,
        )
        self._layout_lbl.pack(anchor="w", pady=(2, 0))

    def _build_tophat_section(self, parent: tk.Frame) -> None:
        sec = self._section(parent, "Top-Hat Background Subtraction")
        self._tophat_radius_nir = tk.StringVar(value="100")
        self._tophat_radius_fluor = tk.StringVar(value="100")
        self._no_tophat_nir = tk.BooleanVar(value=False)
        self._no_tophat_fluor = tk.BooleanVar(value=False)
        for lbl, rvar, dvar in (
            ("Nuclear radius", self._tophat_radius_nir, self._no_tophat_nir),
            ("Fluor radius", self._tophat_radius_fluor, self._no_tophat_fluor),
        ):
            row = self._row(sec, lbl)
            self._entry(row, rvar, width=6)
            tk.Checkbutton(
                row,
                text="Disable",
                variable=dvar,
                font=FM_TINY,
                fg=TXT_MUT,
                bg=BG_SIDE,
                activebackground=BG_SIDE,
                selectcolor=BG_PANEL,
            ).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(
            sec,
            text="Fluor radius applies to all fluorescent channels.",
            font=FM_TINY,
            fg=TXT_MUT,
            bg=BG_SIDE,
        ).pack(anchor="w", pady=(2, 0))

    def _build_output_options_section(self, parent: tk.Frame) -> None:
        sec = self._section(parent, "Output Options")
        self._compress_input_well_folders = tk.BooleanVar(value=True)
        self._compress_output_well_folders = tk.BooleanVar(value=True)
        self._csv_prefix = tk.StringVar(value="gfp_measurements")
        for txt, var in (
            ("Folder mode only: Compress input well folders to .zip", self._compress_input_well_folders),
            ("Folder mode only: Compress output well folders to .zip", self._compress_output_well_folders),
        ):
            tk.Checkbutton(
                sec,
                text=txt,
                variable=var,
                font=FM_UI,
                fg=TXT_PRI,
                bg=BG_SIDE,
                activebackground=BG_SIDE,
                selectcolor=BG_PANEL,
            ).pack(anchor="w", pady=1)
        r = self._row(sec, "CSV prefix")
        self._entry(r, self._csv_prefix, width=18)

    def _build_compute_options_section(self, parent: tk.Frame) -> None:
        sec = self._section(parent, "Compute Options")
        self._tf_threads = tk.StringVar(value="0")
        self._workers = tk.StringVar(value="0")
        self._cpu_only = tk.BooleanVar(value=False)
        self._force = tk.BooleanVar(value=False)

        row = self._row(sec, "TF threads (0=auto)")
        self._entry(row, self._tf_threads, width=4)
        tk.Label(row, text="(0 → auto-select 4)", font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        workers_row = self._row(sec, "Workers (0=auto)")
        self._entry(workers_row, self._workers, width=4)
        tk.Label(workers_row, text="(process count override)", font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        for txt, var in (
            ("CPU only (disable GPU)", self._cpu_only),
            ("Force reprocess all wells", self._force),
        ):
            tk.Checkbutton(
                sec,
                text=txt,
                variable=var,
                font=FM_UI,
                fg=TXT_PRI,
                bg=BG_SIDE,
                activebackground=BG_SIDE,
                selectcolor=BG_PANEL,
            ).pack(anchor="w", pady=1)

    def _build_run_controls(self, parent: tk.Frame) -> None:
        btn_frame = tk.Frame(parent, bg=BG_SIDE, padx=12, pady=10)
        btn_frame.pack(fill=tk.X)

        self._run_btn = ttk.Button(btn_frame, text="▶  Run Pipeline",
                                   command=self._run, style="Run.TButton")
        self._run_btn.pack(side=tk.LEFT)

        self._stop_btn = ttk.Button(btn_frame, text="■  Stop",
                                    command=self._stop, style="Stop.TButton",
                                    state="disabled")
        self._stop_btn.pack(side=tk.LEFT, padx=(8, 0))

    # ------------------------------------------------------------------
    # Fluorescent channel list helpers
    # ------------------------------------------------------------------
    def _fluor_add_row(self, default_token: str = "") -> None:
        """Append a new fluorescent channel row to the fluor frame."""
        var = tk.StringVar(value=default_token)
        self._fluor_vars.append(var)
        var.trace_add("write", lambda *_: self._refresh_schema_preview())

        row = tk.Frame(self._fluor_frame, bg=BG_SIDE)
        row.pack(fill=tk.X, pady=1)

        entry = tk.Entry(
            row, textvariable=var,
            font=FM_MONO, fg=ACCENT, bg=BG_PANEL,
            relief=tk.FLAT, highlightthickness=1,
            highlightcolor=ACCENT, highlightbackground=BORDER,
            width=10)
        entry.pack(side=tk.LEFT)

        # Remove button — disabled when only one channel remains.
        remove_btn = ttk.Button(row, text="✕", style="SideMuted.TButton",
                                command=lambda r=row, v=var: self._fluor_remove_row(r, v))
        remove_btn.pack(side=tk.LEFT, padx=(4, 0))
        smfish_var = tk.BooleanVar(value=False)
        self._fluor_smfish_vars.append(smfish_var)
        tk.Checkbutton(
            row, text="smFISH", variable=smfish_var,
            font=FM_TINY, fg=TXT_MUT, bg=BG_SIDE,
            activebackground=BG_SIDE, selectcolor=BG_PANEL,
        ).pack(side=tk.LEFT, padx=(8, 0))

        self._fluor_refresh_remove_buttons()
        self._refresh_schema_preview()
        # Bind scroll to the newly created widgets.
        if hasattr(self, "_bind_form_scroll"):
            self._bind_form_scroll()

    def _fluor_remove_row(self, row_frame: tk.Frame, var: tk.StringVar) -> None:
        """Remove a fluorescent channel row (never removes the last one)."""
        if len(self._fluor_vars) <= 1:
            return
        idx = self._fluor_vars.index(var)
        self._fluor_smfish_vars.pop(idx)
        self._fluor_vars.remove(var)
        row_frame.destroy()
        self._fluor_refresh_remove_buttons()
        self._refresh_schema_preview()

    def _fluor_refresh_remove_buttons(self) -> None:
        """Enable/disable all remove buttons based on current channel count."""
        only_one = len(self._fluor_vars) == 1
        for widget in self._fluor_frame.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, tk.Button) and child.cget("text") == "✕":
                    child.config(state=tk.DISABLED if only_one else tk.NORMAL)

    def _fluor_tokens_list(self) -> list[str]:
        """Return non-empty token strings from the fluor channel list."""
        return [v.get().strip() for v in self._fluor_vars if v.get().strip()]

    def _segmentation_validation_errors(self) -> list[str]:
        errors: list[str] = []
        method = self._segmentation_method.get().strip() or "stardist_nuclei"
        if method == "stardist_seeded_watershed_cell":
            cytoplasm_token = self._cytoplasm_token.get().strip()
            nuclear_token = self._nuclear_token.get().strip()
            if not cytoplasm_token:
                errors.append("Watershed mode requires a cytoplasm token.")
            if cytoplasm_token and cytoplasm_token == nuclear_token:
                errors.append("Cytoplasm token must differ from nuclear token.")
            try:
                area = int(self._min_nucleus_area_px.get().strip())
                if area <= 0:
                    errors.append("Minimum nucleus area must be a positive integer.")
            except ValueError:
                errors.append("Minimum nucleus area must be a positive integer.")
        return errors

    def _refresh_segmentation_hints(self) -> None:
        if not hasattr(self, "_segmentation_hint_lbl"):
            return
        method = self._segmentation_method.get().strip() or "stardist_nuclei"
        controls_enabled = method == "stardist_seeded_watershed_cell"
        if hasattr(self, "_cyto_row"):
            cyto_row_frame = self._cyto_row.master
            if controls_enabled and not cyto_row_frame.winfo_ismapped():
                cyto_row_frame.pack(fill=tk.X, pady=2, before=self._segmentation_hint_lbl)
            elif not controls_enabled and cyto_row_frame.winfo_ismapped():
                cyto_row_frame.pack_forget()
        if hasattr(self, "_area_row"):
            area_row_frame = self._area_row.master
            if controls_enabled and not area_row_frame.winfo_ismapped():
                area_row_frame.pack(fill=tk.X, pady=2, before=self._segmentation_hint_lbl)
            elif not controls_enabled and area_row_frame.winfo_ismapped():
                area_row_frame.pack_forget()
        if hasattr(self, "_cytoplasm_entry"):
            self._cytoplasm_entry.config(state=tk.NORMAL if controls_enabled else tk.DISABLED)
        if hasattr(self, "_min_nucleus_area_entry"):
            self._min_nucleus_area_entry.config(state=tk.NORMAL if controls_enabled else tk.DISABLED)
        if method == "stardist_seeded_watershed_cell":
            errors = self._segmentation_validation_errors()
            if errors:
                self._segmentation_hint_lbl.config(text="  ".join(errors), fg=CLR_DANGER)
            else:
                self._segmentation_hint_lbl.config(
                    text="Watershed mode uses StarDist seeds + cytoplasm mask and also quantifies the cytoplasm channel.",
                    fg=TXT_MUT,
                )
        else:
            self._segmentation_hint_lbl.config(
                text="Default mode: StarDist nuclei segmentation (backward compatible).",
                fg=TXT_MUT,
            )

    def _smfish_tokens_list(self) -> list[str]:
        return [v.get().strip() for v, sm in
                zip(self._fluor_vars, self._fluor_smfish_vars)
                if sm.get() and v.get().strip()]

    # ------------------------------------------------------------------
    # Schema helpers
    # ------------------------------------------------------------------
    def _schema_field_list(self) -> list[str]:
        """Return the current schema as a list of field-name strings."""
        return [_LABEL_TO_FIELD.get(v.get(), "ignore") for v in self._schema_vars]

    def _on_combobox_selected(self, var: tk.StringVar, cb: "ttk.Combobox") -> None:
        """Handle a dropdown selection — update the StringVar and rebuild the
        schema string field directly from all five dropdowns."""
        var.set(cb.get())
        # Rebuild string field from all dropdowns now
        if hasattr(self, "_schema_str_var") and hasattr(self, "_schema_vars"):
            new_schema = ":".join(
                _LABEL_TO_FIELD.get(v.get(), "ignore") for v in self._schema_vars
            )
            self._schema_str_var.set(new_schema)
        self._refresh_schema_preview()

    def _sync_string_from_dropdowns(self) -> None:
        """Update the schema string entry to reflect the current dropdown state."""
        if not hasattr(self, "_schema_str_var"):
            return
        # Read directly from dropdowns (not _build_schema_arg which reads the string)
        new_val = ":".join(self._schema_field_list())
        if self._schema_str_var.get() != new_val:
            self._schema_str_var.set(new_val)
            self._schema_str_last_synced = new_val

    def _sync_dropdowns_from_string(self) -> None:
        """Parse the schema string entry and update the dropdowns to match.

        Called when the user commits the schema string field (Return/Tab/FocusOut).
        Updates _schema_str_last_synced so subsequent dropdown changes don't
        clobber the user's manually entered value.
        """
        if not hasattr(self, "_schema_vars") or not hasattr(self, "_schema_str_var"):
            return
        raw = self._schema_str_var.get().strip()
        if not raw:
            return
        # Parse colon-separated field names, pad/truncate to 5 slots
        parts = [p.strip().lower() for p in raw.split(":")]
        parts = (parts + ["ignore"] * 5)[:5]
        current = self._schema_field_list()
        if parts == current:
            self._schema_str_last_synced = raw
            return  # nothing changed
        for var, field in zip(self._schema_vars, parts):
            label = _FIELD_TO_LABEL.get(field, "— ignore —")
            if var.get() != label:
                var.set(label)
        # Record that this string is now in sync with the dropdowns
        self._schema_str_last_synced = raw
        self._refresh_schema_preview()

    def _schema_errors(self) -> list[str]:
        """Return validation error strings, or [] if the schema is valid.
        Reads from the string field (single source of truth).
        """
        schema_str = self._build_schema_arg()
        fields = [f.strip().lower() for f in schema_str.split(":") if f.strip()]
        errors: list[str] = []
        if fields.count("channel") != 1:
            errors.append(
                f'"Channel" must appear exactly once '
                f'(found {fields.count("channel")}).'
            )
        if fields.count("well") != 1:
            errors.append(
                f'"Well" must appear exactly once '
                f'(found {fields.count("well")}).'
            )
        return errors

    def _build_schema_arg(self) -> str:
        """Return the colon-joined schema string for the pipeline CLI.

        Prefers the editable string field as the source of truth — this
        ensures the value passed to the pipeline matches what the user
        actually sees and can type, regardless of any Combobox sync issues.
        Falls back to reading the dropdowns if the field isn't built yet.
        """
        if hasattr(self, "_schema_str_var"):
            raw = self._schema_str_var.get().strip()
            if raw:
                return raw
        return ":".join(self._schema_field_list())

    def _refresh_schema_preview(self) -> None:
        """Update the live preview label, validation message, and folder lock.

        Important: this method NEVER reverts any field values.  Validation
        errors are displayed but do not undo what the user just changed.
        The string field is always kept in sync with the dropdowns so the
        user can see the current schema regardless of validity.
        """
        # Guard: called during construction before all widgets exist — bail out.
        if not hasattr(self, "_schema_vars") or not hasattr(self, "_schema_err_lbl"):
            return

        errors = self._schema_errors()
        fields = self._schema_field_list()
        sep    = self._filename_sep.get() or DEFAULT_SEP

        # String field is the source of truth — dropdowns never overwrite it here.
        # Dropdowns update the string only via _on_combobox_selected.

        schema_valid = not errors

        # ── Lock / unlock the folder widgets ──────────────────────────────
        if hasattr(self, "_input_entry"):
            folder_state = tk.NORMAL if schema_valid else tk.DISABLED
            self._input_entry.config(state=folder_state)
            self._browse_btn.config(state=folder_state)
            if hasattr(self, "_folder_lock_lbl"):
                self._folder_lock_lbl.config(
                    text="" if schema_valid
                    else "Define the filename schema above first.")

        if errors:
            self._schema_err_lbl.config(text="  ".join(errors))
            self._schema_preview_lbl.config(text="")
            if hasattr(self, "_run_btn"):
                self._run_btn.config(state=tk.DISABLED)
            return

        self._schema_err_lbl.config(text="")
        if hasattr(self, "_run_btn"):
            self._run_btn.config(state=tk.NORMAL)

        # Build a representative example filename from placeholder tokens.
        nuclear_tok = (
            self._nuclear_token.get().strip()
            if hasattr(self, "_nuclear_token") else "NIR"
        ) or "NIR"

        fluor_toks = (
            self._fluor_tokens_list()
            if hasattr(self, "_fluor_vars") else ["GFP"]
        ) or ["GFP"]

        def _make_example(chan_tok: str) -> str:
            parts = []
            for field in fields:
                if field == "channel":
                    parts.append(chan_tok)
                else:
                    parts.append(_PREVIEW_TOKENS.get(field, "X"))
            return sep.join(parts) + ".tif"

        lines = [f"e.g. {_make_example(nuclear_tok)}"]
        for ftok in fluor_toks[:2]:
            lines.append(f"     {_make_example(ftok)}")
        self._schema_preview_lbl.config(text="\n".join(lines))

    def _build_log(self, parent: tk.Frame) -> None:
        """Build the right-side log panel."""
        hdr = tk.Frame(parent, bg=BG_SIDE, pady=6, padx=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="Pipeline Output", font=FM_BOLD,
                 fg=TXT_PRI, bg=BG_SIDE).pack(side=tk.LEFT)
        self._status_lbl = tk.Label(hdr, text="Idle", font=FM_TINY,
                                    fg=TXT_MUT, bg=BG_SIDE)
        self._status_lbl.pack(side=tk.LEFT, padx=(12, 0))
        ttk.Button(hdr, text="Clear", command=self._clear_log,
                   style="Secondary.TButton").pack(side=tk.RIGHT)

        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X)

        # Progress bar — sits between header and log text
        prog_frame = tk.Frame(parent, bg=BG_SIDE, padx=12, pady=6)
        prog_frame.pack(fill=tk.X)

        self._prog_lbl = tk.Label(prog_frame, text="", font=FM_TINY,
                                  fg=TXT_MUT, bg=BG_SIDE, anchor="w")
        self._prog_lbl.pack(side=tk.LEFT)

        from tkinter import ttk as _ttk
        self._progress = _ttk.Progressbar(
            prog_frame, orient=tk.HORIZONTAL,
            mode="determinate", maximum=100, value=0)
        self._progress.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(12, 0))

        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X)

        log_frame = tk.Frame(parent, bg=BG_PANEL)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        vsb = tk.Scrollbar(log_frame, relief=tk.FLAT, width=8,
                           bg=BORDER, troughcolor=BG_SIDE)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._log = tk.Text(
            log_frame, bg=BG_PANEL, fg=TXT_PRI,
            font=FM_MONO, relief=tk.FLAT,
            wrap=tk.NONE, state=tk.DISABLED,
            yscrollcommand=vsb.set,
            selectbackground=ACCENT, selectforeground=CLR_WHITE)
        self._log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.config(command=self._log.yview)

        # Horizontal scrollbar
        hsb = tk.Scrollbar(parent, orient=tk.HORIZONTAL, relief=tk.FLAT,
                           width=8, bg=BORDER, troughcolor=BG_SIDE,
                           command=self._log.xview)
        hsb.pack(fill=tk.X, padx=4)
        self._log.config(xscrollcommand=hsb.set)

        # Tag colours for log levels
        self._log.tag_configure("INFO",    foreground=TXT_PRI)
        self._log.tag_configure("WARNING", foreground=WARN)
        self._log.tag_configure("ERROR",   foreground=CLR_DANGER)
        self._log.tag_configure("DONE",    foreground=CLR_SUCCESS, font=FM_BOLD)
        self._log.tag_configure("CMD",     foreground=TXT_MUT)

    # ------------------------------------------------------------------
    # Folder resolution
    # ------------------------------------------------------------------
    def _browse_input(self) -> None:
        d = filedialog.askdirectory(title="Select input folder")
        if d:
            self._input_var.set(d)

    def _refresh_output(self) -> None:
        """Re-evaluate the in/out path and update the display labels.
        Never runs the zipper — preview only."""
        raw_str = self._input_var.get().strip()
        if not raw_str:
            self._output_var.set("—")
            self._layout_lbl.config(text="")
            return
        raw = Path(raw_str)
        if not raw.is_dir():
            self._output_var.set("—")
            self._layout_lbl.config(text="Not a directory.", fg=CLR_DANGER)
            return

        # Rule 1: folder named "in"
        if raw.name.lower() == "in":
            self._output_var.set(str(raw.parent / "out"))
            self._layout_lbl.config(text="✓ Using selected folder as input",
                                    fg=CLR_SUCCESS)
            return

        # Rule 2: contains "in/" with zips or well-named subfolders
        in_sub = raw / "in"
        if in_sub.is_dir() and _has_well_content(in_sub):
            self._output_var.set(str(raw / "out"))
            self._layout_lbl.config(text="✓ Found in/ subfolder — using as input",
                                    fg=CLR_SUCCESS)
            return

        # Rule 3: has TIF files — will need WellPlateZipper (don't run it here)
        tifs = _tif_files_in(raw)
        if len(tifs) > 3:
            self._output_var.set(str(raw / "out"))
            self._layout_lbl.config(
                text=f"✓ Will run WellPlateZipper on {len(tifs)} TIF files → in/",
                fg=CLR_SUCCESS)
            return

        # Nothing matched
        self._output_var.set("—")
        self._layout_lbl.config(
            text="No TIF files or in/ folder found in selected directory.",
            fg=CLR_DANGER)

    def _run(self) -> None:
        """Validate paths, build args, spawn subprocess."""
        pipeline = self._validate_run_request()
        if pipeline is None:
            return
        self._set_running_ui_state()
        opts = self._collect_run_options()
        threading.Thread(
            target=self._run_pipeline_thread,
            args=(pipeline, opts),
            daemon=True,
        ).start()

    def _validate_run_request(self) -> Optional[Path]:
        raw_str = self._input_var.get().strip()
        if not raw_str:
            messagebox.showerror("Input Error", "No input folder selected.", parent=self)
            return None
        schema_errors = self._schema_errors()
        if schema_errors:
            messagebox.showerror(
                "Schema Error",
                "Invalid filename schema:\n\n" + "\n".join(schema_errors),
                parent=self,
            )
            return None
        fluor_tokens = self._fluor_tokens_list()
        if not fluor_tokens:
            messagebox.showerror(
                "Channel Error",
                "At least one fluorescent channel token is required.",
                parent=self,
            )
            return None
        seg_errors = self._segmentation_validation_errors()
        if seg_errors:
            messagebox.showerror(
                "Segmentation Error",
                "\n".join(seg_errors),
                parent=self,
            )
            return None
        pipeline = find_pipeline_script()
        if pipeline is None:
            messagebox.showerror(
                "Configuration Error",
                f"process_microscopy_v2.py not found.\nExpected: {_PIPELINE_SCRIPT}",
                parent=self,
            )
            return None
        return pipeline

    def _set_running_ui_state(self) -> None:
        self._running = True
        self._well_total = 0
        self._well_done = 0
        self._zip_mode_warning_logged = False
        self._progress["value"] = 0
        self._prog_lbl.config(text="Preparing…", fg=TXT_MUT)
        self._run_btn.config(state=tk.DISABLED)
        self._stop_btn.config(state=tk.NORMAL)
        self._status_lbl.config(text="Running…", fg=WARN)

    def _collect_run_options(self) -> dict:
        segmentation_method = self._segmentation_method.get().strip() or "stardist_nuclei"
        min_area_raw = self._min_nucleus_area_px.get().strip()
        try:
            min_area = int(min_area_raw) if min_area_raw else 50
        except ValueError:
            min_area = 50
        cytoplasm_token = self._cytoplasm_token.get().strip()
        if segmentation_method != "stardist_seeded_watershed_cell":
            cytoplasm_token = ""
        return dict(
            raw=Path(self._input_var.get().strip()),
            nuclear_token=self._nuclear_token.get().strip() or "NIR",
            fluor_tokens=self._fluor_tokens_list(),
            csv_prefix=self._csv_prefix.get().strip() or "gfp_measurements",
            tophat_radius_nir=self._tophat_radius_nir.get(),
            tophat_radius_fluor=self._tophat_radius_fluor.get(),
            no_tophat_nir=self._no_tophat_nir.get(),
            no_tophat_fluor=self._no_tophat_fluor.get(),
            compress_input_well_folders=self._compress_input_well_folders.get(),
            compress_output_well_folders=self._compress_output_well_folders.get(),
            force=self._force.get(),
            cpu_only=self._cpu_only.get(),
            tf_threads=self._tf_threads.get(),
            workers=self._workers.get(),
            filename_schema=self._build_schema_arg(),
            filename_sep=self._filename_sep.get() or DEFAULT_SEP,
            smfish_tokens=self._smfish_tokens_list(),
            segmentation_method=segmentation_method,
            cytoplasm_token=cytoplasm_token,
            min_nucleus_area_px=min_area,
        )

    def _expected_well_count(self, opts: dict) -> int:
        raw = opts["raw"]
        in_sub = raw / "in"
        if raw.name.lower() == "in":
            return _count_well_content(raw) or 1
        if in_sub.is_dir() and _has_well_content(in_sub):
            return _count_well_content(in_sub) or 1
        import re as _re2

        well_re = _re2.compile(r"[A-Ha-h]\d{1,2}", _re2.I)
        tifs = _tif_files_in(raw)
        sep = opts["filename_sep"]
        fields = [f.strip() for f in opts["filename_schema"].split(":")]
        try:
            well_idx = fields.index("well")
        except ValueError:
            well_idx = -1
        wells: set[str] = set()
        for tif_path in tifs:
            parts = tif_path.stem.split(sep)
            token = parts[well_idx] if 0 <= well_idx < len(parts) else ""
            if token and well_re.fullmatch(token):
                wells.add(token.upper())
        return len(wells) or len(tifs) or 1

    def _resolve_run_dirs(self, opts: dict) -> tuple[Path, Path] | None:
        try:
            self._log_q.put(("zipper_start", self._expected_well_count(opts)))
            input_dir, output_dir = resolve_input_output(
                opts["raw"],
                log_fn=lambda msg: self._log_q.put(("line", msg)),
                progress_fn=lambda tok: self._log_q.put(("zipper_well", tok)),
                filename_schema=opts["filename_schema"],
                filename_sep=opts["filename_sep"],
            )
            self._log_q.put(("zipper_done", None))
            return input_dir, output_dir
        except (ValueError, RuntimeError) as exc:
            self._log_q.put(("error", f"Input error: {exc}\n"))
            return None

    def _write_pipeline_sidecar(self, input_dir: Path, output_dir: Path, opts: dict) -> None:
        try:
            available_timepoints = collect_available_timepoints(
                input_dir,
                filename_schema=opts["filename_schema"],
                filename_sep=opts["filename_sep"],
            )
            available_fovs = collect_available_fovs(
                input_dir,
                filename_schema=opts["filename_schema"],
                filename_sep=opts["filename_sep"],
            )
            info_path = write_pipeline_info(
                output_dir,
                filename_schema=opts["filename_schema"],
                filename_sep=opts["filename_sep"],
                nuclear_token=opts.get("nuclear_token", ""),
                fluor_tokens=opts.get("fluor_tokens", []),
                smfish_tokens=opts.get("smfish_tokens", []),
                segmentation_method=opts.get("segmentation_method", "stardist_nuclei"),
                cytoplasm_token=opts.get("cytoplasm_token", ""),
                min_nucleus_area_px=opts.get("min_nucleus_area_px", 50),
                available_timepoints=available_timepoints,
                available_fovs=available_fovs,
                execution_options=opts,
            )
            self._log_q.put(("line", f"[info] Wrote {info_path}\n"))
        except Exception as exc:
            self._log_q.put(("line", f"[warn] Could not write pipeline_info.json: {exc}\n"))

    def _log_pipeline_command(self, args: list[str], input_dir: Path, output_dir: Path, opts: dict) -> None:
        self._log_q.put(("line", f"$ {' '.join(args)}\n"))
        self._log_q.put(("line", f"Input  : {input_dir}\n"))
        self._log_q.put(("line", f"Output : {output_dir}\n"))
        self._log_q.put(("line", f"Schema : {opts['filename_schema']}  sep={opts['filename_sep']!r}\n\n"))

    def _run_pipeline_subprocess(self, args: list[str]) -> None:
        try:
            self._proc = spawn_pipeline(args)
            assert self._proc.stdout is not None
            for line in self._proc.stdout:
                self._log_q.put(("line", line))
            self._proc.wait()
            rc = self._proc.returncode
            if rc == 0:
                self._log_q.put(("done", "Pipeline completed successfully.\n"))
            else:
                self._log_q.put(("error", f"Pipeline exited with code {rc}.\n"))
        except Exception as exc:
            self._log_q.put(("error", f"Failed to start pipeline: {exc}\n"))

    def _run_pipeline_thread(self, pipeline: Path, opts: dict) -> None:
        try:
            resolved = self._resolve_run_dirs(opts)
            if resolved is None:
                return
            input_dir, output_dir = resolved
            if any(input_dir.glob("*.zip")):
                self._log_q.put(
                    (
                        "line",
                        "[warn] Zip mode detected (input contains *.zip wells); folder-mode compression options do not apply.\n",
                    )
                )
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                self._log_q.put(("error", f"Cannot create output dir: {exc}\n"))
                return
            self._last_output_dir = output_dir
            self._write_pipeline_sidecar(input_dir, output_dir, opts)
            args = build_pipeline_args(pipeline, input_dir, output_dir, opts)
            self._log_pipeline_command(args, input_dir, output_dir, opts)
            self._run_pipeline_subprocess(args)
        finally:
            self._log_q.put(("finished", None))

    def _stop(self) -> None:
        """Terminate the running subprocess."""
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            self._log_line("\n[User stopped the pipeline]\n", tag="WARNING")

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------
    def _log_line(self, text: str, tag: str = "INFO") -> None:
        """Append *text* to the log widget (must be called from main thread)."""
        self._log.config(state=tk.NORMAL)
        self._log.insert(tk.END, text, tag)
        self._log.see(tk.END)
        self._log.config(state=tk.DISABLED)

    def _clear_log(self) -> None:
        self._log.config(state=tk.NORMAL)
        self._log.delete("1.0", tk.END)
        self._log.config(state=tk.DISABLED)

    def _classify_line(self, line: str) -> str:
        """Return a log tag based on line content."""
        ll = line.lower()
        if "error" in ll or "traceback" in ll or "exception" in ll:
            return "ERROR"
        if "warning" in ll or "warn" in ll or "skipping" in ll:
            return "WARNING"
        return "INFO"

    def _parse_progress(self, line: str) -> None:
        """
        Inspect a pipeline log line and update the progress bar if relevant.
        Zipper-phase progress is handled separately via zipper_well queue messages.

        Total-well signals (set denominator):
          "Zip mode: N well(s) to process, ..."
          "Flat mode: N well(s), ..."

        Well-complete signals (increment numerator):
          Zip mode:  "Well XX — temporary directories removed."
          Flat mode: "Well XX -> gfp_measurements_XX.csv  (N rows)"
        """
        import re as _re

        # Skip zipper lines — those are tracked via zipper_well messages
        if line.startswith("[zipper]"):
            return

        if ("Zip mode:" in line or "Zip mode complete" in line) and not getattr(
            self, "_zip_mode_warning_logged", False
        ):
            self._zip_mode_warning_logged = True
            self._log_q.put(
                (
                    "line",
                    "[warn] Zip mode detected (input contains *.zip wells); folder-mode compression options do not apply.\n",
                )
            )

        # ── Worker count — log once when the pipeline announces it ───────
        m = _re.search(r"TF threads/worker\s*:\s*\d+\s+\(workers:\s*(\d+)\s+x", line)
        if m:
            self._log_q.put(("workers", int(m.group(1))))

        # ── Set total ────────────────────────────────────────────────────
        if not self._well_total:
            m = _re.search(r"(?:Zip mode|Flat mode|Folder mode):\s+(\d+)\s+well", line)
            if m:
                self._well_total = int(m.group(1))
                self._progress["maximum"] = self._well_total
                self._progress["value"]   = 0
                self._prog_lbl.config(
                    text=f"Pipeline: 0 / {self._well_total} wells", fg=TXT_MUT)
                return

        # ── Increment on completion ───────────────────────────────────────
        if self._well_total:
            completed = False
            if "temporary directories removed" in line:
                completed = True
            elif _re.search(r"Well\s+\S+\s+->\s+\S+\.csv\s+\(\d+\s+rows?\)", line):
                completed = True

            if completed:
                self._well_done += 1
                self._progress["value"] = self._well_done
                pct = int(self._well_done / self._well_total * 100)
                self._prog_lbl.config(
                    text=f"Pipeline: {self._well_done} / {self._well_total} wells  ({pct}%)",
                    fg=CLR_SUCCESS if self._well_done == self._well_total else TXT_MUT)

    def _poll_log(self) -> None:
        """Drain the thread-safe queue and write to the log widget."""
        try:
            while True:
                kind, payload = self._log_q.get_nowait()
                if kind == "line":
                    self._parse_progress(payload)
                    self._log_line(payload, self._classify_line(payload))
                elif kind == "zipper_start":
                    # payload is the actual well count from the input directory
                    n = payload if payload else 96
                    self._zipper_done = 0
                    self._progress["maximum"] = n
                    self._progress["value"]   = 0
                    self._prog_lbl.config(
                        text=f"Grouping: 0 / {n} wells", fg=TXT_MUT)
                elif kind == "zipper_well":
                    n_total = self._progress["maximum"] or 96
                    self._zipper_done = getattr(self, "_zipper_done", 0) + 1
                    self._progress["value"] = self._zipper_done
                    pct = int(self._zipper_done / n_total * 100)
                    done = self._zipper_done == n_total
                    self._prog_lbl.config(
                        text=f"Grouping: {self._zipper_done} / {n_total} wells  ({pct}%)",
                        fg=CLR_SUCCESS if done else TXT_MUT)
                elif kind == "zipper_done":
                    # Reset bar for pipeline phase (maximum set when pipeline starts)
                    self._progress["maximum"] = 100
                    self._progress["value"]   = 0
                    self._well_total = 0
                    self._well_done  = 0
                    self._prog_lbl.config(
                        text="Grouping complete — starting pipeline…", fg=CLR_SUCCESS)
                elif kind == "workers":
                    n = payload
                    self._log_line(
                        f"[info] Workers: {n} parallel well(s) will be processed simultaneously.\n",
                        "INFO")
                elif kind == "done":
                    self._progress["value"] = self._progress["maximum"] or 100
                    n = self._well_done or getattr(self, "_zipper_done", 0)
                    self._prog_lbl.config(
                        text=f"Complete — {n} well(s) processed",
                        fg=CLR_SUCCESS)
                    self._log_line(payload, "DONE")
                    self._log_line("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                   "  Processing Complete\n"
                                   "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
                                   "DONE")
                    if self._on_pipeline_complete is not None and self._last_output_dir is not None:
                        try:
                            self._on_pipeline_complete(self._last_output_dir)
                        except Exception as exc:
                            self._log_line(f"[warn] Could not open Review tab automatically: {exc}\n", "WARNING")
                elif kind == "error":
                    self._log_line(payload, "ERROR")
                elif kind == "finished":
                    self._running = False
                    self._run_btn.config(state=tk.NORMAL)
                    self._stop_btn.config(state=tk.DISABLED)
                    self._status_lbl.config(text="Idle", fg=TXT_MUT)
                    self._proc = None
        except queue.Empty:
            pass
        self.after(80, self._poll_log)

    def destroy(self) -> None:
        """Ensure subprocess is killed when the widget is destroyed."""
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        super().destroy()


# ---------------------------------------------------------------------------
# Standalone test harness
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Analyze Tab — standalone test")
    root.geometry("1100x700")
    root.configure(bg=BG_APP)
    tab = AnalyzeTab(root)
    tab.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
