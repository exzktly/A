import os
import re
import sys
import argparse
from zipfile import ZipFile, ZIP_DEFLATED
from typing import List, Optional

# ---------------------------------------------------------------------------
# Schema constants (kept in sync with process_microscopy_v2.py)
# ---------------------------------------------------------------------------
SCHEMA_FIELDS   = ("experiment", "channel", "well", "fov", "timepoint", "ignore")
DEFAULT_SCHEMA  = "experiment:channel:well:fov:timepoint"
DEFAULT_SEP     = "_"

# Fallback regex used when no schema is provided (legacy behaviour).
# Matches _A01_ or _A1_ (case-insensitive) anywhere in the filename.
_LEGACY_WELL_RE = re.compile(r"_([A-H])(0?\d)_", re.IGNORECASE)


def parse_schema(schema_str: str) -> List[str]:
    """Parse a colon-delimited schema string into a list of field names."""
    known = set(SCHEMA_FIELDS)
    return [
        tok if tok in known else "ignore"
        for tok in schema_str.strip().split(":")
        if tok
    ]


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Zip TIFF files by 96-well plate IDs in filenames"
    )
    parser.add_argument("-s", "--search-dir", required=True)
    parser.add_argument("-o", "--output-dir", default=None)
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument(
        "--filename_schema", default=DEFAULT_SCHEMA,
        help=(
            "Colon-separated ordered field names describing the filename "
            "structure.  \"well\" must appear exactly once.  "
            f"Default: \"{DEFAULT_SCHEMA}\""
        ),
    )
    parser.add_argument(
        "--filename_sep", default=DEFAULT_SEP,
        help=f"Field separator character in filenames.  Default: \"{DEFAULT_SEP}\"",
    )
    return parser


def generate_wells() -> List[str]:
    return [f"{r}{c:02d}" for r in "ABCDEFGH" for c in range(1, 13)]


def _well_index_from_schema(schema: List[str]) -> Optional[int]:
    """Return the position index of the \"well\" field, or None if absent."""
    try:
        return schema.index("well")
    except ValueError:
        return None


def _extract_well_from_filename(
    fname: str,
    schema: List[str],
    sep: str,
) -> Optional[str]:
    """
    Extract the well token from *fname* using the given schema.

    Returns the normalised well label (e.g. "A01") if the filename contains a
    valid 96-well plate position at the schema's "well" slot, otherwise None.
    Falls back to the legacy _A01_ regex pattern when the schema has no "well"
    slot.
    """
    stem = os.path.splitext(fname)[0]
    well_idx = _well_index_from_schema(schema)

    if well_idx is not None:
        # Schema-based extraction: split on sep and read the well slot.
        parts = stem.split(sep)
        if well_idx >= len(parts):
            return None
        token = parts[well_idx]
    else:
        # Legacy fallback: find _A01_ or _A1_ anywhere in the stem.
        m = _LEGACY_WELL_RE.search(fname)
        if not m:
            return None
        token = m.group(0).strip("_")

    # Validate and normalise: must match A-H, 01-12.
    m = re.fullmatch(r"([A-Ha-h])(\d{1,2})", token)
    if not m:
        return None
    col = int(m.group(2))
    if not (1 <= col <= 12):
        return None
    return f"{m.group(1).upper()}{col:02d}"


def find_matching_files(
    well: str,
    search_dir: str,
    recursive: bool,
    schema: List[str],
    sep: str,
) -> List[str]:
    """Return all TIFF files in *search_dir* whose well token matches *well*."""
    matches = []
    for root, _, files in os.walk(search_dir):
        for fname in files:
            if not fname.lower().endswith((".tif", ".tiff")):
                continue
            extracted = _extract_well_from_filename(fname, schema, sep)
            if extracted and extracted.upper() == well.upper():
                matches.append(os.path.join(root, fname))
        if not recursive:
            break
    return matches


def zip_well(well: str, files: List[str], output_dir: str):
    if not files:
        return
    zip_path = os.path.join(output_dir, f"{well}.zip")
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, arcname=os.path.basename(f))
    print(f"{well}: {len(files)} files")


def main():
    args = build_arg_parser().parse_args()

    search_dir = args.search_dir
    output_dir = args.output_dir or search_dir
    schema     = parse_schema(args.filename_schema)
    sep        = args.filename_sep

    if not os.path.isdir(search_dir):
        sys.exit(f"Invalid directory: {search_dir}")

    os.makedirs(output_dir, exist_ok=True)

    for well in generate_wells():
        files = find_matching_files(well, search_dir, args.recursive, schema, sep)
        zip_well(well, files, output_dir)


if __name__ == "__main__":
    main()
