from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config not found: {p}")

    text = p.read_text(encoding="utf-8")

    if p.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    elif p.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        raise ValueError("config must be .yaml/.yml/.json")

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise TypeError("config root must be a mapping/dict")

    return data


def parse_override(s: str) -> tuple[list[str], Any]:
    """
    Parse 'a.b.c=VALUE' -> (['a','b','c'], parsed_value)
    VALUE is parsed via yaml.safe_load so numbers/bools/null become proper types.
    """
    if "=" not in s:
        raise ValueError(f"override must contain '=': {s}")

    key, raw = s.split("=", 1)
    key = key.strip()
    raw = raw.strip()

    if not key:
        raise ValueError(f"override key is empty: {s}")

    keys = key.split(".")
    value = yaml.safe_load(raw)  # typed parsing: 1e-3 -> float, true -> bool, etc.
    return keys, value


def set_by_path(d: dict[str, Any], keys: list[str], value: Any) -> None:
    cur: dict[str, Any] = d
    for k in keys[:-1]:
        if k not in cur:
            cur[k] = {}
        if not isinstance(cur[k], dict):
            raise TypeError(f"override path hits non-dict at '{k}'")
        cur = cur[k]
    cur[keys[-1]] = value


def apply_overrides(cfg: dict[str, Any], overrides: list[str]) -> dict[str, Any]:
    out = deepcopy(cfg)
    for s in overrides:
        keys, val = parse_override(s)
        set_by_path(out, keys, val)
    return out


def config_hash(cfg: dict[str, Any]) -> str:
    """
    Stable hash for config content.
    We canonicalize via JSON with sorted keys.
    """
    blob = json.dumps(cfg, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def dump_yaml(path: str | Path, cfg: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(cfg, sort_keys=True, allow_unicode=True), encoding="utf-8")

