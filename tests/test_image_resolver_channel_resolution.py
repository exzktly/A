import logging

from well_viewer.image_resolver import ResolvedFrameRef, resolve_channel_frame_refs


def test_resolve_channel_frame_refs_applies_canonical_precedence() -> None:
    refs_by_kind = {
        "fluor_raw": {("1", "0"): "raw_10", ("2", "0"): "raw_20"},
        "fluor_processed": {("1", "0"): "proc_10"},
        "smfish": {("1", "0"): "smfish_10"},
        "overlay": {("3", "0"): "overlay_30"},
        "mask": {("4", "0"): "mask_40"},
    }

    resolved = resolve_channel_frame_refs(refs_by_kind=refs_by_kind)

    assert resolved[("1", "0")] == ResolvedFrameRef(
        key=("1", "0"),
        kind="smfish",
        ref="smfish_10",
        reason="selected_first_preference",
    )
    assert resolved[("2", "0")].kind == "fluor_raw"
    assert resolved[("2", "0")].reason == "selected_fallback_preference"
    assert resolved[("3", "0")].kind == "overlay"
    assert resolved[("4", "0")].kind == "mask"


def test_resolve_channel_frame_refs_treats_fluor_processed_as_tophat_alias() -> None:
    resolved = resolve_channel_frame_refs(
        refs_by_kind={"fluor_processed": {("1", "0"): "proc_10"}},
    )

    assert resolved[("1", "0")] == ResolvedFrameRef(
        key=("1", "0"),
        kind="tophat",
        ref="proc_10",
        reason="selected_fallback_preference",
    )


def test_resolve_channel_frame_refs_returns_reason_for_unresolved_keys() -> None:
    resolved = resolve_channel_frame_refs(
        refs_by_kind={"fluor_raw": {("1", "0"): "raw_10"}},
        expected_keys={("1", "0"), ("9", "9")},
    )

    assert resolved[("9", "9")] == ResolvedFrameRef(
        key=("9", "9"),
        kind="missing",
        ref=None,
        reason="missing_all_candidates",
    )


def test_resolve_channel_frame_refs_emits_diagnostics(caplog) -> None:
    logger = logging.getLogger("resolver-test")
    with caplog.at_level(logging.DEBUG):
        _ = resolve_channel_frame_refs(
            refs_by_kind={"fluor_raw": {("1", "0"): "raw_10"}},
            expected_keys={("1", "0")},
            logger=logger,
            context={"well": "A01", "channel": "gfp"},
        )

    joined = "\n".join(caplog.messages)
    assert "image_resolver context=" in joined
    assert "image_resolver discovered counts:" in joined
    assert "image_resolver decision key=('1', '0')" in joined
