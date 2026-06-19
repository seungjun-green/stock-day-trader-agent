# Improvement Notes — 2026-06-17 (US, v1-v1-v1)

> Combo P&L (open entry, TP 5% / SL 3%): Track A **−1.81%** (0 TP, 4 HOLD, 1 SL), Track B **+0.51%** (3 TP, 0 HOLD, 2 SL).
> First positive Track B day since tracking began. **ARWR was the cleanest single winner** (+5.87% O→C, O→L −0.81%, clean ↑ pattern).
> Market backdrop: SPY −1.25%, QQQ −1.01%, IWM −0.75%, VIX **+12.37%** → genuine risk-off into FOMC. Warsh's hawkish dot plot was the dominant event.

---

## Track A — theme over-concentration killed the result

Four of five Track A picks are direct plays on the same "Iran peace deal / oil unwind" rotation: UAL, DAL, RCL, and (with a thinner connection) CAT via industrial momentum. NEM was the only orthogonal diversifier. On a fragile FOMC tape this looks like **4 votes for 1 thesis** — when the theme fades, the whole track fades together. The Korean side learned this exact lesson with the 06-15 semis over-concentration → D1 rule. **US has no D1 yet**, and the data just confirmed why we need it.

### Pick-by-pick

| Ticker | Score | O→H | O→L | Result | Diagnosis |
|---|---|---|---|---|---|
| UAL | 4 | +1.52% (09:36) | −2.62% | HOLD −2.25% | High at 09:36, ↓ all day. Research called it "the lead airline" — but lead = already extended. Same "narrative-extended at entry" failure as Korean SK하이닉스/HD현대일렉트릭. |
| CAT | 4 | +1.95% (15:02) | −0.42% | HOLD −0.11% | Range-bound = pattern. Late-day high. Research **literally wrote** "though valuation is stretched" and picked it anyway. **E4 self-contradiction violation** — Korean code would have cut this. |
| NEM | 4 | +3.70% (11:35) | −2.49% | HOLD −2.32% | Λ pattern; pre-FOMC pop, post-FOMC fade. Gold-hedge thesis was correct *direction*, wrong *holding window*. A pre-FOMC exit at 13:30 would have captured +3% before the dot-plot reaction. |
| DAL | 3 | +0.80% (09:36) | −1.73% | HOLD −1.36% | Same theme as UAL but shallower range. Research itself: "DAL closed +1.22% vs UAL +3.85% on Monday, making it the secondary play." Picking the *secondary* play in an over-concentrated theme means you eat the fade with none of the upside. |
| RCL | 3 | +1.93% (09:36) | −3.23% | **SL −3.00%** | Research: "RCL is the higher-quality cruise name but **already extended after Monday's pop**." Picked anyway. **Second E4 violation.** |

### Pattern across Track A losers

- **3 of 5 had `high_time` within the first 6 minutes** (UAL 09:36, DAL 09:36, RCL 09:36). Same open-as-high distribution signature as the Korean side. Add this to the rubric: if pre-market gap is positive AND theme is already 2+ days hot, treat "open auction high" as a hard exit signal, not a continuation.
- **The "already extended" pattern is now confirmed for the third time** — Korean SK하이닉스 (06-12), Korean SK스퀘어 (06-15), US UAL/RCL (06-17). The rule should be: if research reasoning contains words like *extended, stretched, lagged, secondary, already up X%*, drop the candidate. The Korean pipeline does this mechanically via E4 regex. **US needs the same pattern, calibrated to English hedge words.**
- **NEM's Λ pattern is a separate lesson**: gold as a "FOMC hedge" was right pre-decision, wrong post-decision. Either we exit before 14:00 ET or we don't use FOMC hedges as day-trades. Static set-and-forget TP/SL is the wrong execution for event-day hedges.

---

## Track B — the first true winning day, with one big lesson per loser

