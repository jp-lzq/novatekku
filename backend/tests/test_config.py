from pathlib import Path

import pytest
from app.config import MemberSettings


def test_example_configuration():
    settings = MemberSettings.from_file(
        Path(__file__).parents[1] / "examples/members.example.toml"
    )
    assert settings == MemberSettings()


@pytest.mark.parametrize(
    "values",
    [
        {"session_seconds": 0},
        {"session_seconds": True},
        {"max_sessions": 0},
        {"attempts_per_client": -1},
        {"rate_window_seconds": 0},
        {"max_sessions": "5"},
    ],
)
def test_invalid_configuration(values):
    with pytest.raises(ValueError):
        MemberSettings(**values)


@pytest.mark.parametrize(
    "document",
    [
        "[members]\nunknown = 1\n",
        "[unrelated]\nvalue = 1\n",
        "members = 1\n",
    ],
)
def test_unknown_configuration_rejected(tmp_path, document):
    path = tmp_path / "settings.toml"
    path.write_text(document)
    with pytest.raises(ValueError):
        MemberSettings.from_file(path)
