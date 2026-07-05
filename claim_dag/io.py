from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def read_yaml(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return default if data is None else data


def write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_frontmatter(path: Path) -> dict[str, Any]:
    """Parse a leading YAML frontmatter block (--- ... ---) from a Markdown or
    YAML audit artifact. Returns {} when the file has no frontmatter. A pure
    YAML file (no fences) is parsed whole if it is a mapping."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("---"):
        body = stripped[3:]
        end = body.find("\n---")
        if end != -1:
            block = body[:end]
            try:
                data = yaml.safe_load(block)
            except yaml.YAMLError:
                return {}
            return data if isinstance(data, dict) else {}
        return {}
    # No fence: accept a bare YAML mapping (e.g. an artifact written as .yaml).
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def read_artifacts(directory: Path) -> list[tuple[Path, dict[str, Any]]]:
    """Read every audit artifact in a directory, returning (path, frontmatter)
    for each .md or .yaml file. Files whose frontmatter fails to parse are
    returned with an empty mapping so the caller can flag them."""
    out: list[tuple[Path, dict[str, Any]]] = []
    if not directory.is_dir():
        return out
    for child in sorted(directory.iterdir()):
        if child.suffix.lower() in {".md", ".yaml", ".yml"} and child.is_file():
            out.append((child, read_frontmatter(child)))
    return out
