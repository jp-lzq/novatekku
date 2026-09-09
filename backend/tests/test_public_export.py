import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "public_backend", ROOT / "scripts/public_backend.py"
)
publication = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publication)


def fixture_source(tmp_path):
    source = tmp_path / "source"
    (source / "backend/app").mkdir(parents=True)
    (source / "public").mkdir()
    paths = ["backend/app/__init__.py", "backend/app/example.py", publication.MANIFEST]
    (source / "backend/app/__init__.py").write_text("")
    (source / "backend/app/example.py").write_text("VALUE = 1\n")
    (source / publication.MANIFEST).write_text(
        json.dumps({"version": 1, "files": paths})
    )
    return source


def test_public_tree_is_self_contained():
    payloads = publication.validate(ROOT, strict=True)
    assert "backend/app/application/members.py" in payloads


def test_export_skips_private_source_files(tmp_path):
    source = fixture_source(tmp_path)
    (source / "backend/private_settings.py").write_text("PRIVATE_VALUE = 1\n")
    output = tmp_path / "output"
    publication.export(source, output)
    assert not (output / "backend/private_settings.py").exists()
    assert publication.validate(output, strict=True)
    with pytest.raises(ValueError, match="Unclassified"):
        publication.validate(source, strict=True)


def test_export_never_overwrites(tmp_path):
    source = fixture_source(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    (output / "keep.txt").write_text("keep")
    with pytest.raises(ValueError, match="must not exist"):
        publication.export(source, output)
    assert (output / "keep.txt").read_text() == "keep"


@pytest.mark.parametrize(
    "bad_path",
    [
        "../secret.txt",
        "/tmp/secret.txt",
        ".git/config",
        ".env",
        "backend/../secret.txt",
    ],
)
def test_unsafe_manifest_paths(tmp_path, bad_path):
    source = fixture_source(tmp_path)
    (source / publication.MANIFEST).write_text(
        json.dumps({"version": 1, "files": [bad_path, publication.MANIFEST]})
    )
    with pytest.raises(ValueError, match="Unsafe"):
        publication.validate(source, strict=False)


def test_source_symlink_is_rejected_before_export(tmp_path):
    source = fixture_source(tmp_path)
    target = source / "backend/app/example.py"
    target.unlink()
    secret = tmp_path / "secret.txt"
    secret.write_text("hidden")
    target.symlink_to(secret)
    with pytest.raises(ValueError, match="Symlink"):
        publication.export(source, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_parent_symlink_is_rejected(tmp_path):
    source = fixture_source(tmp_path)
    hidden = tmp_path / "hidden"
    shutil.move(source / "backend/app", hidden)
    (source / "backend/app").symlink_to(hidden)
    with pytest.raises(ValueError, match="Symlink"):
        publication.validate(source, strict=False)


def test_private_import_is_rejected(tmp_path):
    source = fixture_source(tmp_path)
    (source / "backend/app/example.py").write_text(
        "from app.unpublished import service\n"
    )
    with pytest.raises(ValueError, match="Unpublished dependency"):
        publication.validate(source, strict=True)


def test_embedded_credential_is_rejected(tmp_path):
    source = fixture_source(tmp_path)
    header = "-----BEGIN " + "PRIVATE KEY-----"
    (source / "backend/app/example.py").write_text(f"VALUE = {header!r}\n")
    with pytest.raises(ValueError, match="Sensitive content"):
        publication.validate(source, strict=True)


@pytest.mark.parametrize(
    "statement",
    [
        "from app import unpublished",
        "from . import unpublished",
        "import unpublished",
        "from unpublished import service",
    ],
)
def test_unpublished_import_variants_rejected(tmp_path, statement):
    source = fixture_source(tmp_path)
    (source / "backend/app/example.py").write_text(statement + "\n")
    with pytest.raises(ValueError, match="dependency"):
        publication.validate(source, strict=True)


def test_package_attributes_and_relative_imports_are_supported(tmp_path):
    source = fixture_source(tmp_path)
    (source / "backend/app/__init__.py").write_text("VALUE = 1\n")
    (source / "backend/app/example.py").write_text("from . import VALUE\n")
    assert publication.validate(source, strict=True)


def test_public_package_module_imports_are_supported(tmp_path):
    source = fixture_source(tmp_path)
    (source / "backend/app/__init__.py").write_text("from app import example\n")
    assert publication.validate(source, strict=True)
