# Improvement Notes — 2026-06-16

> **Headline:** KOSPI +2.11% / KOSDAQ **−1.48%** — 06-15에 이어 **2일 연속 kospi_strong_diverge** 패턴. KOSPI 대형주는 갭상승 후 분배 (제한적 +1~3%), KOSDAQ은 그냥 분배.
>
> | Combo | Track A | Track B | 비고 |
> |---|---|---|---|
> | **v1-v1-v1** | **+1.80%** (4/5) | **−0.72%** (2/5) | 한화에어로/한화오션/현대로템 3 TP |
> | **v2-v2-v2** | **−1.00%** (4/5) | **−3.00%** (0/5) | HPSP/원익IPS/테크윙 -10~-18% 폭락 |
> | **v3-v3-v3** | **−1.00%** (4/5) | **+0.20%** (1/5) | mechanical filter는 작동, but HD현대일렉트릭 −8% 양 트랙 발목 |
>
> 3일 연속 v1 우위 (06-15 +2.28/+1.80, 06-16 +1.80/−0.72). v3가 v2 대비 Track B는 회복 (+3.20%p 차이) — E5/E3 mechanical filter의 명백한 effect.

---

## Losers — why agent picked them

### v3 critical loser: 267260 HD현대일렉트릭 — Track A & B 양쪽 SL −3% (실측 −8.09%)

**같은 종목이 양 track에 중복 픽되어 양쪽 SL 동시 hit.** Track A score 4, Track B score 4. 둘 다 sub_theme="전력 인프라-변압기". brief rule #8 (cross-track dedup) 위반.

- **picks 시점 reasoning:** "NVDA 채권 200억달러 발행 → AI 인프라 전력 narrative 강화 + 동일업종 +9.94% 동반 강세 + 전일 +4.34% 건전 추세."
- **What happened:** 갭+1.51% 시초 → 첫 5분 min −3.38% (SL 즉시 hit) → ↓ 패턴, 종일 분배, 저점 −8.66% (14:47).
- **Diagnosis 1 (단기):** **첫 5분 dip −3.38%** = 06-12 lesson 룰에 따르면 entry defer 대상. mechanical filter는 entry timing은 못 잡음 — prompt-level rule.
- **Diagnosis 2 (구조):** HD현대일렉트릭은 **3일 연속 우리 픽** (06-12 SL, 06-15 미픽, 06-16 SL). 같은 종목이 같은 narrative ("AI 인프라 전력")로 반복 픽되는데 매번 갭상승 후 분배. **이건 universe 문제가 아니라 narrative attachment 문제** — agent가 NVDA/AI 데이터센터 뉴스 = HD현대일렉트릭이라는 자동 매핑을 못 끊음.
- **Diagnosis 3 (cross-track dup):** brief agent v3가 두 track에 별도 호출되어 같은 후보를 두 번 추천. v3 brief에 "rule #8 cross-track dedup" 명시했지만 두 호출이 독립적이라 적용 불가. **이건 pipeline 측 mechanical fix 필요.**

### v3 Track B loser: 277810 레인보우로보틱스 — SL −3% (실측 −9.41%)
- **Reasoning:** "휴머노이드 대장주, 초정밀지향마운트 자체개발, 전일 +5.77% 건전 추세."
- **What happened:** 갭+3.03% → 첫 5분 min −2.5% (경계선) → ↓ 패턴 종일 분배, 저점 −10.29% (14:59).
- **Diagnosis:** "휴머노이드 멀티위크 모멘텀"은 narrative leakage. fresh_catalyst 일자 없이 multi-week trend로만 픽. KOSDAQ 분배 환경(-1.48%)에서 KOSDAQ 모멘텀 종목은 1순위 매도 대상. **P3 (regime + gap > 3%) 가 발동했어야 하는데 regime=continuation으로 분류되어 발동 안됨.**

### v3 Track B loser: 083650 비에이치아이 — SL −3% (실측 −2.44%)
- **Reasoning:** "웨스팅하우스 폴란드 원전 + SMR multi-week."
- **What happened:** 갭+3.11% → ↓ 패턴 분배, 저점 −3.73%.
- **Diagnosis:** Polish reactor news는 dated catalyst가 아니라 multi-week. SMR 테마는 진짜지만 KOSDAQ 분배 환경에서 약한 종목.

### v2 catastrophic Track B (참고용): HPSP −17.64%, 원익IPS −11.46%, 테크윙 −12.30%

세 종목 모두 **06-15에 +5% 이상 상승했던 종목**. 6/15 HPSP +5%(TP), 원익IPS +5%(TP), 테크윙 +5%(TP). 즉 어제 TP 친 종목을 다음날 또 픽 → 익일 분배 직격.

