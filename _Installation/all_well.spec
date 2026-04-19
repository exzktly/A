# all_well.spec
# -------------
# PyInstaller spec file for building AllWell.app on macOS.
#
# Usage (run from the directory containing this file):
#   pyinstaller all_well.spec
#
# Output:
#   dist/AllWell.app   — double-clickable macOS application bundle
#
# Requires: pyinstaller >= 6.0, all packages in requirements.txt installed
# in the active Python environment.

import sys
import os
from pathlib import Path
import importlib.util


# ---------------------------------------------------------------------------
# Helper: locate a package's data directory
# ---------------------------------------------------------------------------

def pkg_dir(name: str) -> Path:
    spec = importlib.util.find_spec(name)
    if spec is None:
        raise RuntimeError(f"Package {name!r} not found — install requirements.txt first")
    return Path(spec.origin).parent


# ---------------------------------------------------------------------------
# Sibling scripts bundled as data files
# PyInstaller cannot follow exec() calls in all_well.py, so these scripts
# are bundled explicitly and extracted to sys._MEIPASS at runtime.
# ---------------------------------------------------------------------------

_here = Path(SPECPATH)   # directory containing this .spec file (_Installation/)  # noqa: F821
_parent = _here.parent   # repository root (one level up)

sibling_scripts = [
    (str(_parent / "all_well.py"),              "."),
    (str(_parent / "analyze_tab.py"),           "."),
    (str(_parent / "analyze_tab_qt.py"),        "."),
    (str(_parent / "process_microscopy_v2.py"), "."),
    (str(_parent / "WellPlateZipper.py"),       "."),
    (str(_parent / "ui/qt_theme.py"),           "ui"),
    (str(_parent / "ui/qt_plot_host.py"),       "ui"),
    (str(_parent / "ui/qt_ui.py"),              "ui"),
    (str(_parent / "well_viewer/runtime_app_qt.py"), "well_viewer"),
]

# matplotlib ships fonts, styles, and mpl-data at runtime
mpl_data = (str(pkg_dir("matplotlib") / "mpl-data"), "matplotlib/mpl-data")

# stardist ships .json config and .npz weight files inside the package
stardist_data = (str(pkg_dir("stardist")), "stardist")

# csbdeep ships no data files but include the package dir for safety
csbdeep_data = (str(pkg_dir("csbdeep")), "csbdeep")

datas = sibling_scripts + [mpl_data, stardist_data, csbdeep_data]


# ---------------------------------------------------------------------------
# Hidden imports
# ---------------------------------------------------------------------------

hiddenimports = [
    # numpy internals
    "numpy.core._multiarray_umath",
    "numpy.core._multiarray_tests",
    "numpy.core.multiarray",
    "numpy.random",
    "numpy.random._common",
    "numpy.random._bounded_integers",
    "numpy.random._generator",
    "numpy.random.mtrand",

    # scipy — stats and ndimage used by well_viewer + process_microscopy
    "scipy.stats",
    "scipy.stats._stats_py",
    "scipy.stats._continuous_distns",
    "scipy.stats._discrete_distns",
    "scipy.stats._kde",              # gaussian_kde moved here in scipy 1.11
    "scipy.ndimage",
    "scipy.ndimage._morphology",
    "scipy.ndimage._filters",
    "scipy.ndimage._interpolation",
    "scipy.special",
    "scipy.special._ufuncs",         # _cython_special renamed in scipy 1.11
    "scipy.linalg",
    "scipy.linalg.blas",
    "scipy.linalg.lapack",
    "scipy._lib.messagestream",
    "scipy._lib._util",

    # scikit-image — verified against skimage 0.21.0 arm64 wheel contents
    "skimage",
    "skimage.morphology",
    "skimage.morphology._grayreconstruct",   # correct spelling (no 'e' in gray)
    "skimage.morphology._convex_hull",
    "skimage.morphology._flood_fill",
    "skimage.morphology.binary",
    "skimage.morphology.gray",
    "skimage.morphology.footprints",
    "skimage.segmentation",
    "skimage.segmentation.boundaries",       # no leading underscore in skimage 0.21
    "skimage.segmentation._watershed",
    "skimage.segmentation._slic",
    "skimage._shared",
    "skimage._shared.utils",
    "skimage._shared._geometry",
    "skimage.filters",
    "skimage.filters.rank",
    "skimage.filters.thresholding",
    "skimage.measure",
    "skimage.measure._regionprops",
    "skimage.util",
    "skimage.util.dtype",

    # matplotlib backends
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_agg",
    "matplotlib.figure",
    "matplotlib.patches",
    "matplotlib.lines",
    "matplotlib.collections",
    "matplotlib.axes._axes",
    "matplotlib.axis",

    # PIL / Pillow
    "PIL",
    "PIL.Image",
    "PIL.ImageOps",
    "PIL.TiffImagePlugin",
    "PIL.PngImagePlugin",

    # tifffile + imageio
    "tifffile",
    "imageio",
    "imageio.plugins.tifffile",

    # imagecodecs — optional but prevents codec errors on compressed TIFFs
    "imagecodecs",

    # Qt runtime
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",

    # standard library PyInstaller sometimes misses
    "zipfile",
    "csv",
    "json",
    "statistics",
    "copy",
    "queue",
    "threading",
    "subprocess",
    "shutil",
    "importlib.util",
    "html",
    "html.parser",
    "http",
    "http.client",
    "pyparsing",
    "pyparsing.helpers",
    "pyparsing.core",
    "pyparsing.common",
    "pyparsing.results",

    # stardist — compiled C extension; PyInstaller misses submodules entirely
    "stardist",
    "stardist.models",
    "stardist.models.model2d",
    "stardist.models.base",
    "stardist.geometry",
    "stardist.geometry.geom2d",
    "stardist.nms",
    "stardist.rays3d",
    "stardist.sample_patches",
    "stardist.utils",
    "stardist.matching",
    "stardist.plot",
    "stardist.data",

    # csbdeep — pure Python but uses dynamic plugin loading
    "csbdeep",
    "csbdeep.utils",
    "csbdeep.utils.utils",
    "csbdeep.utils.tf",
    "csbdeep.data",
    "csbdeep.data.transform",
    "csbdeep.data.generate",
    "csbdeep.models",
    "csbdeep.models.base_model",
    "csbdeep.models.care_standard",
    "csbdeep.internals",
    "csbdeep.internals.blocks",
    "csbdeep.internals.predict",
    "csbdeep.internals.train",

    # numba — stardist's NMS uses numba JIT; needs its full internal stack
    "numba",
    "numba.core",
    "numba.core.types",
    "numba.core.typing",
    "numba.core.compiler",
    "numba.core.dispatcher",
    "numba.np",
    "numba.np.ufunc",
    "numba.np.numpy_support",
    "numba.typed",
    "numba.typed.typeddict",
    "numba.typed.typedlist",
    "numba.cpython",
    "numba.cuda",
    "llvmlite",
    "llvmlite.binding",

    # tensorflow internals — needed when TF is imported inside worker processes
    "tensorflow",
    "tensorflow.python",
    "tensorflow.python.keras",
    "tensorflow.python.saved_model",
    "tensorflow.python.framework",
    "tensorflow.python.ops",
    "tensorflow.python.platform",
    "tensorflow.python.util",
    "tensorflow.python.eager",
    "keras",

    # h5py — used by keras/csbdeep to load model weights
    "h5py",
    "h5py._hl",
    "h5py._hl.files",
    "h5py._hl.dataset",
    "h5py._hl.group",
    "h5py.h5",
    "h5py.h5f",
    "h5py.h5d",
    "h5py.h5g",
    "h5py.h5s",
    "h5py.h5t",
    "h5py.h5z",

    # six — csbdeep dependency
    "six",

    # packaging — csbdeep uses it for version checks
    "packaging",
    "packaging.version",
    "packaging.requirements",

    # tqdm — csbdeep uses for progress bars
    "tqdm",
    "tqdm.auto",
    "tqdm.std",
]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

