#!/usr/bin/env python3
"""Small smoke check for Review Image view preservation on channel change."""

from __future__ import annotations

from types import SimpleNamespace

import well_viewer.runtime_app as runtime_app


class _Var:
    def __init__(self, value: str) -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value


class _Menu(dict):
    pass


class _Status:
    def config(self, **_kwargs) -> None:
        return


class _Notebook:
    def select(self) -> str:
        return "tab-id"

    def tab(self, _sel: str, key: str) -> str:
        if key != "text":
            raise AssertionError(f"unexpected key: {key}")
        return "Review Image"


def _build_refresh_stub() -> SimpleNamespace:
    app = SimpleNamespace()
    app._review_image_label = object()
    app._preview_selected_well = "A01"
    app._preview_fov_var = _Var("1")
    app._review_image_tp_var = _Var("0")
    app._review_image_tp_menu = _Menu()
    app._preview_fluor = {("1", "0"): "fluor-ref"}
    app._preview_tophat_fluor = {}
    app._preview_mask = {("1", "0"): "mask-ref"}
    app._review_image_status = _Status()
    app._review_image_preserve_view_on_refresh = False
    app._review_image_is_tif = False
    app._review_load_rows = lambda _well: []
    app._review_row_keys = lambda _row: ("", "", "")
    app._active_channel = "gfp"
    return app


def main() -> int:
    orig_open = runtime_app.open_imgref_as_array
    orig_np = runtime_app._np
    orig_np_available = runtime_app._NP_AVAILABLE
    orig_pil_available = runtime_app._PIL_AVAILABLE
    try:
        class _TinyNP:
            @staticmethod
            def asarray(value):
                return value

            @staticmethod
            def unique(_value):
                return [0, 1]

        runtime_app._np = _TinyNP()
        runtime_app._NP_AVAILABLE = True
        runtime_app._PIL_AVAILABLE = True
        runtime_app.open_imgref_as_array = (
            lambda ref, greyscale=True: [[1, 2], [3, 4]]
            if "fluor" in str(ref)
            else [[0, 1], [1, 0]]
        )

        # Smoke 1: _refresh_review_image consumes one-shot preserve flag.
        refresh_app = _build_refresh_stub()
        seen: list[bool] = []
        refresh_app._draw_review_image = lambda *_args, **kwargs: seen.append(bool(kwargs.get("preserve_view")))

        refresh_app._review_image_preserve_view_on_refresh = True
        runtime_app.WellViewerApp._refresh_review_image(refresh_app)
        assert seen[-1] is True, "Expected preserve_view=True on one-shot refresh."
        assert refresh_app._review_image_preserve_view_on_refresh is False, "One-shot flag was not consumed."

        refresh_app._review_image_preserve_view_on_refresh = False
        runtime_app.WellViewerApp._refresh_review_image(refresh_app)
        assert seen[-1] is False, "Expected preserve_view=False on ordinary refresh."

        # Smoke 2: channel change path sets one-shot preserve flag before preview refresh.
        channel_app = SimpleNamespace(
            _active_channel="gfp",
            _smfish_channels=set(),
            _active_metric="mean_intensity",
            _review_image_lut_by_channel={},
            _preview_selected_well="A01",
            _review_image_preserve_view_on_refresh=False,
            _notebook=_Notebook(),
            _bar_tp_cb=object(),
            _active_val_col="gfp_mean_intensity",
            _recalculate_threshold=lambda: None,
            _invalidate_stats_cache=lambda: None,
            _redraw=lambda: None,
            _redraw_bars=lambda: None,
            _update_preview=lambda _well: None,
        )
        runtime_app.WellViewerApp._set_active_channel(channel_app, "mcherry")
        assert channel_app._review_image_preserve_view_on_refresh is True, (
            "Expected channel change path to request preserve_view on the next Review Image refresh."
        )
    finally:
        runtime_app.open_imgref_as_array = orig_open
        runtime_app._np = orig_np
        runtime_app._NP_AVAILABLE = orig_np_available
        runtime_app._PIL_AVAILABLE = orig_pil_available

    print("OK: review image preserve-view smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
