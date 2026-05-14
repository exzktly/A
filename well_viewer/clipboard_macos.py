"""Native macOS pasteboard helper + AppleScript-driven Keynote insert.

Qt6's QMacMimeRegistry doesn't surface ``application/pdf`` /
``com.adobe.pdf`` from a :class:`QMimeData` to the macOS pasteboard,
so Copy-as-PDF via :meth:`QClipboard.setMimeData` lands as nothing in
Keynote / Pages / Preview. We went through every variation of writing
PDF data directly to ``NSPasteboard`` (legacy ``setData:forType:``,
modern ``NSPasteboardItem`` + ``writeObjects:``, with and without a
PNG fallback, with ``public.file-url`` alongside, with file URL alone)
over PRs #195/#197/#198/#199/#200/#201. Illustrator / Affinity /
Preview paste vector from every variant; Keynote rasterises every
variant. The asymmetry proves Keynote's paste handler picks raster on
a code path no pasteboard contents can influence.

The only path that gets a vector .pdf into Keynote reliably is the
same one ``Insert > Choose…`` and drag-drop use. We reach it via
AppleScript:

    tell application "Keynote"
        tell front document
            tell current slide
                make new image with properties {file: POSIX file "..."}
            end tell
        end tell
    end tell

Copy SVG now does both: writes the file URL to the pasteboard (so
Illustrator / Affinity / Preview keep working via paste), **and**, if
Keynote is already running, tells Keynote to insert the figure on
the current slide of the front document. No new UI; the existing
button just does the right thing when Keynote is open.

The AppleScript send requires Automation > Keynote permission. macOS
prompts once on the first attempt; if the user declines we report
that in the status bar and fall back to pasteboard-only.

The module is import-safe on every OS: ``write_vector_pdf_pasteboard``
returns ``False`` when not running on macOS or when PyObjC isn't
available, and the caller falls back to its in-Qt clipboard path.
``last_failure_reason`` and ``last_keynote_status`` expose
human-readable diagnostics so the UI can surface what happened.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Last reason ``write_vector_pdf_pasteboard`` returned ``False``. Kept
# as module state so callers (e.g. the Copy-SVG status bar) can show a
# diagnostic without piping a tuple through every call site.
last_failure_reason: str = ""

# Outcome of the most recent AppleScript-to-Keynote send. One of:
#   ""                  — not attempted (no PDF written / non-darwin)
#   "inserted"          — make-new-image succeeded
#   "not-running"       — Keynote.app wasn't running; skipped silently
#   "no-document"       — Keynote running but no documents open
#   "no-slide"          — front document has no slides
#   "permission-denied" — TCC Automation > Keynote not granted
#   "timeout"           — osascript ran > _OSASCRIPT_TIMEOUT_SEC
#   "missing-cli"       — pgrep or osascript not on PATH (shouldn't happen)
#   anything else       — verbatim AppleScript error message (truncated)
last_keynote_status: str = ""

_TMP_SUBDIR = "allwell-clipboard"
_TMP_MAX_AGE_SEC = 3600
_OSASCRIPT_TIMEOUT_SEC = 15


def write_vector_pdf_pasteboard(*, pdf_bytes: bytes) -> bool:
    """Write a PDF file URL to the macOS pasteboard + auto-insert into Keynote.

    Returns ``True`` when the pasteboard was written, ``False`` when
    the platform isn't macOS, PyObjC isn't importable, or the write
    itself failed.

    Writes the PDF bytes to a temp file under
    ``NSTemporaryDirectory()/allwell-clipboard`` and puts the resulting
    file URL on the general pasteboard via
    ``pb.writeObjects_([NSURL])``. Then, if Keynote.app is currently
    running, sends an AppleScript event asking Keynote to make a new
    image on the current slide of the front document from that same
    temp file — the only path that reliably produces a *vector* paste
    in Keynote.

    The AppleScript send is fire-and-forget for the caller's purposes:
    the pasteboard write succeeded either way (return value
    reflects the pasteboard, not the Keynote insert), and the Keynote
    outcome is reported separately via ``last_keynote_status``.
    """
    global last_failure_reason, last_keynote_status
    last_failure_reason = ""
    last_keynote_status = ""

    if sys.platform != "darwin":
        last_failure_reason = "not macOS"
        return False
    if not pdf_bytes:
        last_failure_reason = "no PDF bytes"
        return False
    try:
        from AppKit import NSPasteboard
        from Foundation import NSURL
    except Exception as exc:
        last_failure_reason = (
            "PyObjC framework not installed — "
            "`pip install pyobjc-framework-Cocoa` "
            f"({exc.__class__.__name__}: {exc})"
        )
        return False

    tmp_dir = Path(tempfile.gettempdir()) / _TMP_SUBDIR
    try:
        tmp_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        last_failure_reason = f"temp dir create failed: {exc}"
        return False
    _prune_stale(tmp_dir)

    try:
        fd, pdf_path_str = tempfile.mkstemp(
            suffix=".pdf", prefix="figure-", dir=str(tmp_dir),
        )
        with os.fdopen(fd, "wb") as fp:
            fp.write(pdf_bytes)
    except OSError as exc:
        last_failure_reason = f"temp PDF write failed: {exc}"
        return False

    file_url = NSURL.fileURLWithPath_(pdf_path_str)
    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    if not bool(pb.writeObjects_([file_url])):
        last_failure_reason = "NSPasteboard.writeObjects_([NSURL]) returned NO"
        return False

    last_keynote_status = _try_insert_into_keynote(pdf_path_str)
    return True


def status_suffix() -> str:
    """Short status hint reflecting the most recent Keynote insert attempt.

    Empty string when Keynote wasn't running (the common case when the
    user just wants the figure on the clipboard). Callers append it to
    their Copy-SVG status message when non-empty.
    """
    s = last_keynote_status
    if not s or s == "not-running":
        return ""
    table = {
        "inserted": "also inserted into Keynote",
        "no-document": "Keynote insert skipped: no document open",
        "no-slide": "Keynote insert skipped: front document has no slides",
        "permission-denied": (
            "Keynote insert blocked: grant Automation > Keynote in "
            "System Settings → Privacy & Security"
        ),
        "timeout": "Keynote insert timed out",
        "missing-cli": "Keynote insert skipped: osascript/pgrep missing",
    }
    return table.get(s, f"Keynote insert error: {s[:80]}")


# ────────────────────────────────────────────────────────────────────────────
# Internals
# ────────────────────────────────────────────────────────────────────────────

def _prune_stale(tmp_dir: Path) -> None:
    """Best-effort cleanup of clipboard PDFs older than the cap.

    Quiet on errors — this is hygiene, not correctness.
    """
    now = time.time()
    try:
        entries = list(tmp_dir.iterdir())
    except OSError:
        return
    for stale in entries:
        try:
            if stale.is_file() and (now - stale.stat().st_mtime) > _TMP_MAX_AGE_SEC:
                stale.unlink()
        except OSError:
            pass


def _try_insert_into_keynote(pdf_path: str) -> str:
    """Ask Keynote to insert the PDF on the front slide via AppleScript.

    Returns one of the status tokens documented on
    ``last_keynote_status``. Never raises — every error path is
    caught and reduced to a token so the caller can keep going.

    Uses ``pgrep`` (no TCC permission needed) to skip the AppleScript
    altogether when Keynote isn't running, which is the common case
    and avoids surprising the user with permission prompts the first
    time they Copy SVG without Keynote open.
    """
    if not (shutil.which("pgrep") and shutil.which("osascript")):
        return "missing-cli"

    try:
        rc = subprocess.run(
            ["pgrep", "-x", "Keynote"],
            capture_output=True, timeout=5,
        ).returncode
    except Exception:
        return "missing-cli"
    if rc != 0:
        return "not-running"

    # mkstemp paths from tempfile.gettempdir() are POSIX-clean (no quotes,
    # no backslashes on darwin), but defend anyway in case the temp dir
    # contains an unusual character.
    escaped = pdf_path.replace("\\", "\\\\").replace('"', '\\"')
    script = (
        'tell application "Keynote"\n'
        '    if (count of documents) is 0 then return "no-document"\n'
        '    tell front document\n'
        '        if (count of slides) is 0 then return "no-slide"\n'
        '        tell current slide\n'
        f'            make new image with properties {{file:POSIX file "{escaped}"}}\n'
        '        end tell\n'
        '    end tell\n'
        '    return "inserted"\n'
        'end tell'
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True,
            timeout=_OSASCRIPT_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        return "timeout"
    except Exception as exc:
        return f"osascript-failed: {exc.__class__.__name__}"

    if result.returncode != 0:
        err = (result.stderr or "").strip()
        low = err.lower()
        # Error 1743 = "not authorized to send Apple events"
        if "1743" in err or "not authorized" in low or "not allowed" in low:
            return "permission-denied"
        return f"osascript-error: {err[:120]}" if err else "osascript-error"

    out = (result.stdout or "").strip()
    return out or "inserted"
