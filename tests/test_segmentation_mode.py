from pathlib import Path

from process_microscopy_v2 import build_parser
from services.pipeline_service import build_pipeline_args


def test_parser_segmentation_defaults() -> None:
    parser = build_parser()
    args = parser.parse_args(["--input_dir", "in", "--output_dir", "out"])
    assert args.segmentation_method == "stardist_nuclei"
    assert args.cytoplasm_token == ""
    assert args.min_nucleus_area_px == 50


def test_pipeline_args_include_watershed_options() -> None:
    args = build_pipeline_args(
        pipeline=Path("process_microscopy_v2.py"),
        input_dir=Path("in"),
        output_dir=Path("out"),
        opts={
            "nuclear_token": "NIR",
            "fluor_tokens": ["GFP"],
            "csv_prefix": "x",
            "filename_schema": "experiment:channel:well:fov:timepoint",
            "filename_sep": "_",
            "segmentation_method": "stardist_seeded_watershed_cell",
            "cytoplasm_token": "CYTO",
            "min_nucleus_area_px": 77,
        },
    )
    assert "--segmentation_method" in args
    assert "stardist_seeded_watershed_cell" in args
    assert "--cytoplasm_token" in args
    assert "CYTO" in args
    assert "--min_nucleus_area_px" in args
    assert "77" in args


def test_pipeline_args_do_not_emit_cytoplasm_for_stardist() -> None:
    args = build_pipeline_args(
        pipeline=Path("process_microscopy_v2.py"),
        input_dir=Path("in"),
        output_dir=Path("out"),
        opts={
            "nuclear_token": "NIR",
            "fluor_tokens": ["GFP"],
            "csv_prefix": "x",
            "filename_schema": "experiment:channel:well:fov:timepoint",
            "filename_sep": "_",
            "segmentation_method": "stardist_nuclei",
            "cytoplasm_token": "CYTO_SHOULD_BE_IGNORED",
            "min_nucleus_area_px": 50,
        },
    )
    assert "--segmentation_method" in args
    assert "stardist_nuclei" in args
    assert "--cytoplasm_token" not in args


def test_pipeline_args_emit_explicit_compress_flags() -> None:
    args = build_pipeline_args(
        pipeline=Path("process_microscopy_v2.py"),
        input_dir=Path("in"),
        output_dir=Path("out"),
        opts={
            "nuclear_token": "NIR",
            "fluor_tokens": ["GFP"],
            "csv_prefix": "x",
            "filename_schema": "experiment:channel:well:fov:timepoint",
            "filename_sep": "_",
            "compress_input_well_folders": False,
            "compress_output_well_folders": True,
        },
    )
    assert "--no-compress_input_well_folders" in args
    assert "--compress_output_well_folders" in args
