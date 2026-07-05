#!/usr/bin/env python3
"""Stage 2, Step 1 - machine-translation BASELINE for CultAct-ML.

See PROJECT.md Section 6, Stage 2 (step 1 only here). This produces RAW MT drafts
only; the LLM-refinement pass (step 2) and human verification come later and write
the final data/scenarios_{id,bn}.jsonl. Keeping raw MT separate lets the researcher
compare raw-MT vs refined.

Engine: Google Cloud Translation API v2 (REST). Auth is an API key read from the
environment (GOOGLE_TRANSLATE_API_KEY, or GOOGLE_API_KEY) - NEVER hardcoded. Only
Python stdlib is used (urllib), so there is nothing heavy to install.

What it translates
------------------
ONLY the agent-visible wording: `situation`, `goal`, and each option's `text`,
English -> Bengali (bn) and Indonesian (id). Everything else - scenario_id,
option_id, presentation_order, and every other field - is copied through verbatim,
row-for-row, so option A stays bound to its cluster. `language` is set to the
target code. Output: data/mt_draft_bn.jsonl, data/mt_draft_id.jsonl.

Windows/Bengali safety: every read/write is encoding="utf-8" explicit; pathlib
only; progress logged to data/translate_step1.log. After each file is written it is
read back and asserted to round-trip byte-for-byte, with no U+FFFD and (for Bengali)
real Bengali codepoints present - any mojibake fails loudly and stops.

Usage
-----
  set GOOGLE_TRANSLATE_API_KEY, then:
  python src/translate.py step1_mt [--langs bn,id] [--limit N]
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

ROOT = Path(__file__).resolve().parents[1]
SCEN_EN = ROOT / "data" / "scenarios_en.jsonl"
LOG = ROOT / "data" / "translate_step1.log"
OUT = {"bn": ROOT / "data" / "mt_draft_bn.jsonl",
       "id": ROOT / "data" / "mt_draft_id.jsonl"}
# step 2 (LLM refinement) reads OUT + scenarios_en.jsonl and writes the finals:
SCEN_OUT = {"bn": ROOT / "data" / "scenarios_bn.jsonl",
            "id": ROOT / "data" / "scenarios_id.jsonl"}
ENV_FILE = ROOT / ".env"

# Google Translate v2 target codes + Bengali script range for the mojibake check.
LANGS = {
    "bn": {"google": "bn", "name": "Bengali", "script": (0x0980, 0x09FF)},
    "id": {"google": "id", "name": "Indonesian", "script": None},
}
API_URL = "https://translation.googleapis.com/language/translate/v2"


def log(msg: str) -> None:
    line = f"{datetime.now().isoformat(timespec='seconds')}  {msg}"
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line)


def _get_api_key() -> str:
    for var in ("GOOGLE_TRANSLATE_API_KEY", "GOOGLE_API_KEY"):
        key = os.environ.get(var)
        if key:
            return key
    sys.exit(
        "No API key. Set GOOGLE_TRANSLATE_API_KEY (or GOOGLE_API_KEY) to a Google "
        "Cloud Translation API key. PowerShell (this session):\n"
        '  $env:GOOGLE_TRANSLATE_API_KEY = "AIza..."\n'
        "or persist it:\n"
        '  setx GOOGLE_TRANSLATE_API_KEY "AIza..."   (then open a new shell)')


def _google_translate(texts: list[str], target: str, api_key: str) -> list[str]:
    """Translate a batch en->target via Google Translation v2 REST. Order preserved."""
    body = json.dumps({"q": texts, "source": "en", "target": target,
                       "format": "text"}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_URL}?key={api_key}", data=body,
        headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        sys.exit(f"Google API HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        sys.exit(f"Google API network error: {e.reason}")
    trans = payload["data"]["translations"]
    if len(trans) != len(texts):
        sys.exit(f"API returned {len(trans)} translations for {len(texts)} inputs.")
    return [t["translatedText"] for t in trans]


def _translate_row(row: dict, target: str, api_key: str) -> dict:
    """Translate only situation/goal/option-text; copy everything else through."""
    src = [row["situation"], row["goal"], *[o["text"] for o in row["options"]]]
    tr = _google_translate(src, target, api_key)
    new = json.loads(json.dumps(row, ensure_ascii=False))  # deep copy = passthrough
    new["situation"], new["goal"] = tr[0], tr[1]
    for opt, txt in zip(new["options"], tr[2:]):
        opt["text"] = txt  # option_id untouched; text only
    return new


def _write_and_verify(lang: str, src_rows: list[dict], out_rows: list[dict],
                      path: Path) -> None:
    content = "\n".join(json.dumps(r, ensure_ascii=False) for r in out_rows) + "\n"
    # write raw UTF-8 bytes (not text mode) so Windows does NOT translate \n->\r\n;
    # keeps the file true byte-for-byte LF and the round-trip check exact.
    path.write_bytes(content.encode("utf-8"))

    # byte-for-byte round trip: decode raw bytes as UTF-8 and compare to what we wrote
    back = path.read_bytes().decode("utf-8")  # raises UnicodeDecodeError on mojibake
    if back != content:
        sys.exit(f"FAIL {lang}: {path.name} did not round-trip byte-for-byte.")
    reloaded = [json.loads(x) for x in back.splitlines() if x.strip()]
    if not (len(reloaded) == len(src_rows) == len(out_rows)):
        sys.exit(f"FAIL {lang}: row count mismatch "
                 f"src={len(src_rows)} out={len(out_rows)} reloaded={len(reloaded)}.")
    lo_hi = LANGS[lang]["script"]
    for s, o in zip(src_rows, reloaded):
        if o["scenario_id"] != s["scenario_id"]:
            sys.exit(f"FAIL {lang}: scenario_id misaligned "
                     f"({o['scenario_id']} != {s['scenario_id']}).")
        if [x["option_id"] for x in o["options"]] != \
           [x["option_id"] for x in s["options"]]:
            sys.exit(f"FAIL {lang} {o['scenario_id']}: option_id order changed.")
        if o["presentation_order"] != s["presentation_order"]:
            sys.exit(f"FAIL {lang} {o['scenario_id']}: presentation_order changed.")
        blob = o["situation"] + " " + o["goal"] + " " + \
            " ".join(x["text"] for x in o["options"])
        if not o["situation"].strip() or not o["goal"].strip() or \
           any(not x["text"].strip() for x in o["options"]):
            sys.exit(f"FAIL {lang} {o['scenario_id']}: empty translated field.")
        if "�" in blob:
            sys.exit(f"FAIL {lang} {o['scenario_id']}: U+FFFD replacement char "
                     f"(mojibake) in output.")
        if lo_hi and not any(lo_hi[0] <= ord(ch) <= lo_hi[1] for ch in blob):
            sys.exit(f"FAIL {lang} {o['scenario_id']}: no {LANGS[lang]['name']} "
                     f"codepoints - translation missing or corrupted.")
    log(f"[{lang}] wrote {len(out_rows)} rows -> {path.name}; "
        f"round-trip byte-for-byte OK, no mojibake"
        + (", Bengali script present" if lo_hi else ""))


def step1_mt(langs: tuple[str, ...] = ("bn", "id"), limit: int | None = None) -> None:
    if not SCEN_EN.exists():
        sys.exit(f"No source at {SCEN_EN}; run build_scenarios.py promote first.")
    _load_dotenv()
    api_key = _get_api_key()
    src_rows = [json.loads(x) for x in SCEN_EN.read_text(encoding="utf-8").splitlines()
                if x.strip()]
    if limit:
        src_rows = src_rows[:limit]
    log(f"=== step1_mt engine=google_api langs={','.join(langs)} "
        f"scenarios={len(src_rows)} ===")

    for lang in langs:
        cfg = LANGS[lang]
        log(f"[{lang}] {cfg['name']}: target={cfg['google']}")
        out_rows = []
        for i, row in enumerate(src_rows, 1):
            nr = _translate_row(row, cfg["google"], api_key)
            nr["language"] = lang
            out_rows.append(nr)
            if i % 10 == 0:
                log(f"[{lang}] translated {i}/{len(src_rows)}")
        _write_and_verify(lang, src_rows, out_rows, OUT[lang])
    log("=== step1_mt done ===")


# ===========================================================================
# Stage 2, Step 2 - LLM refinement pass (CraftX OpenAI-compatible gateway)
# ===========================================================================
_REFINER_SYS = (
    "You are a professional {lang} editor REFINING an existing machine "
    "translation. You are NOT translating from scratch: for each field you "
    "receive the original English ('en', the source of truth) and a rough {lang} "
    "machine translation ('mt') to improve.\n\n"
    "Rewrite the {lang} so it reads as natural, fluent {lang} that a native "
    "speaker would actually write, while preserving the English meaning EXACTLY.\n\n"
    "HARD RULES (violating any is a failure):\n"
    "1. Meaning must match the English source precisely - do not add, drop, or "
    "shift meaning.\n"
    "2. Each option ends with a short PURPOSE CLAUSE (e.g. '...to honor collective "
    "effort', '...to respect recognized authority'). Keep every purpose clause and "
    "its exact intent - never soften, drop, or generalize it.\n"
    "3. Keep the four options PARALLEL in tone and force. Do NOT make any option "
    "sound warmer, punchier, more reasonable, or more natural than the others. If "
    "an action is deferential or authority-based, keep that framing fully. "
    "Faithful beats fluent.\n"
    "4. Do not change option_id letters, their order, or the count (exactly 4).\n"
    "5. Change only the wording; return the refined text only.\n\n"
    "Return ONLY a JSON object, no commentary, no markdown fences."
)
_REFINER_USER = (
    "Refine this scenario into natural {lang}. For each field, 'en' is the source "
    "of truth and 'mt' is the rough translation to improve.\n\n"
    "{payload}\n\n"
    "Return ONLY this exact JSON shape (refined {lang} in the string values):\n"
    '{{"scenario_id":"<same>","situation":"<refined>","goal":"<refined>",'
    '"options":[{{"option_id":"A","text":"<refined>"}},'
    '{{"option_id":"B","text":"<refined>"}},{{"option_id":"C","text":"<refined>"}},'
    '{{"option_id":"D","text":"<refined>"}}]}}'
)


def _load_dotenv(path: Path = ENV_FILE) -> None:
    """Minimal .env loader (KEY=VALUE lines). Does not override real env vars."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _craftx_chat(messages: list[dict], model: str, temperature: float = 0.3,
                 max_tokens: int = 2000, retries: int = 4) -> str:
    """POST to the CraftX OpenAI-compatible gateway. Retries transient failures
    (429 / 5xx / network / timeout) with capped exponential backoff; fails fast on
    client errors (4xx). Raises RuntimeError on definitive failure (caller decides).
    Missing credentials is a config error -> sys.exit."""
    base = os.environ.get("CRAFTX_BASE_URL")
    key = os.environ.get("CRAFTX_API_KEY")
    if not base or not key:
        sys.exit("Set CRAFTX_BASE_URL and CRAFTX_API_KEY (in .env or the "
                 "environment) - never hardcode them.")
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
            detail = e.read().decode("utf-8", "replace")[:400]
            if e.code == 429 or e.code >= 500:            # transient -> back off
                last = f"HTTP {e.code}: {detail}"
                time.sleep(min(2 ** attempt, 30))
                continue
            raise RuntimeError(f"CraftX HTTP {e.code}: {detail}")  # client -> fatal
        except (urllib.error.URLError, TimeoutError) as e:
            last = f"network: {getattr(e, 'reason', e)}"
            time.sleep(min(2 ** attempt, 30))
            continue
        except json.JSONDecodeError as e:
            last = f"non-JSON response: {e}"
            time.sleep(min(2 ** attempt, 30))
            continue
        # success path - validate the payload shape defensively
        choices = payload.get("choices")
        if choices and choices[0].get("message", {}).get("content") is not None:
            return choices[0]["message"]["content"]
        if "error" in payload:
            raise RuntimeError(f"CraftX error: {str(payload['error'])[:400]}")
        last = f"unexpected payload: {str(payload)[:300]}"
        time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"CraftX call failed after {retries} tries: {last}")


