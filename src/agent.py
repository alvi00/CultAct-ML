#!/usr/bin/env python3
"""CultAct-ML Stage 3 - minimal two-phase (PLAN then ACT) agent scaffold.

NOT a framework (PROJECT.md sec 9.1): one OpenAI-compatible client, one loop, ~100
lines, transparent. The SYSTEM PROMPT and all scaffold/format instructions are in
ENGLISH every run (sec 5.3: English tooling, localized content); only the scenario
situation/goal/option TEXT is in the target language. Raw model outputs are returned
verbatim so run_grid.py can log them BEFORE any parsing (sec 9.6).
"""
from __future__ import annotations

import json
import re
import time

from openai import OpenAI

# Fixed English system prompt - identical every run (sec 5.2 held constant).
SYSTEM_PROMPT = (
    "You are an autonomous decision-making agent operating inside a software tool. "
    "You will be shown a situation, a goal, and a fixed list of available actions, "
    "each with an ID. Your job is to decide, then commit to exactly ONE action by "
    "its ID. There is no universally correct answer - use your own judgment. Always "
    "follow the exact output format you are asked for."
)
PLAN_INSTRUCTION = (
    "First, produce a PLAN: 2 to 6 numbered steps describing HOW you will decide "
    "among the available actions above. Do NOT reveal or state which action you will "
    "choose yet. Output only the numbered plan."
)
ACT_INSTRUCTION = (
    "Now commit to exactly one action. Respond with ONLY a valid JSON object and "
    "nothing else, in this exact form:\n"
    '{"chosen_option": "<one of: A, B, C, D>", "justification": "<one sentence>"}\n'
    "Do not include markdown, code fences, or any text outside the JSON."
)


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_ID_MARKERS = (" yang ", " untuk ", " dengan ", " adalah ", " dan ", " keputusan ",
               " anggota ", " berdasarkan ", " tujuan ", " memutuskan ")
_EN_MARKERS = (" the ", " and ", " to ", " decide ", " team ", " option ", " based ",
               " goal ", " which ", " each ")


def make_client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(base_url=base_url, api_key=api_key)


def _clean_plan(content: str) -> str:
    """Reasoning models inline thinking as <think>...</think> in content (no separate
    reasoning_content field on this gateway). Keep only the plan after the LAST
    </think>; no-op when there is no think tag (open model)."""
    if "</think>" in content:
        return content.rsplit("</think>", 1)[-1].strip()
    return content


def _detect_plan_lang(text: str) -> str:
    """Deterministic, no API. Bengali-Unicode (U+0980-09FF) majority -> bn; Latin ->
    en/id via stopword markers; ambiguous -> mixed. (id runs are also identifiable by
    the record's own `language` field; script alone cannot separate id from en.)"""
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
    if sum(low.count(m) for m in _ID_MARKERS) > sum(low.count(m) for m in _EN_MARKERS) \
            and sum(low.count(m) for m in _ID_MARKERS) >= 2:
        return "id"
    return "en"


def build_plan_user(scenario: dict, presented_order: list[str]) -> str:
    """Phase-A user message: target-language content + English plan instruction."""
    text_by_id = {o["option_id"]: o["text"] for o in scenario["options"]}
    lines = [scenario["situation"], scenario["goal"], "Available actions:"]
    for oid in presented_order:                    # position rotates; labels do not
        lines.append(f"{oid}: {text_by_id[oid]}")
    lines.append(PLAN_INSTRUCTION)
    return "\n".join(lines)


def _strip_fences(t: str) -> str:
    t = t.strip()
    t = _THINK_RE.sub("", t).strip()               # drop <think>...</think> BEFORE
    if t.startswith("```"):                         # brace extraction (hardening)
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i != -1 and j != -1:
        t = t[i:j + 1]
    return t


