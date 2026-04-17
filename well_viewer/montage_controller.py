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


def _wheel_steps(event) -> int:
    """Normalize wheel/button events to signed integer step count."""
    num = getattr(event, "num", None)
    if num == 4:
        return 1
    if num == 5:
        return -1
    if num == 6:
        return -1
    if num == 7:
        return 1
    delta = int(getattr(event, "delta", 0) or 0)
    if delta == 0:
        return 0
    # Windows wheel notch is +/-120; high-resolution mice/trackpads emit
    # larger/smaller values. Preserve magnitude as number of steps.
    if abs(delta) >= 120:
        steps = abs(delta) // 120
    else:
        steps = 1
    return steps if delta > 0 else -steps


def montage_zoom_step(app, direction: int) -> None:
    cur = float(getattr(app, "_montage_zoom", 1.0) or 1.0)
    factor = 1.15
    if direction > 0:
        app._montage_zoom = min(16.0, cur * factor)
    elif direction < 0:
        app._montage_zoom = max(0.05, cur / factor)
    app._montage_redraw_at_zoom()


def montage_zoom_steps(app, steps: int) -> None:
    if steps == 0:
        return
    cur = float(getattr(app, "_montage_zoom", 1.0) or 1.0)
    factor = 1.15
    app._montage_zoom = min(16.0, max(0.05, cur * (factor ** steps)))
    app._montage_redraw_at_zoom()


def montage_zoom_fit(app) -> None:
    app._montage_zoom = 1.0
    app._montage_redraw_at_zoom()


def on_montage_wheel(app, event) -> None:
    steps = _wheel_steps(event)
    montage_zoom_steps(app, steps)


def on_montage_shift_wheel(app, event) -> None:
    steps = _wheel_steps(event)
    if steps:
        app._montage_canvas.xview_scroll(-3 * steps, "units")


def montage_redraw_at_zoom(app) -> None:
    fov = app._preview_fov_var.get()
    if fov == "—" or not app._montage_fluor_arrays:
        return
    tp_list = [(tp, ref) for (f, tp), ref in sorted(app._preview_fluor.items()) if f == fov]
    if tp_list:
        app._draw_montage_thumbs(tp_list)