- **v3에선 자동 차단:** v3 brief가 prev_day_change_pct를 추적 + research E5 (전일 +15% EXCLUDE) 적용. HPSP/원익IPS는 06-15에 +5% 정도라 E5 발동 안됐지만 v3 brief에서 후보로 안 올림 (다른 sub_theme 분산).
- 결과적으로 **v3가 v2 대비 Track B +3.20%p 우위** — E5/E3 mechanical filter 효과 입증.

### v1 Track B 손실 (3 SL): 가온전선, STX엔진, 효성중공업
- **STX엔진:** 06-15에 +12.54% (high) 찍은 종목 → 익일 분배. 06-12에도 우리 픽이었음 (3일 연속).
- **효성중공업 (변압기):** HD현대일렉트릭과 동일 sub_theme. 같은 운명.
- **가온전선 (전선):** 갭+4.96% 후 첫 5분 min −1.53%, 그 후 9:05에 −3.59% SL.

→ Track B 6종(v1+v2 합산)이 다 손실, v3 Track B만 +0.20%로 살아남음. **mechanical filter ROI 확실.**

---

## Best entry timing

| Ticker | 종목 | open entry | best entry | 차이 | 패턴 분석 |
|---|---|---|---|---|---|
| 005930 삼성전자 | HOLD 0% | 10:09 HOLD +1.95% | 본질 같음 (TP 미터치) | = 박스 |
| 000660 SK하이닉스 | SL −3% | 10:09 HOLD +3.19% | 오전 10시 단기 push 후 다시 분배 | = 박스 |
| 267260 HD현대일렉트릭 | SL −3% | 14:47 HOLD +0.45% | 종일 분배 중 마감 직전 데드캣 | ↓ |
| 277810 레인보우로보틱스 | SL −3% | 14:56 HOLD −0.16% | best entry조차 손실 | ↓ |
| 011200 HMM | TP +5% | 09:00 TP +5% | 시초 진입 = 최선 | ~ |

**관찰:**
1. **2일 연속 "장 후반 14시대 best entry" 패턴.** 06-15도 동일했음 — 손실 종목들은 모두 종일 분배 후 마감 직전 미세 반등이 best entry. 우리 strategy (TP까지 hold) 와 무관, 매도 시점 best ≠ entry.
2. **유일하게 09:00 진입이 정답이었던 종목: HMM** (호르무즈 + WTI −5% dated catalyst). **dated fresh_catalyst가 있는 종목만 시초 entry가 작동.** narrative-only 종목은 14시 best entry가 시그널.
3. **첫 5분 dip rule re-검증 (06-12, 06-15 lesson):**

| Ticker | first5_min | Open→SL/TP | 결과 |
|---|---|---|---|
| 064350 현대로템 (Track B) | −1.13% | TP@open | ✅ entry 정답 |
| 011200 HMM | −2.14% | TP@open | ✅ entry 정답 (보더라인) |
| 267260 HD현대일렉트릭 | **−3.38%** | SL | 룰 적용 시 defer → 종일 분배, 별 도움 안됨 |
| 277810 레인보우로보틱스 | **−2.50%** | SL | 룰 적용 시 defer → 도움 안됨 |
| 083650 비에이치아이 | None (no data) | SL | - |
| 032820 우리기술 (Track B TP) | −1.69% | TP@open | ✅ entry 정답 |

**룰 검증:** first5_min ≤ −2.5% → 전부 SL. first5_min ≥ −2.1% → TP. **여전히 강력한 signal**. 다만 SL 종목들은 defer해도 종일 분배라 실익 제한적. **룰을 코드에 정확히 구현하려면 09:05 시점 entry skip + 09:15에 시초가 회복 여부 재확인.** 만약 회복 안되면 그날 그 종목 skip.

---

## Top 30 winners we missed

오늘 catchable subset 14/30 평균 +3.29%. 우리 picks 21종 중 top 30에 들어간 종목은 **0개**. 즉 오늘은 mega/large + 우리 mid universe가 통째로 일일 winner 분포 밖에 있었음.

### 🚨 가장 큰 누락 클러스터: 풍력/태양광 (top 13에 5종!)

| Rank | Ticker | Name | Mkt | O→C | 패턴 | Catch |
|---|---|---|---|---|---|---|
| 1 | 297090 | 씨에스베어링 | KOSDAQ | **+29.79%** | 상한가 | ✅ ok |
| 2 | 112610 | 씨에스윈드 | KOSPI | **+29.68%** | 상한가 | ✅ ok |
| 4 | 100090 | SK오션플랜트 | KOSPI | +27.60% | ~ | ⚠️ narrow |
| 11 | 100130 | 동국S&C | KOSDAQ | +16.81% | ~ | ⚠️ narrow |
| 13 | 389260 | 대명에너지 | KOSDAQ | +16.55% | ~ | ✅ ok |

