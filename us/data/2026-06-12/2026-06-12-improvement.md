# Improvement Notes — 2026-06-12 (US, v1-v1-v1)

> Combo P&L (open entry, TP 5% / SL 3%): Track A **+2.08%** (2 TP, 2 HOLD, 1 SL), Track B **−1.40%** (1 TP, 4 SL).  
> Of 10 picks, only **3 actually hit TP** (INTC, KLAC, IREN); 5 hit SL (RKLB, LUNR, ALAB, SOFI, CRDO); 2 closed green but never reached TP (MU +1.01% HOLD, AMD +2.38% HOLD).  
> Day's main thesis (semis rebound + AI infra) was partly correct — INTC/KLAC delivered clean TPs — but the damage came from **space-sympathy picks (RKLB, LUNR)** getting crushed exactly as the brief's own "SpaceX IPO liquidity drain" warning predicted, plus Track B AI-connectivity names (ALAB, CRDO) distributing into the SPCX debut.  
> Market backdrop: SPY +0.54%, QQQ +0.59%, IWM +0.87%, VIX −9.05% → "muted risk-on" tape where gap-ups generally faded.

---

## Losers — why agent picked them

Open-entry losers: **1 of 5 in Track A (RKLB)**, **4 of 5 in Track B (LUNR, ALAB, SOFI, CRDO)**. Three of the five losers were the names flagged by the brief itself as carrying "SpaceX rotation risk" — and that risk actually fired.

