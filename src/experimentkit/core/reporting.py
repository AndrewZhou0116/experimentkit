from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _md_escape(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def _as_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def _render_kv_table(rows: list[tuple[str, Any]]) -> str:
    out = []
    out.append("| Field | Value |")
    out.append("|---|---|")
    for k, v in rows:
        out.append(f"| {k} | {_md_escape(_as_str(v))} |")
    return "\n".join(out)


def _render_metrics_table(metrics: dict[str, Any]) -> str:
    # 只把标量放进表里（float/int/str/bool）
    items = []
    for k, v in metrics.items():
        if isinstance(v, (int, float, str, bool)) or v is None:
            items.append((k, v))
    items.sort(key=lambda x: x[0])
    return _render_kv_table(items)


def copy_plot_assets(run_dir: Path, out_assets_dir: Path) -> list[str]:
    """
    Copy run_dir/plots/*.png|*.jpg|*.jpeg into out_assets_dir.
    Returns list of copied filenames (relative to out_assets_dir).
    """
    plots_dir = run_dir / "plots"
    if not plots_dir.exists():
        return []

    out_assets_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for p in sorted(plots_dir.iterdir()):
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            dst = out_assets_dir / p.name
            shutil.copyfile(p, dst)
            copied.append(p.name)
    return copied


def generate_report(run_dir: Path, out_dir: Path) -> Path:
    """
    Generate reports/<run_id>/report.md from a run folder.
    Expects:
      - meta.json
      - config_final.yaml (optional)
      - metrics.json (optional)
      - plots/ (optional)
    """
    if not run_dir.exists():
        raise FileNotFoundError(f"run_dir not found: {run_dir}")

    meta_path = run_dir / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"meta.json not found in: {run_dir}")

    meta = read_json(meta_path)

    config_text = ""
    cfg_path = run_dir / "config_final.yaml"
    if cfg_path.exists():
        config_text = read_text(cfg_path)

    metrics: dict[str, Any] = {}
    m_path = run_dir / "metrics.json"
    if m_path.exists():
        metrics = read_json(m_path)

    run_id = run_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)

    assets_dir = out_dir / "assets"
    copied_imgs = copy_plot_assets(run_dir, assets_dir)

    # --- Markdown assembly ---
    title = f"# Experiment Report — {run_id}\n"
    summary_rows = [
        ("run_id", meta.get("run_id")),
        ("created_at", meta.get("created_at")),
        ("cwd", meta.get("cwd")),
        ("command", meta.get("command")),
        ("seed", meta.get("seed")),
        ("config_path", meta.get("config_path")),
        ("config_hash", meta.get("config_hash")),
        ("deps_hash", meta.get("deps_hash")),
        ("git_commit", meta.get("git_commit")),
        ("git_dirty", meta.get("git_dirty")),
        ("duration_sec", meta.get("duration_sec")),
        ("platform", meta.get("platform")),
        ("python_version", meta.get("python_version")),
    ]

    md = []
    md.append(title)
    md.append("## Summary")
    md.append(_render_kv_table(summary_rows))
    md.append("")

    md.append("## Metrics")
    if metrics:
        md.append(_render_metrics_table(metrics))
    else:
        md.append("_metrics.json not found (this run may have failed or metrics were not generated)._")
    md.append("")

    md.append("## Plots")
    if copied_imgs:
        for name in copied_imgs:
            md.append(f"### {name}")
            md.append(f"![{name}](assets/{name})")
            md.append("")
    else:
        md.append("_No plot assets found._")
        md.append("")

    md.append("## Final Config Snapshot")
    if config_text.strip():
        md.append("```yaml")
        md.append(config_text.rstrip())
        md.append("```")
    else:
        md.append("_config_final.yaml not found._")
    md.append("")

    md.append("## Reproduce")
    # 复现命令：直接给当时的 command（最可审计）
    cmd = meta.get("command") or ""
    if cmd:
        md.append("```bash")
        md.append(cmd)
        md.append("```")
    else:
        md.append("_No command recorded._")
    md.append("")

    report_path = out_dir / "report.md"
    report_path.write_text("\n".join(md), encoding="utf-8")
    return report_path

