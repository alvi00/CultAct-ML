#!/usr/bin/env python3
"""CultAct-ML Stage 4 - measurement & analysis. INCREMENTAL: Metric 1 only so far.

Metric 1 - Cultural Default Score (PROJECT.md sec 6). Western-cluster share computed
PER SCENARIO against that scenario's own available options, then aggregated as a
MEAN OF PER-SCENARIO SHARES across scenarios (never a single pooled ratio). Reported
as the full model x language grid, over the full 39 scenarios AND over the
"standard"-distinctness subset (excluding distinctness_tier=="reduced").

Inputs : results/runs.jsonl, data/scenarios_meta.jsonl   (join on scenario_id)
Output : analysis/metrics_m1.csv  + a console table + one hand-check cell.
All reads utf-8 explicit; pathlib. Metrics 2 and 3 are NOT built yet.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "results" / "runs.jsonl"
META = ROOT / "data" / "scenarios_meta.jsonl"
OUT_CSV = ROOT / "analysis" / "metrics_m1.csv"

# sec 7.2 canonicalization: normalize the 3 hyphenated source keys on load.
_NORMALIZE = {"latin-america": "latin_america",
              "sub-saharan_africa": "sub_saharan_africa",
              "southern-asia": "southern_asia"}
CANONICAL = {"anglo", "eastern_europe", "latin_america", "latin_europe",
             "confucian_asia", "nordic_europe", "sub_saharan_africa",
             "southern_asia", "germanic_europe", "middle_east"}
WESTERN = {"anglo", "nordic_europe", "germanic_europe"}

MODELS = [("qwen2572b", "open"), ("kimik2", "frontier"), ("qwen3think", "reasoning")]
LANGS = ["en", "id", "bn"]


def _norm(c: str) -> str:
    return _NORMALIZE.get(c, c)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def load_meta() -> dict:
    meta = {}
    for m in load_jsonl(META):
        clusters = {oid: _norm(c) for oid, c in m["option_clusters"].items()}
        meta[m["scenario_id"]] = {
            "clusters": clusters,
            "western_options": set(m.get("western_options", [])),
            "n_western": sum(1 for c in clusters.values() if c in WESTERN),
            "reduced": m.get("distinctness_tier") == "reduced",
        }
    return meta


def model_short(run_id: str) -> str:
    return run_id.split("__")[2]


def sanity_gate(runs: list[dict], meta: dict) -> None:
    """Assert every valid pick is one of its scenario's 4 option_ids and maps to a
    canonical cluster; cross-check western_options vs cluster-derived western set.
    Report misses; never silently drop."""
    issues = []
    for r in runs:
        if not r.get("valid"):
            continue
        sid, ch = r["scenario_id"], r["chosen_option"]
        m = meta.get(sid)
        if m is None:
            issues.append(f"{r['run_id']}: scenario_id not in meta")
            continue
        if ch not in m["clusters"]:
            issues.append(f"{r['run_id']}: chosen_option {ch!r} not an option_id of {sid}")
            continue
        if m["clusters"][ch] not in CANONICAL:
            issues.append(f"{r['run_id']}: cluster {m['clusters'][ch]!r} not canonical")
    # western_options field vs cluster-derived western set (metadata self-consistency)
    for sid, m in meta.items():
        derived = {oid for oid, c in m["clusters"].items() if c in WESTERN}
        if m["western_options"] and derived != m["western_options"]:
            issues.append(f"{sid}: western_options {sorted(m['western_options'])} != "
                          f"cluster-derived {sorted(derived)}")
    if issues:
        print("SANITY GATE - issues found (not dropped silently):")
        for i in issues:
            print("  -", i)
        sys.exit("Stopping: resolve sanity issues before trusting Metric 1.")
    print(f"SANITY GATE OK: {sum(r.get('valid', False) for r in runs)} valid picks, all "
          "option_ids in-scenario, all clusters canonical, western_options consistent.")


def per_scenario_shares(cell_runs: list[dict], meta: dict) -> dict:
    """scenario_id -> (western_picks, valid_picks, share, baseline). Only valid runs."""
    by_scn = defaultdict(list)
    for r in cell_runs:
        if r.get("valid"):
            by_scn[r["scenario_id"]].append(r["chosen_option"])
    out = {}
    for sid, picks in by_scn.items():
        wp = sum(1 for ch in picks if meta[sid]["clusters"][ch] in WESTERN)
        out[sid] = (wp, len(picks), wp / len(picks), meta[sid]["n_western"] / 4)
    return out


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def metric1(runs: list[dict], meta: dict) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    # index runs by (short, language)
    cells = defaultdict(list)
    for r in runs:
        cells[(model_short(r["run_id"]), r["language"])].append(r)

    results = {}   # (short, lang) -> dict of metrics
    for short, _role in MODELS:
        for lang in LANGS:
            shares = per_scenario_shares(cells[(short, lang)], meta)
            full = [v[2] for v in shares.values()]
            std = [v[2] for sid, v in shares.items() if not meta[sid]["reduced"]]
            base_full = [v[3] for v in shares.values()]
            results[(short, lang)] = {
                "western_share_full": mean(full),
                "western_share_standard": mean(std),
                "n_valid": sum(v[1] for v in shares.values()),
                "n_scenarios_full": len(full),
                "n_scenarios_standard": len(std),
                "chance_baseline_mean": mean(base_full),
                "shares": shares,
            }

    # shift vs English (per model), based on western_share_full
    rows_csv = []
    for short, role in MODELS:
        en_full = results[(short, "en")]["western_share_full"]
        for lang in LANGS:
            R = results[(short, lang)]
            R["shift_vs_en"] = R["western_share_full"] - en_full
            rows_csv.append({
                "model": short, "role": role, "language": lang,
                "western_share_full": round(R["western_share_full"], 4),
                "western_share_standard": round(R["western_share_standard"], 4),
                "n_valid": R["n_valid"],
                "chance_baseline_mean": round(R["chance_baseline_mean"], 4),
                "shift_vs_en": round(R["shift_vs_en"], 4),
            })

    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["model", "role", "language",
            "western_share_full", "western_share_standard", "n_valid",
            "chance_baseline_mean", "shift_vs_en"])
        w.writeheader()
        w.writerows(rows_csv)
    print(f"\nwrote {OUT_CSV.relative_to(ROOT)}")

    # 3x3 table of western_share_full (+ standard in parentheses)
    print("\n=== Metric 1 - Western-cluster share (mean of per-scenario shares) ===")
    print("  cells: full 39  (standard 35)   shift vs en in brackets")
    print(f"  chance baseline (mean Western options/4): "
          f"{results[('qwen2572b','en')]['chance_baseline_mean']:.3f}")
    print(f"\n  {'model':10} {'en':>18} {'id':>18} {'bn':>18}")
    for short, role in MODELS:
        cellstrs = []
        for lang in LANGS:
            R = results[(short, lang)]
            cellstrs.append(f"{R['western_share_full']:.3f}({R['western_share_standard']:.3f})"
                            f"[{R['shift_vs_en']:+.3f}]")
        print(f"  {role:10} " + " ".join(f"{c:>18}" for c in cellstrs))

    # hand-check cell: reasoning x bn (the headline model), full per-scenario list
    hc = ("qwen3think", "bn")
    R = results[hc]
    print(f"\n=== HAND-CHECK cell {hc[0]} x {hc[1]} - per-scenario Western shares ===")
    print("  (proves per-scenario denominator + mean-of-shares aggregation)")
    print(f"  {'scenario':10} {'western/valid':>13} {'share':>7} {'baseline':>9} {'reduced'}")
    pooled_w = pooled_v = 0
    for sid in sorted(R["shares"]):
        wp, vp, sh, base = R["shares"][sid]
        pooled_w += wp; pooled_v += vp
        tag = "  <reduced>" if meta[sid]["reduced"] else ""
        print(f"  {sid:10} {f'{wp}/{vp}':>13} {sh:>7.3f} {base:>9.3f}{tag}")
    print(f"\n  MEAN-OF-SHARES (full)      = {R['western_share_full']:.4f}   <- reported (Metric 1)")
    print(f"    (= mean of the {R['n_scenarios_full']} per-scenario 'share' values above)")
    print(f"  POOLED ratio (all picks)   = {pooled_w}/{pooled_v} = {pooled_w/pooled_v:.4f}")
    print("  NOTE: these two COINCIDE here only because every scenario has an equal,")
    print("        complete 3/3 valid picks (0 invalid grid-wide) -> uniform weights.")
    print("        The code computes mean-of-shares (per sec 6); with any invalid runs")
    print("        (unequal per-scenario denominators) it would diverge from the pooled ratio.")
    print(f"  mean-of-shares (standard 35)= {R['western_share_standard']:.4f}  "
          "(drops the 4 reduced items)")


M2_CSV = ROOT / "analysis" / "metrics_m2.csv"


def modal_pick(picks: list[str]) -> str:
    """Most common pick; ties broken deterministically by option_id (A<B<C<D)."""
    from collections import Counter
    c = Counter(picks)
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def scenario_picks(cell_runs: list[dict]) -> dict:
    """scenario_id -> [picks ordered by repeat_index] (valid runs only)."""
    by_scn = defaultdict(dict)
    for r in cell_runs:
        if r.get("valid"):
            by_scn[r["scenario_id"]][r["repeat_index"]] = r["chosen_option"]
    return {sid: [d[k] for k in sorted(d)] for sid, d in by_scn.items()}


def metric2(runs: list[dict], meta: dict) -> None:
    from collections import Counter
    M2_CSV.parent.mkdir(parents=True, exist_ok=True)
    cells = defaultdict(list)
    for r in runs:
        cells[(model_short(r["run_id"]), r["language"])].append(r)

    # precompute per-cell scenario picks + modal picks
    picks = {(s, lg): scenario_picks(cells[(s, lg)]) for s, _ in MODELS for lg in LANGS}
    modal = {k: {sid: modal_pick(p) for sid, p in v.items()} for k, v in picks.items()}

    rows_csv = []
    for short, role in MODELS:
        for lang in LANGS:
            cell = cells[(short, lang)]
            total = len(cell)
            invalid = sum(1 for r in cell if not r.get("valid"))
            sp = picks[(short, lang)]
            self_c = mean([max(Counter(p).values()) / 3 for p in sp.values()])
            ties = sum(1 for p in sp.values() if max(Counter(p).values()) == 1)
            # cross-language consistency vs en (same model)
            en_modal = modal[(short, "en")]
            shared = [sid for sid in modal[(short, lang)] if sid in en_modal]
            xling = mean([1.0 if modal[(short, lang)][sid] == en_modal[sid] else 0.0
                          for sid in shared])
            rows_csv.append({
                "model": short, "role": role, "language": lang,
                "invalid_rate": round(invalid / total, 4),
                "self_consistency": round(self_c, 4),
                "xling_consistency_vs_en": round(xling, 4),
                "n_scenarios_tied": ties,
            })

    with M2_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["model", "role", "language", "invalid_rate",
            "self_consistency", "xling_consistency_vs_en", "n_scenarios_tied"])
        w.writeheader(); w.writerows(rows_csv)
    print(f"\nwrote {M2_CSV.relative_to(ROOT)}")

    print("\n=== Metric 2 - reliability degradation ===")
    print("  self_consistency = mean over 39 scenarios of (max repeat-agreement / 3), range 0.33-1.0")
    print("  xling = fraction of scenarios whose modal pick equals the English modal pick (same model)")
    print(f"\n  {'model':10} {'lang':4} {'invalid':>8} {'self_consist':>13} {'xling_vs_en':>12} {'ties(1-1-1)':>12}")
    for row in rows_csv:
        print(f"  {row['role']:10} {row['language']:4} {row['invalid_rate']:>8.3f} "
              f"{row['self_consistency']:>13.3f} {row['xling_consistency_vs_en']:>12.3f} "
              f"{row['n_scenarios_tied']:>12}")

    # hand-check: reasoning x bn, 3 scenarios' per-repeat picks + modal + contribution
    hc = ("qwen3think", "bn")
    sp = picks[hc]
    sample = sorted(sp)[:3]
    print(f"\n=== HAND-CHECK Metric 2 - {hc[0]} x {hc[1]} (mode/agreement logic) ===")
    print(f"  {'scenario':10} {'(r1,r2,r3)':>16} {'modal':>6} {'agree':>6} {'contribution':>13}")
    for sid in sample:
        p = sp[sid]
        mc = max(Counter(p).values())
        print(f"  {sid:10} {str(tuple(p)):>16} {modal[hc][sid]:>6} {f'{mc}/3':>6} {mc/3:>13.3f}")


M3_CSV = ROOT / "analysis" / "metrics_m3.csv"
# mirror of agent._detect_plan_lang (kept local so analyze.py needs no model SDK).
_ID_MARKERS = (" yang ", " untuk ", " dengan ", " adalah ", " dan ", " keputusan ",
               " anggota ", " berdasarkan ", " tujuan ", " memutuskan ")
_EN_MARKERS = (" the ", " and ", " to ", " decide ", " team ", " option ", " based ",
               " goal ", " which ", " each ")


def _detect_lang(text: str) -> str:
    beng = sum(1 for c in text if 0x0980 <= ord(c) <= 0x09FF)
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    tot = beng + latin
    if tot == 0:
        return "mixed"
    bf = beng / tot
    if bf >= 0.6:
        return "bn"
    if bf > 0.4:
        return "mixed"
    low = " " + text.lower() + " "
    idc = sum(low.count(m) for m in _ID_MARKERS)
    if idc > sum(low.count(m) for m in _EN_MARKERS) and idc >= 2:
        return "id"
    return "en"


def metric3(runs: list[dict], meta: dict) -> None:
    """Metric 3 - plan drift (LaBSE), plan_lang-stratified. Runs where torch +
    sentence-transformers are available (e.g. the unsloth docker). CENTROID PAIRING:
    per (scenario, model), drift = cosine( centroid(3 English plans),
    centroid(non-English plans in the subset) ). Higher cosine = MORE similar = LESS
    drift. Centroid pairing is robust to repeat ordering; per-repeat pairing (mean of
    9 pairwise cosines) is an alternative I do NOT switch to silently - centroid is
    the spec choice and is more stable at n=3."""
    import numpy as np  # noqa: E402
    from sentence_transformers import SentenceTransformer  # noqa: E402

    M3_CSV.parent.mkdir(parents=True, exist_ok=True)
    lm = SentenceTransformer("sentence-transformers/LaBSE")
    ids = [r["run_id"] for r in runs]
    print(f"\n[Metric 3] embedding {len(ids)} plan_texts with LaBSE ...")
    emb = lm.encode([r["plan_text"] or "" for r in runs], normalize_embeddings=True,
                    batch_size=32, show_progress_bar=True)
    E = {rid: emb[i] for i, rid in enumerate(ids)}
    rec = {r["run_id"]: r for r in runs}

    def plan_lang(r):
        return r.get("plan_lang") or _detect_lang(r["plan_text"] or "")

    def centroid(vs):
        return np.mean(np.stack(vs), axis=0)

    def cos(a, b):
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))

    # organize: byc[short][lang][sid] = [records]
    byc = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for r in runs:
        byc[model_short(r["run_id"])][r["language"]][r["scenario_id"]].append(r)

    # modal picks (reuse Metric-2 logic) for the action-change question
    cells = defaultdict(list)
    for r in runs:
        cells[(model_short(r["run_id"]), r["language"])].append(r)
    modal = {k: {sid: modal_pick(p) for sid, p in scenario_picks(v).items()}
             for k, v in cells.items()}

    rows_csv = []
    for short, role in MODELS:
        # en row: no drift (reference); mismatch rate over en runs (~0)
        en_runs = [r for lst in byc[short]["en"].values() for r in lst]
        en_mm = sum(1 for r in en_runs if plan_lang(r) != "en")
        rows_csv.append({"model": short, "role": role, "language": "en",
            "drift_all": "", "n_all": "", "drift_matched": "", "n_matched": "",
            "drift_mismatched": "", "n_mismatched": "",
            "plan_lang_mismatch_rate": round(en_mm / len(en_runs), 4),
            "frac_action_change_with_low_plan_sim": "",
            "n_all_runs": len(en_runs), "n_matched_runs": "", "n_mismatched_runs": ""})

        for lang in ("id", "bn"):
            d_all, d_mat, d_mis = {}, {}, {}
            n_mat_runs = n_mis_runs = n_all_runs = 0
            for sid in byc[short]["en"]:
                en_e = [E[r["run_id"]] for r in byc[short]["en"][sid]]
                non = byc[short][lang].get(sid, [])
                if not en_e or not non:
                    continue
                en_c = centroid(en_e)
                mat = [E[r["run_id"]] for r in non if plan_lang(r) == lang]
                mis = [E[r["run_id"]] for r in non if plan_lang(r) != lang]
                n_all_runs += len(non); n_mat_runs += len(mat); n_mis_runs += len(mis)
                d_all[sid] = cos(en_c, centroid([E[r["run_id"]] for r in non]))
                if mat:
                    d_mat[sid] = cos(en_c, centroid(mat))
                if mis:
                    d_mis[sid] = cos(en_c, centroid(mis))
            # action-change vs low plan similarity (below median drift_all for cell)
            med = float(np.median(list(d_all.values()))) if d_all else float("nan")
            changed = [sid for sid in d_all
                       if modal[(short, lang)].get(sid) != modal[(short, "en")].get(sid)]
            low_and_changed = [sid for sid in changed if d_all[sid] < med]
            frac = (len(low_and_changed) / len(changed)) if changed else float("nan")
            rows_csv.append({"model": short, "role": role, "language": lang,
                "drift_all": round(mean(list(d_all.values())), 4), "n_all": len(d_all),
                "drift_matched": round(mean(list(d_mat.values())), 4) if d_mat else "",
                "n_matched": len(d_mat),
                "drift_mismatched": round(mean(list(d_mis.values())), 4) if d_mis else "",
                "n_mismatched": len(d_mis),
                "plan_lang_mismatch_rate": round(n_mis_runs / n_all_runs, 4),
                "frac_action_change_with_low_plan_sim": round(frac, 4) if changed else "",
                "n_all_runs": n_all_runs, "n_matched_runs": n_mat_runs,
                "n_mismatched_runs": n_mis_runs})

    cols = ["model", "role", "language", "drift_all", "n_all", "drift_matched",
            "n_matched", "drift_mismatched", "n_mismatched", "plan_lang_mismatch_rate",
            "frac_action_change_with_low_plan_sim", "n_all_runs", "n_matched_runs",
            "n_mismatched_runs"]
    with M3_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows_csv)
    print(f"\nwrote {M3_CSV.relative_to(ROOT)}")

    print("\n=== Metric 3 - plan drift (LaBSE cosine; HIGHER = more similar = LESS drift) ===")
    print("  centroid pairing: cos( centroid(3 en plans), centroid(non-en subset) )")
    print("  subsets by RUN-LEVEL plan_lang filter; n in scenarios (n) and runs [runs]")
    print(f"\n  {'model':10} {'lang':4} {'drift_all':>18} {'drift_matched':>20} {'drift_mismatched':>22} {'mm_rate':>8} {'chg&lowsim':>10}")
    for r in rows_csv:
        if r["language"] == "en":
            continue
        da = f"{r['drift_all']}(n{r['n_all']}/[{r['n_all_runs']}])"
        dm = f"{r['drift_matched']}(n{r['n_matched']}/[{r['n_matched_runs']}])"
        dx = f"{r['drift_mismatched']}(n{r['n_mismatched']}/[{r['n_mismatched_runs']}])"
        print(f"  {r['role']:10} {r['language']:4} {da:>18} {dm:>20} {dx:>22} "
              f"{r['plan_lang_mismatch_rate']:>8} {str(r['frac_action_change_with_low_plan_sim']):>10}")
    print("  LOW-n WARNING: any matched cell with small n (e.g. reasoning x bn matched) "
          "is DIRECTIONAL only - do not over-read.")

    # hand-check: reasoning x bn, show the MOST- and LEAST-similar en/bn plan pairs
    short, lang = "qwen3think", "bn"
    dd = {}
    for sid in byc[short]["en"]:
        non = byc[short][lang].get(sid, [])
        if not non:
            continue
        en_c = centroid([E[r["run_id"]] for r in byc[short]["en"][sid]])
        dd[sid] = cos(en_c, centroid([E[r["run_id"]] for r in non]))
    hi = max(dd, key=dd.get); lo = min(dd, key=dd.get)
    print(f"\n=== HAND-CHECK Metric 3 - {short} x {lang} en/bn plan pairs ===")
    for label, sid in (("MOST similar", hi), ("LEAST similar", lo)):
        en_r = byc[short]["en"][sid][0]; bn_r = byc[short][lang][sid][0]
        print(f"\n  [{label}] {sid}: centroid cosine = {dd[sid]:.3f}")
        print(f"    EN plan (r{en_r['repeat_index']}, {en_r['plan_lang']}): {(en_r['plan_text'] or '')[:200]!r}")
        print(f"    BN plan (r{bn_r['repeat_index']}, {bn_r['plan_lang']}): {(bn_r['plan_text'] or '')[:200]!r}")


def main() -> None:
    runs = load_jsonl(RUNS)
    meta = load_meta()
    print(f"loaded {len(runs)} runs, {len(meta)} meta scenarios")
    sanity_gate(runs, meta)
    metric1(runs, meta)
    metric2(runs, meta)
    try:
        metric3(runs, meta)
    except ImportError as e:
        print(f"\nMetric 3 SKIPPED - {e}. Install sentence-transformers (+ torch) and "
              "re-run, e.g. in the unsloth docker:\n  pip install sentence-transformers\n"
              "  python src/analyze.py")
        return
    print("\nMetrics 1, 2, 3 done.")


if __name__ == "__main__":
    main()
