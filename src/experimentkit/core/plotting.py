from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def save_confusion_matrix(cm: np.ndarray, labels: list[str], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots()
    im = ax.imshow(cm)
    fig.colorbar(im, ax=ax)

    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_yticklabels(labels)

    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("Confusion Matrix")

    # 写数字
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center")

    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)