**Why missed:** 우리 universe (v1/v2/v3 모두)에 **풍력/태양광 sub_theme이 통째로 없음**. NVDA 데이터센터 전력 narrative를 보고 "전력 인프라" sub_theme으로 잡았는데 그건 변압기/AI 데이터센터에만 매핑. **재생에너지 / 풍력 발전이 NVDA 전력 수요와 직결되는 logic을 놓침.** 정책 측면에서도 6월 중순 한국 정부 그린뉴딜 / 재생에너지 비중 확대 정책이 있었던 것으로 추정.

**Fix:** universe_track_a_v4.txt에 추가:
- 풍력: 씨에스윈드(112610), SK오션플랜트(100090), 두산퓨얼셀
- 태양광: 한화솔루션(009830 — 이미 v2에 있음), 한화에어로스페이스/한화시스템

universe_track_b_v4.txt:
- 풍력 부품: 씨에스베어링(297090), 동국S&C(100130), 태웅(044490)
- 태양광/재생: 대명에너지(389260)

context_agent_v4.txt 테마 리스트에 "재생에너지/풍력" 추가.

### 건설 (top 30에 4종)

| Rank | Ticker | Name | O→C | Catch |
|---|---|---|---|---|
| 3 | 013360 | 일성건설 | +27.72% | ⚠️ narrow |
| 9 | 047040 | 대우건설 | +18.57% | ✅ ok |
| 24 | 042940 | 상지건설 | +13.02% | ✅ ok |
| 28 | 375500 | DL이앤씨 | +10.92% | ✅ ok |

**Why missed:** 건설 sub_theme이 universe에 없음. 호르무즈 + 글로벌 물동량 narrative → 해외 인프라 수주 기대로 건설주 동반 강세. 우리는 같은 narrative로 HD현대중공업/HMM (조선/해운) 만 잡음. 건설은 brief에 등장조차 안함.

**Fix:** universe에 KOSPI 건설 대형주 (DL이앤씨, 현대건설, GS건설, 삼성물산) 추가 + brief의 cross-rotation pairs에 "호르무즈 정상화 → 해외 건설 수주 기대"  매핑 추가.

### 기타 single-name 누락

- **SK이터닉스 (475150) +14.23%** — SK그룹 원전 자회사. universe에 부재.
- **미래에셋생명 (085620) +15.18%** — 금융 보험. 외국인 순매수 전환 직접 수혜.
- **뉴엔AI (463020) +14.95%** — AI 인프라 KOSDAQ. v2 06-12 universe에 있었지만 v3 안 잡음.

---

## Other observations

### 1. 3일 연속 v1 우위 = 우리가 universe/scoring을 잘못 진화시키고 있다는 강한 시그널

| Date | v1 A | v1 B | v2 A | v2 B | v3 A | v3 B |
|---|---|---|---|---|---|---|
| 06-12 | — | — | (single combo legacy) | | | |
| 06-15 | +2.28% | +1.80% | −0.48% | −1.40% | — | — |
| 06-16 | +1.80% | −0.72% | −1.00% | −3.00% | −1.00% | +0.20% |

- **v1이 항상 Track A에서 최고**. v1 universe는 단순한 예시 리스트 (시총 5조+ 대표주 18종) — diversification이 자연스럽게 강제됨.
- **v2/v3는 universe 확장 + sub_theme 세분화 했더니 오히려 narrative-attached 종목 (HD현대일렉트릭, SK스퀘어, 한미반도체) 반복 픽 발생.**
- 의외로 **v3 Track B만 v2 대비 명확한 우위 (+3.20%p)** — KOSDAQ 분배 환경에서 E5/E3 filter가 어제 winner를 자동 cut.

**구조적 결론:** Track A는 universe를 다시 좁히고 v1 수준으로 회귀가 필요할 수도. 또는 D1 (sub_theme max 2) 가 너무 약함 — 동일 sub_theme 중복 후보 자체를 candidate stage에서 cut.

### 2. HD현대일렉트릭 cross-track duplicate — pipeline mechanical fix 필요

v3 brief가 두 track 호출에서 같은 종목을 각각 추천. brief rule #8 ("cross-track dedup") 은 *single brief call 내* 룰이라 두 별개 호출에는 적용 안됨.

**Fix:** `run_morning_pipeline.py`에 post-brief dedup 단계 추가:

