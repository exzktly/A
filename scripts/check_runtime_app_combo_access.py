#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

p = Path(__file__).resolve().parents[1] / 'well_viewer' / 'runtime_app.py'
text = p.read_text()
pat = re.compile(r"_\w+_cb\.get\(")
matches = [(m.start(), m.group(0)) for m in pat.finditer(text)]
if matches:
    print(f"FAIL: found {len(matches)} tkinter-style combobox .get() call(s) in runtime_app.py")
    for idx, _ in matches:
        line = text.count('\n', 0, idx) + 1
        print(f"  line {line}")
    raise SystemExit(1)
print('PASS: no tkinter-style *_cb.get() calls found in runtime_app.py')
