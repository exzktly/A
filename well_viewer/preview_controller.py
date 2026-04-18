"""Preview-related helpers extracted from well_viewer3 for incremental migration."""

from __future__ import annotations

import re
import zipfile
import io
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from well_viewer.image_resolver import classify_filename_kind
from well_viewer import debug_flags


def classify_member(
    *,
    name: str,
    fluor_lower: str,
    mask_re,
    overlay_re,
    tophat_fluor_re,
    fov_tp_extractor,
    legacy_extractor: Callable[[str], Tuple[str, str]],
    pipeline_fields_extractor: Callable[[str], dict[str, str]] | None = None,
) -> Tuple[str, str, str]:
    kind, stem = classify_filename_kind(name, fluor_token=fluor_lower)
    is_mask = kind == "mask" or bool(mask_re.search(name))
    is_overlay = kind == "overlay" or bool(overlay_re.search(name))
    is_smfish = kind == "smfish"
    is_tophat_fluor = kind == "fluor_processed" or bool(tophat_fluor_re.search(name))
    if not stem:
        stem = Path(name).stem

    parsed_fields = pipeline_fields_extractor(stem) if pipeline_fields_extractor else {}
    extractor = fov_tp_extractor if fov_tp_extractor is not None else legacy_extractor
    fov, tp = extractor(stem)
    channel_field = str(parsed_fields.get("channel", "")).strip().lower()

    if is_mask:
        return "mask", fov, tp
    if is_overlay:
        return "overlay", fov, tp
    if is_smfish:
        return "smfish", fov, tp
    if is_tophat_fluor:
        # Apply the same channel filtering policy used for raw fluorescence:
        # prefer schema-derived channel when available, else token-in-stem fallback.
        if channel_field:
            if channel_field == fluor_lower:
                return "tophat_fluor", fov, tp
            return "", fov, tp
        if re.search(rf"(?:^|_)({re.escape(fluor_lower)})(?:_|$)", stem, re.I):
            return "tophat_fluor", fov, tp
        return "", fov, tp

    if channel_field:
        if channel_field == fluor_lower:
            return "fluor", fov, tp
        return "", fov, tp
    if re.search(rf"(?:^|_)({re.escape(fluor_lower)})(?:_|$)", stem, re.I):
        return "fluor", fov, tp
    return "", fov, tp


def read_member_bytes(
    *,
    zip_path: Path,
    member: str,
    logger,
) -> Optional[bytes]:
    """Read a member from zip, supporting one nested level via outer::inner."""
    if "::" in member:
        outer, inner = member.split("::", 1)
        outer_bytes = read_member_bytes(zip_path=zip_path, member=outer, logger=logger)
        if outer_bytes is None:
            return None
        with zipfile.ZipFile(io.BytesIO(outer_bytes), "r") as zf:
            try:
                return zf.read(inner)
            except KeyError:
                return None
    with zipfile.ZipFile(zip_path, "r") as zf:
        try:
            return zf.read(member)
        except KeyError:
            return None


def scan_zip_members(
    *,
    zip_path: Path,
    fluor_lower: str,
    image_exts: set[str],
    classify_member_fn: Callable[[str, str, object], Tuple[str, str, str]],
    imgref_factory: Callable[[Path, str], object],
    logger,
    member_prefix: str = "",
    fov_tp_extractor=None,
    pipeline_info: Optional[dict] = None,
) -> Tuple[Dict[Tuple[str, str], object], Dict[Tuple[str, str], object], Dict[Tuple[str, str], object], Dict[Tuple[str, str], object], Dict[Tuple[str, str], object]]:
    fluor: Dict[Tuple[str, str], object] = {}
    overlay: Dict[Tuple[str, str], object] = {}
    mask: Dict[Tuple[str, str], object] = {}
    tophat: Dict[Tuple[str, str], object] = {}
    smfish: Dict[Tuple[str, str], object] = {}
    try:
        if member_prefix:
            raw = read_member_bytes(zip_path=zip_path, member=member_prefix, logger=logger)
            if raw is None:
                logger.warning("Cannot read nested zip member %r from %s", member_prefix, zip_path)
                return fluor, overlay, mask, tophat, smfish
            zf_src = zipfile.ZipFile(io.BytesIO(raw), "r")
        else:
            zf_src = zipfile.ZipFile(zip_path, "r")

        logger.info("Scanning %s%s  (%d members)", zip_path.name, f" >> {member_prefix}" if member_prefix else "", len(zf_src.infolist()))
        with zf_src:
            for info in zf_src.infolist():
                iname = Path(info.filename).name
                if not iname or iname.startswith("."):
                    continue
                if Path(iname).suffix.lower() not in image_exts:
                    logger.debug("  SKIP non-image: %s", iname)
                    continue
                kind, fov, tp = classify_member_fn(
                    iname,
                    fluor_lower,
                    fov_tp_extractor,
                    pipeline_info,
                )
                member_ref = f"{member_prefix}::{info.filename}" if member_prefix else info.filename
                full = f"{zip_path} >> {member_ref}"
                logger.debug("  %-5s fov=%-6s tp=%-12s  %s", kind or "NONE", fov, tp, full)
                if not kind:
                    continue
                key = (fov, tp)
                ref = imgref_factory(zip_path, member_ref)
                if kind == "fluor" and key not in fluor:
                    fluor[key] = ref
                    logger.info("  + FLUOR      fov=%s tp=%s  %s", fov, tp, full)
                elif kind == "tophat_fluor" and key not in tophat:
                    tophat[key] = ref
                    logger.info("  + TOPHAT     fov=%s tp=%s  %s", fov, tp, full)
                elif kind == "overlay" and key not in overlay:
                    overlay[key] = ref
                    logger.info("  + OVERLAY   fov=%s tp=%s  %s", fov, tp, full)
                elif kind == "mask" and key not in mask:
                    mask[key] = ref
                    logger.info("  + MASK      fov=%s tp=%s  %s", fov, tp, full)
                elif kind == "smfish" and key not in smfish:
                    smfish[key] = ref
                    logger.info("  + SMFISH    fov=%s tp=%s  %s", fov, tp, full)
        logger.info("Result: %d fluor, %d tophat, %d smfish, %d overlay(s), %d mask(s) from %s", len(fluor), len(tophat), len(smfish), len(overlay), len(mask), zip_path.name)
    except Exception as exc:
        logger.warning("Failed scanning %s: %s", zip_path, exc)
    return fluor, overlay, mask, tophat, smfish


