#!/usr/bin/env python3
"""Fail when a Python class defines the same method name multiple times."""

from __future__ import annotations

import ast
import sys
from collections import Counter
from pathlib import Path


def find_duplicates(path: Path) -> list[tuple[str, str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    duplicates: list[tuple[str, str, int]] = []

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        method_names = [
            item.name
            for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        counts = Counter(method_names)
        for method_name, count in counts.items():
            if count > 1:
                duplicates.append((node.name, method_name, count))

    return duplicates


def main(argv: list[str]) -> int:
    targets = [Path(p) for p in argv] if argv else [Path("well_viewer/runtime_app.py")]
    had_dupes = False

    for target in targets:
        if not target.exists():
            print(f"[WARN] missing file: {target}")
            had_dupes = True
            continue
        dupes = find_duplicates(target)
        if not dupes:
            print(f"[OK] {target}: no duplicate class-method names")
            continue
        had_dupes = True
        for cls_name, method_name, count in dupes:
            print(
                f"[DUPLICATE] {target}: class {cls_name} defines "
                f"method {method_name!r} {count} times"
            )

    return 1 if had_dupes else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
