import tomllib
from dataclasses import dataclass, fields
from pathlib import Path


@dataclass(frozen=True)
class MemberSettings:
    session_seconds: int = 3600
    max_sessions: int = 5
    attempts_per_client: int = 20
    attempts_per_account: int = 5
    rate_window_seconds: int = 60

    def __post_init__(self) -> None:
        limits = {
            "session_seconds": (60, 2_592_000),
            "max_sessions": (1, 100),
            "attempts_per_client": (1, 10_000),
            "attempts_per_account": (1, 10_000),
            "rate_window_seconds": (1, 86_400),
        }
        for name, (minimum, maximum) in limits.items():
            value = getattr(self, name)
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"Invalid member setting: {name}")

    @classmethod
    def from_file(cls, path: Path) -> "MemberSettings":
        with path.open("rb") as handle:
            document = tomllib.load(handle)
        if set(document) != {"members"} or not isinstance(document["members"], dict):
            raise ValueError("Expected a members table")
        values = document["members"]
        if set(values) - {item.name for item in fields(cls)}:
            raise ValueError("Unknown member setting")
        return cls(**values)
