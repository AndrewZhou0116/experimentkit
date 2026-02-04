from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class RunMeta:
    run_id: str
    created_at: str
    command: str
    cwd: str
    python_version: str
    platform: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _make_run_id() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    short = uuid.uuid4().hex[:8]
    return f"{ts}_{short}"


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def cmd_run(args: argparse.Namespace) -> int:
    start = time.time()

    runs_dir = Path.cwd() / "runs"
    run_id = _make_run_id()
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    command = " ".join([Path(sys.argv[0]).name, *sys.argv[1:]])

    meta = RunMeta(
        run_id=run_id,
        created_at=_utc_now_iso(),
        command=command,
        cwd=str(Path.cwd()),
        python_version=sys.version.replace("\n", " "),
        platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
    )

    _write_json(run_dir / "meta.json", asdict(meta))

    # Day 1: 只证明“能跑 + 能落盘”。后续 Day 2+ 再加 config/metrics/plots/logs
    elapsed = time.time() - start
    print(f"[OK] run created: {run_id}")
    print(f"     path: {run_dir}")
    print(f"     elapsed: {elapsed:.3f}s")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="exp", description="ExperimentKit CLI (MVP)")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="run one experiment (Day1: creates a run folder)")
    p_run.add_argument("-c", "--config", default=None, help="config path (reserved for Day2)")
    p_run.add_argument("--seed", type=int, default=None, help="seed (reserved for Day2)")
    p_run.set_defaults(func=cmd_run)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

