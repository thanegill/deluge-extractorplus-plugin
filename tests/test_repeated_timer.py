import threading
import time

import pytest

from extractorplus.RepeatedTimer import RepeatedTimer

INTERVAL = 1.0


def run_or_fail(function, timeout, what):
    """Run function in a daemon thread and fail, rather than hang, if it blocks."""
    errors = []

    def target():
        try:
            function()
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        pytest.fail(f"{what} deadlocked")
    if errors:
        raise errors[0]


class FiringTimer(RepeatedTimer):
    def __init__(self, *args, **kwargs):
        self.fired = threading.Event()
        super().__init__(*args, **kwargs)

    def _run(self, *args):
        self.fired.set()
        super()._run(*args)


def test_tick_and_stop_do_not_deadlock():
    ticked = threading.Event()
    timer = RepeatedTimer(0.05, ticked.set)
    assert ticked.wait(5), "RepeatedTimer deadlocked before calling its function"
    run_or_fail(timer.stop, 5, "RepeatedTimer.stop()")


@pytest.mark.parametrize("restart", [False, True], ids=["stop", "stop-then-start"])
def test_stop_mid_tick_leaves_no_timer_running(restart):
    ticks = []

    def scenario():
        # Holding the lock parks a tick that has fired in _run, so stop() lands
        # between the Timer firing and _run re-arming. Re-arming under the lock
        # keeps a slow machine from letting the first tick through early.
        timer = FiringTimer(3600, ticks.append, 1)
        with timer._lock:
            timer.stop()
            timer.interval = INTERVAL
            timer.start()
            assert timer.fired.wait(10), "RepeatedTimer never fired"
            timer.stop()
            if restart:
                timer.start()
        time.sleep(INTERVAL / 4)
        if restart:
            timer.stop()
        ticks_at_stop = len(ticks)
        time.sleep(INTERVAL * 3)
        assert len(ticks) == ticks_at_stop, (
            f"RepeatedTimer ticked {len(ticks) - ticks_at_stop} times after stop()"
        )

    run_or_fail(scenario, 30, "the stop-mid-tick scenario")
