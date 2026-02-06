from __future__ import annotations

import argparse
import json
import logging
import platform
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from experimentkit.core.config import apply_overrides, config_hash, dump_yaml, load_config
from experimentkit.core.tracking import (
    get_git_commit,
    is_git_dirty,
    pip_freeze,
    sha256_text,
    write_text,
)


@dataclass(frozen=True)
class RunMeta:
    run_id: str
    created_at: str
    command: str
    cwd: str
    python_version: str
    platform: str

    config_path: str | None
    config_hash: str
    seed: int | None
    overrides: list[str]

    git_commit: str | None
    git_dirty: bool | None
    deps_hash: str | None
    duration_sec: float


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _make_run_id() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    short = uuid.uuid4().hex[:8]
    return f"{ts}_{short}"


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _setup_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("experimentkit")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


def cmd_run(args: argparse.Namespace) -> int:
    start = time.time()

    # 1) load config (optional)
    if args.config is None:
        cfg: dict = {}
        config_path = None
    else:
        cfg = load_config(args.config)
        config_path = str(Path(args.config))

    # 2) apply seed & overrides -> final config snapshot
    if args.seed is not None:
        cfg["seed"] = int(args.seed)

    overrides: list[str] = list(args.set or [])
    final_cfg = apply_overrides(cfg, overrides)

    # 3) create run folder
    run_id = _make_run_id()
    run_dir = Path.cwd() / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    # 4) logs
    logger = _setup_logger(run_dir / "logs" / "run.log")
    logger.info("run started: %s", run_id)

    # 5) write final config + hash
    dump_yaml(run_dir / "config_final.yaml", final_cfg)
    chash = config_hash(final_cfg)
    logger.info("config_hash=%s", chash)

    # 6) deps snapshot
    deps_hash: str | None = None
    try:
        deps = pip_freeze()
        write_text(run_dir / "deps" / "pip_freeze.txt", deps)
        deps_hash = sha256_text(deps)
        logger.info("deps_hash=%s", deps_hash)
    except Exception as e:
        logger.info("deps snapshot failed: %s", e)

    # 7) git info
    cwd = Path.cwd()
    git_commit = get_git_commit(cwd)
    git_dirty = is_git_dirty(cwd)
    logger.info("git_commit=%s git_dirty=%s", git_commit, git_dirty)

    # 8) meta
    command = " ".join([Path(sys.argv[0]).name, *sys.argv[1:]])
    duration = time.time() - start

    meta = RunMeta(
        run_id=run_id,
        created_at=_utc_now_iso(),
        command=command,
        cwd=str(cwd),
        python_version=sys.version.replace("\n", " "),
        platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
        config_path=config_path,
        config_hash=chash,
        seed=args.seed,
        overrides=overrides,
        git_commit=git_commit,
        git_dirty=git_dirty,
        deps_hash=deps_hash,
        duration_sec=duration,
    )
    _write_json(run_dir / "meta.json", asdict(meta))

    logger.info("run finished duration_sec=%.3f", duration)

    print(f"[OK] run created: {run_id}")
    print(f"     path: {run_dir}")
    print(f"     config_hash: {chash[:12]}...")
    print(f"     duration_sec: {duration:.3f}s")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="exp", description="ExperimentKit CLI (MVP)")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="run one experiment (tracking + config snapshot)")
    p_run.add_argument("-c", "--config", default=None, help="config path (.yaml/.json)")
    p_run.add_argument("--seed", type=int, default=None, help="seed (also written into config)")
    p_run.add_argument(
        "--set",
        action="append",
        default=[],
        help="override config, repeatable. e.g. --set trainer.lr=1e-3",
    )
    p_run.set_defaults(func=cmd_run)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