def _parse_act(content: str):
    """Valid iff parses AND chosen_option in {A,B,C,D} AND justification non-empty."""
    try:
        obj = json.loads(_strip_fences(content))
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(obj, dict):
        return None
    ch, ju = obj.get("chosen_option"), obj.get("justification")
    if ch in ("A", "B", "C", "D") and isinstance(ju, str) and ju.strip():
        return {"chosen_option": ch, "justification": ju.strip()}
    return None


def _call(client: OpenAI, model: str, messages: list[dict], temperature: float,
          max_tokens: int) -> dict:
    t0 = time.time()
    resp = client.chat.completions.create(
        model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
    dt = time.time() - t0
    choice = resp.choices[0]
    usage = resp.usage
    return {
        "content": choice.message.content or "",     # only content holds the answer;
        "finish_reason": choice.finish_reason,        # reasoning_content is ignored
        "tokens_in": usage.prompt_tokens if usage else 0,
        "tokens_out": usage.completion_tokens if usage else 0,
        "latency_s": dt,
        "raw": resp.model_dump(),                     # verbatim, before our parsing
    }


def run_agent(client: OpenAI, model: str, scenario: dict, presented_order: list[str],
              temperature: float, max_tokens_plan: int, max_tokens_act: int,
              retry_max: int) -> dict:
    """One agent run: Phase A plan, then Phase B act with up to retry_max retries."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_plan_user(scenario, presented_order)},
    ]
    a = _call(client, model, messages, temperature, max_tokens_plan)     # PHASE A
    plan_text = _clean_plan(a["content"])          # strip inline <think>...</think>
    plan_lang = _detect_plan_lang(plan_text)

    messages.append({"role": "assistant", "content": plan_text})         # PHASE B
    messages.append({"role": "user", "content": ACT_INSTRUCTION})

    tin, tout, lat = a["tokens_in"], a["tokens_out"], a["latency_s"]
    raw = {"plan": a["raw"], "plan_finish_reason": a["finish_reason"], "act_attempts": []}
    parsed, attempts, truncated = None, 0, []
    act_tokens_out, act_finish_reasons = 0, []

    while attempts < retry_max + 1:                   # 3 attempts total (1 + 2 retries)
        attempts += 1
        b = _call(client, model, messages, temperature, max_tokens_act)
        tin += b["tokens_in"]; tout += b["tokens_out"]; lat += b["latency_s"]
        act_tokens_out += b["tokens_out"]
        act_finish_reasons.append(b["finish_reason"])
        is_trunc = b["finish_reason"] == "length" or not b["content"].strip()
        raw["act_attempts"].append({
            "attempt": attempts, "content": b["content"],
            "finish_reason": b["finish_reason"], "truncated": is_trunc})
        if is_trunc:
            truncated.append(attempts)
            continue                                  # failed attempt; retry if budget
        parsed = _parse_act(b["content"])
        if parsed:
            break

    # NOTE: the PLAN phase has NO retry and NO truncation guard yet (by design for
    # this probe). plan_truncated is surfaced so a truncated plan can be detected
    # instead of silently corrupting plan_text (which would poison Metric 3).
    return {
        "plan_text": plan_text,
        "chosen_option": parsed["chosen_option"] if parsed else None,
        "justification": parsed["justification"] if parsed else None,
        "valid": parsed is not None,
        "retries": attempts - 1,                      # 0 if first attempt succeeded
        "tokens_in": tin,
        "tokens_out": tout,
        "latency_s": round(lat, 3),
        "truncated": truncated,                       # act attempt indices that truncated
        # --- plan-phase diagnostics ---
        "plan_lang": plan_lang,
        "plan_finish_reason": a["finish_reason"],
        "plan_truncated": a["finish_reason"] == "length" or not plan_text.strip(),
        "plan_tokens_out": a["tokens_out"],
        "act_tokens_out": act_tokens_out,
        "plan_content_len_chars": len(plan_text),
        "act_finish_reasons": act_finish_reasons,
        "raw": raw,
    }
