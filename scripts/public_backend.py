import argparse
import ast
import importlib.util
import json
import re
import sys
from pathlib import Path, PurePosixPath

MANIFEST = "public/backend-files.json"
GENERATED = {"__pycache__", ".pytest_cache", ".ruff_cache"}
SENSITIVE = (
    re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b"),
    re.compile(r"https?://docs\.google\.com/spreadsheets/d/[A-Za-z0-9_-]+"),
)


def load_manifest(source: Path) -> tuple[list[str], set[str]]:
    document = json.loads((source / MANIFEST).read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or set(document) - {"version", "files", "external_imports"}
        or type(document.get("version")) is not int
        or document["version"] != 1
    ):
        raise ValueError("Unsupported manifest")
    paths = document.get("files")
    if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
        raise ValueError("Invalid file list")
    if not paths or len(paths) != len(set(paths)):
        raise ValueError("Empty or duplicate file list")
    if MANIFEST not in paths:
        raise ValueError("Manifest must include itself")
    external = document.get("external_imports", [])
    if not isinstance(external, list) or not all(
        isinstance(name, str) and name.isidentifier() for name in external
    ):
        raise ValueError("Invalid external imports")
    for name in paths:
        path = PurePosixPath(name)
        if (
            path.is_absolute()
            or path.as_posix() != name
            or any(
                part in {"..", ".git"} or part.startswith(".env") for part in path.parts
            )
        ):
            raise ValueError(f"Unsafe path: {name}")
        if "\\" in name:
            raise ValueError(f"Unsafe path: {name}")
    return paths, set(external)


def _bindings(tree: ast.Module) -> set[str]:
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                names.update(
                    item.id for item in ast.walk(target) if isinstance(item, ast.Name)
                )
    return names


def check_imports(payloads: dict[str, bytes], external: set[str]) -> None:
    modules = {}
    for name, payload in payloads.items():
        if name.startswith("backend/app/") and name.endswith(".py"):
            parts = list(PurePosixPath(name).with_suffix("").parts[1:])
            is_package = parts[-1] == "__init__"
            if is_package:
                parts.pop()
            tree = ast.parse(payload, filename=name)
            modules[".".join(parts)] = (name, tree, is_package, _bindings(tree))
    allowed_roots = sys.stdlib_module_names | external

    def check_target(target: str, name: str) -> None:
        if target == "app" or target.startswith("app."):
            if target not in modules:
                raise ValueError(f"Unpublished dependency in {name}: {target}")
        elif target.split(".")[0] not in allowed_roots:
            raise ValueError(f"Unapproved external dependency in {name}: {target}")

    for module, (name, tree, is_package, _) in modules.items():
        package = module if is_package else module.rpartition(".")[0]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    check_target(alias.name, name)
            elif isinstance(node, ast.ImportFrom):
                try:
                    target = importlib.util.resolve_name(
                        "." * node.level + (node.module or ""), package
                    )
                except ImportError:
                    raise ValueError(f"Invalid relative import: {name}") from None
                check_target(target, name)
                if target in modules:
                    exported = modules[target][3]
                    for alias in node.names:
                        if (
                            alias.name not in exported
                            and f"{target}.{alias.name}" not in modules
                        ):
                            raise ValueError(
                                f"Unpublished dependency in {name}: {target}.{alias.name}"
                            )


def validate(source: Path, *, strict: bool) -> dict[str, bytes]:
    source = source.resolve()
    if (source / MANIFEST).is_symlink() or (source / "public").is_symlink():
        raise ValueError("Manifest must not be a symlink")
    paths, external = load_manifest(source)
    payloads = {}
    for name in paths:
        path = source / name
        if any(
            parent.is_symlink() for parent in (path, *path.parents) if parent != source
        ):
            raise ValueError(f"Symlink is not allowed: {name}")
        if not path.is_file() or not path.resolve().is_relative_to(source):
            raise ValueError(f"Missing or external file: {name}")
        payload = path.read_bytes()
        content = payload.decode("utf-8")
        if any(pattern.search(content) for pattern in SENSITIVE):
            raise ValueError(f"Sensitive content detected: {name}")
        payloads[name] = payload
    if strict:
        for path in (source / "backend").rglob("*"):
            relative = path.relative_to(source)
            if path.is_symlink():
                raise ValueError(f"Symlink is not allowed: {relative}")
            if set(relative.parts) & GENERATED:
                continue
            if path.is_file() and relative.as_posix() not in payloads:
                raise ValueError(f"Unclassified backend file: {relative}")
    check_imports(payloads, external)
    return payloads


def export(source: Path, destination: Path) -> int:
    if destination.is_symlink() or any(
        parent.is_symlink() for parent in destination.parents
    ):
        raise ValueError("Export destination must not contain symlinks")
    if destination.exists():
        raise ValueError("Export destination must not exist")
    if destination.resolve().is_relative_to(source.resolve()):
        raise ValueError("Export destination must be outside the source tree")
    payloads = validate(source, strict=False)
    destination.mkdir(parents=True)
    for name, payload in payloads.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        path.chmod(0o644)
    return len(payloads)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("check", "export"))
    parser.add_argument(
        "--source", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.exit(1, "Python 3.11 or newer is required\n")
    try:
        if args.command == "export":
            if args.destination is None:
                parser.error("export requires --destination")
            count = export(args.source, args.destination)
        else:
            count = len(validate(args.source, strict=True))
    except (ValueError, OSError, SyntaxError) as error:
        parser.exit(1, f"{error}\n")
    print(f"Public backend: {count} files checked")


if __name__ == "__main__":
    main()
