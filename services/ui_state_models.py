"""Typed UI-independent state models for migration Phases 2/3.

These dataclasses represent feature-domain state that previously lived mostly in
StringVar/BooleanVar/IntVar bags across UI modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AnalysisPipelineState:
    raw_input: Path
    nuclear_token: str
    fluor_tokens: list[str]
    smfish_tokens: list[str]
    csv_prefix: str
    filename_schema: str
    filename_sep: str
    segmentation_method: str
    cytoplasm_token: str
    min_nucleus_area_px: int
    tophat_radius_nir: str
    tophat_radius_fluor: str
    no_tophat_nir: bool
    no_tophat_fluor: bool
    compress_input_well_folders: bool
    compress_output_well_folders: bool
    force: bool
    cpu_only: bool
    tf_threads: str
    workers: str

    @staticmethod
    def _parse_min_area(value: str, fallback: int = 50) -> int:
        try:
            parsed = int(value.strip()) if value.strip() else fallback
        except ValueError:
            return fallback
        return max(0, parsed)

    @classmethod
    def from_ui_values(
        cls,
        *,
        raw_input: str,
        nuclear_token: str,
        fluor_tokens: list[str],
        smfish_tokens: list[str],
        csv_prefix: str,
        filename_schema: str,
        filename_sep: str,
        segmentation_method: str,
        cytoplasm_token: str,
        min_nucleus_area_px: str,
        tophat_radius_nir: str,
        tophat_radius_fluor: str,
        no_tophat_nir: bool,
        no_tophat_fluor: bool,
        compress_input_well_folders: bool,
        compress_output_well_folders: bool,
        force: bool,
        cpu_only: bool,
        tf_threads: str,
        workers: str,
    ) -> "AnalysisPipelineState":
        method = (segmentation_method or "stardist_nuclei").strip() or "stardist_nuclei"
        cyto = (cytoplasm_token or "").strip()
        if method != "stardist_seeded_watershed_cell":
            cyto = ""
        return cls(
            raw_input=Path((raw_input or "").strip()),
            nuclear_token=(nuclear_token or "NIR").strip() or "NIR",
            fluor_tokens=list(fluor_tokens),
            smfish_tokens=list(smfish_tokens),
            csv_prefix=(csv_prefix or "gfp_measurements").strip() or "gfp_measurements",
            filename_schema=filename_schema,
            filename_sep=filename_sep,
            segmentation_method=method,
            cytoplasm_token=cyto,
            min_nucleus_area_px=cls._parse_min_area(min_nucleus_area_px),
            tophat_radius_nir=tophat_radius_nir,
            tophat_radius_fluor=tophat_radius_fluor,
            no_tophat_nir=no_tophat_nir,
            no_tophat_fluor=no_tophat_fluor,
            compress_input_well_folders=compress_input_well_folders,
            compress_output_well_folders=compress_output_well_folders,
            force=force,
            cpu_only=cpu_only,
            tf_threads=tf_threads,
            workers=workers,
        )

    def to_pipeline_options(self) -> dict:
        return {
            "raw": self.raw_input,
            "nuclear_token": self.nuclear_token,
            "fluor_tokens": self.fluor_tokens,
            "csv_prefix": self.csv_prefix,
            "tophat_radius_nir": self.tophat_radius_nir,
            "tophat_radius_fluor": self.tophat_radius_fluor,
            "no_tophat_nir": self.no_tophat_nir,
            "no_tophat_fluor": self.no_tophat_fluor,
            "compress_input_well_folders": self.compress_input_well_folders,
            "compress_output_well_folders": self.compress_output_well_folders,
            "force": self.force,
            "cpu_only": self.cpu_only,
            "tf_threads": self.tf_threads,
            "workers": self.workers,
            "filename_schema": self.filename_schema,
            "filename_sep": self.filename_sep,
            "smfish_tokens": self.smfish_tokens,
            "segmentation_method": self.segmentation_method,
            "cytoplasm_token": self.cytoplasm_token,
            "min_nucleus_area_px": self.min_nucleus_area_px,
        }


@dataclass
class PlotViewState:
    selected_timepoints: list[str] = field(default_factory=list)
    selected_wells: list[str] = field(default_factory=list)
    show_sem: bool = False
    show_sd: bool = True


@dataclass
class GroupingState:
    selected_group: str | None = None
    replicate_sets: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class ExportSettings:
    default_json_name: str = "data.json"
    default_directory: str | None = None
    overwrite_existing: bool = False
