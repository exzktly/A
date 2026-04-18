import json

from services.pipeline_service import write_pipeline_info


def test_write_pipeline_info_persists_effective_fluor_tokens(tmp_path) -> None:
    write_pipeline_info(
        tmp_path,
        filename_schema="experiment:channel:well:fov:timepoint",
        filename_sep="_",
        nuclear_token="NIR",
        fluor_tokens=["GFP", "NIR", "gfp"],
        segmentation_method="stardist_seeded_watershed_cell",
        cytoplasm_token="CYTO",
    )
    data = json.loads((tmp_path / "pipeline_info.json").read_text())
    assert data["fluor_tokens"] == ["NIR", "GFP", "CYTO"]
