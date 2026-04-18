import json

from services.pipeline_service import effective_fluor_tokens, write_pipeline_info
from well_viewer.runtime_app import (
    detect_review_image_channels,
    merge_fluor_channels,
    normalize_channel_tokens,
)


def test_effective_fluor_tokens_includes_nuclear_token() -> None:
    tokens = effective_fluor_tokens(["GFP", "mCherry", "gfp"], nuclear_token="NIR")
    assert tokens == ["nir", "gfp", "mcherry"]


def test_write_pipeline_info_persists_effective_fluor_tokens(tmp_path) -> None:
    write_pipeline_info(
        tmp_path,
        filename_schema="experiment:channel:well:fov:timepoint",
        filename_sep="_",
        nuclear_token="NIR",
        fluor_tokens=["GFP", "NIR", "gfp"],
    )
    data = json.loads((tmp_path / "pipeline_info.json").read_text())
    assert data["fluor_tokens"] == ["nir", "gfp"]


def test_merge_fluor_channels_includes_seg_token_for_viewer_selectors() -> None:
    merged = merge_fluor_channels(["gfp"], ["mcherry"], "nir")
    assert merged == ["gfp", "mcherry", "nir"]


def test_channel_merge_and_review_lists_avoid_duplicates() -> None:
    merged = merge_fluor_channels(["GFP", "nir"], ["gfp", "NIR"], "NIR")
    assert merged == ["gfp", "nir"]

    review = detect_review_image_channels([], normalize_channel_tokens(["GFP", "nir"]), "NIR")
    assert review == ["gfp", "nir"]
