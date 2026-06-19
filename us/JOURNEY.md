# US System — The Road So Far

> This document tracks **what the US day-trading agent has learned trade-by-trade** and how the pipeline has evolved.
> Architecture and usage live in `README.md`. Per-day loss analysis lives in `{date}/{date}-improvement.md`.

---

## Evolution at a glance

| Date | Change | Trigger |
|---|---|---|
| ~06-12 | v1 pipeline built (mirrors Korean structure) | Initial dev |
| **06-12 (Day 1)** | First live picks; first improvement notes written | First trading day |
| **06-16 (Day 2)** | Second trading day; same failure archetype as Korean | Risk-off + high-beta blow-up |
| **06-16 (evening)** | **Universal code enforcement backported from Korean**: E6 + cross-track dedup + Pick→Top30 overlap metric | Code-level lessons ported across markets |
| **06-18 (Day 3+1)** | **E4 self-contradiction filter** (English patterns) added | 06-17 retrospective showed CAT/RCL/UPST self-flagged but still picked |
| **06-19 (Day 4+1)** | **E4 catalyst-absence/stale-source patterns** + **score≥3 floor** + **D2 cross-track sub_theme cap** (US-specific, not a Korean backport) | 06-18 DD: 5/10 losing picks self-flagged ("no stock-specific catalyst", "months stale", "outside drift window"); FORM score=2 promoted to final 5; semi sub-theme had 6/10 cross-track concentration |

Compared to the Korean side, the US journey is **at the equivalent of "Korean Day 1.5"**: we have explicit loss patterns but not yet enough multi-day data to justify market-specific v2/v3 prompts.

---

## Stage 1 — v1 pipeline (pre-06-12)

Same structure as Korean:
- **Context Agent** (Sonnet + web search) — pre-open market briefing
- **Brief Agent** (Opus + web search) — Track A large/mega cap + Track B mid cap, ~10 candidates each
- **Research Agent** (Opus + web search) — scores candidates 1–5
- **Aggregator** — top 5 per track by score

`v1` prompts had no explicit hard-exclusion or diversification rules. Just thematic guidance and example universes.

---

## Stage 2 — Day 1: 2026-06-12 (first lessons)

**Track A**: +2.08% avg (2 TP, 2 HOLD, 1 SL). **Track B**: −1.40% avg (1 TP, 4 SL).

### The dominant failure mode: SpaceX (SPCX) IPO rotation
- Brief itself warned: "investors may sell sympathy plays to buy the SPCX IPO offering"
- Agent picked **two SpaceX sympathy substitutes** (RKLB, LUNR) anyway
- SPCX itself opened +11% from IPO price, ran to +17.68% intraday, closed +7.30% — a textbook TP
- RKLB closed −13.23%; LUNR closed −10.90%
- The penalty for "SpaceX liquidity drain" was applied to CRDO/SOFI (adjacent) but waived for RKLB/LUNR (most directly substitutable). Penalty applied backwards.

### Track B was a microstructure lesson, not a thematic one
- IREN won (the only Track B TP). Why? **Negative gap (−0.37%), low at 09:30, first_5min_min_pct = −0.99%** — well under the −2.5% threshold.
- All four losers (ALAB, LUNR, CRDO, SOFI) had `first_5min_min_pct` worse than −2.12%.
- Same `first_5min_min_pct ≤ −2.5%` rule that the Korean side identified independently. **The rule is market-agnostic intraday microstructure.**

### The dominant *miss*: the SPCX IPO itself
- The brief named SPCX 6 times as "the dominant intraday event"
- It is not in `universe_track_*` because it had no prior trading history
- Picking sympathy substitutes instead of the event itself cost ~16 percentage points of combo P&L

