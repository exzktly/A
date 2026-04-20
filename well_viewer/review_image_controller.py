"""Controller helpers for Review Image <-> Review CSV interactions."""

from __future__ import annotations

from well_viewer.qt_compat import combo_text


def _select_tab_by_text(notebook, text: str) -> None:
    """Select a QTabWidget tab by its text label."""
    for i in range(notebook.count()):
        if notebook.tabText(i) == text:
            notebook.setCurrentIndex(i)
            return


def _table_row_dict(table, row_idx: int) -> dict:
    """Extract a row from a QTableWidget as a {col_name: value} dict."""
    col_names = [
        (table.horizontalHeaderItem(c).text() if table.horizontalHeaderItem(c) else str(c))
        for c in range(table.columnCount())
    ]
    return {
        col_names[c]: (table.item(row_idx, c).text() if table.item(row_idx, c) else "")
        for c in range(table.columnCount())
    }


def on_review_image_click(app, event, logger) -> None:
    mask_arr = getattr(app._review_image_label, "_mask_arr", None)
    if mask_arr is None:
        return
    scale = float(getattr(app, "_review_image_scale", 1.0) or 1.0)
    x = int(event.position().x() / scale)
    y = int(event.position().y() / scale)
    if y < 0 or x < 0 or y >= mask_arr.shape[0] or x >= mask_arr.shape[1]:
        return
    nid = int(mask_arr[y, x])
    if nid <= 0:
        return
    app._review_image_selected_nucleus = nid
    fov = combo_text(getattr(app, "_preview_fov_cb", None)).strip()
    tp_cb = getattr(app, "_review_image_tp_cb", None)
    tp = combo_text(tp_cb).strip() if tp_cb is not None else ""
    if getattr(app, "_review_image_include_edit_mode", False):
        app._set_review_cell_included(fov, tp, str(nid), "0")
        app._set_status(f"Set Included=0 for nucleus {nid} at FOV {fov}, TP {tp}.")
        return
    app._select_review_csv_row_for_cell(fov, tp, str(nid))


def select_review_csv_row_for_cell(app, fov: str, tp: str, nucleus_id: str, logger) -> None:
    if not hasattr(app, "_review_fov_cb"):
        return
    fov_n, tp_n, nucleus_n = app._review_row_keys({"fov": fov, "tp": tp, "nucleus_id": nucleus_id})
    app._review_csv_lookup_context = {
        "well": str(app._preview_selected_well or ""),
        "fov": str(fov_n),
        "tp": str(tp_n),
        "nucleus_id": str(nucleus_n),
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
    if hasattr(app, "_notebook"):
        _select_tab_by_text(app._notebook, "Review CSV")
    app._review_fov_cb.setCurrentText(fov_n)
    app._review_tp_cb.setCurrentText(tp_n)
    app._refresh_review_csv_rows()

    table = app._review_csv_table
    debug_candidates = []
    for row_idx in range(table.rowCount()):
        row = _table_row_dict(table, row_idx)
        rf, rt, rn = app._review_row_keys(row)
        debug_candidates.append((rf, rt, rn))
        if rf == fov_n and rt == tp_n and rn == nucleus_n:
            table.selectRow(row_idx)
            item = table.item(row_idx, 0)
            if item:
                table.scrollToItem(item)
            app._set_status(f"Matched Review CSV row for nucleus {nucleus_n} at FOV {fov_n}, TP {tp_n}.")
            return
    logger.warning(
        "Review CSV exact row match not found. target=(%s,%s,%s) candidates_shown=%d sample=%s",
        fov_n, tp_n, nucleus_n, len(debug_candidates), debug_candidates[:10],
    )
    app._set_status(
        f"No exact Review CSV row match for nucleus {nucleus_n} at FOV {fov_n}, TP {tp_n}; showing fallback rows."
    )


def on_review_csv_row_double_click(app, item) -> None:
    """Called with a QTableWidgetItem from itemDoubleClicked signal."""
    if not hasattr(app, "_review_csv_table"):
        return
    table = app._review_csv_table
    row_idx = item.row()
    row = _table_row_dict(table, row_idx)
    fov, tp, nid = app._review_row_keys(row)
    well_tok = str(row.get("well", "")).strip()
    key = well_tok if well_tok in app._well_paths else None
    if key is None and app._selected_wells:
        key = sorted(app._selected_wells, key=app._parse_rc)[0]
    if key is None:
        return

    if hasattr(app, "_notebook"):
        _select_tab_by_text(app._notebook, "Review Image")
    app._preview_selected_well = key
    app._update_preview(key)
    if fov:
        app._preview_fov_cb.setCurrentText(fov)
    if tp:
        tp_cb = getattr(app, "_review_image_tp_cb", None)
        if tp_cb is not None:
            tp_cb.setCurrentText(tp)
    if nid:
        try:
            app._review_image_selected_nucleus = int(float(nid))
        except Exception:
            app._review_image_selected_nucleus = None
    app._refresh_review_image()
    if hasattr(app, "_zoom_review_image_to_selected_nucleus"):
        app._zoom_review_image_to_selected_nucleus()