def open_imgref_as_array(
    *,
    ref,
    greyscale: bool,
    np_available: bool,
    tifffile_available: bool,
    pil_available: bool,
    tifffile_module,
    pil_image_module,
    np_module,
    io_module,
    read_member_bytes_fn: Callable[[Path, str], Optional[bytes]],
    logger,
):
    """Decode an image reference (disk path or zip member) into a numpy array."""
    if not np_available:
        return None

    if ref.disk_path is not None:
        raw_bytes = None
        disk_path: Optional[Path] = ref.disk_path
    else:
        raw_bytes = (
            read_member_bytes_fn(ref.zip_path, ref.zip_member)
            if ref.zip_path and ref.zip_member
            else None
        )
        disk_path = None

    is_tiff = ref.name.lower().endswith((".tif", ".tiff"))

    try:
        if is_tiff and tifffile_available:
            src = str(disk_path) if disk_path else (io_module.BytesIO(raw_bytes) if raw_bytes else None)
            if src is None:
                return None
            arr = tifffile_module.imread(src)
            while arr.ndim > 3:
                arr = arr[0]
            if arr.ndim == 3 and arr.shape[0] in (1, 3, 4):
                arr = np_module.moveaxis(arr, 0, -1)
            if greyscale:
                if arr.ndim == 3:
                    arr = arr.mean(axis=2)
                arr = arr.astype(np_module.float32)
            if debug_flags.review_image_load_debug_enabled() or debug_flags.movie_montage_load_debug_enabled():
                logger.debug(
                    "tifffile: %s  dtype=%s  shape=%s  range=[%.0f,%.0f]",
                    ref.name,
                    arr.dtype,
                    arr.shape,
                    arr.min(),
                    arr.max(),
                )
            return arr

        if not pil_available:
            return None
        pil = (
            pil_image_module.open(disk_path)
            if disk_path
            else pil_image_module.open(io_module.BytesIO(raw_bytes))
            if raw_bytes
            else None
        )
        if pil is None:
            return None

        if pil.mode in ("I;16", "I;16B", "I;16S", "I;16BS"):
            pil = pil.convert("I")

        if greyscale or pil.mode in ("I", "F", "L"):
            if pil.mode not in ("I", "F", "L"):
                pil = pil.convert("L")
            arr = np_module.array(pil, dtype=np_module.float32)
        elif pil.mode in ("RGB", "RGBA"):
            arr = np_module.array(pil.convert("RGB"), dtype=np_module.uint8)
        else:
            arr = np_module.array(pil.convert("L"), dtype=np_module.float32)

        if debug_flags.review_image_load_debug_enabled() or debug_flags.movie_montage_load_debug_enabled():
            logger.debug(
                "PIL: %s  mode=%s  shape=%s  range=[%.0f,%.0f]",
                ref.name,
                pil.mode,
                arr.shape,
                arr.min(),
                arr.max(),
            )
        return arr
    except Exception as exc:
        logger.warning("open_imgref_as_array failed for %s: %s", ref.name, exc)
        return None