| Ticker | Score | O→H | O→L | Result | Notes |
|---|---|---|---|---|---|
| **ARWR** | **3** | +7.75% (13:22) | **−0.81%** | **TP +5.00%** | Clean ↑ pattern, low at open then steady climb. Closed +5.87% O→C. **Best pick of day across both tracks.** |
| **IREN** | 4 | +4.58% (14:44) | −2.14% | **TP +5.00%** | Hit TP intraday on AI-infra strength; closed −1.46% O→C. Λ pattern but TP-then-fade still captures the trade. |
| **UPST** | 3 | +5.76% (13:02) | −5.20% | **TP +5.00%** | Hit TP at 13:02 (just before FOMC), then full reversal. Closed −5.11% — the trade was a *win* under our TP/SL rules but the *thesis* (fintech holds into Warsh) was clearly wrong. Lucky timing. |
| ANF | 4 | +2.60% (09:44) | −4.97% | **SL −3.00%** | Oversold bounce + Iran rotation thesis. Got faded with the broader rotation on FOMC fragility. |
| ASTS | 4 | +3.44% (14:44) | −3.26% (09:32) | **SL −3.00%** | **Hit SL in the first 2 minutes** of trading. Textbook "sell-the-news" — BlueBird launch was at 02:39 ET, well before open, so the catalyst was already in the pre-market price. |

### Lessons

**1. ARWR is the prototype "clean" pick the system should reproduce more of.**
- Sector: biotech (NOT in any over-hyped theme — no Iran rotation, no SpaceX adjacency, no AI infra)
- Catalyst: FDA-approved drug + Phase 3 trials ongoing; analyst-flagged top 2026 biotech catalyst (TD Cowen, Dec 2025)
- Research reasoning: **zero hedging words** — no "but", "however", "extended", "headwind"
- Got the *lowest score of Track B* (3, same as UPST) and delivered the highest P&L
- Sub-theme: biotech-Phase-3-data, orthogonal to everything else in the picks
- **Action**: Audit the scoring rubric — why does this clean a pick score only 3? The "biotech binary risk flag" in the brief is over-deducting. Adjust so a Phase-3 with a dated, analyst-validated catalyst keeps its base score.

**2. ASTS = the Korean "stale catalyst" rule, US edition.**
- Catalyst (BlueBird launch) fired **at 02:39 ET — almost 7 hours before market open**
- By 09:30 the news was fully priced; opening the position at the open meant buying the high of post-news enthusiasm
- The picks should distinguish between:
  - *Pre-open catalyst* (already priced → sell-the-news risk → DROP or score down)
  - *During-session catalyst* (price discovery still ahead → can be tradable)
  - *After-close catalyst* (next-day setup → tradable if news flow continues)
- Korean v3 already encodes this via "fresh_catalyst within 2 trading days but **dated to today's session, not last night**." US v1 has no such guard.

**3. UPST's TP was lucky, not skilled.**
- Brief and research **both** flagged the hawkish-FOMC headwind
- Specifically research_reasoning said: "rate-sensitive AI-lender faces headwinds into hawkish FOMC risk; insider sell by President Datta on June 9 is a minor offset"
- We picked it anyway with score 3 → **Third E4 self-contradiction violation of the day**
- The TP at 13:02 was a pre-FOMC pump; if we'd entered at 13:30 the trade would have been a clean SL
- **Don't read this as "the system worked." Read it as "the system picked a coin-flip and the coin landed heads."**

**4. ANF was a regime mistake, not a stock mistake.**
- Oversold + consumer-rotation thesis is fine *on a stable risk-on day*
- On a "VIX +12% into hawkish FOMC" day, oversold consumer names get flushed because the very rotation thesis (risk-off → defensives) doesn't apply — risk-off goes to cash/bonds/gold, not retail
- Same lesson as Korean side: **the regime tag from the brief was "Risk-off tilt / sideways" — and we still picked rotation/oversold-bounce plays that need risk-on tape**

---

## E4 self-contradiction count today: **3 of 10 picks** (CAT, RCL, UPST)

The US brief reasoning is **rich with English-language hedge phrases** that match the structural pattern Korean E4 catches. Today's hits in research_reasoning:

