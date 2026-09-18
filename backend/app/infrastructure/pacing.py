import math
import random
import time
from collections.abc import Callable
from threading import Lock


class RequestPacer:
    def __init__(
        self,
        minimum: float,
        maximum: float,
        *,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        for value in (minimum, maximum):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValueError("Intervals must be finite and nonnegative")
        if minimum > maximum:
            raise ValueError("Minimum interval exceeds maximum")
        self.minimum = minimum
        self.maximum = maximum
        self._sleep = sleep
        self._jitter = jitter
        self._lock = Lock()

    def wait(self) -> float:
        with self._lock:
            fraction = self._jitter()
            if (
                isinstance(fraction, bool)
                or not isinstance(fraction, (int, float))
                or not math.isfinite(fraction)
                or not 0 <= fraction <= 1
            ):
                raise ValueError("Jitter must return a value between 0 and 1")
            delay = self.minimum + (self.maximum - self.minimum) * fraction
            self._sleep(delay)
            return delay