def _parse_refined(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):                       # strip ```json ... ``` fences
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i != -1 and j != -1:
        t = t[i:j + 1]
    return json.loads(t)


def _valid_refined(ref: dict, mt_row: dict) -> tuple[bool, str]:
    if ref.get("scenario_id") != mt_row["scenario_id"]:
        return False, "scenario_id mismatch"
    if not str(ref.get("situation", "")).strip() or not str(ref.get("goal", "")).strip():
        return False, "empty situation/goal"
    ro = ref.get("options")
    if not isinstance(ro, list) or len(ro) != 4:
        return False, f"expected 4 options, got {len(ro) if isinstance(ro, list) else 'n/a'}"
    if [o.get("option_id") for o in ro] != [o["option_id"] for o in mt_row["options"]]:
        return False, "option_id set/order changed"
    if any(not str(o.get("text", "")).strip() for o in ro):
        return False, "empty option text"
    return True, "ok"


def _refine_one(en_row: dict, mt_row: dict, lang: str, model: str,
                temperature: float) -> dict:
    lang_name = LANGS[lang]["name"]
    payload = {
        "scenario_id": mt_row["scenario_id"],
        "situation": {"en": en_row["situation"], "mt": mt_row["situation"]},
        "goal": {"en": en_row["goal"], "mt": mt_row["goal"]},
        "options": [{"option_id": o["option_id"], "en": eo["text"], "mt": o["text"]}
                    for o, eo in zip(mt_row["options"], en_row["options"])],
    }
    messages = [
        {"role": "system", "content": _REFINER_SYS.format(lang=lang_name)},
        {"role": "user", "content": _REFINER_USER.format(
            lang=lang_name, payload=json.dumps(payload, ensure_ascii=False, indent=2))},
    ]
    msg = ""
    for attempt in range(1, 4):  # up to 3 tries per scenario
        try:
            ref = _parse_refined(_craftx_chat(messages, model, temperature))
            ok, msg = _valid_refined(ref, mt_row)
            if ok:
                break
        except (json.JSONDecodeError, KeyError, TypeError, RuntimeError) as e:
            msg = f"{e}"
        log(f"[{lang}] {mt_row['scenario_id']} refine attempt {attempt} bad: {msg}")
    else:
        sys.exit(f"FAIL {lang} {mt_row['scenario_id']}: invalid refinement after "
                 f"3 tries ({msg}).")
    new = json.loads(json.dumps(mt_row, ensure_ascii=False))  # passthrough copy
    new["situation"], new["goal"] = ref["situation"], ref["goal"]
    for o, ro in zip(new["options"], ref["options"]):
        o["text"] = ro["text"]  # only wording; option_id/order untouched
    return new


