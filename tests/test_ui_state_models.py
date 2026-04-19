from services.ui_state_models import AnalysisPipelineState


def test_analysis_state_normalizes_defaults_and_cytoplasm() -> None:
    state = AnalysisPipelineState.from_ui_values(
        raw_input=" /tmp/raw ",
        nuclear_token="",
        fluor_tokens=["GFP"],
        smfish_tokens=[],
        csv_prefix="",
        filename_schema="experiment:channel:well:fov:timepoint",
        filename_sep="_",
        segmentation_method="stardist_nuclei",
        cytoplasm_token="CYTO",
        min_nucleus_area_px="oops",
        tophat_radius_nir="100",
        tophat_radius_fluor="100",
        no_tophat_nir=False,
        no_tophat_fluor=False,
        compress_input_well_folders=True,
        compress_output_well_folders=True,
        force=False,
        cpu_only=False,
        tf_threads="0",
        workers="0",
    )
    opts = state.to_pipeline_options()
    assert state.nuclear_token == "NIR"
    assert state.csv_prefix == "gfp_measurements"
    assert state.min_nucleus_area_px == 50
    assert state.cytoplasm_token == ""
    assert str(opts["raw"]) == "/tmp/raw"


def test_analysis_state_keeps_cytoplasm_when_seeded_watershed() -> None:
    state = AnalysisPipelineState.from_ui_values(
        raw_input="/tmp/raw",
        nuclear_token="NIR",
        fluor_tokens=["GFP"],
        smfish_tokens=["SMFISH"],
        csv_prefix="csv",
        filename_schema="experiment:channel:well:fov:timepoint",
        filename_sep="_",
        segmentation_method="stardist_seeded_watershed_cell",
        cytoplasm_token="CYTO",
        min_nucleus_area_px="73",
        tophat_radius_nir="100",
        tophat_radius_fluor="100",
        no_tophat_nir=False,
        no_tophat_fluor=True,
        compress_input_well_folders=True,
        compress_output_well_folders=False,
        force=True,
        cpu_only=True,
        tf_threads="2",
        workers="4",
    )
    assert state.cytoplasm_token == "CYTO"
    assert state.min_nucleus_area_px == 73
