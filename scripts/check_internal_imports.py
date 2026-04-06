#!/usr/bin/env python3
"""Validate intra-repo `from X import name` targets exist.

This catches refactor regressions where a helper is moved/renamed but an
import statement still references the old symbol.
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _module_name(path: Path) -> str:
    rel = path.relative_to(ROOT)
    if rel.parent == Path("."):
        return path.stem
    return ".".join(rel.with_suffix("").parts)


def _public_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[-1])
    return names


def main() -> int:
    py_files = [
        p
        for p in (list(ROOT.glob("*.py")) + list((ROOT / "well_viewer").glob("*.py")))
        if p.is_file()
    ]
    modules = {_module_name(path): _public_names(ast.parse(path.read_text())) for path in py_files}

    failures: list[str] = []
    for path in py_files:
        src_mod = _module_name(path)
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            target_mod = node.module
            if not target_mod or target_mod not in modules:
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                if alias.name not in modules[target_mod]:
                    failures.append(
                        f"{src_mod}:{node.lineno} imports missing symbol "
                        f"'{alias.name}' from '{target_mod}'"
                    )

    if failures:
        print("[FAIL] broken internal imports detected:")
        for msg in failures:
            print(f"  - {msg}")
        return 1

    print("[OK] internal imports resolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
