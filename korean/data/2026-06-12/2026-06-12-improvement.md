# Improvement Notes — 2026-06-12

> Combo P&L (open entry): Track A −1.99% (catchable 3/5), Track B +1.80% (catchable 2/5).  
> Day was the right call thematically (반도체 +HBM rally fired) but Track A got distributed at open and Track B 50% of TPs were given back via deep open-dips.

---

## Losers — why agent picked them

Open-entry losers were all in **Track A**. Track B had 2 SL hits (원익IPS, 테크윙) but both eventually printed +12% / +9% intraday highs — those are entry-window problems, covered in the next section.

### 000660 SK하이닉스 — SL −3.00% (gap +2.33%, O→C −5.74%, pattern ~)
- **Agent picked it score 5/5:** "마이크론 +11%, 램리서치 +12.7% 직접 수혜 대장주, 반도체 수출 3배 급증 펀더멘털 + HBM 테마 리더십."
- **What actually happened:** Gap was a soft **+2.33%** — far smaller than the +10~12% US semis move the agent leaned on. High at 09:11 (+1.01% from open), then steady distribution all day to low at 14:50.
- **Diagnosis:** The "직접 수혜 대장주" thesis assumed the gap would *expand* during the session. Instead the modest gap was the entire move — the catalyst was already arbitraged via the 2026-06-11 +2.64% close. Foreign selling persisting (per the brief itself) capped any continuation.
- **Signal mis-weight:** `premarket_strength` was checked but agent had no actual premarket print to verify against — it was inferred from US semis. When the live premarket landed soft (+2.33%), nothing in the score recalculated.

### 267260 HD현대일렉트릭 — SL −3.00% (gap +9.39%, O→C +2.08%, pattern ~)
- **Agent picked it score 4/5:** "AI 인프라·전력기기 대장주, 2028년까지 데이터센터 증설 사이클."
- **What actually happened:** Opened high, ran to +5.24% by **09:04** (best entry, TP-able), then collapsed to −5.24% by 10:22 before recovering. Λ-shape with low *after* high.
- **Diagnosis:** Right theme, wrong size of gap. A +9.39% overnight gap on a "테마 대장주" with a vague narrative (no day-specific catalyst) is the textbook distribution setup — institutions used the US infra rally to dump. Brief itself flagged this name's catalyst as "반도체 대비 약함" (own warning) and the score still came in at 4.
- **Signal mis-weight:** Agent gave `theme_leader` + `theme_alignment` + `clean_narrative` (3 signals) but every one of those is a *macro narrative* signal — none were dated to today. No `fresh_catalyst`, no `premarket_strength` confirmation, yet still scored 4.

### 042660 한화오션 — SL −3.00% (gap +7.85%, O→C −4.00%, pattern ↓)
- **Agent picked it score 3/5:** "조선 LNG 수주 모멘텀 유효, HD현대중공업 강세 동조."
- **What actually happened:** Opened at the day's high (09:02), then ↓ pattern straight down. First-5min `min=-4.69%` — SL hit before 09:07.
- **Diagnosis:** This was a sympathy pick (HD현대중공업 was the actual mover yesterday). A +7.85% sympathy gap with no own catalyst = supply on open. The brief said "오늘은 반도체 쏠림 국면이라 테마 강도는 2순위" — the agent literally wrote the disqualifier in its own reasoning, then picked it anyway.
- **Signal mis-weight:** Score 3 = "moderate setup," but the brief's own context flagged the sector as 후순위. Per the research prompt's penalty rule ("if context flags sector as risky/weak/uncertain, reduce score by 1"), this should have scored 2 and been cut.

**Common thread across Track A losers:** All three got picked on **narrative-only signals** (`theme_leader` / `theme_alignment` / `clean_narrative`) without a *dated* same-day catalyst. None had a hard `fresh_catalyst` specific to today. The brief itself was a "Bounce" regime with persistent foreign selling — exactly the regime where gap-ups get faded. Track A scores systematically over-weighted macro narrative and under-weighted gap-fade risk in a fading-foreigner tape.

---

## Track B open-dips — who held vs who flushed

All 5 Track B picks closed O→C positive. The split that matters is **whether the open-dip ate the −3% SL before the TP run**:

| Ticker | Name | Gap | O→L from open | Low time | Pattern | Result |
|---|---|---|---|---|---|---|
| 403870 | HPSP | +30.00% | **−1.22%** | 09:00 | 상 | TP ✅ |
| 095340 | ISC | +20.73% | **−0.99%** | 09:00 | ↑ | TP ✅ |
| 042700 | 한미반도체 | +24.05% | **−2.61%** | 09:16 | ~ | TP ✅ |
| 240810 | 원익IPS | +30.00% | **−7.97%** | 09:17 | 상 | SL → +12.39% close |
| 089030 | 테크윙 | +6.87% | **−3.09%** | 09:00 | Λ | SL → +0.77% close |

