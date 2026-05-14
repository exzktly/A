"""
all_well_launcher.py
--------------------
PyInstaller entry point for AllWell.app.

Referenced by _Installation/all_well.spec as the entry point for the
macOS bundle. When the app is launched, PyInstaller runs this module
instead of all_well.py directly.

This launcher ensures:
  * matplotlib backend is set to QtAgg before any pyplot imports
  * bundled sibling modules are discoverable from the PyInstaller
    extracted resource directory (_MEIPASS)
  * all_well.main() is invoked without runtime patching of __name__
  * when re-invoked with ``--run-pipeline`` as the first argument,
    the launcher dispatches to ``process_microscopy_v2.main()``
    instead of the GUI. The Analyze tab uses that path to spawn the
    pipeline subprocess from inside the frozen bundle, where
    ``sys.executable`` points at the .app binary and not a Python
    interpreter.

When running from source (not bundled), sys._MEIPASS is not set, so
modules are loaded from the repository root instead.
"""

import matplotlib
matplotlib.use("QtAgg")

import sys
from pathlib import Path

if hasattr(sys, "_MEIPASS"):
    _BUNDLE_DIR = Path(sys._MEIPASS)
else:
    _BUNDLE_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(_BUNDLE_DIR))


def _dispatch() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--run-pipeline":
        # Strip the sentinel so process_microscopy_v2's argparse sees
        # only its own flags. argv[0] stays as the executable path.
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        import process_microscopy_v2
        process_microscopy_v2.main()
        return
    from all_well import main
    main()


if __name__ == "__main__":
    _dispatch()