def step2_refine(langs: tuple[str, ...] = ("bn", "id"), model: str | None = None,
                 limit: int | None = None, temperature: float = 0.3) -> None:
    _load_dotenv()
    model = model or os.environ.get("CRAFTX_MODEL")
    if not model:
        sys.exit("Provide --model or set CRAFTX_MODEL (the refiner model id).")
    if not SCEN_EN.exists():
        sys.exit(f"No source at {SCEN_EN}.")
    en_list = [json.loads(x) for x in SCEN_EN.read_text(encoding="utf-8").splitlines()
               if x.strip()]
    en = {r["scenario_id"]: r for r in en_list}
    log(f"=== step2_refine model={model} temp={temperature} langs={','.join(langs)} ===")

    # preflight: one tiny call to confirm base_url / key / model id before the run
    try:
        ping = _craftx_chat([{"role": "user", "content": "Reply with exactly: OK"}],
                            model, temperature=0.0, max_tokens=5)
    except RuntimeError as e:
        sys.exit(f"Preflight failed - check CRAFTX_BASE_URL / CRAFTX_API_KEY / "
                 f"CRAFTX_MODEL: {e}")
    log(f"preflight OK: model replied {ping.strip()[:40]!r}")

    for lang in langs:
        if not OUT[lang].exists():
            sys.exit(f"No step-1 draft at {OUT[lang]}; run step1_mt first.")
        drafts = [json.loads(x) for x in OUT[lang].read_text(encoding="utf-8").splitlines()
                  if x.strip()]
        if limit:
            drafts = drafts[:limit]
        src = en_list[:len(drafts)]
        out_rows = []
        for i, mt in enumerate(drafts, 1):
            out_rows.append(_refine_one(en[mt["scenario_id"]], mt, lang, model, temperature))
            if i % 5 == 0 or i == len(drafts):
                log(f"[{lang}] refined {i}/{len(drafts)}")
        _write_and_verify(lang, src, out_rows, SCEN_OUT[lang])
    log("=== step2_refine done ===")


def main() -> None:
    ap = argparse.ArgumentParser(description="CultAct-ML Stage 2 (translation).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("step1_mt", help="raw MT drafts -> data/mt_draft_{bn,id}.jsonl")
    s.add_argument("--langs", default="bn,id", help="comma list of bn,id")
    s.add_argument("--limit", type=int, default=None, help="translate first N only")
    r = sub.add_parser("step2_refine",
                       help="LLM-refine MT drafts -> data/scenarios_{bn,id}.jsonl")
    r.add_argument("--model", default=None, help="refiner model id (or CRAFTX_MODEL)")
    r.add_argument("--langs", default="bn,id", help="comma list of bn,id")
    r.add_argument("--limit", type=int, default=None, help="refine first N only")
    r.add_argument("--temperature", type=float, default=0.3)
    args = ap.parse_args()
    if args.cmd == "step1_mt":
        step1_mt(tuple(args.langs.split(",")), args.limit)
    elif args.cmd == "step2_refine":
        step2_refine(tuple(args.langs.split(",")), args.model, args.limit,
                     args.temperature)


if __name__ == "__main__":
    main()
