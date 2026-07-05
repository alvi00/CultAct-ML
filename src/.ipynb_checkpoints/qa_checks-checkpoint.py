#!/usr/bin/env python3
"""Stage 2, Step 3 - automated translation QA suite for CultAct-ML.

MEASURE AND FLAG ONLY. This never fixes, drops, or edits any scenario - the
fix/drop decisions are the researcher's (Bengali is hand-verified). See PROJECT.md
Section 6, Stage 2 (checks 2.3 + 2.6).

Reads   data/scenarios_en.jsonl, scenarios_bn.jsonl, scenarios_id.jsonl
Writes  data/translation_qa_report.md   (worst-first review surface)
Logs    data/qa_checks.log

Checks
------
1. Structural integrity - valid JSON, schema == en, exactly 4 options,
   scenario_id/option_id/presentation_order match en row-for-row, metadata
   (scenarios_meta.jsonl, shared across languages) intact. (no dependencies)
2. Semantic similarity per option, two signals:
   - PRIMARY  LaBSE cross-lingual cosine (sentence-transformers/LaBSE): embed the
     EN option and target option directly in LaBSE's shared space. Needs torch.
   - SECONDARY round-trip: back-translate target->EN with Google Translate
     (official API if GOOGLE_TRANSLATE_API_KEY is set, else deep-translator's
     keyless GoogleTranslator), then cosine(source_EN, back-translated_EN).
   Low scores are FLAGS for human attention, not auto-fails.
3. LLM-judge alignment (CraftX Llama 3.3 70B Instruct, != the Qwen3 refiner):
   (a) functional per option: same / partial / diverged
   (b) cultural per scenario: ok / awkward / off-target
   Judge returns structured labels + a one-line reason only.

Usage
-----
  python src/qa_checks.py [--checks 1,2,3] [--langs bn,id] [--limit N]
                          [--judge-model "CraftX Llama 3.3 70B Instruct"]
                          [--labse-threshold 0.70]

Environment: torch (CHECK 2) is expected to be present (e.g. the unsloth docker).
sentence-transformers and, for keyless back-translation, deep-translator are
imported lazily with a clear message if missing.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# reuse the hardened gateway client + .env loader from the Stage-2 translator
sys.path.insert(0, str(Path(__file__).resolve().parent))
from translate import _craftx_chat, _load_dotenv, _parse_refined  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FILES = {"en": ROOT / "data" / "scenarios_en.jsonl",
         "bn": ROOT / "data" / "scenarios_bn.jsonl",
         "id": ROOT / "data" / "scenarios_id.jsonl"}
META = ROOT / "data" / "scenarios_meta.jsonl"
REPORT = ROOT / "data" / "translation_qa_report.md"
LOG = ROOT / "data" / "qa_checks.log"
LANG_NAME = {"bn": "Bengali", "id": "Indonesian"}
GOOGLE_BACK = {"bn": "bn", "id": "id"}
DEFAULT_JUDGE = "CraftX Llama 3.3 70B Instruct"


def log(msg: str) -> None:
    line = f"{datetime.now().isoformat(timespec='seconds')}  {msg}"
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line)


def _load(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()
            if x.strip()]


# ---------------------------------------------------------------------------
# CHECK 1 - structural integrity
# ---------------------------------------------------------------------------
def check1_structural(en: list[dict], targets: dict[str, list[dict]]) -> dict:
    meta_ids = {m["scenario_id"] for m in _load(META)} if META.exists() else set()
    out = {"meta_ids": len(meta_ids), "langs": {}}
    for lang, rows in targets.items():
        failures = []
        if len(rows) != len(en):
            failures.append((None, f"row count {len(rows)} != en {len(en)}"))
        for e, t in zip(en, rows):
            f = []
            if set(t.keys()) != set(e.keys()):
                f.append(f"schema keys differ: {sorted(set(t)^set(e.keys()))}")
            if len(t.get("options", [])) != 4:
                f.append(f"{len(t.get('options', []))} options (need 4)")
            if t.get("scenario_id") != e["scenario_id"]:
                f.append(f"scenario_id {t.get('scenario_id')} != {e['scenario_id']}")
            if [o.get("option_id") for o in t.get("options", [])] != \
               [o["option_id"] for o in e["options"]]:
                f.append("option_id set/order differs")
            if t.get("presentation_order") != e.get("presentation_order"):
                f.append("presentation_order differs")
            if t.get("language") != lang:
                f.append(f"language {t.get('language')} != {lang}")
            if e["scenario_id"] not in meta_ids:
                f.append("scenario_id absent from scenarios_meta.jsonl")
            if f:
                failures.append((e["scenario_id"], "; ".join(f)))
        out["langs"][lang] = {"n": len(rows), "pass": len(rows) - len(failures),
                              "fail": len(failures), "failures": failures}
    return out


# ---------------------------------------------------------------------------
# CHECK 2 - semantic similarity (LaBSE direct + Google round-trip)
# ---------------------------------------------------------------------------
def _back_translate(texts: list[str], source: str) -> list[str]:
    """target(source lang) -> English. Official Google API if a key is set,
    else deep-translator's keyless GoogleTranslator."""
    key = os.environ.get("GOOGLE_TRANSLATE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        out: list[str] = []
        for i in range(0, len(texts), 100):
            chunk = texts[i:i + 100]
            body = json.dumps({"q": chunk, "source": source, "target": "en",
                               "format": "text"}).encode("utf-8")
            req = urllib.request.Request(
                "https://translation.googleapis.com/language/translate/v2?key=" + key,
                data=body, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    payload = json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                sys.exit(f"Google back-translate HTTP {e.code}: "
                         f"{e.read().decode('utf-8', 'replace')[:300]}")
            out.extend(t["translatedText"] for t in payload["data"]["translations"])
        return out
    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        sys.exit("CHECK 2 back-translation needs deep-translator "
                 "(pip install deep-translator) or a GOOGLE_TRANSLATE_API_KEY.")
    gt = GoogleTranslator(source=source, target="en")
    return [gt.translate(t) for t in texts]


def check2_similarity(en: list[dict], targets: dict[str, list[dict]]) -> dict:
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except ImportError:
        sys.exit("CHECK 2 needs sentence-transformers + torch "
                 "(pip install sentence-transformers; run where torch is present).")
    log("CHECK 2: loading sentence-transformers/LaBSE (downloads ~1.8GB first time)")
    model = SentenceTransformer("sentence-transformers/LaBSE")
    scores: dict = {}
    for lang, rows in targets.items():
        keys, en_txt, tgt_txt = [], [], []
        for e, t in zip(en, rows):
            for oe, ot in zip(e["options"], t["options"]):
                keys.append((e["scenario_id"], oe["option_id"]))
                en_txt.append(oe["text"])
                tgt_txt.append(ot["text"])
        log(f"[{lang}] back-translating {len(tgt_txt)} options -> EN (Google)")
        back_txt = _back_translate(tgt_txt, GOOGLE_BACK[lang])
        log(f"[{lang}] embedding {len(en_txt)} triples in LaBSE")
        e_en = model.encode(en_txt, normalize_embeddings=True, batch_size=32)
        e_tg = model.encode(tgt_txt, normalize_embeddings=True, batch_size=32)
        e_bk = model.encode(back_txt, normalize_embeddings=True, batch_size=32)
        for i, k in enumerate(keys):
            scores[(lang, *k)] = {
                "labse": float(np.dot(e_en[i], e_tg[i])),
                "roundtrip": float(np.dot(e_en[i], e_bk[i])),
                "back": back_txt[i]}
    return scores


# ---------------------------------------------------------------------------
# CHECK 3 - LLM-judge alignment
# ---------------------------------------------------------------------------
_JUDGE_SYS = (
    "You are a bilingual translation QA judge for {lang}. You compare an English "
    "source scenario with its {lang} translation. You do NOT rewrite anything - you "
    "only LABEL.\n\n"
    "For EACH option, judge FUNCTIONAL alignment - does the {lang} keep the SAME "
    "action semantics (the concrete action AND its trailing purpose) as the "
    "English?\n"
    "  same     = same action and intent\n"
    "  partial  = mostly right but a nuance/purpose is shifted or weakened\n"
    "  diverged = the action or its meaning changed\n\n"
    "For the SCENARIO as a whole, judge CULTURAL alignment - does it read as "
    "sensible, on-target {lang} for that locale?\n"
    "  ok         = natural and sensible\n"
    "  awkward    = understandable but stiff/unnatural\n"
    "  off-target = nonsensical, mistranslated, or culturally wrong\n\n"
    "Return ONLY JSON, no prose, no markdown fences, one-line reasons."
)
_JUDGE_USER = (
    "{payload}\n\n"
    "Return ONLY:\n"
    '{{"scenario_id":"<same>","cultural":"ok|awkward|off-target",'
    '"cultural_reason":"<one line>","options":[{{"option_id":"A",'
    '"functional":"same|partial|diverged","reason":"<one line>"}},'
    '{{"option_id":"B","functional":"...","reason":"..."}},'
    '{{"option_id":"C","functional":"...","reason":"..."}},'
    '{{"option_id":"D","functional":"...","reason":"..."}}]}}'
)
_FUNC = {"same", "partial", "diverged"}
_CULT = {"ok", "awkward", "off-target"}


def _judge_one(e: dict, t: dict, lang: str, model: str) -> dict:
    payload = {
        "scenario_id": e["scenario_id"],
        "english": {"situation": e["situation"], "goal": e["goal"],
                    "options": e["options"]},
        "target": {"language": LANG_NAME[lang], "situation": t["situation"],
                   "goal": t["goal"], "options": t["options"]},
    }
    messages = [
        {"role": "system", "content": _JUDGE_SYS.format(lang=LANG_NAME[lang])},
        {"role": "user", "content": _JUDGE_USER.format(
            payload=json.dumps(payload, ensure_ascii=False, indent=2))},
    ]
    msg = ""
    for attempt in range(1, 4):
        try:
            j = _parse_refined(_craftx_chat(messages, model, temperature=0.0,
                                            max_tokens=700))
            oids = [o.get("option_id") for o in j.get("options", [])]
            if (j.get("cultural") in _CULT and len(j.get("options", [])) == 4
                    and oids == [o["option_id"] for o in e["options"]]
                    and all(o.get("functional") in _FUNC for o in j["options"])):
                return j
            msg = f"bad labels/shape: {str(j)[:120]}"
        except (json.JSONDecodeError, KeyError, TypeError, RuntimeError) as ex:
            msg = f"{ex}"
        log(f"[{lang}] {e['scenario_id']} judge attempt {attempt} bad: {msg}")
    sys.exit(f"FAIL {lang} {e['scenario_id']}: judge invalid after 3 tries ({msg}).")


def check3_judge(en: list[dict], targets: dict[str, list[dict]], model: str) -> dict:
    try:
        ping = _craftx_chat([{"role": "user", "content": "Reply with exactly: OK"}],
                            model, temperature=0.0, max_tokens=5)
    except RuntimeError as e:
        sys.exit(f"Judge preflight failed (check CRAFTX creds / model id): {e}")
    log(f"CHECK 3 preflight OK: judge {model!r} replied {ping.strip()[:20]!r}")
    res: dict = {}
    for lang, rows in targets.items():
        for i, (e, t) in enumerate(zip(en, rows), 1):
            res[(lang, e["scenario_id"])] = _judge_one(e, t, lang, model)
            if i % 5 == 0 or i == len(rows):
                log(f"[{lang}] judged {i}/{len(rows)}")
    return res


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def _esc(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


def build_report(en, targets, struct, sim, judge, checks, threshold, judge_model):
    en_by = {e["scenario_id"]: e for e in en}
    lines = ["# Translation QA report - Stage 2 Step 3", "",
             f"Generated {datetime.now().isoformat(timespec='seconds')}. "
             f"LaBSE flag threshold < {threshold}. Refiner-under-test = Qwen3 235B. "
             f"Judge = {judge_model}. Back-translation = Google Translate.", ""]
    lines.append("> Measure-and-flag only; no scenario was edited. A flag means "
                 "\"look here,\" not \"wrong.\" Round-trip is noisy and does not "
                 "trigger flags on its own.")
    lines.append("> NOTE: forward MT was Google and back-translation is also "
                 "Google, so the round-trip shares an engine on unchanged spans; "
                 "the target is Qwen3-REFINED though, so it is not pure "
                 "self-consistency. Treat round-trip as the weaker signal.")
    lines.append("")

    # ---- CHECK 1 summary ----
    lines.append("## CHECK 1 - structural integrity")
    if struct:
        for lang, s in struct["langs"].items():
            lines.append(f"- **{LANG_NAME[lang]}**: {s['pass']}/{s['n']} pass, "
                         f"{s['fail']} fail.")
            for sid, why in s["failures"]:
                lines.append(f"    - FAIL {sid}: {why}")
        lines.append(f"- metadata: scenarios_meta.jsonl covers "
                     f"{struct['meta_ids']} scenario_ids (clusters/western_options "
                     f"live there, one shared copy per scenario - untouched by "
                     f"translation).")
    else:
        lines.append("- (not run)")
    lines.append("")

    # ---- assemble per-option rows for checks 2/3 ----
    rows = []  # dicts with all fields
    for lang, tgt in targets.items():
        tgt_by = {t["scenario_id"]: t for t in tgt}
        for e in en:
            sid = e["scenario_id"]
            if sid not in tgt_by:
                continue
            jc = judge.get((lang, sid), {}) if judge else {}
            func_map = {o["option_id"]: o for o in jc.get("options", [])}
            for oe, ot in zip(e["options"], tgt_by[sid]["options"]):
                oid = oe["option_id"]
                sc = sim.get((lang, sid, oid), {}) if sim else {}
                fj = func_map.get(oid, {})
                rows.append({
                    "lang": lang, "sid": sid, "oid": oid,
                    "en": oe["text"], "tgt": ot["text"], "back": sc.get("back", ""),
                    "labse": sc.get("labse"), "rt": sc.get("roundtrip"),
                    "functional": fj.get("functional"),
                    "cultural": jc.get("cultural"),
                    "reason": fj.get("reason") or jc.get("cultural_reason", ""),
                })

    def flagged(r):
        if r["labse"] is not None and r["labse"] < threshold:
            return True
        if r["functional"] and r["functional"] != "same":
            return True
        if r["cultural"] and r["cultural"] != "ok":
            return True
        return False

    def severity(r):  # lower = worse (sorts first)
        base = r["labse"] if r["labse"] is not None else 1.0
        pen = {"diverged": 0.5, "partial": 0.25}.get(r["functional"], 0.0)
        pen += {"off-target": 0.5, "awkward": 0.25}.get(r["cultural"], 0.0)
        return base - pen

    hdr = ("| scenario_id | opt | source EN | target | back-translated EN | LaBSE "
           "| round-trip | functional | cultural | judge reason |")
    sep = "|---|---|---|---|---|---|---|---|---|---|"

    def table(rs):
        out = [hdr, sep]
        for r in rs:
            out.append("| {sid} | {oid} | {en} | {tgt} | {back} | {labse} | {rt} "
                       "| {func} | {cult} | {reason} |".format(
                           sid=r["sid"], oid=r["oid"], en=_esc(r["en"]),
                           tgt=_esc(r["tgt"]), back=_esc(r["back"]),
                           labse=f"{r['labse']:.3f}" if r["labse"] is not None else "-",
                           rt=f"{r['rt']:.3f}" if r["rt"] is not None else "-",
                           func=r["functional"] or "-", cult=r["cultural"] or "-",
                           reason=_esc(r["reason"])))
        return out

    lines.append("## Flagged options (worst-first)")
    lines.append("")
    for lang in targets:
        lang_rows = [r for r in rows if r["lang"] == lang]
        flags = sorted([r for r in lang_rows if flagged(r)], key=severity)
        title = LANG_NAME[lang]
        note = (" - NOT native-verified; every partial/diverged/awkward/off-target "
                "surfaced regardless of similarity" if lang == "id" else
                " - researcher hand-verifies")
        lines.append(f"### {title} flags ({len(flags)} of {len(lang_rows)})"
                     f"{note}")
        lines.append("")
        lines.extend(table(flags) if flags else ["(none flagged)"])
        lines.append("")

    # ---- per-language summary stats ----
    lines.append("## Per-language summary")
    lines.append("")
    for lang in targets:
        lang_rows = [r for r in rows if r["lang"] == lang]
        labses = [r["labse"] for r in lang_rows if r["labse"] is not None]
        rts = [r["rt"] for r in lang_rows if r["rt"] is not None]
        from collections import Counter
        fc = Counter(r["functional"] for r in lang_rows if r["functional"])
        cc = Counter(r["cultural"] for r in lang_rows if r["cultural"])
        lines.append(f"### {LANG_NAME[lang]}")
        if labses:
            lines.append(f"- LaBSE: mean {sum(labses)/len(labses):.3f}, "
                         f"min {min(labses):.3f}, "
                         f"< {threshold}: {sum(1 for x in labses if x < threshold)}")
        if rts:
            lines.append(f"- round-trip: mean {sum(rts)/len(rts):.3f}, "
                         f"min {min(rts):.3f}")
        if fc:
            lines.append(f"- functional (per option): " + ", ".join(
                f"{k}={fc.get(k, 0)}" for k in ("same", "partial", "diverged")))
        if cc:
            lines.append(f"- cultural (per scenario, counted per option): " +
                         ", ".join(f"{k}={cc.get(k, 0)}" for k in
                                   ("ok", "awkward", "off-target")))
        lines.append("")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote report -> {REPORT}")
    return rows, {lang: sorted([r for r in rows if r["lang"] == lang and flagged(r)],
                               key=severity) for lang in targets}


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="CultAct-ML Stage 2 Step 3 (QA).")
    ap.add_argument("--checks", default="1,2,3", help="comma subset of 1,2,3")
    ap.add_argument("--langs", default="bn,id")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--judge-model", default=os.environ.get("CRAFTX_JUDGE_MODEL",
                                                            DEFAULT_JUDGE))
    ap.add_argument("--labse-threshold", type=float, default=0.70)
    args = ap.parse_args()
    _load_dotenv()

    which = set(args.checks.replace(" ", "").split(","))
    langs = tuple(args.langs.split(","))
    en = _load(FILES["en"])
    targets = {l: _load(FILES[l]) for l in langs}
    if args.limit:
        en = en[:args.limit]
        targets = {l: r[:args.limit] for l, r in targets.items()}
    log(f"=== qa_checks checks={sorted(which)} langs={','.join(langs)} "
        f"scenarios={len(en)} ===")

    struct = check1_structural(en, targets) if "1" in which else None
    sim = check2_similarity(en, targets) if "2" in which else None
    judge = check3_judge(en, targets, args.judge_model) if "3" in which else None
    build_report(en, targets, struct, sim, judge, which,
                 args.labse_threshold, args.judge_model)
    log("=== qa_checks done ===")


if __name__ == "__main__":
    main()