The dividing line is brutally clean: **picks with open-dip ≤ −3% hit SL, ≥ −2.7% kept the entry alive**. Patterns I can spot:

1. **상한가-and-hold vs 상한가-and-distribute (HPSP vs 원익IPS).** Both opened at +30% (limit up). HPSP's dip was −1.22% (one tick of fake supply at 09:00), then it locked 상 all day. 원익IPS dipped −7.97% — that's a 10 percentage-point gap give-back in the first 17 minutes. Why the difference?
   - HPSP is a smaller-cap KOSDAQ pure-play (고압 수소 어닐링 독점), thin float, retail-heavy → 상한가 sticks.
   - 원익IPS is the bellwether mid-cap semi-equipment name with deep institutional ownership → profit-takers at the +30% gap.
   - **Rule of thumb:** when a thinner pure-theme name and a bellwether both 상한가 open on the same catalyst, the bellwether is the one that gives back.

2. **`low_time = 09:00` is the bullish tell, not `low_time = 09:15+`.** The 3 TP winners all had their day-low *at or in the first minute of* the open, meaning the gap was bought from tick 1. The 2 SL casualties had lows at **09:16–09:17** — institutional selling pressure rolled in *after* the open auction. The agent does not currently look at `low_time` vs `high_time` ordering for Track B, but it's the cleanest gap-quality signal in the file.

3. **Smaller gap ≠ safer entry.** 테크윙 had the smallest gap (+6.87%) of the five, and the agent might naïvely think "more room to TP." But the small gap + Λ pattern reveals there wasn't institutional buying conviction at all — it gapped on sympathy, not on its own catalyst, and got distributed immediately. **Conviction-weighted gap > headline gap size.**

4. **`first_5min_min_pct` predicted the SL outcome cleanly.** Both SL casualties had first-5min min ≤ −3.09% (테크윙: −3.09%, 원익IPS: −4.97%). Both TP winners (HPSP, ISC) had first-5min min ≥ −1.22%. 한미반도체 was the edge case (first-5min min −1.96%, full session min −2.61% at 09:16). **Action:** the scoring/back-test rubric should add a "first-5min drawdown" tag — if a pick's first-5min min is worse than −2.5%, the open entry should be deferred or scaled, even if it eventually TPs.

**Takeaway:** Track B's theme call (HBM/semis) was correct — all 5 names finished with positive O→C, average +13.84%. But blindly entering at the open cost 2 of 5 SL. A simple rule of "skip open-entry if first 5min prints worse than −2.5% from open, then re-enter on the first higher-low" would have salvaged both 원익IPS and 테크윙 (best entries were 09:13 and 09:00, both TP-able with patience).

---

## Top 30 winners we missed (catchable, not in our picks)

