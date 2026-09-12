# CultAct-ML

**Measuring cultural value defaults in multilingual LLM agents that plan and act.**

> Paper: *CultAct-ML: Measuring Cultural Value Defaults in Multilingual LLM Agents Under Action* — accepted at the **ORACLE Workshop @ EMNLP 2026**.
> Repository: <https://github.com/alvi00/CultAct-ML>

When a language-model agent has to *act* in a situation where one culture's values conflict with another's, whose values does it fall back on? CultAct-ML answers this at an intersection prior work has not studied together: **acting** (not just answering), **value conflict**, and **language** — including a low-resource language (Bangla) whose translations a native speaker has verified by hand.

We take **39 value-conflict dilemmas**, recast them from opinion statements into second-person **agent actions**, tag every option with a hidden [GLOBE](https://globeproject.com/) cultural cluster, and run a minimal two-phase (**plan → act**) agent over **English, Indonesian, and Bangla**, across **three models** and **three repeats** — **1,053 plan-and-act decisions**, all valid, no retries.

---

## Models

Three models, served through an OpenAI-compatible gateway at temperature 0.7 with plan/act token budgets of 4,096/6,144, fixed across models and languages.

| CLI flag | Model |
|---|---|
| `--models open` | Qwen2.5-72B |
| `--models frontier` | Kimi K2 |
| `--models reasoning` | Qwen3-235B |

---

## Key findings

| Finding | Summary |
|---|---|
| **A Western default is present, but model-dependent** | Western-cluster actions are chosen above each scenario's own chance baseline (0.468) for Qwen2.5-72B and Kimi K2 in every language, and for Qwen3-235B in English. Qwen3-235B is statistically indistinguishable from chance in Indonesian and Bangla. |
| **The per-language shift is not the story** | No per-language shift is significant at *n*=39 (all 95% bootstrap CIs include zero). The direction differs by model — Qwen2.5-72B drifts *more* Western in Bangla (+0.043), Qwen3-235B *less* (−0.085) — so the reliable signal is model identity, not a language gradient. |
| **A reasoning model abandons the local language at planning** | Qwen3-235B writes its plan in English rather than the scenario language at a rate of **0% → 9.4% → 70.1%** across English/Indonesian/Bangla. Pooled, its Bangla plan drift looks negligible (0.938); on the 35 plans genuinely written in Bangla it falls to 0.838 — a mechanism only a plan-language-stratified analysis reveals. |

**Cultural Default Score (Metric 1), Western share per model × language:**

| Model | EN | ID | BN |
|---|---|---|---|
| Qwen2.5-72B | 0.761 ↑ | 0.838 ↑ | 0.803 ↑ |
| Kimi K2 | 0.761 ↑ | 0.761 ↑ | 0.744 ↑ |
| Qwen3-235B | 0.641 ↑ | 0.581 n.s. | 0.556 n.s. |

↑ = 95% bootstrap CI entirely above the 0.468 chance baseline; n.s. = interval overlaps chance. *n* = 117 runs per cell.

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
│   ├── scenarios_bn.jsonl    # Bangla (native-speaker verified)
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
# 1. Smoke test (45 runs, Qwen2.5-72B only — no --confirm needed)
python src/run_grid.py --pilot

# 2. Full grid, one model at a time (resumable; skips completed runs)
python src/run_grid.py --confirm --models open        # Qwen2.5-72B
python src/run_grid.py --confirm --models frontier    # Kimi K2
python src/run_grid.py --confirm --models reasoning   # Qwen3-235B
#    -> appends to results/runs.jsonl, raw dumps to results/raw/

# 3. Metrics 1 & 2 (no torch); Metric 3 (LaBSE) runs where torch is available
python src/analyze.py
#    -> analysis/metrics_m{1,2,3}.csv, prints the tables + hand-check cells

# 4. Consolidated metrics + the 3 figures
python src/make_figures.py
#    -> analysis/metrics.csv, analysis/figures/*.png
```

`run_grid.py` prints an estimated call count and requires `--confirm` before the full grid. Runs are keyed by `run_id`, so an interrupted grid resumes on re-invocation.

Note on cost: Bangla is split into far more sub-word tokens than English. For Qwen2.5-72B the mean input grows from 693 to 2,471 tokens (3.6×) and mean output from 142 to 688, with per-run latency of 30.0s in Bangla versus 10.9s in English. Budget accordingly.

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

Western set = `{anglo, nordic_europe, germanic_europe}`. Every scenario contains at least one Western and one non-Western option, and option positions are Latin-square rotated (seed 42) so none is favored by placement.

---

## Metrics

- **Metric 1 — Cultural Default Score.** Western share computed **within each scenario** over its own options, then averaged across scenarios (never a single global denominator), reported with 95% bootstrap CIs (*B* = 20,000 resamples over the 39 scenarios).
- **Metric 2 — Reliability.** Invalid rate (0.000 everywhere), self-consistency across repeats (0.786–0.863, against a 1/3 floor), and cross-language consistency of the modal choice versus English (drops to 0.641/0.692/0.615 in Bangla).
- **Metric 3 — Plan drift.** LaBSE cosine between the English and non-English plan centroids, **stratified by the plan's detected language** (matched / mismatched), plus the plan-language mismatch rate.

---

## Translation verification

Every translated option was checked twice: automatically by a multi-model audit, then by a native Bangla speaker. Items were edited only where meaning was actually wrong, leaving pure wording or fluency issues alone. In total 6 of 156 Bangla options (3.8%; 5 meaning, 1 fluency) and 2 of 156 Indonesian options (1.3%) were corrected, and the intended cultural cluster of every option was preserved across all 39 scenarios.

Indonesian is cross-checked by LLMs and a best-effort human pass rather than a native speaker, so Indonesian results should be read with less confidence than the Bangla ones.

---

## Citation

```bibtex
@inproceedings{fahmid2026cultactml,
  title     = {CultAct-ML: Measuring Cultural Value Defaults in Multilingual
               LLM Agents Under Action},
  author    = {Fahmid, Ahmad and Mim, Jannatul Ferdous and Arefeen, Md Adnan},
  booktitle = {Proceedings of the ORACLE Workshop at EMNLP 2026},
  year      = {2026},
  url       = {https://github.com/alvi00/CultAct-ML}
}
```

## License and attribution

- **Code** is released under the MIT License (see `LICENSE`).
- **Scenarios** are *recast* — rewritten, not copied — from the CCD-Bench dilemmas
  (Rahman and Salam, 2025, [arXiv:2510.03553](https://arxiv.org/abs/2510.03553)).
  We release these adaptations with attribution and do **not** redistribute CCD-Bench
  source text; cluster labels follow the GLOBE framework (House et al., 2004).
- The measurement is normative-neutral: "Western" / GLOBE labels are a coarse analytic
  proxy, and results are evidence about **model behavior, not about cultures**.
- CultAct-ML is a diagnostic for surfacing and comparing defaults. It should not be used
  to certify an agent as culturally appropriate for a community, which would call for
  participatory, community-grounded evaluation.