# Collect all submodules of packages that use dynamic imports.
# NOTE: stardist, csbdeep, and pkg_resources are handled by custom hooks
# in hooks/ — do NOT call collect_submodules() on them here because that
# requires importing them, which fails when pkg_resources is not yet visible.
from PyInstaller.utils.hooks import collect_submodules, collect_data_files  # noqa: E402

_numba_excluded = {"numba.tests", "numba.pycc"}
_numba_mods = collect_submodules("numba")
hiddenimports += [m for m in _numba_mods
                  if not any(m == e or m.startswith(e + ".") for e in _numba_excluded)]
hiddenimports += collect_submodules("llvmlite")
hiddenimports += collect_submodules("h5py")

# Filter out dead/moved skimage submodules before adding to hiddenimports
_skimage_mods = collect_submodules("skimage")
_skimage_excluded = {"skimage.future.graph"}
hiddenimports += [m for m in _skimage_mods if m not in _skimage_excluded]

# Collect data files
datas += collect_data_files("numba")
datas += collect_data_files("skimage")

a = Analysis(
    [str(_parent / "all_well_launcher.py")],
    pathex=[str(_parent)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(_here / "hooks")],   # custom hooks for stardist/csbdeep/pkg_resources
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Heavy third-party packages not used by this app
        "IPython",
        "jupyter",
        "notebook",
        "pandas",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "wx",
        "gtk",
        # Dead/moved skimage submodule — raises ModuleNotFoundError on import
        "skimage.future.graph",
        # keras benchmark module has syntax errors and is never used at runtime
        "keras.src.benchmarks",
        # NOTE: ssl intentionally NOT excluded — process_microscopy_v2 patches
        # ssl._create_default_https_context for StarDist model download
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data)   # noqa: F821


# ---------------------------------------------------------------------------
# Executable
# ---------------------------------------------------------------------------

exe = EXE(   # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AllWell",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # UPX breaks macOS code-signing
    console=False,       # GUI app — no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,    # None = native; use "universal2" for M1+Intel fat binary
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(   # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AllWell",
)


# ---------------------------------------------------------------------------
# macOS .app bundle
# ---------------------------------------------------------------------------

app = BUNDLE(   # noqa: F821
    coll,
    name="AllWell.app",
    icon=None,           # replace with "all_well_icon.icns" if you have one
    bundle_identifier="com.allwell.app",
    version="1.0.0",
    info_plist={
        "NSHighResolutionCapable": True,
        "NSAppleEventsUsageDescription":
            "AllWell needs access to open microscopy data files.",
        "CFBundleShortVersionString": "1.0",
        "CFBundleVersion": "1.0.0",
        "CFBundleName": "AllWell",
        "CFBundleDisplayName": "All Well",
        "CFBundleExecutable": "AllWell",
        "LSMinimumSystemVersion": "10.13",
        "NSPrincipalClass": "NSApplication",
        "NSRequiresAquaSystemAppearance": False,  # support dark mode
    },
)