Of the 30 movers, 11 were `✅ ok` catchable. We owned 2 of those (한미반도체 #16, 한전KPS… wait — we didn't own 한전KPS). Real overlap with `✅ ok`: just **한미반도체 (#16)**. HPSP (#5) was ⚠️ narrow, not ok. So we got 1/11 catchable. The misses below are the ones we should have screened in.

### The dominant miss: **원자력 / 전력 인프라 sub-theme** (3 of top 9)

| Rank | Ticker | Name | Sub-theme | O→C | Catchable |
|---|---|---|---|---|---|
| 3 | 051600 | 한전KPS | 원전 정비/SMR | +27.54% (상) | ✅ |
| 8 | 052690 | 한전기술 | 원전 설계 | +23.51% (상) | ✅ |
| 9 | 083650 | 비에이치아이 | 원전 보조기기/SMR | +23.24% (상) | ✅ |

**Why we missed:** The brief identified "AI 인프라·전력기기" as an active theme but mapped it to **HD현대일렉트릭 / LS일렉트릭** only — i.e., the variable-frequency-drive and 변압기 layer. It never connected "AI 데이터센터 전력 수요 → 원전 르네상스." This is a known June-2026 macro story (한미 SMR 협력, 두산에너빌리티 모멘텀) and the universe filter for both tracks excluded it.

**Concrete fix for the universe prompts:**
- **`universe_track_a_v1.txt`** examples list misses 두산에너빌리티(034020), 한전KPS(051600). Add them — they are clearly large/mega cap (시총 5조 이상).
- **`universe_track_b_v1.txt`** should add KOSDAQ SMR/원전 names: 비에이치아이(083650), 우리기술(032820 — was #6 mover), 보성파워텍, 우진엔텍.
- The `context_agent_v1.txt` brief prompt should add "원전/SMR" to the explicit theme list ("반도체, AI, 로봇, 조선, 방산, 바이오, **원전/SMR, 전력 인프라**").

### Secondary miss: **방산 reversal** (we explicitly de-rated it)

| Rank | Ticker | Name | O→C | Catchable |
|---|---|---|---|---|
| 7 | 484870 | 엠앤씨솔루션 | +23.79% | ✅ |
| 21 | 288180 | 케이피항공산업 | +16.42% (SL) | ✅ |

The brief said "**미-이란 긴장 완화로 단기 차익 실현 압력 가능**" and the agent dropped 방산 from picks entirely. But two 방산 names made the top 21 catchable list. Lesson: "차익실현 압력" is a single-day call that can flip on any geopolitical headline; if a theme is on a multi-week trend (방산 has been since May), it deserves at least 1 watch-list slot regardless of the day's macro framing.

### Tertiary misses: individual catalysts (not theme-bucketable)

| Rank | Ticker | Name | Why catchable was missed |
|---|---|---|---|
| 13 | 204320 | HL만도 | 자율주행/현대차 그룹 — not in universe examples |
| 18 | 045520 | 크린앤사이언스 | 필터/공기청정 — no theme link |
| 22 | 012750 | 에스원 | 보안 — defensive rotation, brief flagged it as "디펜시브 매력 제한적" |
| 23 | 144960 | 뉴파워프라즈마 | KOSDAQ 반도체 장비 — **should have been picked**, identical thesis to 원익IPS |
| 25 | 464080 | 에스오에스랩 | 라이다/자율주행 KOSDAQ |
| 30 | 241770 | 메카로 | 반도체 장비 KOSDAQ — **should have been picked** |

**Most painful single miss: 뉴파워프라즈마 (#23) and 메카로 (#30).** Both are KOSDAQ 반도체 장비 — *exact* same thematic logic as our 원익IPS / HPSP picks. The candidate-screening prompt produced 10 names but only had 4 KOSDAQ 반도체 장비 names (원익IPS, HPSP, 테크윙, ISC) plus 한미반도체. Widen the candidate pool from 10 to 15 in the strongest theme of the day — when the theme is this strong (3 of top 5 are KOSDAQ semis equipment), the marginal pick is more valuable than diversification.

---

## Other observations

1. **The brief's regime tag ("Bounce") was correct, but the agent ignored its implication.** Bounce regimes punish gap-ups in Track A (low-conviction follow-through) and reward gap-and-go in Track B (short-covering + retail FOMO). Our results mirror this exactly: Track A −1.99% / Track B +1.80%. The scoring rubric should explicitly down-weight Track A scores by 1 when regime = bounce and gap > 5%, since the gap *is* the entire move in a bounce.

2. **`change_pct` (gap) data was never fed back into scoring.** The agent scored picks at ~08:30 with no premarket prices. By the time we know the actual open gap, no re-score happens. For Track A specifically, if the live gap is < +3%, the "premarket_strength" signal — which contributed to both SK하이닉스 (5/5) and 삼성전자 (5/5) — was false and the score should drop. Adding a pre-open re-score step (read the open auction, recompute) would have cut SK하이닉스 from the picks.

3. **"clean_narrative" is the most over-used signal.** It appeared on 4 of 5 final Track A picks and 3 of 5 final Track B picks. It's also the cheapest signal — every analyst can write a clean narrative for any stock. Either drop it from the rubric or cap it at +0.5 to total score.

4. **The brief is being copy-pasted into reasoning.** The brief, context, and reasoning files are nearly identical in their `Today's setup` paragraphs. The "reasoning" file should add agent-specific reasoning (why each candidate maps to the brief), not duplicate the brief. Right now it reads as one giant context blob followed by per-pick reasoning — that bloats the prompt and hides the actual mapping logic.

5. **Top-30 catchable / picked overlap = 1/5 for Track B (한미반도체).** That's actually decent given the universe constraint, but the next iteration should report this overlap as a metric in the summary so we can track it over time. Suggested addition to `2026-06-12-summary.txt`: "Pick→Top30 overlap: Track A 0/5, Track B 1/5."

6. **HPSP's perfect outcome was partly luck.** It opened at +30% (상한가) and stuck. If even one institutional seller had hit the bid at 09:00, we'd be looking at a 원익IPS-style flush. We should not over-update on HPSP — the *process* (picking it) was sound, but the outcome variance was high. Conversely, we should not over-punish ourselves for missing 한전KPS — that's a *process* miss (universe gap), and process misses are the only ones worth fixing.
