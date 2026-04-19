# PySide6 Migration — Port Progress

Strategy: break each large file into ≤200-line write chunks to avoid stream timeouts.

## analyze_tab.py (1399 → ~480 LoC) ✓ DONE

## Controllers (thin — one write each) ✓ DONE

## Callbacks + Services ✓ DONE

## Monoliths
- [x] batch_export_dialog.py (2030 LoC) — 4 parts
- [x] runtime_app.py (6941 LoC)
    - [x] imports + module-level helpers (make_fluor_thumb, make_overlay_thumb, ask_name_dialog, _bind_drag, save/load_json)
    - [x] WellViewerApp.__init__ + tk.Variable attrs (23)
    - [x] WellViewerApp UI build methods (plate grid, tabs, sidebar, preview, montage, LUT editor)
    - [x] WellViewerApp controller/callback methods (~5000 LoC of tk.bind / widget plumbing)
    - [x] main()

## Final
- [x] Acceptance grep sweep (0 hits for tkinter/ttk/messagebox/filedialog/after/bind/StringVar)
- [ ] pytest tests/ (blocked: libEGL.so.1 missing in sandbox; Qt import fails at test collection)
- [ ] Commit + push
