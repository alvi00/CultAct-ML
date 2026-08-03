# CultAct-ML

**Measuring Western cultural defaults in multilingual LLM agents that plan and act.**

> Paper: *Whose Values? Measuring Western Cultural Defaults in Multilingual LLM Agent Planning and Action* — under review at **REALM @ EMNLP 2026**.
> Repository: <https://github.com/alvi00/CultAct-ML>

When a language-model agent has to *act* in a situation where one culture's values conflict with another's, whose values does it fall back on? CultAct-ML answers this at an intersection prior work has not studied together: **acting** (not just answering), **value conflict**, and **language** — including a low-resource language (Bengali) whose translations a native speaker has verified by hand.

We take **39 value-conflict dilemmas**, recast them from opinion statements into second-person **agent actions**, tag every option with a hidden [GLOBE](https://globeproject.com/) cultural cluster, and run a minimal two-phase (**plan → act**) agent over **English, Indonesian, and Bengali**, across **three model classes** and **three repeats** — **1,053 plan-and-act decisions**, all valid.

---

## Key findings

| Finding | Summary |
|---|---|
| **A Western default is present** | Western-cluster actions are chosen above each scenario's own chance baseline (0.468) for the open and frontier models in every language, and for the reasoning model in English. |
| **It is model-dependent, not a language gradient** | The per-language shift is small and not significant at *n*=39; it even points *down* for the reasoning model, which fades to chance in Indonesian and Bengali. |
| **Reasoning models abandon the local language at planning** | The reasoning model plans in English rather than the scenario language at a rate of **0% → 9.4% → 70.1%** across English/Indonesian/Bengali — a mechanism only a plan-language-stratified drift analysis reveals. |

All numbers are reproducible from `results/runs.jsonl` via `src/analyze.py`.

---

## Repository layout

```
CultAct-ML/
├── src/
│   ├── build_scenarios.py    # Stage 1: recast render / validate / promote
│   ├── translate.py          # Stage 2: MT baseline + LLM refinement
│   ├── qa_checks.py          # Stage 2: structural + LaBSE + LLM-judge QA
│   ├── llm_crosscheck.py     # Stage 2: supplementary multi-model cross-check
│   ├── agent.py              # Stage 3: two-phase plan/act agent (~100 lines)
│   ├── run_grid.py           # Stage 3: resumable, cost-gated grid runner
│   ├── analyze.py            # Stage 4: Metrics 1 (CDS), 2 (reliability), 3 (plan drift)
│   └── make_figures.py       # Stage 4: consolidated metrics.csv + 3 figures
├── configs/run_config.yaml   # single source of truth (models, seeds, ceilings)
├── data/
│   ├── scenarios_en.jsonl    # 39 agent-visible scenarios (English, frozen)
│   ├── scenarios_id.jsonl    # Indonesian (LLM-refined + LLM-cross-checked)
│   ├── scenarios_bn.jsonl    # Bengali (native-speaker verified)
│   └── scenarios_meta.jsonl  # hidden metadata: GLOBE clusters, Western options, tiers
├── results/
│   ├── runs.jsonl            # one line per run (1,053 total)
│   └── raw/                  # verbatim per-run model outputs
└── analysis/
    ├── metrics_m{1,2,3}.csv  # per (model × language) metrics
    ├── metrics.csv           # consolidated
    └── figures/              # the 3 paper figures
```

The agent-visible scenario files contain **no** cultural labels; clusters live only in `scenarios_meta.jsonl`, so the agent never sees them.

---

## Setup

```bash
python -m pip install -r requirements.txt        # Python 3.10+
cp .env.example .env                              # then edit .env
```

Set these in `.env` (never commit it):

| Variable | Used by | Notes |
|---|---|---|
| `CRAFTX_BASE_URL` | agent grid, LLM QA | base URL of any **OpenAI-compatible** chat-completions gateway |
| `CRAFTX_API_KEY`  | agent grid, LLM QA | key for that gateway |
| `GOOGLE_TRANSLATE_API_KEY` | `translate.py` only | Google Cloud Translation v2 (Stage 2 MT); not needed to re-run the grid |

Metric 3 (plan drift, LaBSE) additionally needs `torch` + `sentence-transformers`; run those steps where a GPU/torch is available.

---

## Reproducing the results

The scenarios are frozen, so you can go straight to execution and analysis.

```bash
# 1. Smoke test (45 runs, open model only — no --confirm needed)
python src/run_grid.py --pilot

# 2. Full grid, one model class at a time (resumable; skips completed runs)
python src/run_grid.py --confirm --models open
python src/run_grid.py --confirm --models frontier
python src/run_grid.py --confirm --models reasoning
#    -> appends to results/runs.jsonl, raw dumps to results/raw/

# 3. Metrics 1 & 2 (no torch); Metric 3 (LaBSE) runs where torch is available
python src/analyze.py
#    -> analysis/metrics_m{1,2,3}.csv, prints the tables + hand-check cells

# 4. Consolidated metrics + the 3 figures
python src/make_figures.py
#    -> analysis/metrics.csv, analysis/figures/*.png
```

`run_grid.py` prints an estimated call count and requires `--confirm` before the full grid. Runs are keyed by `run_id`, so an interrupted grid resumes on re-invocation.

---

## Data format

**Agent-visible** (`scenarios_{en,id,bn}.jsonl`):

```json
{"scenario_id": "ca_007", "language": "en",
 "situation": "...", "goal": "...",
 "options": [{"option_id": "A", "text": "..."}],
 "presentation_order": ["A", "B", "C", "D"]}
```

**Hidden metadata** (`scenarios_meta.jsonl`, never shown to the agent):

```json
{"scenario_id": "ca_007", "domain": "Work",
 "option_clusters": {"A": "anglo", "B": "confucian_asia", "C": "middle_east", "D": "nordic_europe"},
 "western_options": ["A", "D"], "distinctness_tier": "standard"}
```

Western set = `{anglo, nordic_europe, germanic_europe}`. Every scenario contains at least one Western and one non-Western option.

---

## Metrics

- **Metric 1 — Cultural Default Score.** Western share computed **within each scenario** over its own options, then averaged across scenarios (never a single global denominator), reported with 95% bootstrap CIs.
- **Metric 2 — Reliability.** Invalid rate, self-consistency across repeats, and cross-language consistency of the modal choice.
- **Metric 3 — Plan drift.** LaBSE cosine between the English and non-English plan centroids, **stratified by the plan's detected language** (matched / mismatched), plus the plan-language mismatch rate.

---

## Citation

```bibtex
@misc{cultactml2026,
  title  = {Whose Values? Measuring Western Cultural Defaults in Multilingual
            LLM Agent Planning and Action},
  author = {<add author name(s)>},
  year   = {2026},
  note   = {Under review at REALM @ EMNLP 2026},
  url    = {https://github.com/alvi00/CultAct-ML}
}
```

## License and attribution

- **Code** is released under the MIT License (add a `LICENSE` file).
- **Scenarios** are *recast* — rewritten, not copied — from the CCD-Bench dilemmas
  (Rahman and Salam, 2025, [arXiv:2510.03553](https://arxiv.org/abs/2510.03553)).
  We release these adaptations with attribution and do **not** redistribute CCD-Bench
  source text; cluster labels follow the GLOBE framework (House et al., 2004).
- The measurement is normative-neutral: "Western" / GLOBE labels are a coarse analytic
  proxy, and results are evidence about **model behavior, not about cultures**.
