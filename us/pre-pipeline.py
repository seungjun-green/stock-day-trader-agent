#!/usr/bin/env python3
"""
Morning agent pipeline for US stock day-trading — variant matrix edition.

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
    python3 pre-pipeline.py --date 2026-06-10     # override date (US trading day, ET)

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

CONTEXT_VARIANTS = ["v1"]
BRIEF_VARIANTS = ["v1"]
RESEARCH_VARIANTS = ["v1"]


# ============================================================
# Mechanical post-research filters (apply at aggregate_top_5 stage)
# Universal rules — enforce regardless of prompt variant since they're data-driven.
# (Korean-specific E4 self-contradiction patterns / E5 / D1 are omitted here — they
# depend on Korean prompt v3 fields and language tokens.)
# ============================================================

# E6: ticker that hit SL on N distinct trading days in the last lookback window → EXCLUDE.
# Detects narrative-attached repeat-loser names (e.g. picks that keep failing on the same name).
E6_RECENT_LOSER_LOOKBACK_DAYS = 5
E6_RECENT_LOSER_SL_THRESHOLD = 2

# CROSS_TRACK_DEDUP: if a ticker appears in both Track A and Track B candidate lists, keep it
# only in Track A (large/mega listing takes precedence). Prevents double-pick that would cause
# matching SLs in both tracks.
CROSS_TRACK_DEDUP_ENABLED = True

# E4 (US edition): English-language self-contradiction patterns.
# Calibrated from the 06-12, 06-16, 06-17 picks. Phrases in this list, when present in the
# research_reasoning text, indicate the LLM picked a stock while explicitly flagging its own
# bear case (e.g. "valuation is stretched", "already extended after Monday's pop").
#
# Calibration notes:
# - Conservatism: only phrases that are unambiguously bearish *about the pick itself* are
#   included. Generic words like "headwind", "lagged", "secondary play" are EXCLUDED because
#   they can appear in legitimate winners (e.g. IREN 06-17 said "tech rotation headwind today
#   reduces score by 1 from a base 5" — that's the model showing its work on a soft penalty,
#   not contradicting the pick).
# - Specificity: "faces headwinds" is included because it consistently appears in
#   contradicting picks (UPST 06-17). "headwind" alone would false-positive on IREN.
# - Match is case-insensitive substring.
E4_DISQUALIFIER_PATTERNS_US = [
    # --- valuation/exhaustion family (06-17 lesson: CAT/RCL/UPST) ---
    "stretched",                       # CAT 06-17 ("valuation is stretched")
    "already extended",                # RCL 06-17 ("already extended after Monday's pop")
    "extended after",                  # variant of above
    "overbought",
    "exhausted",
    "sell-the-news",
    "sell the news",
    "fully priced",
    "already priced",
    "faces headwinds",                 # UPST 06-17 ("faces headwinds into hawkish FOMC")
    "extension risk",
    "liquidity-drain",
    "liquidity drain",
    # --- catalyst-absence family (06-18 lesson: COIN/ONTO/VKTX/AGX/FORM) ---
    # Research text directly admits no fresh stock-specific catalyst — these picks
    # consistently SL or HOLD-near-zero. The model writes its own contradiction.
    "no stock-specific catalyst",      # COIN 06-18 ("Single-theme alignment without a stock-specific catalyst today")
    "no company-specific catalyst",    # ONTO 06-18 ("No company-specific catalyst")
    "without a stock-specific catalyst",
    "without a company-specific catalyst",
    "lacks a direct catalyst",         # FORM 06-18 ("FORM lacks a direct catalyst and the supporting Zacks source is months stale")
    "lacks a stock-specific catalyst",
    "lacks a company-specific catalyst",
    "lacking a direct catalyst",
    "lacking a stock-specific catalyst",
    "no fresh catalyst",
    "no direct catalyst",
    # --- stale-source / outside-window family (06-18 lesson: FORM/AGX/VKTX) ---
    "months stale",                    # FORM 06-18 ("months stale")
    "source is stale",                 # variant
    "source is months stale",
    "stale catalyst",
    "stale source",
    "outside the drift window",        # AGX 06-18 ("Earnings June 4 are outside the drift window")
    "outside drift window",
    # NOTE: "not the leader" / "not the chip-rally leader" patterns were tested on
    # 06-18 candidates and false-positived on winning picks (MU +2.34%, AVGO +0.57%,
    # META +0.74%). Self-demotion vs theme leader is too weak a signal — winners often
    # carry that hedge. Removed. The catalyst-absence and stale-source families above
    # are the strong signals.
]


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
    - Leading prose before the JSON
    - Placeholder JSON blocks like `{"scored": [...]}` that appear before the real payload
      (model emits a "let me show the schema" preamble — skip those and find the real one)

    Strategy: scan every `{` position, try raw_decode at each. If `expected_key` is
    provided, prefer the first object that contains that key (with non-empty value).
    Otherwise return the first object that parses.
    """
    text = text.strip()
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
            val = obj[expected_key]
            if isinstance(val, list) and len(val) == 0:
                continue
            return obj

    if candidates:
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
# Raw response logging + parsing-agent fallback + stage checkpoints
#
# Three coupled mechanisms designed to make a partially-failed pipeline cheaply
# resumable instead of forcing a full re-run from scratch (which is the painful
# default because brief/research are Opus + web_search → slow + expensive).
#
#   1. Raw logging: every LLM response is mirrored to `raw_debug/raw-<stage>.txt`.
#   2. Parsing-agent fallback: if `extract_json` fails or the parsed object is
#      missing the expected key, ship the raw text to a cheap Sonnet (no web
#      search) that reshapes the malformed output into the expected JSON shape.
#   3. Stage checkpoint: per-combo `_checkpoints/<combo>/<stage>.{raw.txt,parsed.json}`
#      cache. Resume policy — if parsed exists → return directly. If only raw
#      exists → re-parse without an LLM call. Otherwise → call the LLM, save raw,
#      parse, save parsed.
#
# End-of-pipeline cleanup removes `_checkpoints/` only when ALL combos succeed.
# ============================================================

