# Translation QA report - Stage 2 Step 3

Generated 2026-07-05T04:57:35. LaBSE flag threshold < 0.7. Refiner-under-test = Qwen3 235B. Judge = CraftX Llama 3.3 70B Instruct. Back-translation = Google Translate.

> Measure-and-flag only; no scenario was edited. A flag means "look here," not "wrong." Round-trip is noisy and does not trigger flags on its own.
> NOTE: forward MT was Google and back-translation is also Google, so the round-trip shares an engine on unchanged spans; the target is Qwen3-REFINED though, so it is not pure self-consistency. Treat round-trip as the weaker signal.

## CHECK 1 - structural integrity
- **Bengali**: 3/3 pass, 0 fail.
- **Indonesian**: 3/3 pass, 0 fail.
- metadata: scenarios_meta.jsonl covers 39 scenario_ids (clusters/western_options live there, one shared copy per scenario - untouched by translation).

## Flagged options (worst-first)

### Bengali flags (1 of 12) - researcher hand-verifies

| scenario_id | opt | source EN | target | back-translated EN | LaBSE | round-trip | functional | cultural | judge reason |
|---|---|---|---|---|---|---|---|---|---|
| ca_003 | D | Rally the close-knit team to push hard together and put in extra hours, to deliver as one. | একতাবদ্ধ দলকে একসাথে কঠোর পরিশ্রম করে অতিরিক্ত সময় দেওয়ার জন্য উদ্বুদ্ধ করুন, একত্রে সাফল্য অর্জনের জন্য। | Motivate a cohesive team to work hard together and put in extra time, to achieve success together. | 0.674 | 0.749 | same | ok | effectively translates the idea of rallying the team to work together and put in extra hours |

### Indonesian flags (1 of 12) - NOT native-verified; every partial/diverged/awkward/off-target surfaced regardless of similarity

| scenario_id | opt | source EN | target | back-translated EN | LaBSE | round-trip | functional | cultural | judge reason |
|---|---|---|---|---|---|---|---|---|---|
| ca_003 | D | Rally the close-knit team to push hard together and put in extra hours, to deliver as one. | Ajak tim yang solid untuk bekerja keras bersama dan menambah jam kerja, agar menyelesaikannya sebagai satu kesatuan. | Invite a solid team to work hard together and increase working hours, to complete it as one unit. | 0.675 | 0.765 | same | ok | Action and intent of rallying the team to work hard together to deliver as one is preserved |

## Per-language summary

### Bengali
- LaBSE: mean 0.815, min 0.674, < 0.7: 1
- round-trip: mean 0.881, min 0.749
- functional (per option): same=12, partial=0, diverged=0
- cultural (per scenario, counted per option): ok=12, awkward=0, off-target=0

### Indonesian
- LaBSE: mean 0.824, min 0.675, < 0.7: 1
- round-trip: mean 0.917, min 0.765
- functional (per option): same=12, partial=0, diverged=0
- cultural (per scenario, counted per option): ok=12, awkward=0, off-target=0