### Other process failures noted
- `high_time = 09:30 / 09:31` (open = high) was the single cleanest losing signal of the day across 4 of 5 losers
- `clean_narrative` over-weighted (3 of 5 in each track)
- No pre-open re-score loop (RKLB pre-market +8% should have triggered a penalty re-eval)
- "Risk-on" regime tag too coarse — needs `risk_on_strong` (gap-ups extend) vs `risk_on_muted` (gap-ups fade) sub-classes

(Full breakdown: `2026-06-12/2026-06-12-improvement.md` — long and detailed.)

---

## Stage 3 — Day 2: 2026-06-16

**Market**: SPY −0.60%, QQQ −1.90%, IWM −0.87%, VIX +1.30% — clean risk-off day.

**Track A**: −1.19% avg, catchable 2/5, top30 hit 1/5 (AAL #5).
**Track B**: all five picks high-beta speculative names; 4 of 5 had open-to-low ≤ −4.91%.

### The failure archetype repeats — same as Korean
- **All 5 Track B picks gapped down at open** (CRDO −1.27%, IREN −1.41%, ACHR −0.90%, JOBY −0.21%, RGTI −2.86%)
- All 5 were beta 2+ speculative growth: semis (CRDO), quantum (RGTI), eVTOL (ACHR, JOBY), bitcoin miner (IREN)
- On a QQQ −1.9% day, beta 2+ names mathematically draw down 4–7%
- No sub-theme diversification — 5 picks, 1 archetype
- **This is the exact same pattern as Korean 06-12** (SK하이닉스/HD현대일렉트릭/한화오션, narrative-only picks on a bounce day)

### What Track A got right vs wrong
- Right: AAL was top 30 (#5, +3.85% intraday high), correctly identified as risk-off rotation
- Wrong: 3 of 5 Track A picks were airlines (DAL, UAL, AAL) — same sub-theme concentration mistake
- The single hit was diluted across three highly correlated names

### Dominant missed winners
- **#1 OBAI** +21.98% (sub-$1 micro cap — universe-excluded for liquidity)
- **#2 CRWV** CoreWeave +8.06% (AI infrastructure — *should* have been in our universe)
- **#3 BBWI** +5.09% (consumer discretionary)
- **#4 SSRM** +4.22% (gold miner)
- Pattern: agent missed AI-infra rotation winner (CRWV) and consumer/defensive rotation winners (BBWI, SSRM). Same diagnosis as Korean's missed 풍력/건설 clusters.

(Full breakdown: `2026-06-16/2026-06-16-improvement.md` — stub at time of writing.)

---

## Stage 4 — Code enforcement backport (06-16 evening)

After the Korean side concluded that prompt-level rules are routinely ignored by the LLM and **must be enforced in code**, the universal subset was ported to the US pipeline.

Backported to `us/pre-pipeline.py`:
- **Cross-track dedup** — if a ticker appears in both Track A and Track B candidate lists, it is automatically dropped from Track B (Track A wins). Prevents the kind of double-pick that caused matching SLs in both tracks on the Korean side.
- **E6 recent-loser filter** — any ticker that hit SL on 2 or more distinct trading days in the last 5 trading days is automatically excluded. Reads from prior `market_data_{date}.json` files. Currently active blocks: **CRDO** (SL on 2026-06-12 and 2026-06-16).
- **`filter_audit` / `cross_track_dedup` fields** in the picks JSON for post-hoc auditing of what was dropped and why.

Backported to `us/post-pipeline.py`:
- **Pick → Top30 overlap section** in the summary — for each combo, shows how many picks landed in the top 30 intraday movers (which tickers, at which ranks), plus the top 15 missed winners. This is the canonical data source for future universe expansion.

Korean-specific rules **deliberately not backported**:
- **E4 self-contradiction patterns** — the Korean regex matches Korean-language hedging words (e.g. "후순위", "부재", "약함"). These don't apply to English research output.
- **E5 prev-day spike threshold** — relies on the `prev_day_change_pct` field that only the Korean v3 brief emits. US v1 brief does not produce this field.
- **D1 sub-theme diversification** — relies on the `sub_theme` field that only the Korean v3 brief emits.

These will be ported when the US side gets its own v2/v3 prompts.

---

## Current state of the pipeline

### Prompt variants

| Variant | Status | Notes |
|---|---|---|
| v1 | Active | Baseline. No explicit E/P/D rules in the prompt. |
| v2 | Partial / unused | Only `research_agent_v2.txt` and `context_agent_v2.txt` exist. `brief_agent_v2.txt` and the v2 universe files are missing. Not used because incomplete. |

Daily run: **`v1-v1-v1` only**.

### Active rules

| Rule | Source | Enforcement |
|---|---|---|
| Cross-track dedup | Universal code | ✓ pipeline |
| E6 recent loser (SL on ≥2 of last 5 trading days) | Universal code | ✓ pipeline |

The US side does **not yet have**:
- E1 (gap-up exhaustion) — universal idea, no threshold calibrated for US yet
- E2 (context contradiction) — universal idea, not in prompt yet
- E3 (stale catalyst >5 days) — universal idea, not in prompt yet
- D1 (sub-theme diversification) — requires v2 brief emitting `sub_theme`
- Pre-open re-score loop — same as Korean, not built

---

## Lessons confirmed identical between markets

| Lesson | Korean evidence | US evidence |
|---|---|---|
| `first_5min_min_pct ≤ −2.5%` is a clean SL predictor | HPSP/ISC stayed in band → won; 원익IPS/테크윙 broke it → SL | IREN stayed in band (−0.99%) → won; ALAB/LUNR/CRDO/SOFI all broke it → SL |
| `high_time = 09:30 (or 09:00 KR)` is a distribution signature | 6-12 SK하이닉스, 한화오션 | 6-12 RKLB, LUNR, CRDO |
| `low_time = open` (first minute) is bullish | HPSP, 한미반도체 | IREN |
| Narrative-only picks (no fresh dated catalyst) get faded on event days | SK하이닉스/HD현대일렉트릭 (bounce regime, narrative only) | RKLB/LUNR (SpaceX IPO day, sympathy narrative) |
| Sub-theme over-concentration kills variance | 6-15 v2 over-loaded on semis | 6-16 Track B all high-beta speculative growth; Track A 3 airlines |
| `clean_narrative` is over-used and under-predictive | Multi-day | Multi-day |
| LLM ignores prompt-level rules → must enforce in code | Multi-day | 6-16 confirmed via same archetype repeating |

---

## Pending work (US-specific)

1. **Collect more days of data.** US has only three trading days logged (06-12 / 06-16 / 06-17). Pattern confirmation needs n ≥ 4–5 before writing v2 prompts.
2. **Build a v2 brief that emits `sub_theme` and `prev_day_change_pct` fields** — needed to backport Korean E5 and D1 mechanically. Currently both are prompt-only "soft" rules in v1.
3. **Universe expansion for AI-infra mid-caps** (CRWV missed on 06-16) and consumer rotation names (BBWI, SSRM type).
4. **IPO event-day handling** — add a watch-list slot mechanism in the brief prompt so high-profile IPOs (SPCX-like events) are flagged for trader review rather than ignored because they have no trading history.
5. **`first_5min_min_pct < −2.5%` automatic entry-defer** — same blocker as Korean side: the data only exists post-open, so this can only inform trader execution, not the pick list.
6. **Top-30 as retrospective alternative-pick reference, NOT as a hit-rate KPI.** Reframing note: TP at +5% is the actual scoring criterion — hitting top-30 movers is *not* the goal. Top-30 is useful for the *losing* slots: "this pick SL'd, what could we have picked instead?" On 06-17 Track B already had 2/5 TP (ARWR, IREN) — those slots are fine. The retrospective question is only about the ANF / ASTS / UPST SL slots, and the relevant comparison is "did the day's actual top-30 contain candidates from sub-themes our brief didn't consider?" (06-17 leaders included bio rotation, crypto-beta, small-cap fintech — see entry below). This is a *learning* signal for universe expansion, not a *grading* signal for the day.

---

## 06-19 (Day 4+1, prep day) — US-specific iteration after 06-18 DD

Triggered by the user's 06-18 due-diligence pass: "why the f did we pick those losing stocks."

**Findings from 06-18 reasoning audit:**
- 5/10 picks self-flagged their own catalyst weakness in plain English:
  - COIN: *"Single-theme alignment **without a stock-specific catalyst today**"* → SL −3.00%
  - ONTO: *"No company-specific catalyst"* → −1.25%
  - VKTX: *"Lake Street initiated Buy **on May 28**"* (21 days stale) → −1.01%
  - AGX: *"Earnings June 4 are **outside the drift window**"* → 09:30 +0.94% / 09:35 SL
  - FORM: *"FORM **lacks a direct catalyst** and the supporting Zacks source is **months stale**"* → 09:30 +0.36% / 09:35 SL
- FORM was score=**2** yet still promoted to Track B final 5 — candidate pool was too thin.
- 6/10 combined picks were in the same broad semi theme (NVDA/AVGO/MU + RMBS/ONTO/FORM). One catalyst fading = both tracks down together.

**Code (`pre-pipeline.py`):**
- **Expanded `E4_DISQUALIFIER_PATTERNS_US`** with catalyst-absence and stale-source families:
  - `"no stock-specific catalyst"`, `"no company-specific catalyst"`, `"without a stock-specific catalyst"`, `"without a company-specific catalyst"`
  - `"lacks a direct catalyst"`, `"lacks a stock-specific catalyst"`, `"lacks a company-specific catalyst"`, `"lacking a direct catalyst"`, `"lacking a stock-specific catalyst"`, `"no fresh catalyst"`, `"no direct catalyst"`
  - `"months stale"`, `"source is stale"`, `"source is months stale"`, `"stale catalyst"`, `"stale source"`
  - `"outside the drift window"`, `"outside drift window"`
- **Rejected** `"not the leader" / "not the chip-rally leader" / "but not the leader"` from the pattern list — tested on 06-18 candidates and false-positived on winning picks (MU +2.34%, AVGO +0.57%, META +0.74%). Self-demotion vs theme leader is too weak a signal; winners regularly carry that hedge.
- **Score≥3 floor in `aggregate_top_5`**: picks with score < 3 are excluded as sub-conviction → cash slot for that position. Trade-off accepted: occasionally Track B will return 1–3 picks instead of 5 when candidate pool is weak. Reasoning: 06-18 FORM (score=2 with "lacks direct catalyst" + "stale source") hit SL on the 09:35 sim; the slot was worth more empty than filled.
- **D2 cross-track sub_theme cap** (new function `apply_cross_track_subtheme_cap`, max 4 picks per `sub_theme` across both tracks). Drops lowest-scored Track B overflow first (Track A is protected; mega/large caps tend to have more durable catalysts).

**Prompts (`brief_agent_v1.txt`):**
- Added required `sub_theme` field to the JSON output schema with narrow-label examples (`semi-memory`, `semi-design`, `ai-power-infra`, `crypto-beta`, `biotech-glp1`, etc.). The D2 cap reads this field; previous picks fell back to `primary_signal` which was too coarse (everything was `theme_alignment`).
- Augmented rule 6 (sub-theme diversification) with the 06-18 lesson and a concrete sub_theme taxonomy.

**Smoke test (06-18 candidates re-run through new rules):**
| | Track A | Track B | Combined |
|---|---|---|---|
| Original avg | +0.52% (5 picks) | +0.62% (5 picks) | +0.57% |
| New rules avg | +1.52% (~4 picks) | +4.05% (1 pick) | ~+2.03% |
| Δ | +1.00%p | +3.43%p | +1.46%p |

Caveat: Track B drops to 1 pick (RMBS) because 9/10 candidates either hit E4 or fell below score=3. This is the desired conservatism trade-off, but means brief candidate quality becomes the bottleneck. Either accept smaller Track B days or expand brief candidate count (10 → 15) in a future iteration.

---

## 06-18 (Day 3+1, prep day) — code & prompt iteration after 06-17

Triggered by the 06-17 retro and the user's request to "improve US code and prompts."

**Code (`pre-pipeline.py`):**
- Added **E4 (US edition) self-contradiction filter** — English-language pattern list applied universally to all variants inside `aggregate_top_5`. Calibrated against 06-12/06-16/06-17 picks: 0 false-positives on winners across 27 picks, correctly cuts CAT/RCL/UPST (06-17) and CRDO (06-12).
- Conservatism notes: generic words like "headwind"/"lagged"/"secondary play" are NOT in the list because they can appear in legitimate winners (IREN 06-17 said "tech rotation headwind today reduces score by 1 from a base 5" — soft penalty acknowledgment, not contradiction). Only unambiguous bearish-direction phrases included: `stretched`, `already extended`, `extended after`, `overbought`, `exhausted`, `sell-the-news`/`sell the news`, `fully priced`, `already priced`, `faces headwinds`, `extension risk`, `liquidity-drain`/`liquidity drain`.

**Code (`post-pipeline.py`):**
- Fixed `fetch_top_30_intraday` scraper. Two root causes:
  1. `api.nasdaq.com/api/marketmovers/STOCKS` endpoint returns 404 since at least mid-2026. Removed from fallback chain.
  2. Yahoo gainers `data-symbol="..."` selector now matches symbols across the *entire* React-rendered page (BTC-USD, META in news cards, etc.), not just the gainers table. Fix: scope extraction to the gainers `<tbody>` only.
- Added **stockanalysis.com** as a secondary fallback for when Yahoo returns < 10 rows.
- Re-running 06-17 collect now produces a populated Pick→Top30 overlap section.

**Prompts (`research_agent_v1.txt`, `brief_agent_v1.txt`):**
- Added **E1 catalyst-timing guard**: if `fresh_catalyst` references an event that fired before 04:00 ET (overnight / yesterday after-close), this is sell-the-news territory — drop or score ≤ 2. Explicitly references the 06-17 ASTS BlueBird launch failure (catalyst at 02:39 ET → SL at 09:32).
- Added **E2 already-extended-leader guard**: if candidate already gained 3%+ in prior 1–2 sessions on the same theme, drop. Tomorrow's distribution.
- Added **E3 self-contradiction rule (to research)**: explicit instruction not to write picks that flag their own bear case in the same reasoning sentence — with a list of disqualifying phrases mirroring the code-level filter.
- Added to brief: catalyst-timing guard (rule 5), sub-theme diversification request (rule 6, informal — will become strict in v2 with `sub_theme` field), and a copy of the self-contradiction phrase list (rule 7) so the brief LLM knows downstream filtering will reject those phrases.

---

## Relationship to the Korean system

The two systems share architecture (`pre-pipeline.py` orchestration is essentially identical) and now share the **universal code enforcement layer** (cross-track dedup, E6, Pick→Top30 metric). They diverge on:
- Prompts (language, universe, sources)
- Data layer (yfinance + NASDAQ API vs. FinanceDataReader + Naver)
- Market-specific rules (Korean v3 has prev_day_spike / sub_theme / hedging-regex rules; US v1 does not)

When the US side accumulates enough data to justify a v2, the natural starting point is to port the **universal subset** of Korean v2/v3 ideas (E1 gap-up exhaustion, E2 context contradiction, E3 stale catalyst, D1 sub-theme limit) into English. Language- or market-specific specifics (Korean hedging-word regex, KOSPI/KOSDAQ divergence rules, foreign-flow signals) stay Korean-only.
