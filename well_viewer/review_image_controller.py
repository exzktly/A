"""Controller helpers for Review Image <-> Review CSV interactions."""

from __future__ import annotations


def on_review_image_click(app, event, logger) -> None:
    mask_arr = getattr(app._review_image_label, "_mask_arr", None)
    if mask_arr is None:
        return
    scale = float(getattr(app, "_review_image_scale", 1.0) or 1.0)
    x, y = int(event.x / scale), int(event.y / scale)
    if y < 0 or x < 0 or y >= mask_arr.shape[0] or x >= mask_arr.shape[1]:
        return
    nid = int(mask_arr[y, x])
    if nid <= 0:
        return
    app._review_image_selected_nucleus = nid
    fov = app._preview_fov_var.get().strip()
    tp = app._review_image_tp_var.get().strip()
    if getattr(app, "_review_image_include_edit_mode", False):
        app._set_review_cell_included(fov, tp, str(nid), "0")
        app._set_status(f"Set Included=0 for nucleus {nid} at FOV {fov}, TP {tp}.")
        return
    app._select_review_csv_row_for_cell(
        fov,
        tp,
        str(nid),
    )


def select_review_csv_row_for_cell(app, fov: str, tp: str, nucleus_id: str, logger) -> None:
    if not hasattr(app, "_review_fov_var"):
        return
    app._review_csv_lookup_context = {
        "well": str(app._preview_selected_well or ""),
        "fov": str(fov),
        "tp": str(tp),
        "nucleus_id": str(nucleus_id),
    }
    app._set_status(
        "Review CSV lookup request: "
        f"well={app._review_csv_lookup_context['well']}  "
        f"fov={app._review_csv_lookup_context['fov']}  "
        f"tp={app._review_csv_lookup_context['tp']}  "
        f"nucleus_id={app._review_csv_lookup_context['nucleus_id']}"
    )
    logger.info(
        "Review-image click -> Review CSV lookup: well=%s fov=%s tp=%s nucleus_id=%s",
        app._preview_selected_well, fov, tp, nucleus_id,
    )
    app._review_fov_var.set(fov)
    app._review_tp_var.set(tp)
    app._refresh_review_csv_rows()
    table = app._review_csv_table
    debug_candidates = []
    for iid in table.get_children():
        vals = table.item(iid, "values")
        cols = table["columns"]
        row = {c: vals[i] for i, c in enumerate(cols)}
        rf, rt, rn = app._review_row_keys(row)
        debug_candidates.append((rf, rt, rn))
        if rf == fov and rt == tp and rn == nucleus_id:
            table.selection_set(iid)
            table.focus(iid)
            table.see(iid)
            app._set_status(f"Matched Review CSV row for nucleus {nucleus_id} at FOV {fov}, TP {tp}.")
            break
    else:
        logger.warning(
            "Review CSV exact row match not found. target=(%s,%s,%s) candidates_shown=%d sample=%s",
            fov, tp, nucleus_id, len(debug_candidates), debug_candidates[:10],
        )
        app._set_status(
            f"No exact Review CSV row match for nucleus {nucleus_id} at FOV {fov}, TP {tp}; showing fallback rows."
        )
    app._set_status(
        f"Queued Review CSV selection for nucleus {nucleus_id} at FOV {fov}, TP {tp}."
    )


def on_review_csv_row_double_click(app, event) -> None:
    if not hasattr(app, "_review_csv_table"):
        return
    table = app._review_csv_table
    iid = table.identify_row(event.y) or table.focus()
    if not iid:
        return
    values = table.item(iid, "values")
    cols = table["columns"]
    row = {c: values[i] for i, c in enumerate(cols)}
    fov, tp, nid = app._review_row_keys(row)
    well_tok = str(row.get("well", "")).strip()
    label = app._tok_to_label.get(well_tok, None)
    if label is None and app._selected_wells:
        label = sorted(app._selected_wells, key=app._parse_rc)[0]
    if label is None:
        return

    app._preview_selected_well = label
    app._update_preview(label)
    if fov:
        app._preview_fov_var.set(fov)
    if tp and hasattr(app, "_review_image_tp_var"):
        app._review_image_tp_var.set(tp)
    if nid:
        try:
            app._review_image_selected_nucleus = int(float(nid))
        except Exception:
            app._review_image_selected_nucleus = None
    app._refresh_review_image()
    if hasattr(app, "_zoom_review_image_to_selected_nucleus"):
        app._zoom_review_image_to_selected_nucleus()
    if hasattr(app, "_notebook") and hasattr(app._notebook, "select_by_text"):
        app._notebook.select_by_text("Review Image")