_RAW_DEBUG_DIR = None     # set in run_one_combo
_CHECKPOINT_DIR = None    # set in run_one_combo


def _save_raw_response(label, response):
    if _RAW_DEBUG_DIR is None:
        return
    try:
        _RAW_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        (_RAW_DEBUG_DIR / f"raw-{label}.txt").write_text(response, encoding="utf-8")
    except Exception:
        pass


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
    """extract_json + parsing-agent fallback. Raw is always saved to raw_debug/."""
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


def _checkpoint_paths(stage_key):
    if _CHECKPOINT_DIR is None:
        return None, None
    return (
        _CHECKPOINT_DIR / f"{stage_key}.raw.txt",
        _CHECKPOINT_DIR / f"{stage_key}.parsed.json",
    )


def _load_parsed_checkpoint(stage_key):
    _, p = _checkpoint_paths(stage_key)
    if p and p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _save_parsed_checkpoint(stage_key, payload):
    _, p = _checkpoint_paths(stage_key)
    if p:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_raw_checkpoint(stage_key):
    p, _ = _checkpoint_paths(stage_key)
    if p and p.is_file():
        return p.read_text(encoding="utf-8")
    return None


def _save_raw_checkpoint(stage_key, raw_text):
    p, _ = _checkpoint_paths(stage_key)
    if p:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(raw_text, encoding="utf-8")


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


# ============================================================
# Pipeline stages — variant-aware
# ============================================================

def run_context_agent(target_date, variant):
    template = load_prompt(f"context_agent_{variant}")
    system = template.replace("{date}", target_date)
    user = f"Generate today's US market briefing for {target_date}."
    return call_sonnet(system, user, use_web_search=True)


def run_brief_agent(track, context, target_date, brief_variant):
    """
    Brief variant determines which prompt + which universe filter to use.
    Universe is paired with the brief variant: universe_track_a_{brief_variant}.txt etc.
    """
    universe_name = f"universe_track_{'a' if track == 'A' else 'b'}_{brief_variant}"
    universe = load_prompt(universe_name)
    template = load_prompt(f"brief_agent_{brief_variant}")
    system = template.replace("{universe_filter}", universe).replace("{date}", target_date)
    user = f"Today's US market context:\n\n{context}"
    stage_key = f"brief-{track.lower()}"
    return _run_stage(
        stage_key,
        "candidates",
        lambda: call_opus(system, user, use_web_search=True),
    )


def run_research_agent(candidates, context, target_date, research_variant, track=""):
    template = load_prompt(f"research_agent_{research_variant}")
    system = template.replace("{date}", target_date)
    candidates_str = json.dumps(candidates, ensure_ascii=False, indent=2)
    user = f"Today's US market context:\n\n{context}\n\nCandidates to score:\n\n{candidates_str}"
    stage_key = f"research-{track.lower()}" if track else "research"
    return _run_stage(
        stage_key,
        "scored",
        lambda: call_opus(system, user, use_web_search=True),
    )


# ============================================================
# Mechanical filters: cross-track dedup + E6 recent-loser
# ============================================================