| Pick | Hedge phrase in own reasoning | Outcome |
|---|---|---|
| CAT | "though valuation is **stretched**" | HOLD −0.11% (escaped only because of tight range) |
| RCL | "**already extended** after Monday's pop" | SL −3.00% ❌ |
| UPST | "rate-sensitive AI-lender faces **headwinds** into hawkish FOMC risk" | TP (lucky) +5.00% |

If we add an English E4 regex to the US pipeline, recommended pattern set (initial draft for discussion, not committed yet):
```
stretched, extended, headwind, already up, lagged, secondary,
overbought, exhausted, faded, no fresh catalyst, sell-the-news
```
Plus the universal hedging phrases:
```
but, however, although, despite, risk that
```
…with a cap of 1 such phrase per reasoning before triggering exclusion (because real reasoning often acknowledges *one* risk). Two or more → cut.

---

## Top 30 overlap = unavailable today (scraper issue)

`collect_daily_data.py` reported "Got 0 candidates" from both NASDAQ API and Yahoo fallback. The Pick→Top30 overlap section in the summary was empty. This is the same intermittent issue noted on 06-16. **Action separate from prompts: investigate `fetch_top_30_intraday` in `us/collect_daily_data.py`** — likely an API endpoint/format change or a rate limit.

---

## What worked (file under "keep doing")

1. **Code enforcement fired correctly and silently**:
   - Cross-track dedup dropped UAL from Track B (would have caused matching loss in both tracks otherwise — same archetype as the Korean 06-16 HD현대일렉트릭 disaster the rule was designed to prevent)
   - E6 silently excluded CRDO from being re-picked after 2 SL days (06-12, 06-16). We will never know if the LLM tried to pick it again, but if it did, we're protected.
2. **ARWR's selection mechanism worked** — biotech with a dated catalyst, analyst validation, no over-themed exposure. Whatever signal weighting got us here should be preserved.
3. **IREN is becoming our most reliable mid-cap winner** — also TP on 06-16's catchable set (one of the few catchables we owned). Now confirmed TP today. AI-infra mid-cap with concrete revenue contracts is currently the system's best-performing archetype.

---

## Concrete action items (in priority order)

1. **(HIGH)** Add English E4 regex set to `us/run_morning_pipeline.py` mechanical filter. Mirror the Korean pipeline's E4 mechanism but with English hedge words. Calibration: 06-12 + 06-16 + 06-17 picks all available — backtest the regex over the 30+ picks we've made and tune the threshold so true winners (ARWR, INTC, KLAC, IREN) survive and self-contradictory picks (CAT/RCL/UPST/RKLB/LUNR) get cut.
2. **(HIGH)** Add a "catalyst-timing" guard to brief or research v2: if `fresh_catalyst` references an event that fired *before* US 09:00 ET pre-market, downgrade by 1 OR move the pick to a "watch open price action" status rather than auto-entering at open. This addresses both ASTS (06-17) and SPCX-rotation sympathy plays (06-12).
3. **(HIGH)** Fix the `fetch_top_30_intraday` scraper. Without Pick→Top30 overlap we're flying blind on which winners we systematically miss — that's the primary signal for universe expansion.
4. **(MEDIUM)** Begin v2 brief work, focused on emitting `sub_theme` per candidate. Even without other v2 rules, just **having `sub_theme` as a field** unlocks the universal D1 diversification rule that the Korean side uses. Today would have caught the 4× Iran-peace-deal concentration in Track A.
5. **(MEDIUM)** Investigate scoring asymmetry: why ARWR (the day's best pick) only scored 3 while RCL (a clear loser) scored 3. Likely cause: the rubric over-weights `theme_alignment` and under-weights `fresh_catalyst with no hedging`. Backtest a re-weighted scorer on our existing picks before committing.
6. **(LOW)** ASTS post-mortem deserves a permanent "IPO-event-day / overnight-launch" tag in the playbook — same as the SPCX 06-12 lesson. We're starting to accumulate these as a distinct archetype.
