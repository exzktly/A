from well_viewer.scatter_callbacks import (
    _lookup_filename_from_row_value,
)
from well_viewer.image_resolver import resolve_filename_candidates
from well_viewer.image_resolver import resolve_ref_by_fov_tp


def test_lookup_filename_drops_absolute_path() -> None:
    assert _lookup_filename_from_row_value("/tmp/some/run/A01_NIR_t0.tif") == "A01_NIR_t0.tif"


def test_lookup_filename_drops_relative_path() -> None:
    assert _lookup_filename_from_row_value("nested/in/A01_NIR_t0.tif") == "A01_NIR_t0.tif"


def test_lookup_filename_passthrough_plain_name() -> None:
    assert _lookup_filename_from_row_value("A01_NIR_t0.tif") == "A01_NIR_t0.tif"


def test_schema_adjusted_name_candidates_replace_channel() -> None:
    pipeline_info = {
        "separator": "_",
        "schema_fields": ["experiment", "channel", "well", "fov", "timepoint"],
    }
    out = resolve_filename_candidates(
        "exp_nir_A01_1_0.tif",
        pipeline_info=pipeline_info,
        target_channel="gfp",
    )
    assert "exp_gfp_A01_1_0.tif" in out


def test_schema_adjusted_name_candidates_keep_channel_for_output_matching() -> None:
    pipeline_info = {
        "separator": "_",
        "schema_fields": ["experiment", "channel", "well", "fov", "timepoint"],
    }
    out = resolve_filename_candidates(
        "exp_nir_A01_1_0.tif",
        pipeline_info=pipeline_info,
        output_kind="mask",
    )
    assert "exp_nir_A01_1_0_labels.tif" in out


def test_resolve_ref_by_fov_tp_normalized_match() -> None:
    refs = {("1", "24"): "img_ref"}
    out = resolve_ref_by_fov_tp(
        refs,
        fov_raw="1.0",
        tp_raw="24.0",
        norm_timepoint=lambda value: str(int(float(str(value)))) if str(value).strip() else "",
    )
    assert out == "img_ref"