### RKLB Rocket Lab USA — SL −3.00% (gap +2.81%, O→C −13.23%, pattern ↓)
- **Agent picked it score 4/5:** "Cleanest SpaceX IPO sympathy play with a hard Nasdaq-100 inclusion catalyst on June 22." Signals: `theme_leader`, `fresh_catalyst`, `clean_narrative`, `momentum_continuation`.
- **What actually happened:** Opened at $118.00 (+2.81% gap), printed the day's high in the first minute (09:30, +0.32% from open), then ↓-pattern all day to low at 12:03 (−15.58% from open). Closed −13.23% from open, the single worst pick of the day across both tracks.
- **Diagnosis:** Classic "sympathy substitute gets killed when the real event trades." The research note even cited the risk — `RKLB traded over 8% higher overnight ahead of Friday` was flagged as triggering a gap-up penalty, but the score stayed at 4. Once SPCX opened at $150 (+11% from its $135 IPO price) and *held*, every dollar of "SpaceX exposure" demand routed straight to SPCX, not to the substitutes. RKLB, LUNR, VOYG (#17, −10.93%), ASTS (#18, −14.74%), YSS (#19, −17.07%), FLY (#20, −17.62%) all collapsed in lockstep — top 30 movers had **five space-sympathy names in the worst-6 losers**. This was a sector-wide rotation event, not a single-name mistake.
- **Signal mis-weight:** The brief's "SpaceX IPO debut — investors may need to sell existing holdings… to buy the offering" warning was applied as a −1 penalty to CRDO and SOFI in Track B, but **not** to RKLB or LUNR — the two names most directly substitutable for SPCX. The penalty was applied backwards: it should hit pure-substitute plays hardest, not adjacent themes.

### LUNR Intuitive Machines — SL −3.00% (gap −2.48%, O→C −10.90%, pattern ↓)
- **Agent picked it score 4/5:** "Pure-play space sympathy name into SpaceX (SPCX) Nasdaq debut today." Signals: `theme_alignment`, `fresh_catalyst`, `retail_buzz`, `clean_narrative`.
- **What actually happened:** Same script as RKLB. High at 09:30 (+0.59% from open), then ↓ straight to low at 12:03 (−14.81% from open). Closed −10.90%.
- **Diagnosis:** The research file *literally wrote* the disqualifier — `risk that once SpaceX trades, investors may buy SPCX directly rather than substitutes, pressuring space stocks`. The agent identified the exact failure mode and picked it anyway because the bullish signal stack was longer. **This is the brief-vs-pick contradiction pattern** (same one we saw with 한화오션 in Korean).
- **Signal mis-weight:** `retail_buzz` is doing too much work here. On an event day with a real ticker (SPCX) trading for the first time, retail buzz *moves to the new ticker*. Retail buzz built up pre-event is anti-signal for sympathy names on event day. The rubric should add an explicit "if `event_day_for_parent_ticker = true`, drop sympathy plays" rule.

### CRDO Credo Technology — SL −3.00% (gap +1.98%, O→C −7.11%, pattern ↓)
- **Agent picked it score 3/5:** "AI connectivity chip name that surged 11.08% Thursday." Signals: `momentum_continuation`, `earnings_drift`, `theme_leader`, `fresh_catalyst`. Note: agent already **reduced score 1** for "extension risk and SpaceX IPO liquidity-drain concerns."
- **What actually happened:** Opened at $270 (+1.98%), high at 09:30 (+0.08% from open — basically open was high), then ↓ to low at 10:48 (−10.70%). Closed −7.11%.
- **Diagnosis:** The penalty was applied correctly (score dropped from 4 to 3) but the pick still made the final 5. **The penalty system is too soft** — a score of 3 is still a "moderate setup, take it" in the current rubric. When the brief's macro warning + the name's own extension risk both apply, the pick should be cut, not just dinged.
- **Signal mis-weight:** `earnings_drift` is a *carrying* signal — it makes a name "want to keep going" on a quiet day. But on a high-event day (SPCX debut, oil −4%, Iran headlines), earnings-drift names get rotated against, not for. Treat `earnings_drift` and `event_day_volatility` as conflicting signals — one negates the other.

### ALAB Astera Labs — SL −3.00% (gap +2.59%, O→C −2.61%, pattern Λ)
- **Agent picked it score 4/5:** "AI connectivity leader… direct theme leader for AI infra rebound." Signals: `theme_leader`, `momentum_continuation`, `clean_narrative`.
- **What actually happened:** Opened $377 (+2.59% gap), ran to high $390.99 at 09:31 (+3.71%) — TP-able for a single minute — then Λ-distribution to low at 10:48 (−4.49% from open). Closed −2.61%.
- **Diagnosis:** Best entry was the *first minute* of trading (09:30 → 09:31). A Λ pattern with `high_time` 1 minute after open is the textbook "open-auction pump → institutional distribute" signature. The pick wasn't wrong, but the **rubric had no `clean_narrative` penalty for "no fresh catalyst dated to today"** — the research reasoning cited Q1 results from May 5, more than 5 weeks stale.
- **Signal mis-weight:** `theme_leader` + `momentum_continuation` + `clean_narrative` = three signals, but every one is a *backward-looking* signal. Without a fresh dated catalyst, a Λ-shaped distribution day was the most probable outcome. Symmetric to the Korean HD현대일렉트릭 failure: right theme, wrong day-specific setup.

### SOFI SoFi Technologies — SL −3.00% (gap +1.08%, O→C −1.60%, pattern =)
- **Agent picked it score 3/5:** "Fintech mid-cap that sold off ~13% post Q1." Signals: `oversold_bounce`, `momentum_continuation`, `fresh_catalyst`.
- **What actually happened:** Opened $16.85, barely budged (=, O→H +0.30%, O→L −3.68%), drifted to low at 12:03, closed −1.60%. Best entry of the entire day was a +2.06% HOLD at 12:02 — the name had no meaningful range.
- **Diagnosis:** SOFI was a "regime trade" — agent reasoned that VIX −12.5% + small caps leading should pull fintech up. But IWM was only +0.87% on the day (versus the "small caps leading" thesis from the brief, which proved overstated). When the macro setup is softer than briefed, regime-trade picks have no individual catalyst to fall back on.
- **Signal mis-weight:** `oversold_bounce` as a primary signal requires the broad tape to confirm. The pre-open VIX print (~19.4) was already cooling vs the prior session's -12.5%, but no re-score happened. Same gap as the Korean side: **no pre-open re-score loop** to validate that the regime assumption still holds at 09:25 ET.

**Common thread across all 5 losers:**
1. **3 of 5 were direct/indirect SpaceX rotation casualties** (RKLB, LUNR, CRDO). The brief identified this risk and the agent half-applied it.
2. **4 of 5 had `high_time = 09:30 or 09:31`** (RKLB 09:30, LUNR 09:30, ALAB 09:31, CRDO 09:30). Open-as-high is the cleanest single-bar bearish signal in the data. Add a guard: if a pick's `first_1min_max_pct < 0.5%` from open and `first_5min_min_pct < −1.5%`, defer entry.
3. **0 of 5 had a fresh same-day catalyst.** All five leaned on theme/momentum signals where the catalyst was 1+ days old. On an event day with SPCX/PPI/UMich sentiment, stale-catalyst names get faded.

---

## Track A — true winners (TP), non-loser holds, and the one SL

Under TP 5% / SL 3% rules the Track A bucket breaks into **2 TP wins, 2 marginal HOLDs, 1 SL loss** — not "4 winners and 1 loser." Calling MU and AMD "winners" overstates the result: they happened to close green, but the strategy never closed the trade — capital sat in them all day without ever reaching the +5% exit.

| Ticker | Gap | Pattern | High@ | O→H | Strategy result | Why |
|---|---|---|---|---|---|---|
| INTC | +0.39% | ~ | 13:50 | +8.67% | **TP +5.00%** ✅ | Hit TP intraday and held above |
| KLAC | −1.55% | ↑ | 15:57 | +7.37% | **TP +5.00%** ✅ | Hit TP intraday and held above |
| AMD | +2.30% | ~ | 13:48 | **+4.40%** | HOLD +2.38% ⚠️ | 60bps short of TP — choppy `~` pattern, no clean exit |
| MU | −2.42% | Λ | 10:18 | **+4.20%** | HOLD +1.01% ⚠️ | 80bps short of TP — Λ-shape, peaked at 10:18 then bled |
| RKLB | +2.81% | ↓ | 09:30 | +0.32% | **SL −3.00%** ❌ | Open = high, ↓-pattern all day |

**What separated the 2 TPs from RKLB:**
- Both TPs (INTC, KLAC) had **small or negative gaps** (+0.39% and −1.55%) vs RKLB's +2.81%. Small/negative gaps in a "muted risk-on" tape preserve upside room; gap-ups in a muted tape get faded.
- Both TPs had **dated fresh catalysts** — INTC (BofA double-upgrade June 11), KLAC (10-for-1 split + Cantor $145B WFE estimate). Both ≤1 day old, not 5+ weeks like ALAB.
- **Neither TP was on the "SpaceX adjacent" list.** Pure semi-rebound names sidestepped the SPCX rotation entirely.

**The two HOLDs (MU, AMD) are the most instructive observation of the day:**
- Both had highs of +4.20% / +4.40% — within 1 percentage point of TP. With a slightly tighter TP (e.g., **TP 4% / SL 3%**) both would have flipped to wins, making Track A's average jump from +2.08% → ~+3.4%.
- Pattern matters: AMD `~` (choppy) and MU `Λ` (peak-and-fade at 10:18) both show the same microstructure — intraday push that didn't have enough conviction to break +5%. On `Λ`-pattern names, **a 09:33 best-entry dip** would have given MU's pop a longer runway (low was $959.65 at 09:33, +1.27% better than open) — same "skip open, buy first 5min low" lesson as the Korean side.
- AMD specifically: choppy `~` with high at 13:48 means a `set-TP-and-walk-away` execution was wrong for this name. It needed an active manager, not a static OptPT.

**Best-entry observations for the actual winners:**
- **INTC's TP hit and held above for the next ~2h** (high at 13:50, still above $127.60 OptPT well into the afternoon). **KLAC's TP held above for 6+ hours** (high at 15:57 — the entire session was a slow grind up). Both are "set-and-forget" winners. A **trail-stop or partial-take** strategy would have captured even more upside on KLAC specifically (O→H +7.37% vs TP at +5.00%).
- This contrasts sharply with AMD's `~` pattern — same theme bucket, very different execution requirement. The rubric doesn't currently distinguish "post-TP behavior" — worth adding a tag (e.g., "TP @ HH:MM, held above for next 2h" vs "TP and immediately reversed").

---

## Track B winners — IREN stood alone

| Ticker | Name | Gap | O→L from open | Low time | Pattern | Result |
|---|---|---|---|---|---|---|
| IREN | IREN Limited | −0.37% | **−0.99%** | 09:30 | ↑ | TP ✅ |
| ALAB | Astera Labs | +2.59% | −4.49% | 10:48 | Λ | SL → close −2.61% |
| LUNR | Intuitive Machines | −2.48% | −14.81% | 12:03 | ↓ | SL → close −10.90% |
| CRDO | Credo Tech | +1.98% | −10.70% | 10:48 | ↓ | SL → close −7.11% |
| SOFI | SoFi | +1.08% | −3.68% | 12:03 | = | SL → close −1.60% |

**Why IREN won where the other 4 lost (same lesson as the Korean HPSP vs 원익IPS split):**
1. **Negative gap (−0.37%)** — the only Track B pick that didn't gap up. No supply overhang from gap-fade sellers at the open.
2. **Low-time = 09:30** — same bullish tell we saw in the Korean data. When the day-low is at-or-in-the-first-minute of the open, the gap (or lack of it) is bought from tick 1.
3. **`first_5min_min_pct = −0.99%`** — under the −2.5% threshold. Compare: ALAB −2.61%, LUNR −5.91%, CRDO −5.27%, SOFI −2.12%. IREN was the only one inside the "safe open entry" band.
4. **Catalyst was AI-infra adjacent but NOT space-adjacent** — $3.4bn NVIDIA AI Cloud contract is direct AI compute exposure, no SPCX competition.

**The `first_5min_min_pct` rule is symmetric across US and Korean markets.** The Korean improvement.md called for a "−2.5% first-5min" filter; today's US data confirms it (all 4 SL casualties exceeded that threshold; the 1 winner stayed inside). **Action: add this filter to `research_agent_v1.txt` as a hard pre-trade check, applied identically to both markets.**

---

## Top 30 winners we missed (focusing on catchable ✅ ok)

Top 30 catchable: **11/30**. We owned **INTC (#9)** outright. Real picked-vs-catchable overlap: 1/11. The 10 misses below are where the universe / scoring rubric needs work.

### The dominant miss: we picked sympathy plays instead of the actual event (**SPCX**)

| Rank | Ticker | Open | O→C | Catchable |
|---|---|---|---|---|
| 8 | **SPCX** (SpaceX) | $150 (+11% from IPO) | +7.30% | ⚠️ tight |

The brief named SPCX 6 times and called it "the dominant intraday event." Then the agent picked **two SpaceX sympathy substitutes** (RKLB, LUNR) instead of the event itself. SPCX opened at $150, hit +17.68% intraday, and closed +7.30% — a clean TP. Meanwhile RKLB −13.23% and LUNR −10.90%. **Net swing of putting capital into the right ticker:** +5% TP on SPCX vs. −3% SL on RKLB/LUNR = ~8 percentage points of P&L per slot, ×2 slots = ~16 pp of combo P&L left on the table.

**Why it was missed:** IPO names are not in `universe_track_*` because they have no prior trading history. **Concrete fix for the universe prompts:** add an "IPO event day" rule to `context_agent_v1.txt` — if a high-profile IPO is debuting and is named in the brief, the research agent should reserve **1 watch-list slot for the IPO ticker** with a special "open-auction-only" entry rule. Don't try to pre-score it; just flag it as a known event-day candidate the trader can decide on at the open.

### The other dominant miss: **risk-on rotation beneficiaries** (5 of top 12)

| Rank | Ticker | Sub-theme | O→C | Catchable |
|---|---|---|---|---|
| 6 | ROKU | Streaming/media reset | +15.20% | ⚠️ narrow |
| 10 | NOK | Telecom/5G infra | +3.21% | ✅ |
| 11 | AAL | Airlines (oil −4% beneficiary) | +0.81% | ✅ |
| 12 | WBD | Media | +0.74% | ✅ |
| 13 | NVDA | AI mega-cap | +0.22% | ✅ |

**Why these were missed:** None of these fit the agent's "semis rebound + AI infra" thematic frame. But the brief itself flagged "**Energy sector rotation: crude oil fell more than 4%**" — AAL is the textbook beneficiary (jet fuel is ~25% of airline opex) and was completely absent from the rotation analysis. **Concrete fix:** the brief prompt already lists energy as a *headwind* theme, but the rubric has no symmetric "if X is a sector headwind, list Y = beneficiaries." Add an explicit cross-rotation map: `oil_down → {airlines, refiners (PBF/DK margin relief), consumer discretionary}`, `risk_on → {ROKU, RBLX, streaming reset names}`.

### Tertiary misses: micro/small caps outside universe (informational only)

| Rank | Ticker | O→C | Notes |
|---|---|---|---|
| 1 | CAST | +159.24% | Penny-stock pump, not realistically catchable |
| 2 | SPCL | +35.07% | Micro-cap |
| 3 | PLBL | +17.60% | Micro-cap |
| 4 | ELVN | +16.01% | Small-cap biotech |
| 5 | ALMS | +15.38% | Small-cap |
| 7 | MAAS | +14.93% | Small-cap |

These are correctly excluded from the universe (too thin, too volatile, no fundamentals). Track them only as a sanity check that the top of the leaderboard isn't being driven by names we *should* include but don't.

---

## Other observations

1. **The brief correctly forecasted "SpaceX IPO liquidity drain" and the agent applied the penalty asymmetrically.** CRDO and SOFI got their scores cut by 1 for this risk. RKLB and LUNR — the names *most* exposed because they're direct substitutes — got the penalty waived because their bullish signal stack outweighed it. **Fix:** turn the SpaceX penalty into a hard filter, not a soft score adjustment. If the brief names a high-profile competing ticker and a candidate is flagged as a sympathy play for it, the candidate is **cut**, not scored down.

2. **The day's biggest *outcome* edge ("muted risk-on" → fade gap-ups) wasn't in the scoring rubric.** SPY +0.54% / QQQ +0.59% with VIX −9.05% is a "tape was fine but leaders distributed" day — exactly where gap-ups in extended names get faded. The agent's regime tag from the brief was "Risk-on / bounce continuation," which is *too coarse* — both "bounce" and "muted risk-on" map to "Risk-on" but they have opposite implications for gap-up plays. **Fix:** sub-divide the regime tag: `risk_on_strong` (SPY > +1.0%, gap-ups extend) vs `risk_on_muted` (SPY +0.3-1.0%, gap-ups fade) vs `risk_off`. Today was clearly `risk_on_muted` and Track A should have been gap-up-penalized accordingly.

3. **`high_time = 09:30` was the cleanest losing signal of the day.** RKLB, LUNR, CRDO all had `high_time = 09:30` (open = high) and all three lost. INTC, KLAC, AMD all had `high_time` between 13:48–15:57 (late-day highs) and all three won or held green. **`high_time − open_time`** is a free signal sitting in `market_data_*.json`. It's not in the scoring rubric anywhere. Add it: if a pick's first-minute is the high of the day, that's a distribution signature regardless of fundamental setup.

4. **Symmetric `first_5min_min_pct < −2.5%` rule between markets.** The Korean improvement.md identified this rule (HPSP/ISC stayed inside, 원익IPS/테크윙 broke it). The US data confirms it cleanly: IREN was the only Track B pick under the threshold, and the only winner. **Add this as a shared rule across `us/prompts/research_agent_v1.txt` and `korean/prompts/research_agent_v1.txt`** — it's market-agnostic intraday microstructure.

5. **`clean_narrative` is over-used here too.** It appeared on 3 of 5 Track A picks (RKLB, INTC, [implicit in KLAC]) and 3 of 5 Track B picks (LUNR, IREN, ALAB). Same complaint as the Korean side — drop it or cap it at +0.5.

6. **No pre-open re-score.** The picks were finalized the prior evening. By open the actual gap, VIX print, and SPCX pricing were all known. RKLB pre-market was +8% (research file notes this triggered a gap-up penalty) but the score stayed at 4. **Same recommended fix as Korean side:** add a pre-open re-score step that ingests (a) actual open auction or last pre-market print, (b) live VIX, (c) headline news scrape, and recomputes scores. The infrastructure already exists in `collect_daily_data.py` (it fetches the open prices) — needs to be split out into a lightweight pre-open script that runs at ~09:25 ET.

7. **Pick → Top30 overlap = 1/5 Track A, 0/5 Track B (catchable subset).** Track A got INTC; Track B got nothing (IREN won but wasn't in top 30 — it was a +5.79% O→C, below the +14% cutoff). Suggested addition to `2026-06-12-summary.txt` (mirror the Korean recommendation): "Pick→Top30 overlap: Track A 1/5, Track B 0/5."

8. **INTC's win was partly luck — it was 9th on the leaderboard at +6.09% O→C.** The thesis (BofA double-upgrade drift) was sound, but the actual move size was modest enough that a couple of unfavorable ticks could have made it a HOLD instead of a TP. The *process* (picking it) was clearly right; don't over-update on the +5% outcome by chasing more "BofA upgrade drift" setups indiscriminately. Conversely, **the RKLB loss was a process failure** — the warning was in our own brief, we ignored it. Process losses are the ones worth fixing.
