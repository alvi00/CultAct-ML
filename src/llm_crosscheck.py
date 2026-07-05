#!/usr/bin/env python3
"""Stage 2 - SUPPLEMENTARY LLM cross-check (simulated native fluency + GAIA-style
alignment audit). See PROJECT.md Section 6, Stage 2 point 6.

This is a SECONDARY automated flagging layer only. It is NOT the human native
verification (Bengali is already hand-verified and stands as the paper's quality
claim). It FLAGS; it fixes or drops nothing and edits no scenario file.

Read-only inputs : data/scenarios_en.jsonl, scenarios_bn.jsonl, scenarios_id.jsonl
Write target ONLY: data/llm_crosscheck_report.md  (+ data/llm_crosscheck.log)
It never writes to translation_qa_report.md or any scenarios_*.jsonl.

Judge: CraftX GLM 5.2 via the OpenAI-compatible gateway (CRAFTX_BASE_URL /
CRAFTX_API_KEY from env, never hardcoded). After the first call the model string
the API actually returned is printed and checked; if it is not GLM 5.2 the run
STOPS (a judge silently fell back to another model once before).

Two passes:
  PASS 1  monolingual fluency  - target text only, "read as a native speaker".
  PASS 2  cross-lingual align  - English + target, functional + cultural (step 6).

Stdlib only (urllib); nothing torch/heavy to install. UTF-8 everywhere; pathlib.

Usage:
  python src/llm_crosscheck.py [--langs bn,id] [--passes 1,2] [--limit N]
                               [--model "CraftX GLM 5.2"]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# reuse the tiny .env loader; no other behaviour is imported
sys.path.insert(0, str(Path(__file__).resolve().parent))
from translate import _load_dotenv  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = {
    "en": ROOT / "data" / "scenarios_en.jsonl",
    "bn": ROOT / "data" / "scenarios_bn.jsonl",
    "id": ROOT / "data" / "scenarios_id.jsonl",
}
REPORT = ROOT / "data" / "llm_crosscheck_report.md"
LOG = ROOT / "data" / "llm_crosscheck.log"
LANG_NAME = {"bn": "Bengali", "id": "Indonesian"}
DEFAULT_JUDGE = "CraftX GLM 5.2"

FLUENCY = {"natural", "slightly_awkward", "unnatural"}
FUNCTIONAL = {"same", "partial", "diverged"}
CULTURAL = {"ok", "awkward", "off-target"}


def log(msg: str) -> None:
    line = f"{datetime.now().isoformat(timespec='seconds')}  {msg}"
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line)


# --------------------------------------------------------------------------- #
# CraftX call that returns BOTH the content and the model the API reports back
# --------------------------------------------------------------------------- #
def _craftx_call(messages: list[dict], model: str, temperature: float = 0.2,
                 max_tokens: int = 512, retries: int = 5) -> tuple[str | None, str | None]:
    """POST to the CraftX gateway. Returns (content, returned_model). On definitive
    failure returns (None, None) so the caller can mark items 'unjudged' rather than
    crash. Retries 429/5xx/network/timeout with capped exponential backoff."""
    base = os.environ.get("CRAFTX_BASE_URL")
    key = os.environ.get("CRAFTX_API_KEY")
    if not base or not key:
        sys.exit("Set CRAFTX_BASE_URL and CRAFTX_API_KEY (in .env or environment) "
                 "- never hardcode them.")
    url = base.rstrip("/") + "/chat/completions"
    body = json.dumps({"model": model, "messages": messages,
                       "temperature": temperature,
                       "max_tokens": max_tokens}).encode("utf-8")
    last = ""
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json",
                                     "Authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            if e.code == 429 or e.code >= 500:            # transient -> back off
                last = f"HTTP {e.code}: {detail}"
                time.sleep(min(2 ** attempt, 30))
                continue
            last = f"HTTP {e.code}: {detail}"              # client error -> stop trying
            break
        except (urllib.error.URLError, TimeoutError) as e:
            last = f"network: {getattr(e, 'reason', e)}"
            time.sleep(min(2 ** attempt, 30))
            continue
        except json.JSONDecodeError as e:
            last = f"non-JSON response: {e}"
            time.sleep(min(2 ** attempt, 30))
            continue
        choices = payload.get("choices")
        if choices:
            m = choices[0].get("message", {})
            text = m.get("content")
            # GLM 5.2 is a reasoning model: it fills reasoning_content first and can
            # leave content empty if the token budget is tight. Prefer content; fall
            # back to reasoning_content so a stray-but-valid JSON is still recoverable.
            if not (text and str(text).strip()):
                text = m.get("reasoning_content")
            if text is not None:
                return text, payload.get("model")
        if "error" in payload:
            last = f"error: {str(payload['error'])[:300]}"
            break
        last = f"unexpected payload: {str(payload)[:200]}"
        time.sleep(min(2 ** attempt, 30))
    log(f"  call failed: {last}")
    return None, None


def _parse_json(text: str) -> dict | None:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i != -1 and j != -1:
        t = t[i:j + 1]
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return None


def preflight(model: str) -> str:
    """One call to confirm the gateway/key AND prove which model actually answers.
    Returns the model string the API reported. STOPS the run if it is not GLM 5.2."""
    content, returned = _craftx_call(
        [{"role": "user", "content": "Reply with exactly: OK"}],
        model, temperature=0.0, max_tokens=512)
    if content is None:
        sys.exit("Preflight failed: no response from CraftX. Check CRAFTX_BASE_URL / "
                 "CRAFTX_API_KEY / network.")
    log(f"PREFLIGHT: requested model={model!r}; API returned model={returned!r}; "
        f"reply={content.strip()[:30]!r}")
    if not returned or "glm 5.2" not in returned.lower().replace("  ", " "):
        sys.exit(
            f"JUDGE MISMATCH - requested {model!r} but the API answered as "
            f"{returned!r}, which is not GLM 5.2. Stopping as instructed; a judge "
            f"silently fell back before. Nothing was written.")
    log(f"PREFLIGHT OK: judge confirmed as {returned!r}.")
    return returned


# --------------------------------------------------------------------------- #
# PASS 1 - monolingual native-speaker fluency (target text ONLY, no English)
# --------------------------------------------------------------------------- #
_FLU_SYS = (
    "You are a native {lang} speaker reviewing whether the following text reads "
    "naturally and idiomatically, exactly as a real {lang} person would write it. "
    "Judge ONLY the {lang} text. Do NOT consider or imagine any English - you are "
    "not translating, you are reading. For each item label the fluency as one of "
    "'natural', 'slightly_awkward', or 'unnatural', give a one-line reason, and IF "
    "it is not 'natural' also give a more natural rephrasing (in {lang}). Return "
    "ONLY a JSON object, no commentary, no markdown fences."
)
_FLU_USER = (
    "Review this scenario written in {lang}. First the scene (situation + goal), "
    "then four options.\n\n"
    "SCENE:\n{scene}\n\nOPTIONS:\n{options}\n\n"
    "Return ONLY this JSON shape:\n"
    '{{"scenario_id":"{sid}",'
    '"scene":{{"fluency":"natural|slightly_awkward|unnatural","reason":"...",'
    '"suggestion":"<{lang} rephrasing or empty>"}},'
    '"options":[{{"option_id":"A","fluency":"...","reason":"...","suggestion":"..."}},'
    '{{"option_id":"B","fluency":"...","reason":"...","suggestion":"..."}},'
    '{{"option_id":"C","fluency":"...","reason":"...","suggestion":"..."}},'
    '{{"option_id":"D","fluency":"...","reason":"...","suggestion":"..."}}]}}'
)


def judge_fluency(row: dict, lang: str, model: str) -> dict | None:
    lang_name = LANG_NAME[lang]
    scene = f"situation: {row['situation']}\ngoal: {row['goal']}"
    options = "\n".join(f"{o['option_id']}. {o['text']}" for o in row["options"])
    messages = [
        {"role": "system", "content": _FLU_SYS.format(lang=lang_name)},
        {"role": "user", "content": _FLU_USER.format(
            lang=lang_name, sid=row["scenario_id"], scene=scene, options=options)},
    ]
    for _ in range(5):
        content, _m = _craftx_call(messages, model, temperature=0.2, max_tokens=3000)
        if content is None:
            continue
        parsed = _parse_json(content)
        if isinstance(parsed, dict) and isinstance(parsed.get("options"), list) \
                and isinstance(parsed.get("scene"), dict):
            return parsed
    return None


# --------------------------------------------------------------------------- #
# PASS 2 - cross-lingual alignment audit (English + target). PROJECT.md step 6.
# --------------------------------------------------------------------------- #
_ALN_SYS = (
    "You are a bilingual translation-alignment auditor (English <-> {lang}). You are "
    "given an English source and its {lang} translation. Judge two things and return "
    "ONLY labels with a one-line reason each, no prose.\n"
    "(a) FUNCTIONAL alignment, per option: does the {lang} option keep the SAME "
    "action semantics as the English option? Label 'same', 'partial', or 'diverged'.\n"
    "(b) CULTURAL alignment, whole scenario: is the {lang} scenario nonsensical or "
    "off-target for a {lang}-speaking locale? Label 'ok', 'awkward', or 'off-target'.\n"
    "Return ONLY a JSON object, no markdown fences."
)
_ALN_USER = (
    "SCENE (for context):\nEN situation: {en_sit}\nEN goal: {en_goal}\n"
    "{lang} situation: {t_sit}\n{lang} goal: {t_goal}\n\n"
    "OPTIONS (English source vs {lang} target):\n{options}\n\n"
    "Return ONLY this JSON shape:\n"
    '{{"scenario_id":"{sid}",'
    '"cultural":"ok|awkward|off-target","cultural_reason":"...",'
    '"options":[{{"option_id":"A","functional":"same|partial|diverged","reason":"..."}},'
    '{{"option_id":"B","functional":"...","reason":"..."}},'
    '{{"option_id":"C","functional":"...","reason":"..."}},'
    '{{"option_id":"D","functional":"...","reason":"..."}}]}}'
)


def judge_alignment(en_row: dict, t_row: dict, lang: str, model: str) -> dict | None:
    lang_name = LANG_NAME[lang]
    opts = "\n".join(
        f"{eo['option_id']}.\n  EN: {eo['text']}\n  {lang_name}: {to['text']}"
        for eo, to in zip(en_row["options"], t_row["options"]))
    messages = [
        {"role": "system", "content": _ALN_SYS.format(lang=lang_name)},
        {"role": "user", "content": _ALN_USER.format(
            lang=lang_name, sid=t_row["scenario_id"],
            en_sit=en_row["situation"], en_goal=en_row["goal"],
            t_sit=t_row["situation"], t_goal=t_row["goal"], options=opts)},
    ]
    for _ in range(5):
        content, _m = _craftx_call(messages, model, temperature=0.2, max_tokens=3000)
        if content is None:
            continue
        parsed = _parse_json(content)
        if isinstance(parsed, dict) and isinstance(parsed.get("options"), list):
            return parsed
    return None


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _load(lang: str) -> list[dict]:
    return [json.loads(x) for x in SRC[lang].read_text(encoding="utf-8").splitlines()
            if x.strip()]


def _norm(val, allowed: set[str]) -> str:
    v = str(val).strip().lower().replace("_", "_")
    return v if v in allowed else "unjudged"


def _esc(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


# fluency/label severities for worst-first ordering
_FLU_SEV = {"unnatural": 2, "slightly_awkward": 1, "natural": 0, "unjudged": -1}
_FUN_SEV = {"diverged": 2, "partial": 1, "same": 0, "unjudged": -1}
_CUL_SEV = {"off-target": 2, "awkward": 1, "ok": 0, "unjudged": -1}


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def run(langs: list[str], passes: list[str], model: str, limit: int | None) -> None:
    _load_dotenv()
    for f in (SRC["en"], *[SRC[l] for l in langs]):
        if not f.exists():
            sys.exit(f"Missing input {f}")
    LOG.write_text("", encoding="utf-8")  # fresh log (our own file only)
    log(f"=== llm_crosscheck langs={','.join(langs)} passes={','.join(passes)} "
        f"model={model!r} ===")

    en = {r["scenario_id"]: r for r in _load("en")}
    returned_model = preflight(model)

    # results[lang] = {"fluency": {sid: parsed}, "align": {sid: parsed}}
    results: dict[str, dict] = {}
    unjudged: list[str] = []

    for lang in langs:
        rows = _load(lang)
        if limit:
            rows = rows[:limit]
        results[lang] = {"fluency": {}, "align": {}}

        if "1" in passes:
            for i, row in enumerate(rows, 1):
                sid = row["scenario_id"]
                res = judge_fluency(row, lang, model)
                results[lang]["fluency"][sid] = res
                if res is None:
                    unjudged.append(f"{lang}/fluency/{sid}")
                if i % 5 == 0 or i == len(rows):
                    log(f"[{lang}] fluency {i}/{len(rows)}")

        if "2" in passes:
            for i, row in enumerate(rows, 1):
                sid = row["scenario_id"]
                res = judge_alignment(en[sid], row, lang, model)
                results[lang]["align"][sid] = res
                if res is None:
                    unjudged.append(f"{lang}/align/{sid}")
                if i % 5 == 0 or i == len(rows):
                    log(f"[{lang}] alignment {i}/{len(rows)}")

    build_report(langs, passes, model, returned_model, en, results, unjudged)
    log(f"=== done; report -> {REPORT.name}; unjudged={len(unjudged)} ===")


def _fluency_flags(lang: str, rows: dict, results: dict):
    """Yield (severity, sid, oid, target, fluency, reason, suggestion) for non-natural."""
    out = []
    for sid, res in results[lang]["fluency"].items():
        row = rows[sid]
        omap = {o["option_id"]: o["text"] for o in row["options"]}
        if res is None:
            out.append((99, sid, "*", "(all)", "unjudged", "no judge response", ""))
            continue
        sc = res.get("scene", {})
        fl = _norm(sc.get("fluency"), FLUENCY)
        if fl != "natural":
            out.append((_FLU_SEV[fl], sid, "situation+goal",
                        row["situation"] + " / " + row["goal"], fl,
                        sc.get("reason", ""), sc.get("suggestion", "")))
        for o in res.get("options", []):
            oid = o.get("option_id", "?")
            fl = _norm(o.get("fluency"), FLUENCY)
            if fl != "natural":
                out.append((_FLU_SEV[fl], sid, oid, omap.get(oid, ""), fl,
                            o.get("reason", ""), o.get("suggestion", "")))
    out.sort(key=lambda r: (-r[0], r[1], str(r[2])))
    return out


def _align_flags(lang: str, rows: dict, en: dict, results: dict):
    """Yield (severity, sid, oid, en_text, target, functional, cultural, reason)."""
    out = []
    for sid, res in results[lang]["align"].items():
        row = rows[sid]
        tmap = {o["option_id"]: o["text"] for o in row["options"]}
        emap = {o["option_id"]: o["text"] for o in en[sid]["options"]}
        if res is None:
            out.append((99, sid, "*", "(all)", "(all)", "unjudged", "unjudged",
                        "no judge response"))
            continue
        cultural = _norm(res.get("cultural"), CULTURAL)
        creason = res.get("cultural_reason", "")
        for o in res.get("options", []):
            oid = o.get("option_id", "?")
            fn = _norm(o.get("functional"), FUNCTIONAL)
            if fn != "same" or cultural != "ok":
                sev = _FUN_SEV[fn] + _CUL_SEV[cultural]
                reason = o.get("reason", "")
                if cultural != "ok":
                    reason = f"{reason} | cultural: {creason}"
                out.append((sev, sid, oid, emap.get(oid, ""), tmap.get(oid, ""),
                            fn, cultural, reason))
    out.sort(key=lambda r: (-r[0], r[1], str(r[2])))
    return out


def _counts(labels: list[str], allowed) -> dict:
    c = {k: 0 for k in list(allowed) + ["unjudged"]}
    for x in labels:
        c[x] = c.get(x, 0) + 1
    return c


def build_report(langs, passes, req_model, returned_model, en, results, unjudged):
    rowmap = {l: {r["scenario_id"]: r for r in _load(l)} for l in langs}
    flu = {l: _fluency_flags(l, rowmap[l], results) if "1" in passes else []
           for l in langs}
    aln = {l: _align_flags(l, rowmap[l], en, results) if "2" in passes else []
           for l in langs}

    P: list[str] = []
    P.append("# LLM cross-check report - Stage 2 (supplementary)")
    P.append("")
    P.append(f"Generated {datetime.now().isoformat(timespec='seconds')}. "
             f"Requested judge = {req_model!r}; **API actually answered as "
             f"`{returned_model}`**. temperature 0.2, one scenario per call.")
    P.append("")
    P.append("> This is an LLM-SIMULATED cross-check, NOT human native verification. "
             "Bengali is already the researcher's hand-verified ground truth, so a "
             "Bengali flag here is most likely a false positive - listed anyway for a "
             "30-second eyeball. Indonesian is NOT human-verified, so Indonesian flags "
             "carry real weight and drive fix-or-drop decisions. This tool FLAGS only; "
             "it edited nothing.")
    P.append("")

    # 1. corrected-item spotlight ------------------------------------------------
    P.append("## 1. Corrected-item spotlight - ca_010 D (Bengali)")
    P.append("")
    if "bn" in langs:
        bnrow = rowmap["bn"].get("ca_010")
        enrow = en.get("ca_010")
        if bnrow and enrow:
            d_bn = next((o["text"] for o in bnrow["options"] if o["option_id"] == "D"), "")
            d_en = next((o["text"] for o in enrow["options"] if o["option_id"] == "D"), "")
            fl_res = results.get("bn", {}).get("fluency", {}).get("ca_010")
            al_res = results.get("bn", {}).get("align", {}).get("ca_010")
            fl_lbl = "n/a"
            if isinstance(fl_res, dict):
                d = next((o for o in fl_res.get("options", [])
                          if o.get("option_id") == "D"), {})
                fl_lbl = _norm(d.get("fluency"), FLUENCY)
            fn_lbl = cu_lbl = "n/a"
            if isinstance(al_res, dict):
                d = next((o for o in al_res.get("options", [])
                          if o.get("option_id") == "D"), {})
                fn_lbl = _norm(d.get("functional"), FUNCTIONAL)
                cu_lbl = _norm(al_res.get("cultural"), CULTURAL)
            P.append(f"- **EN source:** {d_en}")
            P.append(f"- **current BN:** {d_bn}")
            P.append(f"- **fluency:** `{fl_lbl}`  |  **functional:** `{fn_lbl}`  |  "
                     f"**cultural:** `{cu_lbl}`")
            P.append(f"- Expectation: all clean, confirming the hand-fix (the spurious "
                     f"\"except the youngest member\" clause is gone).")
        else:
            P.append("- ca_010 not found in inputs.")
    else:
        P.append("- Bengali not in this run.")
    P.append("")

    # 2 & 3. per-language sections ----------------------------------------------
    overlap_all: list[tuple] = []
    for lang in langs:
        name = LANG_NAME[lang]
        weight = ("already hand-verified -> flags most likely false positives"
                  if lang == "bn" else
                  "NOT human-verified -> flags carry real weight")
        idx = "2" if lang == "bn" else "3"
        P.append(f"## {idx}. {name} ({weight})")
        P.append("")

        if "1" in passes:
            P.append(f"### {idx}a. Fluency flags (not 'natural'), worst-first")
            P.append("")
            if flu[lang]:
                P.append("| scenario_id | opt | target | fluency | reason | suggested phrasing |")
                P.append("|---|---|---|---|---|---|")
                for _, sid, oid, tgt, fl, rsn, sug in flu[lang]:
                    P.append(f"| {sid} | {oid} | {_esc(tgt)} | {fl} | {_esc(rsn)} | {_esc(sug)} |")
            else:
                P.append("(none flagged - all read as natural)")
            P.append("")

        if "2" in passes:
            P.append(f"### {idx}b. Alignment flags (functional!=same OR cultural!=ok), worst-first")
            P.append("")
            if aln[lang]:
                P.append("| scenario_id | opt | source EN | target | functional | cultural | reason |")
                P.append("|---|---|---|---|---|---|---|")
                for _, sid, oid, ent, tgt, fn, cu, rsn in aln[lang]:
                    P.append(f"| {sid} | {oid} | {_esc(ent)} | {_esc(tgt)} | {fn} | {cu} | {_esc(rsn)} |")
            else:
                P.append("(none flagged - all functionally aligned and culturally ok)")
            P.append("")

        # overlap: option flagged by BOTH fluency and alignment
        if "1" in passes and "2" in passes:
            flu_keys = {(sid, oid) for _, sid, oid, *_ in flu[lang]}
            aln_keys = {(sid, oid) for _, sid, oid, *_ in aln[lang]}
            for (sid, oid) in sorted(flu_keys & aln_keys):
                overlap_all.append((lang, sid, oid))

    # 4. high-priority overlap ---------------------------------------------------
    P.append("## 4. HIGH-PRIORITY overlap (flagged by BOTH a fluency pass AND alignment)")
    P.append("")
    if "1" in passes and "2" in passes:
        if overlap_all:
            P.append("| language | scenario_id | opt |")
            P.append("|---|---|---|")
            for lang, sid, oid in overlap_all:
                P.append(f"| {LANG_NAME[lang]} | {sid} | {oid} |")
        else:
            P.append("(no item was flagged by both passes)")
    else:
        P.append("(needs both passes 1 and 2; not both run)")
    P.append("")

    # 5. per-language summary ----------------------------------------------------
    P.append("## 5. Per-language summary (counts by every label)")
    P.append("")
    for lang in langs:
        P.append(f"### {LANG_NAME[lang]}")
        if "1" in passes:
            opt_fl, scene_fl = [], []
            for sid, res in results[lang]["fluency"].items():
                if not isinstance(res, dict):
                    opt_fl += ["unjudged"] * 4
                    scene_fl.append("unjudged")
                    continue
                scene_fl.append(_norm(res.get("scene", {}).get("fluency"), FLUENCY))
                for o in res.get("options", []):
                    opt_fl.append(_norm(o.get("fluency"), FLUENCY))
            P.append(f"- fluency (options): {_counts(opt_fl, FLUENCY)}")
            P.append(f"- fluency (scene situation+goal): {_counts(scene_fl, FLUENCY)}")
        if "2" in passes:
            fn, cu = [], []
            for sid, res in results[lang]["align"].items():
                if not isinstance(res, dict):
                    fn += ["unjudged"] * 4
                    cu.append("unjudged")
                    continue
                cu.append(_norm(res.get("cultural"), CULTURAL))
                for o in res.get("options", []):
                    fn.append(_norm(o.get("functional"), FUNCTIONAL))
            P.append(f"- functional (options): {_counts(fn, FUNCTIONAL)}")
            P.append(f"- cultural (scenarios): {_counts(cu, CULTURAL)}")
        P.append("")

    if unjudged:
        P.append("### Unjudged units (no valid judge response after retries)")
        for u in unjudged:
            P.append(f"- {u}")
        P.append("")

    REPORT.write_bytes(("\n".join(P) + "\n").encode("utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Stage 2 supplementary LLM cross-check.")
    ap.add_argument("--langs", default="bn,id", help="comma list of bn,id")
    ap.add_argument("--passes", default="1,2", help="comma list of 1,2")
    ap.add_argument("--limit", type=int, default=None, help="first N scenarios only")
    ap.add_argument("--model", default=os.environ.get("CRAFTX_JUDGE_MODEL", DEFAULT_JUDGE),
                    help="judge model id (default CraftX GLM 5.2)")
    args = ap.parse_args()
    run([x.strip() for x in args.langs.split(",") if x.strip()],
        [x.strip() for x in args.passes.split(",") if x.strip()],
        args.model, args.limit)


if __name__ == "__main__":
    main()
