from pathlib import Path

from well_viewer.image_resolver import OUTPUT_SUFFIXES, resolve_filename_candidates
from well_viewer.preview_controller import classify_member, scan_zip_members


PIPELINE_INFO = {
    "separator": "_",
    "schema_fields": ["experiment", "channel", "well", "fov", "timepoint"],
}


def _identity_variants(filename: str) -> list[str]:
    return [filename]


def test_candidate_order_is_consistent_across_tabs() -> None:
    source = "exp_nir_A01_1_0.tif"

    review_candidates = resolve_filename_candidates(
        source,
        pipeline_info=PIPELINE_INFO,
        target_channel="gfp",
        filename_variants_fn=_identity_variants,
    )
    montage_candidates = resolve_filename_candidates(
        source,
        pipeline_info=PIPELINE_INFO,
        target_channel="gfp",
        filename_variants_fn=_identity_variants,
    )
    scatter_candidates = resolve_filename_candidates(
        source,
        pipeline_info=PIPELINE_INFO,
        target_channel="gfp",
        filename_variants_fn=_identity_variants,
    )

    assert review_candidates == montage_candidates == scatter_candidates
    assert review_candidates[:2] == ["exp_gfp_A01_1_0.tif", "exp_nir_A01_1_0.tif"]

    mask_candidates = resolve_filename_candidates(source, pipeline_info=PIPELINE_INFO, output_kind="mask")
    overlay_candidates = resolve_filename_candidates(source, pipeline_info=PIPELINE_INFO, output_kind="overlay")
    processed_candidates = resolve_filename_candidates(
        source,
        pipeline_info=PIPELINE_INFO,
        target_channel="gfp",
        output_kind="fluor_processed",
    )
    smfish_candidates = resolve_filename_candidates(
        source,
        pipeline_info=PIPELINE_INFO,
        target_channel="gfp",
        output_kind="smfish",
    )

    assert mask_candidates[0].endswith(OUTPUT_SUFFIXES["mask"][0])
    assert overlay_candidates[0].endswith(OUTPUT_SUFFIXES["overlay"][0])
    assert processed_candidates[0].endswith("_tophat.tif")
    assert smfish_candidates[0].endswith("_smfish.tif")
    assert any(name.endswith("_tophat_gfp.tif") for name in processed_candidates)
    assert any(name.endswith("_smfish_gfp.tif") for name in smfish_candidates)


def test_movie_montage_channel_switch_finds_derived_tophat_outputs(tmp_path: Path) -> None:
    import logging
    import re
    import zipfile

    zip_path = tmp_path / "A01_out.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("exp_gfp_A01_1_0_tophat_gfp.tif", b"")
        zf.writestr("exp_mcherry_A01_1_0_tophat_mcherry.tif", b"")
        zf.writestr("exp_nir_A01_1_0_labels.tif", b"")

    extractor = lambda stem: (stem.split("_")[-2], stem.split("_")[-1])
    mask_re = re.compile(r"_labels\.(?:tif|tiff|png)$", re.I)
    overlay_re = re.compile(r"_overlay\.(?:tif|tiff|png|jpe?g)$", re.I)
    tophat_re = re.compile(r"_tophat(?:_\w+)?\.(?:tif|tiff)$", re.I)
    logger = logging.getLogger("resolver_test")

    def _classifier(name: str, fluor_lower: str, fov_tp_extractor, _pipeline_info):
        return classify_member(
            name=name,
            fluor_lower=fluor_lower,
            mask_re=mask_re,
            overlay_re=overlay_re,
            tophat_fluor_re=tophat_re,
            fov_tp_extractor=fov_tp_extractor,
            legacy_extractor=extractor,
            pipeline_fields_extractor=lambda stem: {},
        )

    fluor_g, _ov_g, _mk_g, tophat_g, _sm_g = scan_zip_members(
        zip_path=zip_path,
        fluor_lower="gfp",
        image_exts={".tif", ".tiff", ".png", ".jpg", ".jpeg"},
        classify_member_fn=_classifier,
        imgref_factory=lambda _p, m: m,
        logger=logger,
        fov_tp_extractor=extractor,
    )
    fluor_m, _ov_m, _mk_m, tophat_m, _sm_m = scan_zip_members(
        zip_path=zip_path,
        fluor_lower="mcherry",
        image_exts={".tif", ".tiff", ".png", ".jpg", ".jpeg"},
        classify_member_fn=_classifier,
        imgref_factory=lambda _p, m: m,
        logger=logger,
        fov_tp_extractor=extractor,
    )

    assert fluor_g == {}
    assert fluor_m == {}
    assert ("1", "0") in tophat_g
    assert ("1", "0") in tophat_m
