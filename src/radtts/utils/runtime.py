"""Runtime helpers for retries, timeout, and progress heartbeat."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Callable, TypeVar

from radtts.exceptions import StageRetryExceededError, StageTimeoutError

T = TypeVar("T")


class Heartbeat:
    def __init__(self, interval_seconds: int, on_beat: Callable[[str], None], label: str):
        self.interval_seconds = interval_seconds
        self.on_beat = on_beat
        self.label = label
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.on_beat(f"heartbeat: stage={self.label}")

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1)


def run_with_retry_timeout(
    *,
    stage_name: str,
    fn: Callable[[], T],
    timeout_seconds: int,
    retries: int,
    on_log: Callable[[str], None],
) -> T:
    last_err: Exception | None = None
    for attempt in range(1, retries + 2):
        on_log(f"stage={stage_name} attempt={attempt} starting")
        pool = ThreadPoolExecutor(max_workers=1)
        fut = pool.submit(fn)
        shutdown_wait = True
        try:
            result = fut.result(timeout=timeout_seconds)
            on_log(f"stage={stage_name} attempt={attempt} complete")
            return result
        except FuturesTimeoutError:
            fut.cancel()
            last_err = StageTimeoutError(
                f"stage={stage_name} timed out after {timeout_seconds}s"
            )
            on_log(str(last_err))
            shutdown_wait = False
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            on_log(f"stage={stage_name} attempt={attempt} failed: {exc}")
        finally:
            if not fut.done() or not shutdown_wait:
                pool.shutdown(wait=False, cancel_futures=True)
            else:
                pool.shutdown(wait=True, cancel_futures=True)
        if attempt < retries + 1:
            time.sleep(min(2, attempt))
    raise StageRetryExceededError(f"stage={stage_name} failed after retries: {last_err}")
