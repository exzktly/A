# PySide6 Migration — Port Progress

Strategy: break each large file into ≤200-line write chunks to avoid stream timeouts.

## analyze_tab.py (1399 → ~480 LoC) ✓ DONE

## Controllers (thin — one write each)
- [ ] load_controller.py (114 LoC)
- [ ] stats_controller.py (147 LoC)
- [ ] grouping_controller.py (168 LoC)
- [ ] montage_controller.py (169 LoC)
- [ ] preview_controller.py (251 LoC)
- [ ] barplot_controller.py (251 LoC)
- [ ] lineplot_controller.py (163 LoC)
- [ ] scatter_controller.py (556 LoC) — 2 parts
- [ ] selection_controller.py (222 LoC)
- [ ] review_image_controller.py (114 LoC)

## Callbacks + Services
- [ ] preview_callbacks.py (319 LoC)
- [ ] scatter_callbacks.py (720 LoC) — 2 parts
- [ ] plot_orchestrator.py (137 LoC)
- [ ] export_service.py (403 LoC)

## Monoliths
- [ ] batch_export_dialog.py (2030 LoC) — 4 parts
- [ ] runtime_app.py (6941 LoC) — 10+ parts

## Final
- [ ] Acceptance grep sweep (0 hits for tkinter/ttk/messagebox/filedialog/after/bind/StringVar)
- [ ] pytest tests/
- [ ] Commit + push
