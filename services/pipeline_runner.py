"""Background runner for the microscopy pipeline subprocess.

Owns the worker thread, the subprocess handle, and the log/event queue that
the GUI polls. Decouples ``analyze_tab.py`` from threading + subprocess +
log-line parsing so the tab module is a pure view + form.

Event protocol (queue payloads are ``(kind, payload)`` tuples):
    line          str        Raw stdout line.
    workers       int        Worker count parsed from a TF banner line.
    zipper_start  int        Begin grouping phase, expected well count.
    zipper_well   str|None   One well finished grouping.
    zipper_done   None       Grouping phase finished.
    done          str        Pipeline finished successfully.
    error         str        Pipeline failed; payload is a message.
    finished      None       Final event, always emitted in a finally.
"""

from __future__ import annotations

import os
import queue
import re
import signal
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional, Tuple

from services.pipeline_service import build_pipeline_args, spawn_pipeline


_LOG_LEVELS = ("INFO", "WARNING", "ERROR", "DONE")


def classify_log_line(line: str) -> str:
    """Return the severity tag for a single pipeline stdout line."""
    ll = line.lower()
    if "error" in ll or "traceback" in ll or "exception" in ll:
        return "ERROR"
    if "warning" in ll or "warn" in ll or "skipping" in ll:
        return "WARNING"
    return "INFO"


_RE_TF_WORKERS = re.compile(r"TF threads/worker\s*:\s*\d+\s+\(workers:\s*(\d+)\s+x")
_RE_MODE_WELLS = re.compile(r"(?:Zip mode|Flat mode|Folder mode):\s+(\d+)\s+well")


class ProgressTracker:
    """Pure log-line parser that tracks well-count progress.

    Instances are stateful (zip-mode warning + well counters) but never touch
    the GUI; ``parse(line)`` returns events that the tab forwards to the user.
    """

    def __init__(self) -> None:
        self.zip_mode_warning_logged = False
        self.well_total = 0
        self.well_done = 0

    def reset(self) -> None:
        self.zip_mode_warning_logged = False
        self.well_total = 0
        self.well_done = 0

    def parse(self, line: str) -> list[Tuple[str, object]]:
        """Return queue events for a single stdout line.

        Caller is expected to forward the events to its GUI queue. Returning a
        list (rather than enqueuing directly) keeps this method test-friendly
        and free of any dependency on the queue object.
        """
        events: list[Tuple[str, object]] = []
        if line.startswith("[zipper]"):
            return events
        if (
            ("Zip mode:" in line or "Zip mode complete" in line)
            and not self.zip_mode_warning_logged
        ):
            self.zip_mode_warning_logged = True
            events.append((
                "line",
                "[warn] Zip mode detected; folder-mode compression options do not apply.\n",
            ))
        m = _RE_TF_WORKERS.search(line)
        if m:
            events.append(("workers", int(m.group(1))))
        if not self.well_total:
            m = _RE_MODE_WELLS.search(line)
            if m:
                self.well_total = int(m.group(1))
                events.append(("well_total", self.well_total))
                return events
        if self.well_total:
            # Count a well as "done" only after the per-well cleanup line
            # ('temporary directories removed') — the CSV-write line
            # ('Well xxx -> *.csv (N rows)') fires *before* the slow
            # compression step, so counting both inflated well_done to
            # ~2 × well_total and crushed the ETA estimate. Keep the CSV
            # line in the log for clarity but stop using it as the
            # progress trigger.
            if "temporary directories removed" in line:
                self.well_done += 1
                events.append(("well_done", (self.well_done, self.well_total)))
        return events


class PipelineRunner:
    """Run the pipeline subprocess on a daemon thread and report progress.

    The runner owns its thread, subprocess handle, and event queue. Callers
    (the GUI) consume events via :meth:`poll` and call :meth:`stop` to cancel.
    """

    def __init__(self) -> None:
        self.log_q: "queue.Queue[Tuple[str, object]]" = queue.Queue()
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._last_output_dir: Optional[Path] = None

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    @property
    def last_output_dir(self) -> Optional[Path]:
        return self._last_output_dir

    def start(
        self,
        pipeline: Path,
        opts: dict,
        *,
        resolve_dirs: Callable[[dict, "queue.Queue"], Optional[Tuple[Path, Path]]],
    ) -> None:
        """Spawn the worker thread that runs the pipeline subprocess."""
        self._thread = threading.Thread(
            target=self._run_pipeline_thread,
            args=(pipeline, opts, resolve_dirs),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        # Signal the whole process group / session so multiprocessing
        # workers spawned by the pipeline get torn down too — terminating
        # only the parent leaves the workers running and the parent
        # waiting on them, so the GUI's Stop button appears to do nothing.
        try:
            if os.name == "posix":
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            else:
                proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
        except (ProcessLookupError, OSError, AttributeError):
            proc.terminate()

        def _force_kill_if_alive() -> None:
            if proc.poll() is not None:
                return
            try:
                if os.name == "posix":
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                else:
                    proc.kill()
            except (ProcessLookupError, OSError):
                pass

        threading.Timer(5.0, _force_kill_if_alive).start()

    def _run_pipeline_thread(
        self,
        pipeline: Path,
        opts: dict,
        resolve_dirs: Callable[[dict, "queue.Queue"], Optional[Tuple[Path, Path]]],
    ) -> None:
        try:
            resolved = resolve_dirs(opts, self.log_q)
            if resolved is None:
                return
            input_dir, output_dir = resolved
            if any(input_dir.glob("*.zip")):
                self.log_q.put((
                    "line",
                    "[warn] Zip mode detected; folder-mode compression options do not apply.\n",
                ))
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                self.log_q.put(("error", f"Cannot create output dir: {exc}\n"))
                return
            self._last_output_dir = output_dir
            args = build_pipeline_args(pipeline, input_dir, output_dir, opts)
            self.log_q.put(("line", f"$ {' '.join(args)}\n"))
            self.log_q.put((
                "line",
                f"Input  : {input_dir}\nOutput : {output_dir}\n"
                f"Schema : {opts['filename_schema']}  sep={opts['filename_sep']!r}\n\n",
            ))
            self._run_pipeline_subprocess(args)
        finally:
            self.log_q.put(("finished", None))

    def _run_pipeline_subprocess(self, args: list[str]) -> None:
        try:
            self._proc = spawn_pipeline(args)
            assert self._proc.stdout is not None
            for line in self._proc.stdout:
                self.log_q.put(("line", line))
            self._proc.wait()
            rc = self._proc.returncode
            if rc == 0:
                self.log_q.put(("done", "Pipeline completed successfully.\n"))
            else:
                self.log_q.put(("error", f"Pipeline exited with code {rc}.\n"))
        except Exception as exc:  # noqa: BLE001 — surface any failure to the GUI
            self.log_q.put(("error", f"Failed to start pipeline: {exc}\n"))
