# Crosscheck resolutions log

Generated 2026-07-05T19:57:59. Records how each flag from the automated crosscheck was resolved. Scenario files edited: `scenarios_bn.jsonl`, `scenarios_id.jsonl`. `translation_qa_report.md` and `llm_crosscheck_report.md` were NOT modified.

## Applied edits (8)

| # | lang | scenario/opt | source | flagged as | change (current text after) |
|---|---|---|---|---|---|
| 1 | bn | ca_034 C | native-verified | alignment: diverged; fluency: unnatural | 'সমালোচিত'(criticized) → 'একাত্ম'(aligned)<br>→ দলের জন্য এটি যে গর্বের কারণ হবে তা জোর দিয়ে বলে তাকে দৃঢ়ভাবে অংশগ্রহণে উৎসাহিত করুন, যাতে তাকে সমষ্টিগত লক্ষ্যের সঙ্গে একাত্ম করা যায়। |
| 2 | bn | ca_027 D | native-verified | alignment: diverged | reworded to 'through others accepting it' (was 'even when others don't agree')<br>→ অন্যরা তা মেনে নেওয়ার মাধ্যমে সিদ্ধান্তগুলো জ্যেষ্ঠ প্রধানের হাতে কেন্দ্রীভূত করুন, যাতে কর্তৃত্বের স্পষ্ট রেখা বজায় থাকে। |
| 3 | bn | ca_009 B | native-verified | alignment: partial | 'সামঞ্জস্যপূর্ণ'(harmonious) → 'ঐকমত্যমূলক'(consensus)<br>→ একটি পারিবারিক সভার আয়োজন করুন এবং অর্থ বণ্টনের জন্য সুস্পষ্ট ঐকমত্যমূলক নির্দেশিকা নির্ধারণ করুন, একত্রে সিদ্ধান্ত নেওয়ার জন্য। |
| 4 | bn | ca_024 B | native-verified | alignment: partial; fluency: unnatural | 'নির্দেশিকা পরামর্শ করুন'(advise) → 'নির্দেশিকার পরামর্শ নিন'(consult)<br>→ আপনার সংকোচনগুলি প্রকাশ করুন, পরিবারের নির্দেশিকার পরামর্শ নিন এবং নিয়ম মেনে সমাধান আনতে অন্যদের সম্পৃক্ত করুন, যাতে নিয়ম মেনেই এটি সমাধান করা হয়। |
| 5 | bn | ca_012 C | native-verified | fluency: slightly_awkward (meaning caught by hand) | restored 'chain of command' (কর্তৃপক্ষের ধারা); MT had 'step by step'<br>→ প্রথমে নির্দেশ মান্য করুন, তারপর প্রয়োজনীয় বিস্তারিত জানার জন্য আপনার তত্ত্বাবধায়কের সাথে পরামর্শ করুন, যাতে কর্তৃপক্ষের ধারা বজায় রাখার পাশাপাশি স্পষ্টতা পাওয়া যায়। |
| 6 | bn | ca_012 D | native-verified | fluency: slightly_awkward | opening verb 'সম্মতি দিন' → 'মেনে নিন'; 'aligned' rendering (একত্রিত রাখা) kept<br>→ মেনে নিন, তারপর দলের সাথে মিলে উদ্দেশ্যগুলো নির্ধারণ করুন, গোষ্ঠীকে একত্রিত রাখার উদ্দেশ্যে। |
| 7 | id | ca_027 D | GLM-suggested (not native-verified) | alignment: partial; fluency: unnatural | 'menunduk'(physically bow) → 'patuh'(defer/comply)<br>→ Pusatkan pengambilan keputusan pada kepala keluarga senior sementara anggota lainnya patuh, untuk menjaga garis otoritas yang jelas. |
| 8 | id | ca_007 C | GLM-suggested (not native-verified) | fluency: unnatural | 'Alokasikan kemajuan'(allocate progress) → 'Distribusikan tugas'(distribute tasks)<br>→ Distribusikan tugas dan tanggung jawab melalui hierarki yang jelas, untuk menjaga kemajuan yang teratur. |

- Bengali edits (6): all researcher **native-verified** (FIX 1-4 applied to exact supplied strings; FIX 5-6 ca_012 C/D applied by the researcher by hand).
- Indonesian edits (2): **GLM-suggested**, not native-verified - marked as such; these carry weight because Indonesian has no human verification layer.
- ca_012 D: the researcher confirmed 'একত্রিত রাখা' (keep united) is the accepted rendering of 'keep the group aligned'; only the opening verb was changed.
- Explicitly left as-is per researcher instruction: ID ca_007 A and ca_024 A (functional `partial`, judged acceptable).

## Fluency flags: flagged, not applied, native text preserved

- Bengali: 110 `slightly_awkward` + 6 `unnatural` option flags, 15 scene flags. All not-yet-listed above are preserved unchanged - Bengali is native-verified ground truth; these labels are advisory.
- Indonesian: 87 `slightly_awkward` + 2 `unnatural` option flags, 13 scene flags. Only the 2 `unnatural` errors were fixed; `slightly_awkward` paraphrase preferences were preserved.
- Cultural: 0 flags in either language (39/39 `ok`) → no cultural edits.

## ca_019 (Bengali) - previously unjudged

ca_019 BN fluency hit transient GLM gateway failures during the main batch (recorded `unjudged`). Re-judged in isolation (GLM 5.2 echo verified) → `data/ca_019_fluency_supplement.md`: options A/B/C `slightly_awkward`, D `natural`, scene `slightly_awkward`. All advisory; no edit applied. The main report was left unchanged.
