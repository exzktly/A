from well_viewer.image_resolver import find_well_subfolder_path
from well_viewer.image_resolver import normalize_well_token


def test_normalize_well_token_equivalent_forms() -> None:
    assert normalize_well_token("A1") == "A01"
    assert normalize_well_token("a01") == "A01"
    assert normalize_well_token("H12") == "H12"


def test_find_well_subfolder_accepts_unpadded_folder_name(tmp_path) -> None:
    (tmp_path / "A1").mkdir()
    resolved = find_well_subfolder_path(tmp_path, "A01")
    assert resolved is not None
    assert resolved.name == "A1"


def test_find_well_subfolder_accepts_padded_folder_name(tmp_path) -> None:
    (tmp_path / "B02").mkdir()
    resolved = find_well_subfolder_path(tmp_path, "B2")
    assert resolved is not None
    assert resolved.name == "B02"
