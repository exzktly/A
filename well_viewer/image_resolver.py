"""Shared image resolution helpers used by Review/Preview/Scatter/smFISH tabs."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Mapping, Optional


OUTPUT_SUFFIXES: dict[str, tuple[str, ...]] = {
    "mask": ("_labels.tif", "_labels.tiff", "_labels.png"),
    "overlay": ("_overlay.png", "_overlay.jpg", "_overlay.jpeg", "_overlay.tif"),
}


def normalize_row_filename(filename: str) -> str:
    """Normalize metadata-provided filename to basename only."""
    raw = str(filename or "").strip()
    if not raw:
        return ""
    return Path(raw).name


def normalize_numeric_token(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        return f"{float(raw):g}"
    except Exception:
        return raw


def resolve_ref_by_fov_tp(
    refs: Mapping[tuple[str, str], object],
    *,
    fov_raw: str,
    tp_raw: str,
    norm_timepoint: Callable[[object], str],
) -> Optional[object]:
    """Resolve image ref by exact key, then normalized key."""
    exact = refs.get((fov_raw, tp_raw))
    if exact is not None:
        return exact
    fov_norm = normalize_numeric_token(fov_raw)
    tp_norm = norm_timepoint(tp_raw)
    for (k_fov, k_tp), k_ref in refs.items():
        if normalize_numeric_token(k_fov) == fov_norm and norm_timepoint(k_tp) == tp_norm:
            return k_ref
    return None


def schema_fields(pipeline_info: Optional[dict]) -> list[str]:
    if not pipeline_info:
        return []
    fields = [
        str(f).strip()
        for f in (pipeline_info.get("schema_fields", []) or [])
        if str(f).strip()
    ]
    if fields:
        return fields
    schema = str(pipeline_info.get("schema", "")).strip()
    if not schema:
        return []
    return [f.strip() for f in schema.split(":") if f.strip()]


def parse_stem_with_schema(stem: str, pipeline_info: Optional[dict]) -> dict[str, str]:
    fields = schema_fields(pipeline_info)
    if not fields:
        return {}
    sep = str((pipeline_info or {}).get("separator", "_"))
    parts = stem.split(sep)
    return {field: (parts[i] if i < len(parts) else "") for i, field in enumerate(fields)}


def compose_stem_from_schema(values: dict[str, str], pipeline_info: Optional[dict]) -> str:
    fields = schema_fields(pipeline_info)
    if not fields:
        return ""
    sep = str((pipeline_info or {}).get("separator", "_"))
    parts: list[str] = []
    for field in fields:
        val = str(values.get(field, "")).strip()
        if val:
            parts.append(val)
    return sep.join(parts)


def resolve_filename_candidates(
    filename: str,
    *,
    pipeline_info: Optional[dict],
    target_channel: str = "",
    output_kind: str = "",
    filename_variants_fn: Callable[[str], list[str]] | None = None,
) -> list[str]:
    """Canonical filename resolver used across image-consuming tabs.

    - Normalizes input filename to basename.
    - Uses schema metadata from pipeline_info.json when available.
    - Never drops tokens from output name generation.
    """
    base_name = normalize_row_filename(filename)
    if not base_name:
        return []
    p = Path(base_name)
    stem = p.stem

    # 1) Schema-driven candidate (authoritative when available).
    out: list[str] = []
    fields = parse_stem_with_schema(stem, pipeline_info)
    if fields:
        if target_channel:
            fields["channel"] = target_channel
        schema_stem = compose_stem_from_schema(fields, pipeline_info)
        if schema_stem:
            out.append(f"{schema_stem}{p.suffix}" if p.suffix else schema_stem)

    # 2) Original filename fallback (still rooted to active dataset dirs).
    out.append(base_name)

    # 3) Expand output suffixes where needed.
    if output_kind:
        suffixes = OUTPUT_SUFFIXES.get(output_kind, ())
        expanded: list[str] = []

        # Backwards compatibility: old output naming dropped channel/nuclear tokens.
        legacy_stems: list[str] = []
        if fields:
            channel_dropped = dict(fields)
            channel_dropped.pop("channel", None)
            dropped_schema_stem = compose_stem_from_schema(channel_dropped, pipeline_info)
            if dropped_schema_stem:
                legacy_stems.append(dropped_schema_stem)

        nuclear_token = str((pipeline_info or {}).get("nuclear_token", "")).strip()
        for name in list(out):
            stem_name = Path(name).stem
            if nuclear_token and nuclear_token in stem_name:
                stripped = stem_name.replace(nuclear_token, "")
                if stripped:
                    legacy_stems.append(stripped)

        for stem_name in [Path(name).stem for name in out] + legacy_stems:
            for suffix in suffixes:
                expanded.append(f"{stem_name}{suffix}")
        out = expanded

    # 4) Expand with variant function (well padding etc).
    if filename_variants_fn is not None:
        variants: list[str] = []
        for name in out:
            variants.extend(filename_variants_fn(name))
        out = variants or out

    # Deduplicate while preserving order.
    ordered: list[str] = []
    seen: set[str] = set()
    for name in out:
        if name and name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered
