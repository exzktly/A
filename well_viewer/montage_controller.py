"""Montage interaction helpers extracted from well_viewer3."""

from __future__ import annotations


def montage_tophat_done(app, filtered_arrays: list, partial: bool = False) -> None:
    app._montage_fluor_display_arrays = filtered_arrays
    if not partial:
        valid = [a for a in filtered_arrays if a is not None]
        if valid and app._NP_AVAILABLE:
            lo = min(float(app._np.asarray(a).min()) for a in valid)
            hi = max(float(app._np.asarray(a).max()) for a in valid)
            if hi <= lo:
                hi = lo + 1.0
            app._mon_lmin_var.set(f"{lo:.0f}")
            app._mon_lmax_var.set(f"{hi:.0f}")

    fov = app._preview_fov_var.get()
    tp_list = [(tp, ref) for (f, tp), ref in sorted(app._preview_fluor.items()) if f == fov]
    if tp_list:
        app._draw_montage_thumbs(tp_list)

    if not partial:
        app._set_status(
            f"Top-hat filter applied  ·  {len(filtered_arrays)} frame(s)  ·  radius={app._mon_tophat_radius.get()} px"
        )


def montage_auto_lut(app, redraw: bool = True) -> None:
    tophat_on = getattr(app, "_mon_tophat_var", None) is not None and app._mon_tophat_var.get()
    display_arrays_exist = (
        tophat_on
        and hasattr(app, "_montage_fluor_display_arrays")
        and len(app._montage_fluor_display_arrays) == len(app._montage_fluor_arrays)
        and any(a is not None for a in app._montage_fluor_display_arrays)
    )
    source = [a for a in (app._montage_fluor_display_arrays if display_arrays_exist else app._montage_fluor_arrays) if a is not None]
    if not source:
        return
    lo = min(float(app._np.asarray(a).min()) for a in source)
    hi = max(float(app._np.asarray(a).max()) for a in source)
    if hi <= lo:
        hi = lo + 1.0
    app._mon_lmin_var.set(f"{lo:.0f}")
    app._mon_lmax_var.set(f"{hi:.0f}")
    if redraw:
        tp_list = [(tp, ref) for (f, tp), ref in sorted(app._preview_fluor.items()) if f == app._preview_fov_var.get()]
        if tp_list:
            app._draw_montage_thumbs(tp_list)


def on_montage_canvas_resize(app, _e=None) -> None:
    if hasattr(app, "_montage_resize_job") and app._montage_resize_job:
        try:
            app.after_cancel(app._montage_resize_job)
        except Exception:
            pass
    if app._montage_fluor_arrays:
        app._montage_resize_job = app.after(150, app._montage_resize_deferred)


def montage_resize_deferred(app) -> None:
    app._montage_resize_job = None
    fov = app._preview_fov_var.get()
    tp_list = [(tp, ref) for (f, tp), ref in sorted(app._preview_fluor.items()) if f == fov]
    if tp_list:
        app._draw_montage_thumbs(tp_list)


def on_montage_fluor_motion(app, e) -> None:
    lbl = e.widget
    arr = getattr(lbl, "_raw_arr", None)
    sz_w = getattr(lbl, "_sz_w", 1)
    sz_h = getattr(lbl, "_sz_h", 1)
    lo = getattr(lbl, "_lo", None)
    hi = getattr(lbl, "_hi", None)
    if arr is None or not app._NP_AVAILABLE:
        app._montage_tooltip.hide()
        return
    arr = app._np.asarray(arr, dtype=app._np.float32)
    ih, iw = arr.shape[:2]
    scale = min(sz_w / iw, sz_h / ih, 1.0)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    lw, lh = lbl.winfo_width(), lbl.winfo_height()
    img_x = (e.x - (lw - nw) // 2) / scale
    img_y = (e.y - (lh - nh) // 2) / scale
    if not (0 <= img_x < iw and 0 <= img_y < ih):
        app._montage_tooltip.hide()
        return
    val = float(arr[int(img_y), int(img_x)])
    sx = lbl.winfo_rootx() + e.x
    sy = lbl.winfo_rooty() + e.y
    app._montage_tooltip.show(f"x={int(img_x)}  y={int(img_y)}  {app._active_channel.upper()}:{val:.1f}", sx, sy)


def montage_zoom_step(app, direction: int) -> None:
    cur = getattr(app, "_montage_zoom", 1.0)
    steps = app._ZOOM_STEPS
    idx = min(range(len(steps)), key=lambda i: abs(steps[i] - cur))
    idx = max(0, min(len(steps) - 1, idx + direction))
    app._montage_zoom = steps[idx]
    app._montage_redraw_at_zoom()


def montage_zoom_fit(app) -> None:
    app._montage_zoom = 1.0
    app._montage_redraw_at_zoom()


def on_montage_wheel(app, event) -> None:
    app._montage_zoom_step(+1 if event.delta > 0 else -1)


def montage_redraw_at_zoom(app) -> None:
    fov = app._preview_fov_var.get()
    if fov == "—" or not app._montage_fluor_arrays:
        return
    tp_list = [(tp, ref) for (f, tp), ref in sorted(app._preview_fluor.items()) if f == fov]
    if tp_list:
        app._draw_montage_thumbs(tp_list)
