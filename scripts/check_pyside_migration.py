#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIT = REPO / "_Docs" / "attribute_call_audit.csv"


def main() -> int:
    if not AUDIT.exists():
        print("Audit missing. Run scripts/generate_attribute_audit.py first.")
        return 2

    rows = list(csv.DictReader(AUDIT.open()))
    flagged = [r for r in rows if r.get("migrated_pyside") == "false"]
    print(f"Total rows: {len(rows)}")
    print(f"Flagged non-migrated: {len(flagged)}")

    # Controlled remediation phase gate: zero non-migrated callsites.
    if flagged:
        print("FAIL: Migration gate not met (non-zero flagged callsites).")
        return 1

    print("PASS: Migration gate met.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
