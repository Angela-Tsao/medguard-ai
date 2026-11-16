import json
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
R = Path(__file__).resolve().parents[1] / "results"; F = R / "figures"
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#a3a29c"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False})
res = pd.read_csv(R / "model_comparison.csv")
SYN = "Synthetic test (unseen drugs + templates)"
CHOSEN = "Logistic regression"

# Fig 1: recall by input type
types = ["clean", "brand", "misspelled", "ocr_noise", "dose_attached"]
labels = ["Clean", "Brand name", "Misspelled", "OCR noise", "Dose attached"]
series = [("Exact match (baseline)", AQUA), ("Fuzzy match (baseline)", ORANGE), (CHOSEN, BLUE)]
fig, ax = plt.subplots(figsize=(7.2, 3.4)); w = 0.26; x = np.arange(len(types))
for k, (m, c) in enumerate(series):
    v = [res[(res.model == m) & (res.test_set == SYN) & (res.input_type == t)].recall.iloc[0] for t in types]
    b = ax.bar(x + (k - 1) * (w + 0.02), v, w, color=c, label=m.replace(" (baseline)", " (baseline)"), zorder=3)
    if m.startswith("Exact"):
        for xi, vi in zip(x + (k - 1) * (w + 0.02), v):
            ax.text(xi, vi + 0.02, f"{vi:.0%}", ha="center", fontsize=8, color=INK2)
ax.set_xticks(x, labels); ax.set_ylim(0, 1.12); ax.set_yticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"])
ax.grid(axis="y", color=GRID, zorder=0); ax.set_ylabel("Recall (medication names found)")
ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.16), fontsize=9)
fig.tight_layout(); fig.savefig(F / "fig1_recall_by_input_type.png", dpi=200); plt.close()

# Fig 2: precision and recall with 95% CI, all methods, synthetic test
a = res[(res.test_set == SYN) & (res.input_type == "ALL")].sort_values("f1")
fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.4), sharey=True)
for ax, (m, lo, hi, title) in zip(axes, [("precision", "precision_lo", "precision_hi", "Precision (flags that are real)"),
                                          ("recall", "recall_lo", "recall_hi", "Recall (real names found)")]):
    y = np.arange(len(a))
    cols = [BLUE if mm == CHOSEN else GRAY for mm in a.model]
    ax.hlines(y, a[lo], a[hi], color=cols, lw=2, zorder=3)
    ax.scatter(a[m], y, color=cols, s=40, zorder=4, edgecolor="white", linewidth=1)
    for yi, v in zip(y, a[m]):
        ax.text(min(v, 1.0) + 0.02, yi, f"{v:.1%}", va="center", fontsize=8, color=INK2)
    ax.set_title(title, fontsize=10, color=INK, loc="left"); ax.set_xlim(0.5, 1.1)
    ax.set_xticks([.5, .6, .7, .8, .9, 1.0], ["50%", "60%", "70%", "80%", "90%", "100%"])
    ax.grid(axis="x", color=GRID, zorder=0)
axes[0].set_yticks(np.arange(len(a)), a.model)
fig.text(0.01, 0.01, "Synthetic test set: 1,000 sentences, 1,323 medication mentions; drugs and templates unseen in training. Bars = bootstrap 95% CI.",
         fontsize=7.5, color=INK2)
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(F / "fig2_precision_recall_ci.png", dpi=200); plt.close()

# Fig 3: threshold tuning on validation (chosen model)
cur = pd.read_csv(R / "val_pr_curve_logreg.csv")
thr = json.load(open(R / "thresholds.json"))["logreg"]["threshold"]
fig, ax = plt.subplots(figsize=(6.6, 3.2))
ax.plot(cur.threshold, cur.recall, color=BLUE, lw=2, label="Recall")
ax.plot(cur.threshold, cur.precision, color=ORANGE, lw=2, label="Precision")
ax.axvline(thr, color=INK2, ls="--", lw=1)
ax.text(thr + 0.015, 0.62, f"Chosen threshold {thr:.2f}\nlowest validation cost\n(miss = 10 x false flag)", fontsize=8, color=INK2)
ax.text(0.98, cur.recall.iloc[-1] if False else 0.55, "", fontsize=8)
ax.set_xlim(0, 1); ax.set_ylim(0.5, 1.02); ax.set_xlabel("Model score threshold for 'this word is a medication'")
ax.set_yticks([.5, .6, .7, .8, .9, 1.0], ["50%", "60%", "70%", "80%", "90%", "100%"]); ax.grid(color=GRID)
ax.legend(frameon=False, loc="lower left"); fig.tight_layout(); fig.savefig(F / "fig3_threshold_validation.png", dpi=200); plt.close()
print("ok")
