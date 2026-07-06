#!/usr/bin/env python3
"""CultAct-ML Stage 3 - grid runner (resumable, cost-gated). PROJECT.md sec 5,7,9.

Pilot: `python src/run_grid.py --pilot`  -> 5 scenarios x open model x 3 langs x 3
repeats = 45 runs. Full grid requires `--confirm`. Resumable: skips run_ids already
present in results/runs.jsonl. Everything UTF-8 explicit; logs to results/run_grid.log
and raw dumps to results/raw/<run_id>.json (raw kept even if parsing fails).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent as agent_mod

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "run_config.yaml"
ENV_FILE = ROOT / ".env"
LOG = ROOT / "results" / "run_grid.log"
DHAKA = timezone(timedelta(hours=6))          # +06:00, for ISO timestamps
CANONICAL = ["A", "B", "C", "D"]


def log(msg: str) -> None:
    line = f"{datetime.now(DHAKA).isoformat(timespec='seconds')}  {msg}"
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line)


def load_dotenv(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def presented_order(scenario_id: str, repeat: int, matrix: list[list[int]]) -> list[str]:
    """Deterministic latin-square rotation. repeat is 1..3; row=(N+(r-1))%4."""
    n = int("".join(c for c in scenario_id if c.isdigit()))
    row = (n + (repeat - 1)) % 4
    return [CANONICAL[i] for i in matrix[row]]


def preflight(client, models: list[dict]) -> None:
    """1-token test call to every model id; print the echoed model string. STOP if
    any id fails to resolve (do not guess a corrected name)."""
    log("=== PREFLIGHT ===")
    failures = []
    for m in models:
        try:
            r = client.chat.completions.create(
                model=m["id"], messages=[{"role": "user", "content": "Reply with: OK"}],
                max_tokens=1, temperature=0)
            echoed = r.model
            flag = "" if echoed and echoed.strip() == m["id"] else "  <-- echoed != requested"
            log(f"[{m['role']:8}] requested {m['id']!r} -> echoed {echoed!r}{flag}")
        except Exception as e:                        # noqa: BLE001 - report & stop
            failures.append((m["id"], str(e)[:200]))
            log(f"[{m['role']:8}] requested {m['id']!r} -> FAILED: {str(e)[:200]}")
    if failures:
        sys.exit("PREFLIGHT FAILED - these model ids did not resolve (not guessing a "
                 "corrected name):\n" + "\n".join(f"  {i}: {e}" for i, e in failures))
    log("preflight OK: all three model ids resolve.")


def build_run_list(cfg: dict, pilot: bool = False, probe: bool = False,
                   only_models: list[str] | None = None):
    """Return list of (scenario_id, lang, model_dict, repeat). only_models filters
    the FULL grid to the given model roles/shorts (staged rollout, e.g. open first)."""
    models = {m["role"]: m for m in cfg["models"]}
    if probe:
        p = cfg["probe"]
        sids, used = p["scenario_ids"], [models[p["model_role"]]]
        langs, reps = p["languages"], range(1, p["repeats"] + 1)
    elif pilot:
        sids = cfg["pilot"]["scenario_ids"]
        used = [models[cfg["pilot"]["model_role"]]]
        langs, reps = cfg["languages"], range(1, cfg["repeats"] + 1)
    else:
        sids = [r["scenario_id"] for r in load_jsonl(ROOT / cfg["paths"]["scenarios_en"])]
        used = cfg["models"]
        if only_models:
            sel = set(only_models)
            used = [m for m in cfg["models"] if m["role"] in sel or m["short"] in sel]
        langs, reps = cfg["languages"], range(1, cfg["repeats"] + 1)
    runs = []
    for sid in sids:
        for lang in langs:
            for m in used:
                for r in reps:
                    runs.append((sid, lang, m, r))
    return runs


def main() -> None:
    ap = argparse.ArgumentParser(description="CultAct-ML Stage 3 grid runner.")
    ap.add_argument("--pilot", action="store_true", help="45-run pilot (open model only)")
    ap.add_argument("--probe", action="store_true", help="6-run reasoning-model diagnostic")
    ap.add_argument("--models", default=None,
                    help="comma list of model roles/shorts to include in the FULL grid "
                         "(staged rollout, e.g. 'open'); default = all three")
    ap.add_argument("--confirm", action="store_true", help="required to launch the FULL grid")
    args = ap.parse_args()

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    load_dotenv()
    base_url = os.environ.get(cfg["gateway"]["base_url_env"])
    api_key = os.environ.get(cfg["gateway"]["api_key_env"])
    if not base_url or not api_key:
        sys.exit(f"Set {cfg['gateway']['base_url_env']} and {cfg['gateway']['api_key_env']} "
                 "(in .env or environment) - never hardcode.")
    client = agent_mod.make_client(base_url, api_key)

    # scenarios per language + rotation matrix
    scen = {lang: {r["scenario_id"]: r for r in load_jsonl(ROOT / cfg["paths"][f"scenarios_{lang}"])}
            for lang in cfg["languages"]}
    matrix = cfg["rotation"]["matrix"]
    dec = cfg["decoding"]
    runs_out = ROOT / cfg["paths"]["runs_out"]
    raw_dir = ROOT / cfg["paths"]["raw_dir"]
    raw_dir.mkdir(parents=True, exist_ok=True)

    preflight(client, cfg["models"])

    only_models = [x.strip() for x in args.models.split(",")] if args.models else None
    run_list = build_run_list(cfg, args.pilot, args.probe, only_models)
    if only_models and not run_list:
        sys.exit(f"--models {only_models} matched no models. Roles/shorts available: "
                 + ", ".join(f"{m['role']}/{m['short']}" for m in cfg["models"]))
    if not args.pilot and not args.probe and not args.confirm:
        sys.exit(f"FULL grid = {len(run_list)} runs ({2*len(run_list)} model calls). "
                 "Re-run with --confirm to launch. (Use --pilot / --probe for gates.)")

    # resumable: skip run_ids already present
    done = set()
    if runs_out.exists():
        done = {json.loads(x)["run_id"] for x in runs_out.read_text(encoding="utf-8").splitlines() if x.strip()}
    todo = [(sid, lang, m, r) for (sid, lang, m, r) in run_list
            if f"{sid}__{lang}__{m['short']}__r{r}" not in done]

    mode = "PROBE" if args.probe else "PILOT" if args.pilot else "FULL"
    log(f"=== {mode}: {len(run_list)} runs total, {len(done)} already done, "
        f"{len(todo)} to run => ~{2*len(todo)} model calls (2 phases each) ===")

    for i, (sid, lang, m, r) in enumerate(todo, 1):
        run_id = f"{sid}__{lang}__{m['short']}__r{r}"
        scenario = scen[lang][sid]
        order = presented_order(sid, r, matrix)
        try:
            res = agent_mod.run_agent(
                client, m["id"], scenario, order, dec["temperature"],
                dec["max_tokens_plan"], dec["max_tokens_act"], cfg["retry_max"])
        except Exception as e:                        # noqa: BLE001
            log(f"[{i}/{len(todo)}] {run_id} ERROR: {str(e)[:200]}")
            raise
        # plan/act diagnostics live in the raw dump (keeps runs.jsonl at the sec 7.3
        # schema; nothing silently added to the run record).
        res["raw"]["diagnostics"] = {
            "plan_finish_reason": res["plan_finish_reason"],
            "plan_truncated": res["plan_truncated"],
            "plan_tokens_out": res["plan_tokens_out"],
            "act_tokens_out": res["act_tokens_out"],
            "plan_content_len_chars": res["plan_content_len_chars"],
            "act_finish_reasons": res["act_finish_reasons"],
            "act_truncated_attempts": res["truncated"],
            "retries": res["retries"],
            "valid": res["valid"],
            "chosen_option": res["chosen_option"],
        }
        # raw dump FIRST (never lose the raw record)
        (raw_dir / f"{run_id}.json").write_bytes(
            json.dumps(res["raw"], ensure_ascii=False, indent=2).encode("utf-8"))
        record = {
            "run_id": run_id,
            "scenario_id": sid,
            "language": lang,
            "model": res["raw"]["plan"].get("model", m["id"]),   # resolved string
            "repeat_index": r,
            "presented_order": order,
            "plan_text": res["plan_text"],
            "plan_lang": res["plan_lang"],
            "chosen_option": res["chosen_option"],
            "justification": res["justification"],
            "valid": res["valid"],
            "plan_truncated": res["plan_truncated"],
            "retries": res["retries"],
            "tokens_in": res["tokens_in"],
            "tokens_out": res["tokens_out"],
            "latency_s": res["latency_s"],
            "timestamp": datetime.now(DHAKA).isoformat(timespec="seconds"),
        }
        with runs_out.open("a", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        trunc = f" TRUNC{res['truncated']}" if res["truncated"] else ""
        log(f"[{i}/{len(todo)}] {run_id} valid={res['valid']} "
            f"choice={res['chosen_option']} retries={res['retries']}{trunc}")

    log(f"=== {mode} done ===")


if __name__ == "__main__":
    main()
