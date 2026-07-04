#!/usr/bin/env python3
"""Stage 1 - Scenario construction for CultAct-ML.

Source of truth: PROJECT.md, Section 6 (Stage 1) and Section 7 (schemas).

This script does NOT write the final dataset. It renders hand-authored DRAFT
recasts into a human-review file (data/drafts_for_review.md). The researcher
edits that file by hand; nothing reaches data/scenarios_en.jsonl without explicit
approval (a separate, later `promote` step, not built yet).

Commands
--------
  python src/build_scenarios.py build [--force]
      Render the authored recasts to data/drafts_for_review.md, then validate.
      Refuses to overwrite an existing drafts file unless --force (protects
      manual edits).

  python src/build_scenarios.py promote
      ROADMAP STUB (not built yet; see promote() docstring). After the
      researcher approves all 40 drafts, this will write scenarios_en.jsonl +
      scenarios_meta.jsonl per PROJECT.md 7.1/7.2 and generate per-run
      presentation_order via seeded latin_square_4 rotation (PROJECT.md 9.3).

  python src/build_scenarios.py validate [--file PATH]
      Re-parse the (possibly hand-edited) drafts file and run the lint checks:
        * anonymity  - reject the 10 cluster names / variants + "GLOBE" in
                       agent-visible text (ERROR)
        * structure  - exactly 4 options, >=1 Western and >=1 non-Western,
                       valid distinct clusters (ERROR)
        * length     - the 4 options within +/-25% tokens of their mean (WARN)
        * tone       - equal-confidence: no hedges/loaded words, balanced
                       justification across the 4 options (WARN)

No model calls. UTF-8 everywhere (Windows + Bengali safety). pathlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CCD_JSON = ROOT / "data" / "raw_ccd" / "CCD-Bench" / "datasets" / "CCD-Bench.json"
DRAFTS_MD = ROOT / "data" / "drafts_for_review.md"
SCENARIOS_EN = ROOT / "data" / "scenarios_en.jsonl"
SCENARIOS_META = ROOT / "data" / "scenarios_meta.jsonl"
ROTATION_SEED = 42  # PROJECT.md 9.3 determinism (matches CCD-Bench evaluation.py)

# --- cluster canonicalization (PROJECT.md 7.2) -----------------------------
SOURCE_TO_CANON = {
    "anglo": "anglo",
    "eastern_europe": "eastern_europe",
    "latin-america": "latin_america",
    "latin_europe": "latin_europe",
    "confucian_asia": "confucian_asia",
    "nordic_europe": "nordic_europe",
    "sub-saharan_africa": "sub_saharan_africa",
    "southern-asia": "southern_asia",
    "germanic_europe": "germanic_europe",
    "middle_east": "middle_east",
}
CANON_TO_SOURCE = {v: k for k, v in SOURCE_TO_CANON.items()}
CANON = set(SOURCE_TO_CANON.values())
WESTERN = {"anglo", "nordic_europe", "germanic_europe"}

# Terms rejected by the anonymity lint in agent-visible text. Single words are
# matched on word boundaries; multiword phrases as substrings (case-insensitive).
_LINT_WORDS = ["anglo", "nordic", "germanic", "confucian", "globe"]
_LINT_PHRASES = [
    "eastern europe", "eastern_europe", "eastern-europe",
    "latin america", "latin_america", "latin-america",
    "latin europe", "latin_europe", "latin-europe",
    "confucian asia", "confucian_asia",
    "nordic europe", "nordic_europe",
    "sub-saharan africa", "sub saharan", "sub_saharan_africa", "subsaharan", "sub-saharan",
    "southern asia", "southern_asia", "southern-asia",
    "germanic europe", "germanic_europe",
    "middle east", "middle_east", "middle-east",
]

# Tone lint vocabularies (equal-confidence check).
_HEDGES = ["might", "maybe", "perhaps", "possibly", "probably", "i think",
           "i guess", "try to", "sort of", "kind of", "if possible",
           "hopefully", "could consider", "may want"]
_LOADED = ["clearly", "obviously", "the best", "fairest", "the right",
           "most sensible", "of course", "undoubtedly", "naturally",
           "the smartest", "the obvious"]
# A trailing purpose clause ("..., to <verb> ...") marks an option as justified.
# Equal-confidence wants all-or-none of the 4 options to carry one.
_PURPOSE = re.compile(r",\s+to\s+\w+")


# ---------------------------------------------------------------------------
# Authored draft recasts (Stage 1) live in data/recasts.json, relocated from
# this module for readability (see PROJECT.md 6.5). Each recast holds the
# agent-visible situation/goal, four options as [canonical_cluster, action_text]
# pairs (first-person CCD-Bench opinions recast into second-person AGENT
# ACTIONS), and hidden metadata (distinctness_note, notes, flag). build()
# renders them to the drafts markdown, validate() lints it, promote() (stub)
# will write the final jsonl. western_options is derived, not stored.
# ---------------------------------------------------------------------------
RECASTS_JSON = ROOT / "data" / "recasts.json"
RECASTS = json.loads(RECASTS_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def _load_source() -> list[dict]:
    with CCD_JSON.open(encoding="utf-8") as fh:
        return json.load(fh)


def _letters(n: int) -> list[str]:
    return [chr(ord("A") + i) for i in range(n)]


def build(force: bool = False) -> None:
    if DRAFTS_MD.exists() and not force:
        sys.exit(f"Refusing to overwrite {DRAFTS_MD} (has your edits?). Use --force.")

    source = _load_source()
    blocks: list[str] = []
    for rc in RECASTS:
        entry = source[rc["src"] - 1]  # 1-based index (evaluation.py question_id)
        # Sanity: source domain and cluster keys must line up with our mapping.
        if entry.get("Domain") != rc["domain"]:
            sys.exit(f"{rc['id']}: source domain {entry.get('Domain')!r} != "
                     f"authored {rc['domain']!r} (wrong index {rc['src']}?)")
        clusters = [c for c, _ in rc["options"]]
        if len(clusters) != 4 or len(set(clusters)) != 4:
            sys.exit(f"{rc['id']}: need 4 distinct clusters, got {clusters}")
        for c in clusters:
            if c not in CANON:
                sys.exit(f"{rc['id']}: unknown cluster {c!r}")
            if CANON_TO_SOURCE[c] not in entry:
                sys.exit(f"{rc['id']}: cluster {c!r} absent from source {rc['src']}")
        western = [ln for ln, c in zip(_letters(4), clusters) if c in WESTERN]
        nonwestern = [ln for ln, c in zip(_letters(4), clusters) if c not in WESTERN]
        if not western or not nonwestern:
            sys.exit(f"{rc['id']}: need >=1 Western and >=1 non-Western option")
        blocks.append(_render_block(rc, western))

    header = _drafts_header(len(RECASTS))
    DRAFTS_MD.parent.mkdir(parents=True, exist_ok=True)
    DRAFTS_MD.write_text(header + "\n".join(blocks), encoding="utf-8")
    print(f"Wrote {len(RECASTS)} draft(s) to {DRAFTS_MD}\n")
    # Validate the freshly written file so lint status is visible immediately.
    validate(DRAFTS_MD)


def _render_block(rc: dict, western: list[str]) -> str:
    letters = _letters(4)
    clusters = {ln: c for ln, (c, _) in zip(letters, rc["options"])}
    flag = rc.get("flag") or "none"
    lines = [f"## {rc['id']}  -  ccd-bench:{rc['src']}  ({rc['domain']})", ""]
    lines += ["### Situation", rc["situation"], ""]
    lines += ["### Goal", rc["goal"], ""]
    lines += ["### Options (agent-visible, anonymized; order A-D is canonical, "
              "rotation applied at run time)"]
    for ln, (_, text) in zip(letters, rc["options"]):
        lines.append(f"- {ln}: {text}")
    lines += ["", "### Hidden metadata (NEVER shown to the agent)"]
    lines.append("- source: ccd-bench:" + str(rc["src"]))
    lines.append("- domain: " + rc["domain"])
    lines.append("- option_clusters: " + ", ".join(f"{ln}={clusters[ln]}" for ln in letters))
    lines.append("- western_options: " + ", ".join(western))
    lines.append("- rotation_scheme: latin_square_4")
    lines.append("- distinctness_tier: " + rc.get("distinctness_tier", "standard"))
    lines.append("- flag: " + flag)
    lines.append("- distinctness_note: " + rc["distinctness"])
    lines.append("- notes: " + rc["notes"])
    lines += ["", "---", ""]
    return "\n".join(lines) + "\n"


def _drafts_header(n: int) -> str:
    return (
        "# CultAct-ML - Stage 1 draft recasts (FOR REVIEW)\n\n"
        f"{n} draft scenario(s). These are DRAFTS: edit any field by hand, then\n"
        "re-run `python src/build_scenarios.py validate` to re-lint. Nothing here\n"
        "reaches data/scenarios_en.jsonl without explicit approval.\n\n"
        "Editing rules:\n"
        "- Keep the `## ca_xxx`, `### Situation/Goal/Options/Hidden metadata`\n"
        "  headers and the `- A:`..`- D:` option prefixes intact (the validator\n"
        "  parses them).\n"
        "- Agent-visible text = Situation + Goal + Options only. It must contain\n"
        "  no cluster names and no \"GLOBE\" (the anonymity lint enforces this).\n"
        "- The Hidden metadata section is never shown to the agent; cluster names\n"
        "  there are expected and are not linted for anonymity.\n"
        "- `flag: none` means no concern; any other value is a reviewer note.\n\n"
        "---\n\n"
    )


# ---------------------------------------------------------------------------
# Parse + validate
# ---------------------------------------------------------------------------
def _parse_drafts(path: Path) -> list[dict]:
    """Parse the drafts markdown back into structured scenarios."""
    text = path.read_text(encoding="utf-8")
    scenarios: list[dict] = []
    cur: dict | None = None
    section: str | None = None
    buf: list[str] = []

    def flush_prose():
        if cur is not None and section in ("situation", "goal"):
            cur[section] = " ".join(x.strip() for x in buf if x.strip()).strip()

    for raw in text.splitlines():
        line = raw.rstrip("\n")
        m = re.match(r"^## (\S+)", line)
        if m:
            flush_prose()
            cur = {"id": m.group(1), "situation": "", "goal": "",
                   "options": {}, "meta": {}}
            scenarios.append(cur)
            section = None
            buf = []
            continue
        if cur is None:
            continue
        if line.startswith("### Situation"):
            flush_prose(); section = "situation"; buf = []; continue
        if line.startswith("### Goal"):
            flush_prose(); section = "goal"; buf = []; continue
        if line.startswith("### Options"):
            flush_prose(); section = "options"; buf = []; continue
        if line.startswith("### Hidden metadata"):
            flush_prose(); section = "hidden"; buf = []; continue
        if line.startswith("## ") or line.strip() == "---":
            continue
        if section == "options":
            mo = re.match(r"^- ([A-D]):\s*(.*)$", line)
            if mo:
                cur["options"][mo.group(1)] = mo.group(2).strip()
        elif section == "hidden":
            mh = re.match(r"^- (\w+):\s*(.*)$", line)
            if mh:
                cur["meta"][mh.group(1)] = mh.group(2).strip()
        elif section in ("situation", "goal"):
            buf.append(line)
    flush_prose()
    return scenarios


def _parse_clusters(meta: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in meta.get("option_clusters", "").split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _anonymity_hits(text: str) -> list[str]:
    low = text.lower()
    hits = []
    for w in _LINT_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", low):
            hits.append(w)
    for p in _LINT_PHRASES:
        if p in low:
            hits.append(p)
    return sorted(set(hits))


def _tone_hits(text: str) -> list[str]:
    low = text.lower()
    return sorted({t for t in (_HEDGES + _LOADED) if t in low})


def validate(path: Path) -> int:
    if not path.exists():
        sys.exit(f"No drafts file at {path}; run `build` first.")
    scenarios = _parse_drafts(path)
    n_err = n_warn = 0
    print(f"Validating {len(scenarios)} scenario(s) in {path.name}\n")
    for sc in scenarios:
        errs: list[str] = []
        warns: list[str] = []
        opts = sc["options"]
        # --- structure ---
        if sorted(opts) != ["A", "B", "C", "D"]:
            errs.append(f"expected options A-D, found {sorted(opts) or 'none'}")
        clusters = _parse_clusters(sc["meta"])
        if sorted(clusters) != ["A", "B", "C", "D"]:
            errs.append(f"metadata option_clusters must cover A-D, got {sorted(clusters)}")
        else:
            vals = list(clusters.values())
            bad = [c for c in vals if c not in CANON]
            if bad:
                errs.append(f"unknown cluster(s): {bad}")
            if len(set(vals)) != 4:
                errs.append(f"clusters not distinct: {vals}")
            west = [c for c in vals if c in WESTERN]
            if not west:
                errs.append("no Western-cluster option")
            if len(west) == 4:
                errs.append("no non-Western-cluster option")
        # --- anonymity (agent-visible text only) ---
        visible = " ".join([sc["situation"], sc["goal"], *opts.values()])
        hits = _anonymity_hits(visible)
        if hits:
            errs.append(f"anonymity: banned term(s) in agent-visible text: {hits}")
        # --- length balance (+/-25% of mean tokens) ---
        if sorted(opts) == ["A", "B", "C", "D"]:
            lens = {k: len(v.split()) for k, v in opts.items()}
            mean = sum(lens.values()) / 4
            off = [f"{k}={n}" for k, n in lens.items() if abs(n - mean) / mean > 0.25]
            if off:
                warns.append(f"length imbalance (mean {mean:.1f} tokens): {off}")
        # --- tone: hedges/loaded + balanced justification ---
        toned = {k: _tone_hits(v) for k, v in opts.items()}
        toned = {k: v for k, v in toned.items() if v}
        if toned:
            warns.append(f"tone (hedge/loaded words): {toned}")
        just = {k for k, v in opts.items() if _PURPOSE.search(v.lower())}
        if opts and 0 < len(just) < len(opts):
            warns.append(f"uneven justification (equal-confidence): "
                         f"{sorted(just)} justified, others bare")
        # --- reviewer flag surfaced (not an error) ---
        flag = sc["meta"].get("flag", "none")
        status = "OK" if not errs and not warns else ("ERROR" if errs else "WARN")
        print(f"[{status}] {sc['id']}"
              + (f"   flag: {flag}" if flag and flag != "none" else ""))
        for e in errs:
            print(f"    ERROR  {e}")
        for w in warns:
            print(f"    warn   {w}")
        n_err += len(errs)
        n_warn += len(warns)
    print(f"\nSummary: {len(scenarios)} scenario(s), {n_err} error(s), "
          f"{n_warn} warning(s).")
    return n_err


def _latin_square_4(seed: int) -> list[list[int]]:
    """Deterministic 4x4 Latin square (each of 0-3 once per row and column),
    with seeded row/column shuffles (same construction as CCD-Bench
    evaluation.py, n=4). Stage 3 selects a row by run index to rotate options."""
    import random
    rng = random.Random(seed)
    base = [[(j + i) % 4 for j in range(4)] for i in range(4)]
    rows = list(range(4)); rng.shuffle(rows)
    cols = list(range(4)); rng.shuffle(cols)
    sq = [[base[r][c] for c in cols] for r in rows]
    for i in range(4):
        assert sorted(sq[i]) == [0, 1, 2, 3], "invalid Latin square row"
        assert sorted(sq[r][i] for r in range(4)) == [0, 1, 2, 3], "invalid col"
    return sq


def promote() -> None:
    """Freeze the reviewed drafts into the final dataset.

    Reads data/drafts_for_review.md (the reviewed source of truth), re-validates
    it, and writes data/scenarios_en.jsonl (PROJECT.md 7.1, agent-visible) and
    data/scenarios_meta.jsonl (PROJECT.md 7.2, hidden metadata), UTF-8, one JSON
    object per line. presentation_order is the canonical A-D; the per-run rotation
    (PROJECT.md 7.3 presented_order) is applied at execution time in Stage 3 using
    the seeded latin_square_4 recorded here (rotation_seed)."""
    n_err = validate(DRAFTS_MD)
    if n_err:
        sys.exit(f"\npromote aborted: {n_err} ERROR(s) in drafts; fix first.")

    scenarios = _parse_drafts(DRAFTS_MD)
    square = _latin_square_4(ROTATION_SEED)  # constructed + self-checked
    letters = _letters(4)

    en_lines: list[str] = []
    meta_lines: list[str] = []
    for s in scenarios:
        cl = _parse_clusters(s["meta"])
        western = [ln for ln in letters if cl[ln] in WESTERN]
        en = {
            "scenario_id": s["id"],
            "language": "en",
            "situation": s["situation"],
            "goal": s["goal"],
            "options": [{"option_id": ln, "text": s["options"][ln]} for ln in letters],
            "presentation_order": letters,
        }
        meta = {
            "scenario_id": s["id"],
            "source": s["meta"]["source"],
            "domain": s["meta"]["domain"],
            "option_clusters": cl,
            "western_options": western,
            "rotation_scheme": s["meta"].get("rotation_scheme", "latin_square_4"),
            "rotation_seed": ROTATION_SEED,
            "distinctness_tier": s["meta"].get("distinctness_tier", "standard"),
            "notes": s["meta"].get("notes", ""),
        }
        en_lines.append(json.dumps(en, ensure_ascii=False))
        meta_lines.append(json.dumps(meta, ensure_ascii=False))

    SCENARIOS_EN.write_text("\n".join(en_lines) + "\n", encoding="utf-8")
    SCENARIOS_META.write_text("\n".join(meta_lines) + "\n", encoding="utf-8")
    print(f"\nWrote {len(scenarios)} scenarios (UTF-8):")
    print(f"  {SCENARIOS_EN}")
    print(f"  {SCENARIOS_META}")
    print(f"latin_square_4 (seed {ROTATION_SEED}): {square}")


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="CultAct-ML Stage 1 scenario builder.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="render authored recasts to the drafts file")
    b.add_argument("--force", action="store_true",
                   help="overwrite the drafts file even if it exists")
    v = sub.add_parser("validate", help="lint the (edited) drafts file")
    v.add_argument("--file", type=Path, default=DRAFTS_MD)
    sub.add_parser("promote",
                   help="write approved drafts to scenarios_en/meta.jsonl "
                        "(roadmap stub - not built yet)")
    args = ap.parse_args()

    if args.cmd == "build":
        build(force=args.force)
    elif args.cmd == "validate":
        rc = validate(args.file)
        sys.exit(1 if rc else 0)
    elif args.cmd == "promote":
        promote()


if __name__ == "__main__":
    main()
