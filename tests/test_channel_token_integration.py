import json

from services.pipeline_service import collect_available_fovs, collect_available_timepoints, write_pipeline_info


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


def test_collect_available_timepoints_and_persist(tmp_path) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "A01").mkdir()
    (in_dir / "A01" / "exp_GFP_A01_001_00h00m.tif").write_bytes(b"")
    (in_dir / "A01" / "exp_GFP_A01_001_02h30m.tif").write_bytes(b"")
    (in_dir / "A01" / "exp_GFP_A01_001_01h00m.tif").write_bytes(b"")
    tps = collect_available_timepoints(
        in_dir,
        filename_schema="experiment:channel:well:fov:timepoint",
        filename_sep="_",
    )
    assert tps == ["00h00m", "01h00m", "02h30m"]

    write_pipeline_info(
        tmp_path,
        filename_schema="experiment:channel:well:fov:timepoint",
        filename_sep="_",
        fluor_tokens=["GFP"],
        available_timepoints=tps,
    )
    data = json.loads((tmp_path / "pipeline_info.json").read_text())
    assert data["available_timepoints"] == ["00h00m", "01h00m", "02h30m"]


def test_collect_available_fovs_and_persist(tmp_path) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "A01").mkdir()
    (in_dir / "A01" / "exp_GFP_A01_010_00h00m.tif").write_bytes(b"")
    (in_dir / "A01" / "exp_GFP_A01_002_00h00m.tif").write_bytes(b"")
    (in_dir / "A01" / "exp_GFP_A01_001_00h00m.tif").write_bytes(b"")
    fovs = collect_available_fovs(
        in_dir,
        filename_schema="experiment:channel:well:fov:timepoint",
        filename_sep="_",
    )
    assert fovs == ["001", "002", "010"]

    write_pipeline_info(
        tmp_path,
        filename_schema="experiment:channel:well:fov:timepoint",
        filename_sep="_",
        fluor_tokens=["GFP"],
        available_fovs=fovs,
    )
    data = json.loads((tmp_path / "pipeline_info.json").read_text())
    assert data["available_fovs"] == ["001", "002", "010"]
