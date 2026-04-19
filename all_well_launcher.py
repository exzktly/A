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

from all_well import main

if __name__ == "__main__":
    main()
