from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


def _run_cmd(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout.strip()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def get_git_commit(cwd: Path) -> str | None:
    code, out = _run_cmd(["git", "-C", str(cwd), "rev-parse", "HEAD"])
    return out if code == 0 and out else None


def is_git_dirty(cwd: Path) -> bool | None:
    # 有输出 => dirty；无输出 => clean
    code, out = _run_cmd(["git", "-C", str(cwd), "status", "--porcelain"])
    if code != 0:
        return None
    return bool(out)


def pip_freeze() -> str:
    # 用当前 venv 的 python 调 pip freeze，保证对应环境
    code, out = _run_cmd([sys.executable, "-m", "pip", "freeze"])
    if code != 0:
        raise RuntimeError("pip freeze failed")
    return out + "\n"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

