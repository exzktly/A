"""Preview/montage callback handlers extracted from runtime_app."""

from __future__ import annotations

import logging


_logger = logging.getLogger("well_viewer")


def refresh_preview_montage(app) -> None:
    from well_viewer import runtime_app as rt
    from well_viewer import debug_flags as _debug_flags

    if not hasattr(app, "_montage_inner"):
        return
    montage_debug = _debug_flags.movie_montage_debug_enabled()
    montage_load_debug = montage_debug or _debug_flags.movie_montage_load_debug_enabled()
    app._montage_zoom = 1.0
    if hasattr(app, "_montage_zoom_lbl"):
        app._montage_zoom_lbl.config(text="100%")
    for w in app._montage_inner.winfo_children():
        w.destroy()
    app._montage_photos.clear()
    app._montage_fluor_arrays = []
    app._montage_overlay_arrays = []
    app._montage_fluor_display_arrays = []
    app._montage_th_status = []
    app._montage_th_overlay_lbls = []
    app._montage_th_cancel = True

    well = app._preview_selected_well
    if well is None:
        app._montage_status.config(text="Select a well in the left panel.")
        return
    fov = app._preview_fov_var.get()
    if montage_debug:
        _logger.debug("refresh_preview_montage selected_fov=%r active_channel=%r", fov, getattr(app, "_active_image_channel", ""))
    if fov == "—":
        app._montage_status.config(text="No images found for this well.")
        return

    fluor_refs = [(tp, ref) for (f, tp), ref in sorted(app._preview_fluor.items()) if f == fov]
    tophat_refs = getattr(app, "_preview_tophat_fluor", {})
    used_tophat_as_primary = False
    if not fluor_refs:
        fluor_refs = [(tp, ref) for (f, tp), ref in sorted(tophat_refs.items()) if f == fov]
        used_tophat_as_primary = bool(fluor_refs)
    if montage_debug:
        source_map = "_preview_tophat_fluor" if used_tophat_as_primary else "_preview_fluor"
        _logger.debug(
            "refresh_preview_montage source_map=%s refs_loaded fluor=%d tophat=%d overlay=%d",
            source_map,
            len(fluor_refs),
            len([(tp, ref) for (f, tp), ref in sorted(tophat_refs.items()) if f == fov]),
            len([(tp, ref) for (f, tp), ref in sorted(app._preview_overlay.items()) if f == fov]),
        )
    if montage_load_debug:
        for tp, ref in fluor_refs:
            _debug_flags.debug_with_source(
                _logger,
                "Movie Montage load attempt fluor tp=%s path=%s",
                tp,
                getattr(ref, "full_path_str", str(ref)),
            )
    overlay_refs = [(tp, ref) for (f, tp), ref in sorted(app._preview_overlay.items()) if f == fov]
    if montage_load_debug:
        for tp, ref in overlay_refs:
            _debug_flags.debug_with_source(
                _logger,
                "Movie Montage load attempt overlay tp=%s path=%s",
                tp,
                getattr(ref, "full_path_str", str(ref)),
            )
    ov_map = dict(overlay_refs)
    n = len(fluor_refs)
    if n == 0:
        app._montage_status.config(text="No images for this FOV.")
        return
    app._montage_status.config(text=f"Loading {n} timepoint(s)…")
    app.update_idletasks()
    app._montage_fluor_refs = [ref for _, ref in fluor_refs]
    app._montage_overlay_refs = [ov_map.get(tp) for tp, _ in fluor_refs]
    app._montage_fluor_arrays = [rt.open_imgref_as_array(ref, greyscale=True) for ref in app._montage_fluor_refs]
    app._montage_overlay_arrays = [(rt.open_imgref_as_array(ref) if ref else None) for ref in app._montage_overlay_refs]

    if used_tophat_as_primary:
        app._montage_fluor_display_arrays = list(app._montage_fluor_arrays)
        app._montage_tophat_preloaded = True
    else:
        raw_by_tp = {tp: arr for (tp, _), arr in zip(fluor_refs, app._montage_fluor_arrays)}
        app._montage_fluor_display_arrays = []
        used_any_tophat = False
        for tp, _ in fluor_refs:
            th_ref = tophat_refs.get((fov, tp))
            if th_ref is not None:
                app._montage_fluor_display_arrays.append(rt.open_imgref_as_array(th_ref, greyscale=True))
                used_any_tophat = True
            else:
                app._montage_fluor_display_arrays.append(raw_by_tp[tp])
        app._montage_tophat_preloaded = used_any_tophat

    app._montage_status.config(text="")
    app._montage_auto_lut(redraw=False)
    app._update_tophat_controls()
    draw_montage_thumbs(app, [(tp, _) for tp, _ in fluor_refs])


