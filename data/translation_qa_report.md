# Translation QA report - Stage 2 Step 3

Generated 2026-07-05T05:08:34. LaBSE flag threshold < 0.7. Refiner-under-test = Qwen3 235B. Judge = CraftX Llama 3.3 70B Instruct. Back-translation = Google Translate.

> Measure-and-flag only; the QA suite edited no scenario. A flag means "look here," not "wrong." Round-trip is noisy and does not trigger flags on its own.
> NOTE: forward MT was Google and back-translation is also Google, so the round-trip shares an engine on unchanged spans; the target is Qwen3-REFINED though, so it is not pure self-consistency. Treat round-trip as the weaker signal.
> POST-REPORT: after review, one flag (ca_010 D, Bengali) was hand-approved and corrected in scenarios_bn.jsonl; see "Resolutions" below. The two ca_003 D flags were reviewed and dismissed as false positives.

## CHECK 1 - structural integrity
- **Bengali**: 39/39 pass, 0 fail.
- **Indonesian**: 39/39 pass, 0 fail.
- metadata: scenarios_meta.jsonl covers 39 scenario_ids (clusters/western_options live there, one shared copy per scenario - untouched by translation).

## Flagged options (worst-first)

### Bengali flags (2 of 156) - researcher hand-verifies

| scenario_id | opt | source EN | target | back-translated EN | LaBSE | round-trip | functional | cultural | judge reason |
|---|---|---|---|---|---|---|---|---|---|
| ca_010 | D | Let the most senior member make the final call after discussion, to prioritize the household's present needs. | আলোচনার পর পরিবারের বর্তমান চাহিদাগুলোকে অগ্রাধিকার দেওয়ার উদ্দেশ্যে সর্বকনিষ্ঠ সদস্য ছাড়া সবচেয়ে বয়োজ্যেষ্ঠ সদস্যকে চূড়ান্ত সিদ্ধান্ত নিতে দিন। | After discussion, let the oldest member, except the youngest, make the final decision in order to prioritize the current needs of the family. | 0.716 | 0.780 | diverged | ok | Translation mentions 'সর্বকনিষ্ঠ সদস্য' (youngest member) instead of 'সবচেয়ে বয়োজ্যেষ্ঠ সদস্য' (most senior member) — **[FIXED, see Resolutions]** |
| ca_003 | D | Rally the close-knit team to push hard together and put in extra hours, to deliver as one. | একতাবদ্ধ দলকে একসাথে কঠোর পরিশ্রম করে অতিরিক্ত সময় দেওয়ার জন্য উদ্বুদ্ধ করুন, একত্রে সাফল্য অর্জনের জন্য। | Motivate a cohesive team to work hard together and put in extra time, to achieve success together. | 0.674 | 0.749 | same | ok | effectively translates the notion of rallying the team to work together and put in extra hours — **[false positive, kept]** |

### Indonesian flags (1 of 156) - NOT native-verified; every partial/diverged/awkward/off-target surfaced regardless of similarity

| scenario_id | opt | source EN | target | back-translated EN | LaBSE | round-trip | functional | cultural | judge reason |
|---|---|---|---|---|---|---|---|---|---|
| ca_003 | D | Rally the close-knit team to push hard together and put in extra hours, to deliver as one. | Ajak tim yang solid untuk bekerja keras bersama dan menambah jam kerja, agar menyelesaikannya sebagai satu kesatuan. | Invite a solid team to work hard together and increase working hours, to complete it as one unit. | 0.675 | 0.765 | same | ok | Rallying the team to work together to deliver as one unit maintains the same action semantics — **[false positive, kept]** |

## Per-language summary

### Bengali
- LaBSE: mean 0.815, min 0.674, < 0.7: 1
- round-trip: mean 0.882, min 0.720
- functional (per option): same=155, partial=0, diverged=1
- cultural (per scenario, counted per option): ok=156, awkward=0, off-target=0

### Indonesian
- LaBSE: mean 0.833, min 0.675, < 0.7: 1
- round-trip: mean 0.919, min 0.754
- functional (per option): same=156, partial=0, diverged=0
- cultural (per scenario, counted per option): ok=156, awkward=0, off-target=0

## Resolutions (post-report, researcher-approved)

1. **ca_010 opt D (Bengali) — FIXED.** Qwen3 refinement had inserted "সর্বকনিষ্ঠ সদস্য ছাড়া" (*except the youngest member*), a phrase absent from the English source ("Let the most senior member make the final call"). The Llama-3.3-70B judge caught it as `diverged`; Google back-translation confirmed. Corrected by deleting only that clause; the rest of the option is byte-identical.
   - before: …অগ্রাধিকার দেওয়ার উদ্দেশ্যে **সর্বকনিষ্ঠ সদস্য ছাড়া** সবচেয়ে বয়োজ্যেষ্ঠ সদস্যকে চূড়ান্ত সিদ্ধান্ত নিতে দিন।
   - after: …অগ্রাধিকার দেওয়ার উদ্দেশ্যে সবচেয়ে বয়োজ্যেষ্ঠ সদস্যকে চূড়ান্ত সিদ্ধান্ত নিতে দিন।
   - post-fix re-verify: CHECK 1 structural 39/39 pass (bn), UTF-8 clean (no U+FFFD), Bengali codepoints present, 4 options A–D in order.

2. **ca_003 opt D (Bengali) — kept, false positive.** Judge `same`/`ok`; LaBSE 0.674 only because "deliver as one" was rendered as natural "achieve success together." Meaning preserved.

3. **ca_003 opt D (Indonesian) — kept, false positive.** Judge `same`/`ok`; LaBSE 0.675, same natural-vocabulary reason. Meaning preserved.
