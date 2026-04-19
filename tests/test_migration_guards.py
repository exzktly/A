from pathlib import Path

from ui.ports import get_ui_port


def test_services_are_ui_framework_agnostic() -> None:
    forbidden = ("import tkinter", "from tkinter", "import PySide6", "from PySide6")
    services_dir = Path("services")
    for py_file in services_dir.glob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{py_file} contains forbidden UI import: {needle}"


def test_qt_slices_use_shared_dialog_wrappers() -> None:
    targets = [Path("analyze_tab_qt.py"), Path("well_viewer/runtime_app_qt.py")]
    forbidden = ("QFileDialog", "QMessageBox")
    for path in targets:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} should use ui.qt_ui instead of {needle}"


def test_qt_runtime_path_is_tk_free() -> None:
    runtime_qt_paths = [
        Path("all_well.py"),
        Path("analyze_tab_qt.py"),
        Path("well_viewer/runtime_app_qt.py"),
        Path("ui/qt_ui.py"),
        Path("ui/qt_theme.py"),
        Path("ui/qt_plot_host.py"),
    ]
    forbidden = ("import tkinter", "from tkinter", "backend_tkagg", "TkAgg")
    for path in runtime_qt_paths:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} contains legacy Tk usage: {needle}"


def test_ui_port_exposes_expected_surface() -> None:
    port = get_ui_port()
    for name in (
        "ask_directory",
        "ask_open_file",
        "ask_save_file",
        "info",
        "warn",
        "error",
        "confirm",
        "invoke_later",
        "set_clipboard_text",
        "get_clipboard_text",
    ):
        assert hasattr(port, name), f"missing ui port method: {name}"



def test_repository_is_tk_free_outside_tests() -> None:
    forbidden = ("tkinter", "backend_tkagg", "TkAgg")
    roots = [Path("well_viewer"), Path("ui"), Path("analyze_tab.py"), Path("all_well.py")]
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
        else:
            files.extend(root.rglob("*.py"))
    for path in files:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} contains forbidden legacy token: {needle}"
