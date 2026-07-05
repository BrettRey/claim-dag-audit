from __future__ import annotations

import shlex
import shutil
from pathlib import Path
from typing import Any

import yaml


DEFAULT_POLICY: list[dict[str, str]] = [
    {"family": "zhipu", "model": "glm-4.7-flash:q4_K_M", "tier": "local", "effort": "low",
     "runner": "ollama run glm-4.7-flash:q4_K_M"},
    {"family": "qwen", "model": "qwen3:8b", "tier": "local", "effort": "low",
     "runner": "ollama run qwen3:8b"},
    {"family": "google", "model": "gemma3:12b", "tier": "local", "effort": "low",
     "runner": "ollama run gemma3:12b"},
    {"family": "anthropic", "model": "claude-haiku-4-5", "tier": "cheap", "effort": "low",
     "runner": "claude --model claude-haiku-4-5"},
    {"family": "openai", "model": "gpt-5.4", "tier": "strong", "effort": "medium",
     "runner": "codex exec --sandbox read-only --skip-git-repo-check -m gpt-5.4"},
    {"family": "anthropic", "model": "claude-opus-4-8", "tier": "strong", "effort": "high",
     "runner": "claude --model claude-opus-4-8"},
    {"family": "anthropic", "model": "claude-opus-4-8", "tier": "max", "effort": "max",
     "runner": "claude --model claude-opus-4-8"},
]

_REQUIRED = {"family", "model", "tier", "effort", "runner"}


def load_policy(path: Path | None = None) -> list[dict[str, str]]:
    if path is None:
        return [dict(entry) for entry in DEFAULT_POLICY]
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("policy")
    if not isinstance(data, list):
        raise ValueError("policy file must contain a list or a mapping with a policy list")
    out: list[dict[str, str]] = []
    for index, entry in enumerate(data, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"policy entry #{index} must be a mapping")
        missing = sorted(_REQUIRED - set(entry))
        if missing:
            raise ValueError(f"policy entry #{index} missing {', '.join(missing)}")
        out.append({key: str(entry[key]) for key in _REQUIRED})
    return out


def policy_doctor(policy: list[dict[str, str]]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    missing_commands: set[str] = set()
    for entry in policy:
        tokens = shlex.split(entry["runner"])
        command = tokens[0] if tokens else ""
        found = bool(command and shutil.which(command))
        if not found and command:
            missing_commands.add(command)
        checks.append({
            "family": entry["family"],
            "model": entry["model"],
            "tier": entry["tier"],
            "runner": entry["runner"],
            "command": command,
            "command_found": found,
        })
    return {
        "ok": not missing_commands,
        "missing_commands": sorted(missing_commands),
        "checks": checks,
    }
