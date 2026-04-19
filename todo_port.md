# PySide6 Migration — Port Progress

Strategy: break each large file into ≤200-line write chunks to avoid stream timeouts.

## analyze_tab.py (1399 → ~480 LoC) ✓ DONE

## Controllers (thin — one write each) ✓ DONE

## Callbacks + Services
- [x] preview_callbacks.py — written, uncommitted
- [ ] scatter_callbacks.py (720 LoC) — 2 parts
- [ ] plot_orchestrator.py (137 LoC)
- [ ] export_service.py (403 LoC)
- [ ] ui_helpers.py — verify Qt-clean

## Monoliths
- [ ] batch_export_dialog.py (2030 LoC) — 4 parts
- [ ] runtime_app.py (6941 LoC) — 10+ parts

## Final
- [ ] Acceptance grep sweep (0 hits for tkinter/ttk/messagebox/filedialog/after/bind/StringVar)
- [ ] pytest tests/
- [ ] Commit + push
