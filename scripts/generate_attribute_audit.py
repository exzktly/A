#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "well_viewer"
OUT_CSV = REPO / "_Docs" / "attribute_call_audit.csv"
OUT_MD = REPO / "_Docs" / "attribute_call_audit.md"

LEGACY_METHODS = {
    "config",
    "configure",
    "pack",
    "pack_forget",
    "winfo_exists",
    "winfo_children",
    "winfo_width",
    "winfo_height",
    "winfo_rootx",
    "winfo_rooty",
    "winfo_containing",
    "winfo_manager",
    "tab",
    "select",
}


def classify(file: str, line: int, receiver: str, method: str) -> tuple[str, str]:
    """Return (migrated_pyside, reason)."""
    # helper internals in runtime_app.py intentionally call both APIs
    if file.endswith("runtime_app.py") and 2550 <= line <= 2900:
        return "true", "compat helper internals"

    if method in LEGACY_METHODS:
        return "false", f"legacy method: {method}"

    if method in {"get", "set"} and receiver.endswith("_var"):
        # these are still relevant migration hotspots
        return "false", "direct *_var access (not helper)"

    return "true", "Qt-safe/default"


def main() -> int:
    rows: list[dict[str, object]] = []
    for path in sorted(SRC.rglob("*.py")):
        rel = str(path.relative_to(REPO))
        try:
            tree = ast.parse(path.read_text())
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                try:
                    receiver = ast.unparse(node.func.value)
                except Exception:
                    receiver = ""
                method = node.func.attr
                migrated, reason = classify(rel, node.lineno, receiver, method)
                rows.append(
                    {
                        "file": rel,
                        "line": node.lineno,
                        "col": node.col_offset,
                        "receiver": receiver,
                        "method": method,
                        "migrated_pyside": migrated,
                        "reason": reason,
                    }
                )

    rows.sort(key=lambda r: (str(r["file"]), int(r["line"]), int(r["col"])))
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["file", "line", "col", "receiver", "method", "migrated_pyside", "reason"],
        )
        w.writeheader()
        w.writerows(rows)

    flagged = [r for r in rows if r["migrated_pyside"] == "false"]
    by_method = Counter(r["method"] for r in flagged)

    with OUT_MD.open("w") as f:
        f.write("# Attribute Call Audit (well_viewer)\n\n")
        f.write(f"Total attribute call sites: **{len(rows)}**\\\n")
        f.write(f"Flagged non-migrated: **{len(flagged)}**\\\n")
        f.write(
            "Heuristic: marks legacy tk methods and direct `*_var.get/set` as non-migrated; "
            "compat helper internals are marked migrated.\n\n"
        )
        f.write("## Flagged by Method\n\n")
        for m, c in sorted(by_method.items(), key=lambda x: (-x[1], x[0])):
            f.write(f"- `{m}`: {c}\n")

        f.write("\n## Full Table\n\n")
        f.write("| file | line | receiver | method | migrated_pyside | reason |\n")
        f.write("|---|---:|---|---|---|---|\n")
        for r in rows:
            recv = str(r["receiver"]).replace("|", "\\|")
            reason = str(r["reason"]).replace("|", "\\|")
            f.write(
                f"| {r['file']} | {r['line']} | `{recv}` | `{r['method']}` | {r['migrated_pyside']} | {reason} |\n"
            )

    print(f"Wrote {OUT_CSV} and {OUT_MD}. Flagged non-migrated: {len(flagged)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
