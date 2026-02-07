from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split

from experimentkit.core.plotting import save_confusion_matrix


def run_experiment(cfg: dict[str, Any], run_dir: Path, logger) -> dict[str, Any]:
    """
    Execute one experiment according to cfg and write artifacts into run_dir.
    Returns metrics dict (will be saved by CLI).
    """
    data = cfg.get("data", {})
    name = data.get("name")

    if name == "iris":
        return _run_iris(cfg, run_dir, logger)

    raise ValueError(f"unknown dataset: {name!r} (try data.name: iris)")


def _run_iris(cfg: dict[str, Any], run_dir: Path, logger) -> dict[str, Any]:
    seed = int(cfg.get("seed", 0))

    trainer = cfg.get("trainer", {})
    test_size = float(trainer.get("test_size", 0.2))

    model_cfg = cfg.get("model", {})
    if model_cfg.get("type") not in {"logistic_regression", "logreg", None}:
        logger.info("warning: model.type=%s (Iris demo uses LogisticRegression anyway)", model_cfg.get("type"))

    params = dict(model_cfg.get("params", {}))
    # 给一些合理默认值（防止配置漏写）
    params.setdefault("C", 1.0)
    params.setdefault("max_iter", 200)

    logger.info("load iris dataset")
    iris = load_iris()
    X = iris.data
    y = iris.target

    logger.info("train_test_split test_size=%s seed=%s", test_size, seed)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )

    logger.info("train LogisticRegression params=%s", params)
    clf = LogisticRegression(**params)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)

    acc = float(accuracy_score(y_test, y_pred))
    cm = confusion_matrix(y_test, y_pred)

    # plots
    labels = [str(x) for x in iris.target_names]
    plot_path = run_dir / "plots" / "confusion_matrix.png"
    save_confusion_matrix(cm.astype(int), labels, plot_path)
    logger.info("plot saved: %s", plot_path)

    metrics = {
        "accuracy": acc,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
    }
    return metrics

