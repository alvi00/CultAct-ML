#!/usr/bin/env python3
"""CultAct-ML Stage 4 (step 2) - consolidate metrics + 3 figures (PROJECT.md sec 6).

Reads analysis/metrics_m1.csv, _m2.csv, _m3.csv (produced by analyze.py). Writes:
  analysis/metrics.csv                      (joined, one row per model x language)
  analysis/figures/fig1_western_share.png   (headline: Western share by lang x model)
  analysis/figures/fig2_consistency.png     (self- + cross-language consistency)
  analysis/figures/fig3_plan_drift.png      (plan-similarity stratified + action-change)
Pure csv + matplotlib (no torch). utf-8, pathlib.
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ANA = ROOT / "analysis"
FIG = ANA / "figures"
MODELS = ["open", "frontier", "reasoning"]
LANGS = ["en", "id", "bn"]
COLOR = {"open": "#4C72B0", "frontier": "#DD8452", "reasoning": "#55A868"}


def read_csv(name: str) -> dict:
    """(role, language) -> row dict."""
    out = {}
    with (ANA / name).open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[(r["role"], r["language"])] = r
    return out


def f(x):
    return float(x) if x not in ("", None) else None


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    m1, m2, m3 = read_csv("metrics_m1.csv"), read_csv("metrics_m2.csv"), read_csv("metrics_m3.csv")

    # ---- consolidated metrics.csv (join on role x language) ----
    fields = ["model", "role", "language",
              "western_share_full", "western_share_standard", "shift_vs_en",
              "chance_baseline_mean", "n_valid",
              "invalid_rate", "self_consistency", "xling_consistency_vs_en",
              "drift_all", "drift_matched", "drift_mismatched",
              "n_matched_runs", "n_mismatched_runs",
              "plan_lang_mismatch_rate", "frac_action_change_with_low_plan_sim"]
    with (ANA / "metrics.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for role in MODELS:
            for lang in LANGS:
                a, b, c = m1[(role, lang)], m2[(role, lang)], m3[(role, lang)]
                row = {"model": a["model"], "role": role, "language": lang}
                for k in ("western_share_full", "western_share_standard", "shift_vs_en",
                          "chance_baseline_mean", "n_valid"):
                    row[k] = a[k]
                for k in ("invalid_rate", "self_consistency", "xling_consistency_vs_en"):
                    row[k] = b[k]
                for k in ("drift_all", "drift_matched", "drift_mismatched",
                          "n_matched_runs", "n_mismatched_runs",
                          "plan_lang_mismatch_rate", "frac_action_change_with_low_plan_sim"):
                    row[k] = c[k]
                w.writerow(row)
    print(f"wrote {(ANA/'metrics.csv').relative_to(ROOT)}")

    baseline = f(m1[("open", "en")]["chance_baseline_mean"])

    # ================= FIG 1 - Western share by language x model =================
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(LANGS)); width = 0.25
    for i, model in enumerate(MODELS):
        full = [f(m1[(model, lg)]["western_share_full"]) for lg in LANGS]
        std = [f(m1[(model, lg)]["western_share_standard"]) for lg in LANGS]
        pos = x + (i - 1) * width
        ax.bar(pos, full, width, label=model, color=COLOR[model], zorder=3)
        ax.scatter(pos, std, marker="_", s=260, color="black", zorder=4,
                   label="standard-35 subset" if i == 0 else None)
        for p, v in zip(pos, full):
            ax.text(p, v + 0.01, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
    ax.axhline(baseline, ls="--", color="grey", zorder=2)
    ax.text(2.35, baseline + 0.006, f"chance baseline {baseline:.3f}", color="grey",
            ha="right", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([l.upper() for l in LANGS])
    ax.set_ylabel("Western-cluster share (mean of per-scenario shares)")
    ax.set_ylim(0, 1.0)
    ax.set_title("Metric 1 - Cultural Default Score: Western share by language x model")
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    fig.tight_layout(); fig.savefig(FIG / "fig1_western_share.png", dpi=150); plt.close(fig)
    print("wrote figures/fig1_western_share.png")

    # ================= FIG 2 - consistency across en->id->bn =================
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for model in MODELS:
        sc = [f(m2[(model, lg)]["self_consistency"]) for lg in LANGS]
        xl = [f(m2[(model, lg)]["xling_consistency_vs_en"]) for lg in LANGS]
        axes[0].plot(LANGS, sc, "-o", color=COLOR[model], label=model)
        axes[1].plot(LANGS, xl, "-o", color=COLOR[model], label=model)
    axes[0].set_title("Self-consistency (repeat agreement)")
    axes[0].set_ylabel("mean max-agreement / 3"); axes[0].set_ylim(0.33, 1.0)
    axes[0].axhline(1/3, ls=":", color="grey"); axes[0].legend(fontsize=8)
    axes[1].set_title("Cross-language consistency vs English")
    axes[1].set_ylabel("frac scenarios with same modal pick as EN"); axes[1].set_ylim(0.4, 1.02)
    axes[1].legend(fontsize=8)
    for a in axes:
        a.set_xticks(range(3)); a.set_xticklabels([l.upper() for l in LANGS]); a.grid(alpha=0.3)
    fig.suptitle("Metric 2 - reliability across en -> id -> bn")
    fig.tight_layout(); fig.savefig(FIG / "fig2_consistency.png", dpi=150); plt.close(fig)
    print("wrote figures/fig2_consistency.png")

    # ================= FIG 3 - plan drift stratified + action-change =================
    cells = [(m, lg) for m in MODELS for lg in ("id", "bn")]
    labels = [f"{m}\n{lg}" for m, lg in cells]
    xc = np.arange(len(cells))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    width = 0.26
    for j, (key, name, col) in enumerate([
            ("drift_all", "all", "#B0B0B0"),
            ("drift_matched", "matched (plan in-language)", "#2C7FB8"),
            ("drift_mismatched", "mismatched (plan in English)", "#D95F0E")]):
        vals = [f(m3[c][key]) for c in cells]
        pos = xc + (j - 1) * width
        ax0 = axes[0]
        ax0.bar([p for p, v in zip(pos, vals) if v is not None],
                [v for v in vals if v is not None], width, label=name, color=col, zorder=3)
    # annotate reasoning x bn matched deflation
    rb = cells.index(("reasoning", "bn"))
    da, dm = f(m3[("reasoning", "bn")]["drift_all"]), f(m3[("reasoning", "bn")]["drift_matched"])
    axes[0].annotate(f"language switch\ninflates similarity\n{da:.2f} -> {dm:.2f}",
                     xy=(rb - width, dm), xytext=(rb - 2.1, 0.70), fontsize=8,
                     arrowprops=dict(arrowstyle="->", color="black"))
    axes[0].set_xticks(xc); axes[0].set_xticklabels(labels, fontsize=8)
    axes[0].set_ylabel("plan similarity (LaBSE cosine; higher = less drift)")
    axes[0].set_ylim(0.6, 1.0); axes[0].legend(fontsize=8, loc="lower left")
    axes[0].set_title("Plan drift, plan_lang-stratified")
    # right: does drift start at planning? frac action-change with low plan sim
    fr = [f(m3[c]["frac_action_change_with_low_plan_sim"]) for c in cells]
    axes[1].bar(xc, [v if v is not None else 0 for v in fr],
                color=[COLOR[m] for m, _ in cells], zorder=3)
    for p, v in zip(xc, fr):
        if v is not None:
            axes[1].text(p, v + 0.01, f"{v:.2f}", ha="center", fontsize=8)
    axes[1].axhline(0.5, ls=":", color="grey")
    axes[1].set_xticks(xc); axes[1].set_xticklabels(labels, fontsize=8)
    axes[1].set_ylabel("frac of action-changed scenarios\nwith below-median plan similarity")
    axes[1].set_ylim(0, 1.0); axes[1].set_title("Does drift start at planning?")
    fig.suptitle("Metric 3 - plan drift (MAPS-style), plan_lang-stratified")
    fig.tight_layout(); fig.savefig(FIG / "fig3_plan_drift.png", dpi=150); plt.close(fig)
    print("wrote figures/fig3_plan_drift.png")


if __name__ == "__main__":
    main()
