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
        # The "Zip mode detected" warning is emitted up-front in
        # _run_pipeline_thread (before the pipeline launches) so it
        # arrives even on early failures. No second emission needed
        # when the pipeline echoes the same banner via stdout.
        if "Zip mode:" in line or "Zip mode complete" in line:
            self.zip_mode_warning_logged = True
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
            # Count a well as "done" when the pipeline emits its
            # dedicated marker line. The marker fires *before* the
            # finally-block cleanup (``remove_directory`` for zip mode
            # / staging-dir cleanup for folder mode) so the GUI's ETA
            # keeps ticking even when storage is slow (NAS / network
            # mounts can stall directory deletion for minutes).
            #
            # The CSV + zip artefacts are already on disk by the time
            # the marker fires, so the well *is* functionally done.
            #
            # Older pipeline versions emitted "temporary directories
            # removed" as the only completion log; keep matching it
            # too as a fallback for users running mismatched
            # client/server versions.
            if "— done." in line:
                self.well_done += 1
                events.append(("well_done", (self.well_done, self.well_total)))
        return events


class PipelineRunner:
    """Run the pipeline subprocess on a daemon thread and report progress.

    The runner owns its thread, subprocess handle, and event queue. Callers
    (the GUI) consume events via :meth:`poll` and call :meth:`stop` to cancel.
    """

    # Cap the log queue so a stalled UI thread can't let the reader stuff
    # unbounded lines into memory. Overflow drops are surfaced to the GUI
    # via a single warning line — the ring buffer in all_well captures
    # everything for the help-drawer log tab.
    _LOG_QUEUE_MAXSIZE = 10000

    def __init__(self) -> None:
        self.log_q: "queue.Queue[Tuple[str, object]]" = queue.Queue(
            maxsize=self._LOG_QUEUE_MAXSIZE,
        )
        self._proc: Optional[subprocess.Popen] = None
        # The grouping-phase subprocess (WellPlateZipper). Tracked
        # separately so a Stop click during grouping cancels it instead
        # of waiting for it to finish before reaching the pipeline.
        self._zipper_proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._last_output_dir: Optional[Path] = None
        self._log_overflow_warned: bool = False
        # Set on Stop; checked between the zipper phase and the pipeline
        # launch so a cancel during grouping doesn't slip through and
        # start a fresh pipeline run.
        self._stop_requested: threading.Event = threading.Event()

    def _enqueue(self, event: "Tuple[str, object]") -> None:
        """Non-blocking enqueue; drops the message on overflow with a
        one-shot warning rather than blocking the reader thread."""
        try:
            self.log_q.put_nowait(event)
        except queue.Full:
            if not self._log_overflow_warned:
                self._log_overflow_warned = True
                try:
                    self.log_q.put_nowait((
                        "line",
                        "[warn] log queue full — dropping further "
                        "lines from the live view. Subsequent output is "
                        "still captured in the help-drawer log tab.\n",
                    ))
                except queue.Full:
                    pass

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
        resolve_dirs: Callable[..., Optional[Tuple[Path, Path]]],
    ) -> None:
        """Spawn the worker thread that runs the pipeline subprocess.

        ``resolve_dirs`` is called with ``(opts, log_q, proc_hook=…)`` where
        ``proc_hook`` is the runner's zipper-tracking callback (forwarded
        to the grouping subprocess so Stop can reach it). Old call sites
        that ignore the kwarg still work.
        """
        self._thread = threading.Thread(
            target=self._run_pipeline_thread,
            args=(pipeline, opts, resolve_dirs),
            daemon=True,
        )
        self._thread.start()

    def _track_zipper_proc(self, proc: Optional[subprocess.Popen]) -> None:
        """Register / clear the grouping subprocess so ``stop()`` can
        signal it. Passed to ``resolve_input_output`` as ``proc_hook``."""
        self._zipper_proc = proc

    def stop(self) -> None:
        # Flag the in-progress run as cancelled — used by the worker
        # thread to abort between phases (e.g. between grouping and
        # pipeline launch) so a Stop click during the zipper phase
        # doesn't slip through and start the pipeline.
        self._stop_requested.set()

        # Reach both the grouping subprocess (if active) and the pipeline
        # subprocess. Signal each one's whole process group so any
        # multiprocessing workers it spawned get torn down too.
        for proc in (self._zipper_proc, self._proc):
            self._signal_subprocess(proc)

    @staticmethod
    def _signal_subprocess(proc: Optional[subprocess.Popen]) -> None:
        """SIGTERM the subprocess's session, then SIGKILL after 5 s if
        it's still alive. Captures the pgid up front so a 5-second
        delay doesn't risk SIGKILLing a process whose PID has been
        reused by the OS."""
        if proc is None or proc.poll() is not None:
            return
        pgid: Optional[int] = None
        if os.name == "posix":
            try:
                pgid = os.getpgid(proc.pid)
            except (ProcessLookupError, OSError):
                pgid = None
        try:
            if os.name == "posix":
                if pgid is not None:
                    os.killpg(pgid, signal.SIGTERM)
                else:
                    proc.terminate()
            else:
                proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
        except (ProcessLookupError, OSError, AttributeError):
            proc.terminate()

        def _force_kill_if_alive() -> None:
            # Re-check the live process handle, not just the cached pgid
            # — if the process exited cleanly within the 5 s window, the
            # OS may have re-used the PID for an unrelated process.
            if proc.poll() is not None:
                return
            try:
                if os.name == "posix" and pgid is not None:
                    os.killpg(pgid, signal.SIGKILL)
                elif os.name == "posix":
                    proc.kill()
                else:
                    proc.kill()
            except (ProcessLookupError, OSError):
                pass

        threading.Timer(5.0, _force_kill_if_alive).start()

    def _run_pipeline_thread(
        self,
        pipeline: Path,
        opts: dict,
        resolve_dirs: Callable[..., Optional[Tuple[Path, Path]]],
    ) -> None:
        # Each run starts with a fresh "not cancelled" state.
        self._stop_requested.clear()
        try:
            # Try the new signature first (with proc_hook); fall back for
            # callers that haven't been updated yet.
            try:
                resolved = resolve_dirs(opts, self.log_q, proc_hook=self._track_zipper_proc)
            except TypeError:
                resolved = resolve_dirs(opts, self.log_q)
            # Stop button may have fired during the (potentially long)
            # grouping / resolution phase. Bail before launching the
            # pipeline in that case.
            if self._stop_requested.is_set():
                self._enqueue(("line", "[stopped] Cancelled before pipeline launch.\n"))
                return
            if resolved is None:
                return
            input_dir, output_dir = resolved
            if any(input_dir.glob("*.zip")):
                self._enqueue((
                    "line",
                    "[warn] Zip mode detected; folder-mode compression options do not apply.\n",
                ))
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                self._enqueue(("error", f"Cannot create output dir: {exc}\n"))
                return
            self._last_output_dir = output_dir
            args = build_pipeline_args(pipeline, input_dir, output_dir, opts)
            self._enqueue(("line", f"$ {' '.join(args)}\n"))
            self._enqueue((
                "line",
                f"Input  : {input_dir}\nOutput : {output_dir}\n"
                f"Schema : {opts['filename_schema']}  sep={opts['filename_sep']!r}\n\n",
            ))
            self._run_pipeline_subprocess(args)
        finally:
            self._enqueue(("finished", None))

    def _run_pipeline_subprocess(self, args: list[str]) -> None:
        try:
            self._proc = spawn_pipeline(args)
            assert self._proc.stdout is not None
            for line in self._proc.stdout:
                self._enqueue(("line", line))
            self._proc.wait()
            rc = self._proc.returncode
            if rc == 0:
                self._enqueue(("done", "Pipeline completed successfully.\n"))
            else:
                self._enqueue(("error", f"Pipeline exited with code {rc}.\n"))
        except Exception as exc:  # noqa: BLE001 — surface any failure to the GUI
            self._enqueue(("error", f"Failed to start pipeline: {exc}\n"))