def draw_montage_thumbs(app, tp_list: list) -> None:
    from well_viewer import runtime_app as rt
    def _bind_if_supported(widget, sequence: str, callback) -> None:
        try:
            widget.bind(sequence, callback)
        except rt.tk.TclError:
            pass

    for w in app._montage_inner.winfo_children():
        w.destroy()
    app._montage_photos.clear()
    app._montage_th_overlay_lbls = []
    try:
        lo = float(app._mon_lmin_var.get())
    except ValueError:
        lo = None
    try:
        hi = float(app._mon_lmax_var.get())
    except ValueError:
        hi = None

    preloaded = getattr(app, "_montage_tophat_preloaded", False)
    use_display = preloaded or (
        getattr(app, "_mon_tophat_var", None) is not None
        and app._mon_tophat_var.get()
        and hasattr(app, "_montage_fluor_display_arrays")
        and len(app._montage_fluor_display_arrays) == len(app._montage_fluor_arrays)
    )
    display_source = app._montage_fluor_display_arrays if use_display else app._montage_fluor_arrays
    cw = app._montage_canvas.winfo_width() or 400
    n = len(tp_list)
    gap = 6
    fit_sz = max(60, (cw - gap) // max(n, 1) - gap)
    app._montage_base_sz = fit_sz
    zoom = getattr(app, "_montage_zoom", 1.0)
    sz_w = max(40, int(fit_sz * zoom))
    sz_h = max(35, int(sz_w * 0.8))
    if hasattr(app, "_montage_zoom_lbl"):
        app._montage_zoom_lbl.config(text=f"{int(zoom * 100)}%")

    channel_row_lbl = rt.tk.Label(
        app._montage_inner,
        text=app._active_image_channel.upper(),
        font=rt.FM_TINY,
        fg=rt.TXT_MUT,
        bg=rt.BG_APP,
        anchor="e",
    )
    channel_row_lbl.grid(row=1, column=0, padx=(3, 6), pady=(0, 2), sticky="e")
    overlay_row_lbl = rt.tk.Label(
        app._montage_inner,
        text="overlay",
        font=rt.FM_TINY,
        fg=rt.TXT_MUT,
        bg=rt.BG_APP,
        anchor="e",
    )
    overlay_row_lbl.grid(row=2, column=0, padx=(3, 6), pady=(2, 0), sticky="e")

    for col_idx, ((tp, _), fluor_arr, ov_arr) in enumerate(zip(tp_list, display_source, app._montage_overlay_arrays)):
        col = rt.tk.Frame(app._montage_inner, bg=rt.BG_APP)
        col.grid(row=0, column=col_idx + 1, padx=3, pady=4, sticky="n")
        rt.tk.Label(col, text=tp, font=rt.FM_TINY, fg=rt.TXT_MUT, bg=rt.BG_APP, pady=2).pack()
        fluor_cell = rt.tk.Frame(col, bg=rt.BG_CELL, highlightthickness=1, highlightbackground=rt.BORDER)
        fluor_cell.pack(pady=(0, 2))
        photo_fluor = rt.make_fluor_thumb(fluor_arr, sz_w, sz_h, lo, hi)
        if photo_fluor:
            app._montage_photos.append(photo_fluor)
            lbl_fluor = rt.tk.Label(fluor_cell, image=photo_fluor, bg=rt.BG_APP, cursor="crosshair", bd=0)
            lbl_fluor._raw_arr = fluor_arr
            lbl_fluor._sz_w = sz_w
            lbl_fluor._sz_h = sz_h
            lbl_fluor._lo = lo
            lbl_fluor._hi = hi
            lbl_fluor.pack()
            lbl_fluor.bind("<Motion>", app._on_montage_fluor_motion)
            lbl_fluor.bind("<Leave>", lambda _e: app._montage_tooltip.hide())
            lbl_fluor.bind("<MouseWheel>", app._on_montage_wheel)
            lbl_fluor.bind("<Shift-MouseWheel>", app._on_montage_shift_wheel)
            lbl_fluor.bind("<Button-4>", lambda _e: app._montage_zoom_step(+1))
            lbl_fluor.bind("<Button-5>", lambda _e: app._montage_zoom_step(-1))
            _bind_if_supported(lbl_fluor, "<Button-6>", app._on_montage_shift_wheel)
            _bind_if_supported(lbl_fluor, "<Button-7>", app._on_montage_shift_wheel)
        else:
            rt.tk.Label(fluor_cell, text=f"{app._active_image_channel.upper()}\nunavail", font=rt.FM_TINY, fg=rt.TXT_MUT, bg=rt.BG_CELL, width=sz_w // 7, height=sz_h // 16).pack()

        th_on = getattr(app, "_mon_tophat_var", None) is not None and app._mon_tophat_var.get()
        th_state = app._montage_th_status[col_idx] if col_idx < len(app._montage_th_status) else ""
        overlay_txt = "⏳ filtering…" if th_on and th_state == "pending" else ("✓ filtered" if th_on and th_state == "done" else "")
        if overlay_txt:
            overlay_bg = rt.CLR_SLATE_BG if th_state == "pending" else rt.CLR_SUCCESS_BG_DARK
            overlay_fg = rt.CLR_SLATE_TEXT if th_state == "pending" else rt.CLR_SUCCESS_TEXT_SOFT
            th_lbl = rt.tk.Label(fluor_cell, text=overlay_txt, font=rt.FM_TINY, fg=overlay_fg, bg=overlay_bg, padx=4, pady=1, anchor="center")
            th_lbl.place(relx=0.0, rely=1.0, relwidth=1.0, anchor="sw")
            app._montage_th_overlay_lbls.append(th_lbl)
        else:
            app._montage_th_overlay_lbls.append(None)
        ov_cell = rt.tk.Frame(col, bg=rt.BG_CELL, highlightthickness=1, highlightbackground=rt.BORDER)
        ov_cell.pack(pady=(2, 0))
        photo_ov = rt.make_overlay_thumb(ov_arr, sz_w, sz_h)
        if photo_ov:
            app._montage_photos.append(photo_ov)
            lbl_ov = rt.tk.Label(ov_cell, image=photo_ov, bg=rt.BG_APP, bd=0)
            lbl_ov.pack()
            lbl_ov.bind("<MouseWheel>", app._on_montage_wheel)
            lbl_ov.bind("<Shift-MouseWheel>", app._on_montage_shift_wheel)
            lbl_ov.bind("<Button-4>", lambda _e: app._montage_zoom_step(+1))
            lbl_ov.bind("<Button-5>", lambda _e: app._montage_zoom_step(-1))
            _bind_if_supported(lbl_ov, "<Button-6>", app._on_montage_shift_wheel)
            _bind_if_supported(lbl_ov, "<Button-7>", app._on_montage_shift_wheel)
        else:
            rt.tk.Label(ov_cell, text="overlay\nunavail", font=rt.FM_TINY, fg=rt.TXT_MUT, bg=rt.BG_CELL, width=sz_w // 7, height=sz_h // 16).pack()
    n_ov = sum(1 for a in app._montage_overlay_arrays if a is not None)
    app._montage_status.config(text=f"{n} timepoint(s)  ·  {n_ov} overlay(s)")


def montage_tophat_toggled(app) -> None:
    from well_viewer import runtime_app as rt
    import threading as _threading

    if not app._montage_fluor_arrays:
        return
    app._montage_th_cancel = True
    if app._mon_tophat_var.get():
        try:
            radius = max(1, int(app._mon_tophat_radius.get()))
        except (ValueError, AttributeError):
            radius = 50
        try:
            from skimage.morphology import white_tophat as _wth, disk as _sk_disk
            _selem = _sk_disk(radius)
        except ImportError:
            rt._logger.warning("Top-hat filter requested but scikit-image is not installed. Install it with:  pip install scikit-image")
            app._mon_tophat_var.set(False)
            return
        raw_arrays = list(app._montage_fluor_arrays)
        n_total = len(raw_arrays)
        display = list(raw_arrays)
        app._montage_th_status = ["pending"] * n_total
        app._montage_th_cancel = False
        fov = app._preview_fov_var.get()
        tp_list = [(tp, ref) for (f, tp), ref in sorted(app._preview_fluor.items()) if f == fov]
        app._montage_th_overlay_lbls = []
        if tp_list:
            draw_montage_thumbs(app, tp_list)

        def _update_overlay(idx: int, state: str) -> None:
            if idx >= len(app._montage_th_overlay_lbls):
                return
            lbl = app._montage_th_overlay_lbls[idx]
            if lbl is None:
                return
            if state == "done":
                lbl.config(text="\u2713 filtered", bg=rt.CLR_SUCCESS_BG_DARK, fg=rt.CLR_SUCCESS_TEXT_SOFT)
            elif state == "error":
                lbl.config(text="\u2717 error", bg=rt.CLR_ERROR_BG_DARK, fg=rt.CLR_ERROR_TEXT_SOFT)
            else:
                lbl.config(text="\u29d6 filtering\u2026", bg=rt.CLR_SLATE_BG, fg=rt.CLR_SLATE_TEXT)

        def _on_frame_done(step: int, i: int) -> None:
            if getattr(app, "_montage_th_cancel", True):
                return
            st = app._montage_th_status[i] if i < len(app._montage_th_status) else ""
            _update_overlay(i, st)
            app._set_status(f"Top-hat filter: {step}/{n_total} frame(s)\u2026")

        def _on_all_done() -> None:
            if getattr(app, "_montage_th_cancel", True):
                return
            app._montage_tophat_done(display, partial=False)

        def _on_visible_done() -> None:
            if getattr(app, "_montage_th_cancel", True):
                return
            app._montage_tophat_done(list(display), partial=True)

        try:
            x0_frac, x1_frac = app._montage_canvas.xview()
        except Exception:
            x0_frac, x1_frac = 0.0, 1.0
        visible = [i for i in range(n_total) if x0_frac <= (i + 0.5) / max(n_total, 1) <= x1_frac] or list(range(n_total))
        others = [i for i in range(n_total) if i not in set(visible)]
        ordered = visible + others

        def _worker() -> None:
            for step, i in enumerate(ordered, 1):
                if getattr(app, "_montage_th_cancel", True):
                    return
                if raw_arrays[i] is not None:
                    try:
                        display[i] = _wth(rt._np.asarray(raw_arrays[i], dtype=rt._np.float32), _selem)
                        if i < len(app._montage_th_status):
                            app._montage_th_status[i] = "done"
                    except Exception as exc:
                        rt._logger.error("Top-hat frame %d failed: %s", i, exc)
                        if i < len(app._montage_th_status):
                            app._montage_th_status[i] = "error"
                app.after(0, lambda s=step, ii=i: _on_frame_done(s, ii))
                if step == len(visible) and others:
                    app.after(0, _on_visible_done)
            app.after(0, _on_all_done)

        app._montage_status.config(text="")
        _threading.Thread(target=_worker, daemon=True).start()
    else:
        app._montage_th_cancel = True
        app._montage_fluor_display_arrays = []
        app._montage_th_status = []
        app._montage_th_overlay_lbls = []
        app._montage_auto_lut(redraw=True)
        app._set_status("Top-hat filter removed.")
