# Translation verification summary - GAIA-v2-LILT parity

Generated 2026-07-05T19:57:59. Source: automated crosscheck (`llm_crosscheck_report.md`, judge CraftX GLM 5.2) + researcher review. Bengali is human-verified; Indonesian is LLM-cross-checked only.

## 1. Edit-rate table (Table-1 analog)

Edits actually **applied** to the 156 options per language, by category:

| category | Bengali (n, %) | Indonesian (n, %) |
|---|---|---|
| functional / alignment | 5 (3.2%) | 1 (0.6%) |
| cultural | 0 (0.0%) | 0 (0.0%) |
| fluency (applied) | 1 (0.6%) | 1 (0.6%) |
| **total applied** | **6 (3.8%)** | **2 (1.3%)** |

### Fluency flags deliberately NOT applied (native text preserved)

The crosscheck raised many *fluency* flags; the vast majority were left unchanged on purpose (Bengali is the researcher's native-verified ground truth, and Indonesian `slightly_awkward` calls are advisory paraphrase preferences, not errors). Only clear meaning/word errors were edited.

| fluency label (options) | Bengali | Indonesian |
|---|---|---|
| slightly_awkward | 110 | 87 |
| unnatural | 6 | 2 |
| (scene situation+goal awkward) | 15 | 13 |

Of these, only the options edited above were touched (BN: 4 fluency-flagged options among the 6 edits; ID: 2 unnatural options). All remaining fluency flags → **flagged, not applied, native text preserved.** Cultural flags were **0/39** in both languages, so **0 cultural edits**.

## 2. Option-salience / presentation-parity

A no-correct-answer choice task can be biased if, within one scenario, a single option reads markedly more fluently than its siblings (a fluent option may attract choice regardless of its cultural content). Using the per-scenario fluency labels (crosscheck snapshot; the 8 edits only reduce imbalance), each scenario's four options were compared:

| metric | Bengali | Indonesian |
|---|---|---|
| all 4 options same fluency label (parallel) | 9/39 | 9/39 |
| some within-scenario variance | 30/39 | 30/39 |
| one option strictly MORE fluent than the other 3 (salience risk) | 16/39 | 13/39 |
| one option strictly LESS fluent than the other 3 | 6/39 | 8/39 |

Interpretation: the dominant labels are `natural` and `slightly_awkward`; `unnatural` is rare. A 'strictly more fluent' outlier is almost always a lone `natural` option among `slightly_awkward` siblings - a mild, not categorical, salience gap. The applied edits removed the `unnatural` outliers, which are the only cases of a categorical fluency gap between an option and its siblings.

Bengali scenarios with a strictly-more-fluent option: ca_001(D), ca_005(D), ca_006(C), ca_011(B), ca_014(C), ca_015(D), ca_019(D), ca_020(B), ca_021(D), ca_022(A), ca_025(B), ca_027(C), ca_030(C), ca_031(C), ca_032(C), ca_036(C)

Indonesian scenarios with a strictly-more-fluent option: ca_005(D), ca_008(A), ca_014(C), ca_015(D), ca_017(D), ca_018(B), ca_020(B), ca_026(C), ca_032(A), ca_034(B), ca_035(C), ca_038(B), ca_039(C)

## 3. Method mapping to GAIA-v2-LILT

| GAIA-v2-LILT axis | CultAct-ML analog |
|---|---|
| Functional adequacy (House TQA, manual) | CHECK 3 **functional** label (same/partial/diverged) from multi-model LLM judges, plus LaBSE cross-lingual cosine and Google round-trip as quantitative signals |
| Cultural adequacy | CHECK 3 **cultural** label (ok/awkward/off-target) per scenario |
| Difficulty calibration | **Option-salience / presentation-parity** (§2) - the fit-for-purpose analog for a no-correct-answer choice task |

We substituted **LaBSE + Google round-trip + multi-model LLM judges** (CraftX GLM 5.2 for this pass; Llama 3.3 70B for the earlier CHECK 3) for House's manual Translation Quality Assessment. **Bengali is human (native-speaker) verified**; **Indonesian is LLM-cross-checked only** - a limitation stated honestly per language. This subsection is a drop-in for the paper's translation-QA description.
