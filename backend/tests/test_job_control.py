import subprocess
import sys

import pytest

from app.infrastructure.job_lock import exclusive_job
from app.infrastructure.pacing import RequestPacer
from app.infrastructure.scheduling import daily_slots


def test_daily_slots_preserve_pairs_and_sort():
    assert daily_slots("16:00", "09:30", "09:00") == ((9, 0), (9, 30), (16, 0))


@pytest.mark.parametrize(
    "times",
    [(), ("9:00",), ("24:00",), ("12:60",), ("09:00", "09:00"),
     (" 09:00",), ("09:00\n",), ("０９:００",), (900,), (None,)],
)
def test_invalid_daily_slots(times):
    with pytest.raises(ValueError):
        daily_slots(*times)


def test_pacing_waits_before_every_request_within_bounds():
    waits = []
    fractions = iter([0, 0.5, 1])
    pacer = RequestPacer(2, 4, sleep=waits.append, jitter=lambda: next(fractions))
    assert [pacer.wait() for _ in range(3)] == [2, 3, 4]
    assert waits == [2, 3, 4]


@pytest.mark.parametrize(
    "minimum,maximum",
    [(-1, 2), (2, 1), (True, 2), (1, float("inf")), (float("nan"), 2), ("1", 2)],
)
def test_invalid_pacing_bounds(minimum, maximum):
    with pytest.raises(ValueError):
        RequestPacer(minimum, maximum)


@pytest.mark.parametrize("fraction", [-0.1, 1.1, float("nan"), float("inf"), True, None])
def test_invalid_jitter_never_sleeps(fraction):
    waits = []
    pacer = RequestPacer(1, 2, sleep=waits.append, jitter=lambda: fraction)
    with pytest.raises(ValueError):
        pacer.wait()
    assert not waits


def test_job_lock_rejects_overlap_and_releases(tmp_path):
    path = tmp_path / "job.lock"
    with exclusive_job(path) as first:
        assert first
        with exclusive_job(path) as second:
            assert not second
    with exclusive_job(path) as next_run:
        assert next_run
    assert path.exists()


def test_job_lock_releases_after_exception(tmp_path):
    path = tmp_path / "job.lock"
    with pytest.raises(RuntimeError):
        with exclusive_job(path) as acquired:
            assert acquired
            raise RuntimeError("failed")
    with exclusive_job(path) as acquired:
        assert acquired


def test_job_lock_is_shared_between_processes(tmp_path):
    path = tmp_path / "job.lock"
    probe = (
        "import sys; from app.infrastructure.job_lock import exclusive_job\n"
        "with exclusive_job(sys.argv[1]) as acquired: print(acquired)"
    )
    with exclusive_job(path):
        result = subprocess.run(
            [sys.executable, "-c", probe, str(path)],
            check=True, capture_output=True, text=True, timeout=5,
        )
        assert result.stdout.strip() == "False"


def test_job_lock_does_not_hide_missing_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        with exclusive_job(tmp_path / "missing" / "job.lock"):
            pytest.fail("Missing lock directory must fail closed")
