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

import sys

# ---------------------------------------------------------------------------
# Multiprocessing child-process dispatcher.
#
# On macOS the default start method is "spawn", which re-execs this bundled
# binary for every worker. PyInstaller's multiprocessing runtime hook
# handles ``--multiprocessing-fork`` for the pool workers, but the
# resource_tracker child invocation is hard-coded inside CPython
# (multiprocessing/resource_tracker.py::ensure_running) and bypasses that
# patch — it re-execs as ``<exe> -B -S -I -c "from
# multiprocessing.resource_tracker import main;main(N)"``. Without this
# guard those flags fall through to all_well's argparse and the worker
# dies with "unrecognized arguments: -B -S -I -c ...".
#
# This block must run before any other imports so the child exits cleanly
# without touching matplotlib, Qt, or the user-facing argument parser.
# ---------------------------------------------------------------------------

def _dispatch_multiprocessing_child() -> None:
    argv = sys.argv
    if len(argv) >= 2 and argv[1] == "--multiprocessing-fork":
        from multiprocessing.spawn import spawn_main
        kwds = {}
        for arg in argv[2:]:
            name, value = arg.split("=", 1)
            kwds[name] = int(value)
        spawn_main(**kwds)
        sys.exit()
    if "-c" in argv:
        ci = argv.index("-c")
        if ci + 1 < len(argv) and argv[ci + 1].startswith(
            "from multiprocessing.resource_tracker import main"
        ):
            exec(argv[ci + 1], {"__name__": "__main__"})
            sys.exit()


_dispatch_multiprocessing_child()

import multiprocessing
multiprocessing.freeze_support()

import matplotlib
matplotlib.use("QtAgg")

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
