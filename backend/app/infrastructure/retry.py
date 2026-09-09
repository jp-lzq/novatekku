import math
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    initial_delay: float = 0.25
    max_delay: float = 5.0

    def __post_init__(self) -> None:
        if type(self.attempts) is not int or not 1 <= self.attempts <= 20:
            raise ValueError("attempts must be between 1 and 20")
        for value in (self.initial_delay, self.max_delay):
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError("delays must be finite and nonnegative")
        if self.initial_delay > self.max_delay:
            raise ValueError("initial_delay exceeds max_delay")


def retry(
    operation: Callable[[], T],
    *,
    retryable: Callable[[Exception], bool],
    policy: RetryPolicy | None = None,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = random.random,
) -> T:
    policy = policy or RetryPolicy()
    for attempt in range(policy.attempts):
        try:
            return operation()
        except Exception as error:
            if attempt + 1 == policy.attempts or not retryable(error):
                raise
            fraction = jitter()
            if not math.isfinite(fraction) or not 0 <= fraction <= 1:
                raise ValueError(
                    "jitter must return a value between 0 and 1"
                ) from error
            delay = min(policy.max_delay, policy.initial_delay * 2**attempt)
            sleep(delay * fraction)
    raise AssertionError("unreachable")