```python
def dedup_across_tracks(track_a_candidates, track_b_candidates):
    """KOSPI mega/large는 Track A 우선, Track B에 중복되면 drop."""
    a_tickers = {c['ticker'] for c in track_a_candidates}
    track_b_clean = [c for c in track_b_candidates if c['ticker'] not in a_tickers]
    return track_a_candidates, track_b_clean
```

`run_one_combo`에서 Track A brief 직후 Track B brief 결과에서 중복 cut.

### 3. v3 mechanical filter는 작동하지만 "narrative-attached HD현대일렉트릭" 같은 반복 미스를 못 잡음

E3 (stale catalyst) 가 발동하려면 "5거래일 이전 뉴스" 일치해야 함. HD현대일렉트릭 NVDA narrative는 매일 갱신되어 stale로 분류 안됨. 하지만 **agent 입장에서는 매일 같은 종목, 같은 narrative, 같은 SL 결과**.

**Fix 제안:** picks history 추적 + "직전 5거래일 중 2회 이상 SL hit한 종목"은 E6 (recent loser) 로 EXCLUDE.

```python
# pipeline 측 새 룰
E6_RECENT_LOSER_LOOKBACK_DAYS = 5
E6_RECENT_LOSER_SL_THRESHOLD = 2
# variant_performance.csv 또는 picks JSON 직전 5일 검사
# ticker가 2회 이상 SL hit이면 score=1, hard_exclusions에 E6 추가
```

HD현대일렉트릭은 06-12 SL, 06-16 양 트랙 SL — 직전 5일 SL hit 3회. E6 발동 가능.

### 4. KOSPI/KOSDAQ divergence flag는 작성됐지만 운용에 미반영

v3 context에 `kospi_vs_kosdaq` divergence flag 추가했지만, **brief/research agent가 이 정보를 보고도 Track B 종목 수를 조정 안함**. 5종 모두 채움. **divergence 발동 시 약세 시장 track 픽 수 강제 축소 (5종→3종) 또는 cash slot 명시**가 필요.

**Fix:** 
- aggregate stage에서 context의 divergence flag 파싱
- `kospi_strong_diverge` 면 Track B 최종 3종으로 cap
- 또는 Track B picks에 자동으로 "weight cap = 0.6" 정보 추가하여 사용자가 포지션 사이즈 조정 가능

### 5. WIN 종목 학습: 한화에어로스페이스(012450) +5% TP (v1 only)

v1만 픽한 종목. v2/v3 brief는 한화에어로를 "방산-항공우주" sub_theme으로 인식했지만 final picks에서 빠짐 (대신 현대로템 픽). 

- **6/16 한화에어로 reasoning (v1):** simpler — universe에 listed, brief가 dated catalyst (유로사토리 + 방산 수출) 명시. 
- **v2/v3에서 빠진 이유:** D1 sub_theme cap에 막혔거나, 6/12 +7.5% 상승 데이터가 prev_day로 인식되어 P6 (10~15%) 발동 우려.

**Lesson:** mechanical filter는 winner도 같이 cut할 수 있음. **TP 가능했던 종목이 mechanical filter로 빠진 경우 추적 필요** — 다음 day 운용시 추가 분석.

---

## Action items (우선순위 순)

| 우선순위 | 항목 | 영향 추정 |
|---|---|---|
| **CRITICAL** | Pipeline post-brief cross-track dedup | HD현대일렉트릭 양 트랙 SL 방지 (오늘 −16% 손실 회피) |
| **HIGH** | E6 mechanical: 직전 5일 2회+ SL hit 종목 EXCLUDE | HD현대일렉트릭류 반복 미스 차단 |
| **HIGH** | universe_v4: 풍력/태양광 sub_theme 추가 (씨에스윈드, SK오션플랜트, 씨에스베어링, 동국S&C, 대명에너지) | 오늘 top 13 중 5종 catchable 누락 회복 가능 |
| **HIGH** | universe_v4: 건설 sub_theme 추가 (대우건설, DL이앤씨, 상지건설, 일성건설) | top 30 catchable 4종 회복 |
| **MEDIUM** | context_agent에 "재생에너지/풍력" + "해외 건설 수주" cross-rotation 추가 | 호르무즈/물동량 narrative → 건설 매핑 |
| **MEDIUM** | aggregate stage에서 divergence flag로 Track B 픽 수 cap | KOSDAQ 약세 day 손실 최소화 |
| **LOW** | first5_min ≤ −2.5% defer rule 코드 구현 (runtime entry timing) | open SL 회피, but SL 종목 대부분 종일 분배라 실익 제한적 |
| **LOW** | mechanical filter로 winner cut된 경우 후속 추적 (post-mortem) | filter overshoot 진단 |
