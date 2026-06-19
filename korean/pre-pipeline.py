#!/usr/bin/env python3
"""
Morning agent pipeline for Korean stock day-trading — variant matrix edition.

Pipeline (per (context, brief, research) variant combination):
  Context Agent (Sonnet, web search) → Brief Agent (Opus, web search) → Research Agent (Opus, web search) → Aggregator
  → Top 5 picks per track (Large/Mega + Mid)

Variants are configured at the top of this file. The script runs the cartesian product of
(CONTEXT_VARIANTS × BRIEF_VARIANTS × RESEARCH_VARIANTS) and writes one set of outputs per combo.

Setup:
    export ANTHROPIC_API_KEY=sk-ant-...   (or put it in .env at the project root)
    pip3 install anthropic

Usage:
    python3 pre-pipeline.py                       # run all configured combinations
    python3 pre-pipeline.py --context context.txt # skip context agent (single context)
    python3 pre-pipeline.py --date 2026-06-10     # override date

Outputs (saved to data/{date}/):
    {date}-context-{cv}.txt                       — one file per context variant (cached/reused if present)
    {date}-picks-{cv}-{bv}-{rv}.json              — full pipeline output per combo
    {date}-reasoning-{cv}-{bv}-{rv}.md            — human-readable summary per combo
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime
from pathlib import Path
from itertools import product


# ============================================================
# Variant configuration — edit these to run more combinations
# ============================================================

CONTEXT_VARIANTS = ["v1", "v3"]
BRIEF_VARIANTS = ["v1", "v3"]
RESEARCH_VARIANTS = ["v1", "v3"]

# If True, only run paired combos (v2-v2-v2, v3-v3-v3) instead of full cartesian product.
PAIRED_ONLY = True

# ============================================================
# Mechanical post-research filters (apply at aggregate_top_5 stage)
# These enforce rules that the LLM is supposed to follow but often doesn't.
# ============================================================

# E4: SELF-CONTRADICTION mechanical regex check.
# If any of these tokens appear in research_reasoning, the candidate is dropped
# from final picks regardless of score. Mirrors research_agent_v3 E4 wording.
#
# Group A: explicit hedge phrases (06-15/16 lessons).
# Group B: self-labeled disqualifier (06-18 lesson — LLM names the rule it's violating
#          while still picking the stock, e.g. "E3 발동", "P4 적용", "dated catalyst 미보유").
E4_DISQUALIFIER_PATTERNS = [
    # Group A — hedge / contradiction phrases
    "후순위", "강도 약함", "강도 제한", "대비 약함",
    "catalyst 부재", "catalyst가 부재", "고유 catalyst는 부재", "고유 catalyst 부재",
    "제한적", "우려", "부재",
    "압력 가능", "차익실현 압력", "분배 위험", "리스크 잔존", "신호 약함",
    "단순 sympathy", "sympathy play", "후행", "둔화",
    # Group B — self-labeled disqualifier (06-18 lesson)
    "E1 발동", "E2 발동", "E3 발동", "E5 발동",
    "P3 적용", "P4 적용", "P5 적용", "P6 적용",
    "dated catalyst 미보유", "5거래일 경과", "5거래일 이상 경과", "구조 붕괴",
    "momentum 구조 붕괴",
]

# E5: previous-day spike threshold. Candidates with prev_day_change_pct >= this are dropped.
E5_PREV_DAY_SPIKE_PCT = 15.0

# D1: max same-sub_theme picks allowed in final 5.
D1_MAX_PER_SUB_THEME = 2

# E6: ticker that hit SL >= this many times in the last N trading days → EXCLUDE.
# Detects narrative-attached repeat-loser names (e.g. HD현대일렉트릭 06-12 SL, 06-16 양 트랙 SL).
E6_RECENT_LOSER_LOOKBACK_DAYS = 5
E6_RECENT_LOSER_SL_THRESHOLD = 2

# CROSS_TRACK_DEDUP: if a ticker appears in both Track A and Track B candidate lists, keep it
# only in Track A (KOSPI large/mega listing takes precedence). Prevents the 06-16 HD현대일렉트릭
# double-pick that caused matching SLs in both tracks.
CROSS_TRACK_DEDUP_ENABLED = True


# ============================================================
# Minimal .env loader (kept here so this file is self-contained)
# ============================================================

def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


PROJECT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_ROOT.parent
DATA_DIR = PROJECT_ROOT / "data"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

_load_dotenv(REPO_ROOT / ".env")


try:
    from anthropic import Anthropic
except ImportError:
    print("Install: pip3 install anthropic")
    sys.exit(1)


# ============================================================
# Configuration
# ============================================================

SONNET_MODEL = "claude-sonnet-4-6"   # supports temperature
OPUS_MODEL = "claude-opus-4-7"       # does NOT support temperature

SONNET_TEMPERATURE = 0.1
MAX_TOKENS = 8192

WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 8,
}


# ============================================================
# Prompt loading
# ============================================================

def load_prompt(name: str) -> str:
    """Load prompt file from prompts/ folder. Raises if missing."""
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


# ============================================================
# API helpers — separate functions per model since they have different params
# ============================================================

def _extract_text(response):
    text_parts = []
    for block in response.content:
        if hasattr(block, "type") and block.type == "text":
            text_parts.append(block.text)
        elif hasattr(block, "text"):
            text_parts.append(block.text)
    return "\n".join(text_parts).strip()


def call_sonnet(system, user, use_web_search=True):
    """Sonnet supports temperature. Used for context summarization."""
    client = Anthropic()
    kwargs = {
        "model": SONNET_MODEL,
        "max_tokens": MAX_TOKENS,
        "temperature": SONNET_TEMPERATURE,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    if use_web_search:
        kwargs["tools"] = [WEB_SEARCH_TOOL]
    response = client.messages.create(**kwargs)
    return _extract_text(response)


def call_opus(system, user, use_web_search=True):
    """Opus 4.7+ does NOT accept temperature. Used for brief + research."""
    client = Anthropic()
    kwargs = {
        "model": OPUS_MODEL,
        "max_tokens": MAX_TOKENS,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    if use_web_search:
        kwargs["tools"] = [WEB_SEARCH_TOOL]
    response = client.messages.create(**kwargs)
    return _extract_text(response)


def extract_json(text, expected_key=None):
    """
    Extract the first valid top-level JSON object from `text`.

    Robust to:
    - Markdown code fences (```json ... ```)
    - Trailing prose after the JSON (model ignored "JSON only" instruction)
    - Leading prose / reasoning before the JSON
    - Placeholder JSON blocks like `{"scored": [...]}` that appear before the real payload
      (model emits a "let me show the schema" preamble — we skip those and find the real one)

    Strategy: scan every `{` position, try raw_decode at each. If `expected_key` is
    provided, prefer the first object that contains that key. Otherwise return the
    first object that parses.
    """
    text = text.strip()

    # Strip outer markdown fence if present
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
        if match:
            text = match.group(1)

    decoder = json.JSONDecoder(strict=False)
    candidates = []
    last_error = None

    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except json.JSONDecodeError as e:
            last_error = e
            continue
        if not isinstance(obj, dict):
            continue
        candidates.append(obj)
        if expected_key is not None and expected_key in obj and obj[expected_key]:
            # Reject obvious placeholder values (e.g. the string "..." or list with placeholder).
            val = obj[expected_key]
            if isinstance(val, list) and len(val) == 0:
                continue
            return obj

    if candidates:
        # No exact match with expected_key — return the first/largest candidate.
        if expected_key:
            for obj in candidates:
                if expected_key in obj:
                    return obj
        return candidates[0]

    snippet = text[:800]
    raise ValueError(
        f"Failed to parse JSON (last error: {last_error})\n--- snippet ---\n{snippet}"
    )


# ============================================================
# Pipeline stages — variant-aware
# ============================================================

def run_context_agent(target_date, variant):
    template = load_prompt(f"context_agent_{variant}")
    system = template.replace("{date}", target_date)
    user = f"Generate today's market briefing for {target_date}."
    return call_sonnet(system, user, use_web_search=True)


_RAW_DEBUG_DIR = None     # set in run_one_combo — raw responses land in raw_debug/
_CHECKPOINT_DIR = None    # set in run_one_combo — per-combo stage checkpoints land here


def _save_raw_response(label, response):
    """Persist a raw LLM response to disk so failed combos can be inspected."""
    if _RAW_DEBUG_DIR is None:
        return
    try:
        _RAW_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        path = _RAW_DEBUG_DIR / f"raw-{label}.txt"
        path.write_text(response, encoding="utf-8")
    except Exception:
        pass


# ------------------------------------------------------------
# Parsing-agent fallback: if extract_json fails on the primary response, ship the raw
# text to a cheap Sonnet call (no web search) that reconstructs the expected JSON shape.
# Designed for cases where the primary model emitted a placeholder, used a wrong key,
# wrapped JSON in fences with extra prose, or otherwise produced malformed-but-recoverable
# output. The parsing agent NEVER does new research — only re-shapes the raw text.
# ------------------------------------------------------------

def call_parsing_agent(raw_text, expected_key):
    """Cheap recovery LLM. Returns the parsed list/dict for `expected_key`, or raises."""
    system = (
        f"You are a JSON extractor. The input below is a raw LLM response that was "
        f"supposed to contain a JSON object with the top-level key \"{expected_key}\". "
        f"It may have any of these problems: surrounding prose, markdown fences, the "
        f"wrong key name, malformed JSON syntax, placeholder values (\"...\" literal), "
        f"or the key entirely missing. Your job: reconstruct a SINGLE valid JSON object "
        f"with the key \"{expected_key}\" containing the intended payload. Do NOT invent "
        f"data — only reshape what's already there. If the payload is genuinely empty "
        f"or only a placeholder, return {{\"{expected_key}\": []}}. Return ONLY raw JSON, "
        f"no markdown, no preamble, no commentary."
    )
    user = f"Raw response to recover:\n\n{raw_text}"
    response = call_sonnet(system, user, use_web_search=False)
    obj = extract_json(response, expected_key=expected_key)
    if expected_key not in obj:
        raise KeyError(f"parsing agent did not produce '{expected_key}' key")
    return obj[expected_key]


def _safe_extract(response, expected_key, debug_label):
    """
    Two-level parser:
      1. Try `extract_json` (regex/decoder based — handles most cases).
      2. If that fails (or the parsed object is missing the key), retry via the
         parsing-agent fallback above.
    Raw is saved to raw_debug/ regardless so a manual inspection is always possible.
    """
    _save_raw_response(debug_label, response)

    primary_err = None
    try:
        obj = extract_json(response, expected_key=expected_key)
        if expected_key in obj:
            return obj[expected_key]
        primary_err = KeyError(
            f"missing '{expected_key}'; got keys: {list(obj.keys()) if isinstance(obj, dict) else type(obj).__name__}"
        )
    except (ValueError, KeyError) as e:
        primary_err = e

    print(
        f"    [parse] primary parse failed ({primary_err}); invoking parsing agent fallback...",
        file=sys.stderr,
    )
    try:
        return call_parsing_agent(response, expected_key)
    except Exception as fallback_err:
        raw_path = (_RAW_DEBUG_DIR / f"raw-{debug_label}.txt") if _RAW_DEBUG_DIR else "(unsaved)"
        raise KeyError(
            f"Both primary parse and parsing agent failed for '{expected_key}'.\n"
            f"  Primary: {primary_err}\n"
            f"  Fallback: {fallback_err}\n"
            f"  Raw saved to: {raw_path}"
        )


# ------------------------------------------------------------
# Stage-level checkpoint: persist raw + parsed response per (combo, stage) so a partial
# pipeline can resume from the failure point without re-running upstream (expensive)
# web-search LLM calls.
#
# Resume policy:
#   - If `<stage>.parsed.json` exists → return it directly (no LLM, no parsing).
#   - Else if `<stage>.raw.txt` exists → re-parse only (no LLM call).
#   - Else → call the LLM, save raw, parse (with parsing-agent fallback), save parsed.
#
# Cleanup: end of main() removes the checkpoint root after ALL combos succeed.
# ------------------------------------------------------------

def _checkpoint_paths(stage_key):
    if _CHECKPOINT_DIR is None:
        return None, None
    return (
        _CHECKPOINT_DIR / f"{stage_key}.raw.txt",
        _CHECKPOINT_DIR / f"{stage_key}.parsed.json",
    )


def _load_parsed_checkpoint(stage_key):
    _, parsed_path = _checkpoint_paths(stage_key)
    if parsed_path and parsed_path.is_file():
        try:
            return json.loads(parsed_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _save_parsed_checkpoint(stage_key, payload):
    _, parsed_path = _checkpoint_paths(stage_key)
    if parsed_path:
        parsed_path.parent.mkdir(parents=True, exist_ok=True)
        parsed_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def _load_raw_checkpoint(stage_key):
    raw_path, _ = _checkpoint_paths(stage_key)
    if raw_path and raw_path.is_file():
        return raw_path.read_text(encoding="utf-8")
    return None


def _save_raw_checkpoint(stage_key, raw_text):
    raw_path, _ = _checkpoint_paths(stage_key)
    if raw_path:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(raw_text, encoding="utf-8")


def _run_stage(stage_key, expected_key, llm_call_fn):
    """Generic stage runner with two-level checkpoint + parsing-agent fallback."""
    parsed = _load_parsed_checkpoint(stage_key)
    if parsed is not None:
        print(f"    [checkpoint] {stage_key}: reusing parsed payload from disk", file=sys.stderr)
        return parsed

    raw = _load_raw_checkpoint(stage_key)
    if raw is not None:
        print(f"    [checkpoint] {stage_key}: raw exists, re-parsing only (no LLM call)", file=sys.stderr)
    else:
        raw = llm_call_fn()
        _save_raw_checkpoint(stage_key, raw)

    parsed = _safe_extract(raw, expected_key, stage_key)
    _save_parsed_checkpoint(stage_key, parsed)
    return parsed


def run_brief_agent(track, context, target_date, brief_variant, combo_id=""):
    """
    Brief variant determines which prompt + which universe filter to use.
    Universe is paired with the brief variant: universe_track_a_{brief_variant}.txt etc.
    """
    universe_name = f"universe_track_{'a' if track == 'A' else 'b'}_{brief_variant}"
    universe = load_prompt(universe_name)
    template = load_prompt(f"brief_agent_{brief_variant}")
    system = template.replace("{universe_filter}", universe).replace("{date}", target_date)
    user = f"Today's market context:\n\n{context}"
    stage_key = f"brief-{track.lower()}"
    return _run_stage(
        stage_key,
        "candidates",
        lambda: call_opus(system, user, use_web_search=True),
    )


def run_research_agent(candidates, context, target_date, research_variant, track="", combo_id=""):
    template = load_prompt(f"research_agent_{research_variant}")
    system = template.replace("{date}", target_date)
    candidates_str = json.dumps(candidates, ensure_ascii=False, indent=2)
    user = f"Today's market context:\n\n{context}\n\nCandidates to score:\n\n{candidates_str}"
    stage_key = f"research-{track.lower()}"
    return _run_stage(
        stage_key,
        "scored",
        lambda: call_opus(system, user, use_web_search=True),
    )


def _check_e4_self_contradiction(text):
    """Return the first disqualifier pattern found in `text`, or None."""
    if not text or not isinstance(text, str):
        return None
    for pattern in E4_DISQUALIFIER_PATTERNS:
        if pattern in text:
            return pattern
    return None


# ============================================================
# E6: recent-loser scan (loads past market_data files)
# ============================================================

def _load_recent_loser_set(data_dir, target_date_str, lookback_days, sl_threshold, sl_pct=3.0):
    """
    Walk backwards from target_date for up to `lookback_days * 3` calendar days, loading
    `data/{date}/market_data_{date}.json` (skipping weekends/holidays automatically since they
    have no file). Count UNIQUE trading days on which each ticker hit SL
    (open_to_low_pct <= -sl_pct) in any combo/track. Tickers with hit-day count >=
    sl_threshold are returned for E6 exclusion, paired with metadata for logging.
    """
    from datetime import datetime, timedelta
    try:
        target = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        return {}, []

    hit_days = {}  # ticker → {date_str: (name, worst_ol_pct)}
    days_loaded = 0
    days_checked = 0
    while days_loaded < lookback_days and days_checked < lookback_days * 3:
        days_checked += 1
        d = target - timedelta(days=days_checked)
        d_str = d.strftime("%Y-%m-%d")
        md_path = data_dir / d_str / f"market_data_{d_str}.json"
        if not md_path.is_file():
            continue
        days_loaded += 1
        try:
            data = json.loads(md_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        threshold = -abs(data.get("sl_pct", sl_pct))
        # Collect ticker → worst_ol_pct on THIS day across all combos/tracks.
        day_min = {}
        day_name = {}
        for combo in data.get("combos", []):
            for track_key in ("track_a", "track_b"):
                for s in combo.get(track_key, []) or []:
                    ol = s.get("open_to_low_pct")
                    if ol is None:
                        continue
                    t = s["ticker"]
                    if t not in day_min or ol < day_min[t]:
                        day_min[t] = ol
                        day_name[t] = s.get("name", "-")
        for t, ol in day_min.items():
            if ol <= threshold:
                hit_days.setdefault(t, {})[d_str] = (day_name[t], ol)

    losers = {t: days for t, days in hit_days.items() if len(days) >= sl_threshold}
    info = []
    for t, days in sorted(losers.items(), key=lambda x: -len(x[1])):
        name = next(iter(days.values()))[0]
        date_strs = sorted(days.keys())
        info.append(f"{t} ({name}): SL on {len(days)} days [{', '.join(date_strs)}]")
    return losers, info


# ============================================================
# Cross-track dedup (Track A precedence)
# ============================================================

def dedup_across_tracks(track_a_candidates, track_b_candidates):
    """
    If a ticker appears in both Track A and Track B candidate lists, remove it from
    Track B. Track A (KOSPI large/mega) takes precedence. Returns (clean_b, dropped).
    """
    a_tickers = {c["ticker"] for c in track_a_candidates}
    clean_b = []
    dropped = []
    for c in track_b_candidates:
        if c["ticker"] in a_tickers:
            c = {**c, "filter_excluded_by": "CROSS_TRACK_DEDUP:already in Track A"}
            dropped.append(c)
        else:
            clean_b.append(c)
    return clean_b, dropped


def _apply_mechanical_filters(merged, research_variant, recent_losers=None):
    """
    Apply mechanical checks. Adds `filter_excluded_by` tag to dropped picks.
    - E4 (self-contradiction) / E5 (prev_day spike): v3+ only (depend on v3 prompt fields).
    - E6 (recent loser): UNIVERSAL — applies to all variants since it's pure history scan.
    Returns (eligible, excluded) lists, both sorted by score descending.
    """
    recent_losers = recent_losers or {}
    eligible = []
    excluded = []

    apply_v3_rules = research_variant not in ("v1", "v2")

    for p in merged:
        ticker = p.get("ticker")

        # E6 (universal): ticker hit SL on N distinct days in last lookback window
        if ticker in recent_losers:
            sl_days = len(recent_losers[ticker])
            p["filter_excluded_by"] = f"E6:recent_loser SL on {sl_days} days in last {E6_RECENT_LOSER_LOOKBACK_DAYS} trading days"
            excluded.append(p)
            continue

        if apply_v3_rules:
            # E4: self-contradiction in research reasoning
            reasoning_to_check = p.get("research_reasoning") or p.get("reasoning") or ""
            hit = _check_e4_self_contradiction(reasoning_to_check)
            if hit:
                p["filter_excluded_by"] = f"E4:'{hit}'"
                excluded.append(p)
                continue
            # E5: prev-day spike
            prev_day = p.get("prev_day_change_pct")
            if isinstance(prev_day, (int, float)) and prev_day >= E5_PREV_DAY_SPIKE_PCT:
                p["filter_excluded_by"] = f"E5:prev_day={prev_day:+.1f}%"
                excluded.append(p)
                continue

        eligible.append(p)
    return eligible, excluded


def _apply_d1_diversification(eligible, research_variant):
    """
    Enforce D1: final 5 picks have at most D1_MAX_PER_SUB_THEME from the same sub_theme.
    Walks the score-sorted eligible list and skips candidates that would exceed the cap.
    Only active for research v3+.
    Returns (final_picks_up_to_5, dropped_by_d1).
    """
    if research_variant in ("v1", "v2"):
        return eligible[:5], []

    final = []
    dropped = []
    sub_counts = {}
    for p in eligible:
        sub = (p.get("sub_theme") or "unknown").strip()
        cnt = sub_counts.get(sub, 0)
        if cnt >= D1_MAX_PER_SUB_THEME:
            p["filter_excluded_by"] = f"D1:sub_theme '{sub}' already has {cnt}"
            dropped.append(p)
            continue
        final.append(p)
        sub_counts[sub] = cnt + 1
        if len(final) >= 5:
            break
    return final, dropped


def aggregate_top_5(candidates, scored, research_variant="v1", recent_losers=None):
    """Merge brief + research results, preserving sources from both."""
    scored_dict = {s["ticker"]: s for s in scored}
    merged = []
    for c in candidates:
        s = scored_dict.get(c["ticker"])
        brief_sources = c.get("sources") or []
        if s:
            research_sources = s.get("sources") or []
            combined = {**c, **s}
            combined["brief_reasoning"] = c.get("reasoning")
            combined["research_reasoning"] = s.get("reasoning")
            # `reasoning` after merge is research's (more recent). Keep both for transparency.
            combined["sources"] = brief_sources + research_sources
            merged.append(combined)
        else:
            merged.append({
                **c,
                "score": 0,
                "signals_present": [],
                "reasoning": "(not scored)",
                "brief_reasoning": c.get("reasoning"),
                "research_reasoning": None,
                "sources": brief_sources,
            })
    merged.sort(key=lambda x: -x.get("score", 0))

    # Mechanical filters (E4/E5 v3-only, E6 universal), then D1 diversification.
    eligible, excluded_filters = _apply_mechanical_filters(merged, research_variant, recent_losers)
    final, dropped_d1 = _apply_d1_diversification(eligible, research_variant)

    # Log filtered exclusions to stderr for visibility.
    for p in excluded_filters:
        print(f"    [filter] dropped {p.get('ticker')} {p.get('name','-')} ({p.get('filter_excluded_by')})", file=sys.stderr)
    for p in dropped_d1:
        print(f"    [filter] D1 skip  {p.get('ticker')} {p.get('name','-')} ({p.get('filter_excluded_by')})", file=sys.stderr)

    audit = {
        "excluded_by_filters": [
            {"ticker": p.get("ticker"), "name": p.get("name"), "reason": p.get("filter_excluded_by")}
            for p in excluded_filters
        ],
        "dropped_by_d1": [
            {"ticker": p.get("ticker"), "name": p.get("name"), "reason": p.get("filter_excluded_by")}
            for p in dropped_d1
        ],
    }
    return final, audit


# ============================================================
# Output generation
# ============================================================

def _format_sources(sources):
    if not sources:
        return ""
    lines = []
    for src in sources:
        if not isinstance(src, dict):
            continue
        publisher = src.get("publisher") or "?"
        url = src.get("url") or ""
        date = src.get("date") or ""
        label = f"{publisher}" + (f", {date}" if date else "")
        if url:
            lines.append(f"  - [{label}]({url})")
        else:
            lines.append(f"  - {label}")
    return "\n".join(lines)


def generate_reasoning_md(date, combo_id, context, track_a, track_b):
    cv, bv, rv = combo_id.split("-")
    lines = [f"# Morning Reasoning — {date}  ({combo_id})\n"]
    lines.append(f"_Variants: context={cv}, brief={bv}, research={rv}_\n")
    lines.append("## Market Context\n")
    lines.append(context.strip())
    lines.append("")

    for track_name, picks in [("A — Large/Mega Cap", track_a), ("B — Mid Cap", track_b)]:
        lines.append(f"\n## Track {track_name} — Top 5 Picks\n")
        for i, p in enumerate(picks, 1):
            lines.append(f"### {i}. {p.get('ticker', '-')} {p.get('name', '-')}")
            lines.append(f"- **Score:** {p.get('score', '-')}/5")
            lines.append(f"- **Market:** {p.get('market', '-')}")
            lines.append(f"- **Estimated cap:** {p.get('estimated_cap_tier', '-')}")
            lines.append(f"- **Primary signal:** {p.get('primary_signal', '-')}")
            lines.append(f"- **Signals present:** {', '.join(p.get('signals_present', []))}")
            if p.get("brief_reasoning"):
                lines.append(f"- **Brief reasoning:** {p['brief_reasoning']}")
            if p.get("research_reasoning"):
                lines.append(f"- **Research reasoning:** {p['research_reasoning']}")
            elif p.get("reasoning"):
                lines.append(f"- **Reasoning:** {p['reasoning']}")
            sources_md = _format_sources(p.get("sources", []))
            if sources_md:
                lines.append(f"- **Sources:**")
                lines.append(sources_md)
            lines.append("")

    return "\n".join(lines)


# ============================================================
# Per-combo runner
# ============================================================

def run_one_combo(target_date, output_dir, context, cv, bv, rv, recent_losers=None):
    global _RAW_DEBUG_DIR, _CHECKPOINT_DIR
    combo_id = f"{cv}-{bv}-{rv}"
    _RAW_DEBUG_DIR = output_dir / "raw_debug"
    _CHECKPOINT_DIR = output_dir / "_checkpoints" / combo_id
    print(f"\n--- Combo {combo_id} ---", file=sys.stderr)

    print(f"[{combo_id}] Track A brief (Opus, large/mega cap)...", file=sys.stderr)
    track_a_candidates = run_brief_agent("A", context, target_date, bv, combo_id=combo_id)
    print(f"  Got {len(track_a_candidates)} candidates", file=sys.stderr)

    print(f"[{combo_id}] Track B brief (Opus, mid cap)...", file=sys.stderr)
    track_b_candidates = run_brief_agent("B", context, target_date, bv, combo_id=combo_id)
    print(f"  Got {len(track_b_candidates)} candidates", file=sys.stderr)

    # Cross-track dedup: drop Track B candidates that also appear in Track A (Track A wins).
    dedup_dropped = []
    if CROSS_TRACK_DEDUP_ENABLED:
        track_b_candidates, dedup_dropped = dedup_across_tracks(track_a_candidates, track_b_candidates)
        for p in dedup_dropped:
            print(f"    [cross-track] dropped {p.get('ticker')} {p.get('name','-')} from B (already in A)", file=sys.stderr)

    print(f"[{combo_id}] Track A research (Opus, scoring)...", file=sys.stderr)
    track_a_scored = run_research_agent(track_a_candidates, context, target_date, rv, track="A", combo_id=combo_id)
    track_a_picks, track_a_audit = aggregate_top_5(track_a_candidates, track_a_scored, research_variant=rv, recent_losers=recent_losers)

    print(f"[{combo_id}] Track B research (Opus, scoring)...", file=sys.stderr)
    track_b_scored = run_research_agent(track_b_candidates, context, target_date, rv, track="B", combo_id=combo_id)
    track_b_picks, track_b_audit = aggregate_top_5(track_b_candidates, track_b_scored, research_variant=rv, recent_losers=recent_losers)

    cross_track_audit = [
        {"ticker": p.get("ticker"), "name": p.get("name"), "reason": p.get("filter_excluded_by")}
        for p in dedup_dropped
    ]

    picks_data = {
        "date": target_date,
        "combo_id": combo_id,
        "variants": {"context": cv, "brief": bv, "research": rv},
        "models": {
            "context": SONNET_MODEL,
            "brief": OPUS_MODEL,
            "research": OPUS_MODEL,
        },
        "context": context,
        "track_a_large_mega": {
            "candidates": track_a_candidates,
            "scored": track_a_scored,
            "final_picks": track_a_picks,
            "filter_audit": track_a_audit,
        },
        "track_b_mid": {
            "candidates": track_b_candidates,
            "scored": track_b_scored,
            "final_picks": track_b_picks,
            "filter_audit": track_b_audit,
        },
        "cross_track_dedup": cross_track_audit,
    }

    picks_path = output_dir / f"{target_date}-picks-{combo_id}.json"
    picks_path.write_text(json.dumps(picks_data, ensure_ascii=False, indent=2))

    md_content = generate_reasoning_md(target_date, combo_id, context, track_a_picks, track_b_picks)
    md_path = output_dir / f"{target_date}-reasoning-{combo_id}.md"
    md_path.write_text(md_content)

    return {
        "combo_id": combo_id,
        "track_a_picks": track_a_picks,
        "track_b_picks": track_b_picks,
        "picks_path": picks_path,
        "md_path": md_path,
    }


# ============================================================
# Context loading / caching
# ============================================================

def get_or_run_context(target_date, output_dir, cv, override_path=None):
    """
    Returns the context text for a given context variant. Caches to/reads from disk:
      {output_dir}/{date}-context-{cv}.txt

    If `override_path` is provided (--context flag), that file is loaded and reused for ALL
    context variants — useful when iterating only on brief/research while keeping context fixed.
    """
    if override_path is not None:
        return Path(override_path).read_text(encoding="utf-8")

    cached = output_dir / f"{target_date}-context-{cv}.txt"
    if cached.is_file():
        text = cached.read_text(encoding="utf-8")
        if text.strip():
            print(f"  [Context {cv}] Reusing cached {cached.name}", file=sys.stderr)
            return text

    print(f"  [Context {cv}] Running context agent (Sonnet + web search)...", file=sys.stderr)
    text = run_context_agent(target_date, cv)
    if not text.strip():
        raise RuntimeError(f"Empty context returned for variant {cv}")
    cached.write_text(text, encoding="utf-8")
    print(f"  [Context {cv}] Saved to {cached}", file=sys.stderr)
    return text


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", default=None,
                        help="Path to existing market context file (used for ALL context variants — skips context agent)")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    target_date = args.date or datetime.now().strftime("%Y-%m-%d")
    # Always write under the script's own folder (korean/), not the caller's CWD.
    output_dir = DATA_DIR / target_date
    output_dir.mkdir(parents=True, exist_ok=True)

    if PAIRED_ONLY:
        shared = [v for v in CONTEXT_VARIANTS if v in BRIEF_VARIANTS and v in RESEARCH_VARIANTS]
        combos = [(v, v, v) for v in shared]
    else:
        combos = list(product(CONTEXT_VARIANTS, BRIEF_VARIANTS, RESEARCH_VARIANTS))

    print(f"\n=== Morning Pipeline for {target_date} ===", file=sys.stderr)
    print(f"Models: context={SONNET_MODEL}, brief={OPUS_MODEL}, research={OPUS_MODEL}", file=sys.stderr)
    print(f"Variants: context={CONTEXT_VARIANTS} brief={BRIEF_VARIANTS} research={RESEARCH_VARIANTS}", file=sys.stderr)
    print(f"Total combinations: {len(combos)}", file=sys.stderr)

    # Resolve contexts up-front (one fetch per unique context variant)
    print(f"\n[Stage 1/2] Resolving contexts...", file=sys.stderr)
    context_cache = {}
    for cv in CONTEXT_VARIANTS:
        try:
            context_cache[cv] = get_or_run_context(target_date, output_dir, cv, override_path=args.context)
            print(f"  [Context {cv}] length: {len(context_cache[cv])} chars", file=sys.stderr)
        except Exception as e:
            print(f"\nERROR resolving context variant {cv}: {e}", file=sys.stderr)
            sys.exit(1)

    # E6: pre-load recent-loser set from the last N trading days of market_data files.
    recent_losers, recent_losers_info = _load_recent_loser_set(
        DATA_DIR, target_date, E6_RECENT_LOSER_LOOKBACK_DAYS, E6_RECENT_LOSER_SL_THRESHOLD,
    )
    if recent_losers:
        print(f"\n[E6] Recent-loser set ({len(recent_losers)} tickers, lookback={E6_RECENT_LOSER_LOOKBACK_DAYS}d, SL≥{E6_RECENT_LOSER_SL_THRESHOLD}):", file=sys.stderr)
        for line in recent_losers_info:
            print(f"  - {line}", file=sys.stderr)
    else:
        print(f"\n[E6] No recent losers found in last {E6_RECENT_LOSER_LOOKBACK_DAYS} trading days.", file=sys.stderr)

    # Run each combo
    print(f"\n[Stage 2/2] Running {len(combos)} combination(s)...", file=sys.stderr)
    results = []
    failures = []
    for cv, bv, rv in combos:
        try:
            res = run_one_combo(target_date, output_dir, context_cache[cv], cv, bv, rv, recent_losers=recent_losers)
            results.append(res)
        except Exception as e:
            combo_id = f"{cv}-{bv}-{rv}"
            print(f"\nERROR in combo {combo_id}: {e}", file=sys.stderr)
            failures.append((combo_id, str(e)))

    # Summary
    print(f"\n{'=' * 70}")
    print(f"VARIANT MATRIX SUMMARY — {target_date}")
    print(f"{'=' * 70}")
    print(f"{'combo_id':<14}  {'A picks':<35}  {'B picks':<35}")
    print(f"{'-' * 14}  {'-' * 35}  {'-' * 35}")
    for r in results:
        a = ",".join(p.get("ticker", "?") for p in r["track_a_picks"])
        b = ",".join(p.get("ticker", "?") for p in r["track_b_picks"])
        print(f"{r['combo_id']:<14}  {a:<35}  {b:<35}")
    if failures:
        print(f"\nFailures ({len(failures)}):")
        for cid, err in failures:
            print(f"  - {cid}: {err}")
        print(
            f"\n[checkpoint] Stage cache RETAINED at {output_dir / '_checkpoints'} — "
            f"re-run will resume failed stage(s) without re-calling upstream LLMs.",
            file=sys.stderr,
        )
    else:
        # All combos succeeded → drop the per-combo checkpoint cache.
        ck_root = output_dir / "_checkpoints"
        if ck_root.exists():
            import shutil
            try:
                shutil.rmtree(ck_root)
                print(f"\n[checkpoint] All combos succeeded — cleaned up {ck_root}", file=sys.stderr)
            except Exception as e:
                print(f"\n[checkpoint] Cleanup of {ck_root} failed: {e}", file=sys.stderr)

    # Convenience CLI hint for end-of-day script
    if results:
        print(f"\nFor end-of-day: post-pipeline.py auto-detects all picks-*.json in data/{target_date}/")
        print(f"Manual override examples (per combo):")
        for r in results[:3]:
            ta = ",".join(p["ticker"] for p in r["track_a_picks"])
            tb = ",".join(p["ticker"] for p in r["track_b_picks"])
            print(f"  [{r['combo_id']}] --large {ta} --mid {tb}")

    print(f"\nDone. Wrote {len(results)} combo(s) to {output_dir}/")
    if failures:
        sys.exit(2)


if __name__ == "__main__":
    main()