def dedup_across_tracks(track_a_candidates, track_b_candidates):
    """
    If a ticker appears in both Track A and Track B candidate lists, remove it from
    Track B. Track A (large/mega) takes precedence. Returns (clean_b, dropped).
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


def _load_recent_loser_set(data_dir, target_date_str, lookback_days, sl_threshold, sl_pct=3.0):
    """
    Walk backwards from target_date for up to `lookback_days * 3` calendar days, loading
    `data/{date}/market_data_{date}.json` (skipping weekends/holidays automatically since they
    have no file). Count UNIQUE trading days on which each ticker hit SL
    (open_to_low_pct <= -sl_pct) in any combo/track. Tickers with hit-day count >=
    sl_threshold are returned for E6 exclusion, paired with metadata for logging.
    """
    from datetime import datetime as _dt, timedelta as _td
    try:
        target = _dt.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        return {}, []

    hit_days = {}  # ticker → {date_str: (name, worst_ol_pct)}
    days_loaded = 0
    days_checked = 0
    while days_loaded < lookback_days and days_checked < lookback_days * 3:
        days_checked += 1
        d = target - _td(days=days_checked)
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


# Cross-track sub_theme cap (D2)
# ------------------------------------------------------------
# 06-18 lesson: Track A (NVDA, AVGO, MU) + Track B (RMBS, ONTO, FORM) = 6/10 picks
# in the semi sub-theme on a single "Apple-Intel partnership" catalyst. One catalyst
# fading would have cratered both tracks simultaneously. D1 (per-track sub_theme cap)
# was 2 in each track but says nothing about cross-track concentration. D2 enforces
# a combined cap across both tracks so a single rotation can't dominate.
#
# Heuristic: Track A picks take priority (mega/large caps typically have more
# durable catalysts). When the combined sub_theme cap is exceeded, drop the
# lowest-scored Track B pick first, then the next lowest, until the cap is met.
CROSS_TRACK_SUBTHEME_CAP = 4


def apply_cross_track_subtheme_cap(track_a_picks, track_b_picks, cap=CROSS_TRACK_SUBTHEME_CAP):
    """
    Enforce that no single sub_theme contributes more than `cap` picks across the
    combined A+B final set. When violated, drop the lowest-scored Track B picks first.
    Returns (track_a_picks_kept, track_b_picks_kept, dropped_audit).
    """
    def _theme_of(p):
        return (p.get("sub_theme") or p.get("primary_signal") or "unknown").strip().lower()

    # Tally combined sub_theme counts.
    counts = {}
    for p in track_a_picks + track_b_picks:
        counts[_theme_of(p)] = counts.get(_theme_of(p), 0) + 1

    dropped = []
    track_b_kept = list(track_b_picks)
    for theme, n in list(counts.items()):
        if n <= cap:
            continue
        # Track A picks for this theme are protected. Drop lowest-scored Track B
        # picks until the combined count is back at the cap.
        b_candidates = [(i, p) for i, p in enumerate(track_b_kept) if _theme_of(p) == theme]
        b_candidates.sort(key=lambda ip: (ip[1].get("score", 0), ip[0]))
        overflow = n - cap
        for i_p in b_candidates[:overflow]:
            idx, pick = i_p
            pick = dict(pick)
            pick["filter_excluded_by"] = (
                f"D2:cross-track-subtheme-cap '{theme}' has {n} picks (cap={cap}); "
                f"dropped lowest-score Track B"
            )
            dropped.append(pick)
        # Remove dropped picks from track_b_kept by ticker (preserves the rest).
        dropped_tickers = {dp.get("ticker") for dp in dropped if dp.get("filter_excluded_by", "").startswith(f"D2:cross-track-subtheme-cap '{theme}'")}
        track_b_kept = [p for p in track_b_kept if p.get("ticker") not in dropped_tickers]

    for p in dropped:
        print(f"    [D2] dropped {p.get('ticker')} {p.get('name','-')} from Track B ({p.get('filter_excluded_by')})", file=sys.stderr)

    return list(track_a_picks), track_b_kept, dropped


def aggregate_top_5(candidates, scored, recent_losers=None):
    """Merge brief + research results, preserving sources from both. Returns (final, audit)."""
    recent_losers = recent_losers or {}
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

    # Mechanical filters (universal — applies to all variants):
    # - E6: ticker hit SL on N+ distinct days recently
    # - E4 (US): self-contradicting hedge phrases in research_reasoning
    eligible = []
    excluded = []
    for p in merged:
        ticker = p.get("ticker")

        # E6: recent loser by SL history.
        if ticker in recent_losers:
            sl_days = len(recent_losers[ticker])
            p["filter_excluded_by"] = f"E6:recent_loser SL on {sl_days} days in last {E6_RECENT_LOSER_LOOKBACK_DAYS} trading days"
            excluded.append(p)
            continue

        # E4: research_reasoning contains a strong self-contradiction phrase.
        reasoning_to_check = (p.get("research_reasoning") or p.get("reasoning") or "").lower()
        e4_hit = next((pat for pat in E4_DISQUALIFIER_PATTERNS_US if pat in reasoning_to_check), None)
        if e4_hit:
            p["filter_excluded_by"] = f"E4:self-contradiction '{e4_hit}'"
            excluded.append(p)
            continue

        eligible.append(p)

    for p in excluded:
        print(f"    [filter] dropped {p.get('ticker')} {p.get('name','-')} ({p.get('filter_excluded_by')})", file=sys.stderr)

    # Score ≥ 3 floor (06-18 lesson: FORM was score=2 with "lacks a direct catalyst"
    # in its own reasoning, yet still entered Track B final 5 because the candidate
    # pool was too thin. Picks with score < 3 are sub-conviction — better to hold
    # cash for that slot than enter a flagged trade.
    weak = [p for p in eligible if p.get("score", 0) < 3]
    strong = [p for p in eligible if p.get("score", 0) >= 3]
    for p in weak:
        print(f"    [score-floor] dropped {p.get('ticker')} {p.get('name','-')} score={p.get('score', 0)} "
              f"(< 3 conviction floor → cash slot)", file=sys.stderr)

    audit = {
        "excluded_by_filters": [
            {"ticker": p.get("ticker"), "name": p.get("name"), "reason": p.get("filter_excluded_by")}
            for p in excluded
        ],
        "excluded_by_score_floor": [
            {"ticker": p.get("ticker"), "name": p.get("name"), "score": p.get("score", 0)}
            for p in weak
        ],
    }
    return strong[:5], audit


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

    for track_name, picks in [("A — Large/Mega Cap (NYSE/NASDAQ)", track_a), ("B — Mid Cap (NYSE/NASDAQ)", track_b)]:
        lines.append(f"\n## Track {track_name} — Top 5 Picks\n")
        for i, p in enumerate(picks, 1):
            lines.append(f"### {i}. {p.get('ticker', '-')} {p.get('name', '-')}")
            lines.append(f"- **Score:** {p.get('score', '-')}/5")
            lines.append(f"- **Exchange:** {p.get('exchange', '-')}")
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
    track_a_candidates = run_brief_agent("A", context, target_date, bv)
    print(f"  Got {len(track_a_candidates)} candidates", file=sys.stderr)

    print(f"[{combo_id}] Track B brief (Opus, mid cap)...", file=sys.stderr)
    track_b_candidates = run_brief_agent("B", context, target_date, bv)
    print(f"  Got {len(track_b_candidates)} candidates", file=sys.stderr)

    # Cross-track dedup: drop Track B candidates that also appear in Track A (Track A wins).
    dedup_dropped = []
    if CROSS_TRACK_DEDUP_ENABLED:
        track_b_candidates, dedup_dropped = dedup_across_tracks(track_a_candidates, track_b_candidates)
        for p in dedup_dropped:
            print(f"    [cross-track] dropped {p.get('ticker')} {p.get('name','-')} from B (already in A)", file=sys.stderr)

    print(f"[{combo_id}] Track A research (Opus, scoring)...", file=sys.stderr)
    track_a_scored = run_research_agent(track_a_candidates, context, target_date, rv, track="A")
    track_a_picks, track_a_audit = aggregate_top_5(track_a_candidates, track_a_scored, recent_losers=recent_losers)

    print(f"[{combo_id}] Track B research (Opus, scoring)...", file=sys.stderr)
    track_b_scored = run_research_agent(track_b_candidates, context, target_date, rv, track="B")
    track_b_picks, track_b_audit = aggregate_top_5(track_b_candidates, track_b_scored, recent_losers=recent_losers)

    # D2: cross-track sub_theme cap (combined A+B ≤ 4 picks per sub_theme).
    track_a_picks, track_b_picks, subtheme_dropped = apply_cross_track_subtheme_cap(track_a_picks, track_b_picks)

    cross_track_audit = [
        {"ticker": p.get("ticker"), "name": p.get("name"), "reason": p.get("filter_excluded_by")}
        for p in dedup_dropped
    ]
    cross_track_subtheme_audit = [
        {"ticker": p.get("ticker"), "name": p.get("name"), "reason": p.get("filter_excluded_by")}
        for p in subtheme_dropped
    ]

    picks_data = {
        "date": target_date,
        "market": "US",
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
        "cross_track_subtheme_cap": cross_track_subtheme_audit,
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
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (default: today, ET)")
    args = parser.parse_args()

    target_date = args.date or datetime.now().strftime("%Y-%m-%d")
    # Always write under the script's own folder (us/), not the caller's CWD.
    output_dir = DATA_DIR / target_date
    output_dir.mkdir(parents=True, exist_ok=True)

    combos = list(product(CONTEXT_VARIANTS, BRIEF_VARIANTS, RESEARCH_VARIANTS))

    print(f"\n=== US Morning Pipeline for {target_date} ===", file=sys.stderr)
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
