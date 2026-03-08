from __future__ import annotations

import time

import pytest

from radtts.exceptions import StageRetryExceededError
from radtts.utils.runtime import run_with_retry_timeout


def test_run_with_retry_timeout_returns_without_waiting_for_stuck_work():
    started = time.monotonic()

    def slow_stage():
        time.sleep(1.0)
        return "done"

    with pytest.raises(StageRetryExceededError, match="timed out after 0.05s"):
        run_with_retry_timeout(
            stage_name="generation",
            fn=slow_stage,
            timeout_seconds=0.05,
            retries=0,
            on_log=lambda _: None,
        )

    elapsed = time.monotonic() - started
    assert elapsed < 0.5
