# Improvement Notes — 2026-06-15

> **Headline:** KOSPI 갭+4.95% → O→C +0.23% (gap-and-hold), KOSDAQ 갭+1.86% → O→C **−1.35%** (gap-and-fade).
> Brief predicted "modest +0.5~1.0% gap" — **실제 KOSPI 갭은 예측의 5배**. 이 단일 사실이 오늘의 모든 손실을 설명.
>
> | Combo | Track A | Track B | 비고 |
> |---|---|---|---|
> | **v1-v1-v1** | **+2.28%** (catch 4/5) | **+1.80%** (catch 1/5) | 5종 5테마 분산 |
> | **v2-v2-v2** | **−0.48%** (catch 4/5) | **−1.40%** (catch 3/5) | 4종 반도체, 1종 조선 |
>
> v2가 v1에 졌다 — **v2가 06-12 lesson (반도체 over-concentration)을 그대로 반복**.

---

## Losers — why agent picked them

### v2-v2-v2 Track A 손실 4종 (한화오션 1종만 TP)

#### 000660 SK하이닉스 — HOLD +0.22% (gap +6.19%, O→C +0.22%, pat =)
- **Agent 5/5, primary `theme_leader`:** "HBM4 442억 발주 + 6/12 +4.05% 추가 상승."
- **What happened:** 갭 +6.19%에 시초 형성 → 종일 +0.22% ~ +1.71% 박스, 추가 상승 동력 부재.
- **Diagnosis:** 시초가가 TP(+5%) 대비 위에서 형성되었어야 할 catalyst가 이미 6/12 +4.05%로 소진. 06-12 lesson "갭이 catalyst 전체였다"의 정확한 재현. **E1 (preopen ≥ +8%)** 룰이 작동하려면 실제 가집계가 필요한데 preopen_indication=None이라 발동 안됨. P3 (bounce/foreign_unwind + gap > +3%)는 regime이 `continuation`이라 발동 안됨.

#### 042700 한미반도체 — SL −3% (gap +1.11%, O→C −4.93%, pat ↓)
- **Agent 5/5, primary `fresh_catalyst`:** "SK하이닉스 442억 발주 + 6/12 +24.7% 급등으로 HBM 후공정 대장주 입지 확정."
- **What happened:** 갭은 작았지만(+1.11%) 종일 분배. ↓ 패턴, 종가 −4.93%, 저점 −6.03% (14:55).
- **Diagnosis:** 6/12 +24.7% 급등 다음날 = 차익실현 1순위. agent reasoning "입지 확정"이 정확히 06-12 SK하이닉스 reasoning과 평행한 narrative-only signal. **E2 (브리프가 섹터 위험 표시)는 적용 불가** (브리프가 반도체를 top theme로 추천했으므로). 하지만 reasoning 안에 직접 catalyst가 4일 전(6/8) 발주뿐 — E3 (5거래일 이전 stale) 직전 경계선. **6/12 +24.7% 그 자체가 ⚠️ 신호** 였는데 prompt에 "전일 +X% 이상 종목은 차익실현 1순위" 룰 부재.

#### 005930 삼성전자 — HOLD −1.61% (gap +6.20%, O→C −1.61%, pat =)
- **Agent 4/5, primary `theme_leader`:** "6/12 +7.86% + HBM4 양산 + 외국인 25거래일 만에 첫 순매수."
- **What happened:** 갭 +6.20% → 곧바로 박스, 저점 −2.48% (14:52). 분배 패턴.
- **Diagnosis:** SK하이닉스와 동일. 갭이 catalyst 전체였다. SL(−3%)은 안 깨졌지만 종일 손실 상태. 06-12 lesson 그대로.

#### 402340 SK스퀘어 — SL −3% (gap +5.96%, O→C −1.81%, pat ~)
- **Agent 3/5, primary `momentum_continuation`, P5 applied.** Research reasoning 원문: **"지분가치 재평가 narrative는 sympathy play로 종목 고유 catalyst는 부재."**
- **What happened:** 갭 +5.96% → 저점 −5.84% (10:17), SL hit.
- **Diagnosis:** **이건 명백한 E4 (SELF-CONTRADICTION) 위반인데 model이 P5로 down-rate만 하고 final pick에 포함**. v2 prompt에 "reasoning에 '부재' 라는 단어 들어가면 EXCLUDE" 명시했음에도 model이 안 지킴. **Prompt-following failure** — E4 룰을 더 강하게 강조하거나 mechanical check가 필요.

### v2-v2-v2 Track B 손실 4종 (테크윙 1종만 TP)

전부 KOSDAQ 반도체 장비. KOSDAQ O→C −1.35% 분배 환경에서 5종 100% 노출 = 구조적 손실.

#### 005290 동진쎄미켐 — SL −3% (gap +2.88%, O→C +0.33%, first5min_min **−3.30%**)
- **Agent 4/5, primary `fresh_catalyst`:** "6/12 +6.31% + 1Q 영업이익 +39.4%."
- **What happened:** 시가 +2.88% 갭, **첫 5분 안에 저점 −3.30%로 SL 즉시 hit**. 종가 +0.33%로 결국 회복했지만 entry는 이미 손절.
- **Diagnosis:** 06-12 improvement.md 명시 룰 "첫 5분 min ≤ −2.5%면 entry defer" 가 prompt에 미반영. 동진쎄미켐은 이 룰을 적용했으면 09:00 entry skip → 09:05 이후 reentry로 손실 회피 가능.

#### 036930 주성엔지니어링 — SL −3% (gap +2.81%, O→C −5.26%, pat ~)
- **Agent 4/5, primary `momentum_continuation`:** "6/11 +7% + 6/12 장비주 랠리 동조."
- **What happened:** 갭+2.81% → 09:04 고점 +2.74% → 종일 하락, 저점 −8.21% (14:32).
- **Diagnosis:** 한미반도체와 동일 패턴 — 전일 급등 후 차익실현. ALD 장비 슈퍼사이클은 다주(多週) narrative이지 dated catalyst 아님 → E3 stale-catalyst-only 경계선이지만 agent가 6/11 (4일 전) 가격 행동을 catalyst로 misclassify.

#### 031980 피에스케이홀딩스 — SL −3% (**gap −1.51%**, O→C −9.60%, pat ~)
- **Agent 3/5, primary `theme_alignment`, P5 applied.** "6/12 +13.42% + Fluxless Reflow 비교우위."
- **What happened:** **시가가 prev_close보다 낮게(-1.51%) 형성**. 첫 1분 +5% TP 찍고 즉시 분배, 저점 −11.47% (13:55).
- **Diagnosis:** 갭 다운 시가 = 6/12 +13.42% 가 이미 fade되기 시작했다는 신호. agent가 brief 단계에서 preopen 가격을 못 봤으므로 (preopen_indication=None) 갭 다운 정보 자체가 없었음. **runtime re-score 미작동**. 또한 reasoning "동종 장비주 대비 상승률이 절제되어 추가 상승 여력 보유" — 상승률이 절제됐다는 건 시장이 안 받아준 신호로도 해석 가능. 자기모순 reasoning.

#### 095340 ISC — SL −3% (**gap −0.87%**, O→C −8.11%, pat ~)
- **Agent 3/5, primary `momentum_continuation`, P2 applied (잘못된 적용).**
- **What happened:** 갭 다운 -0.87% 시작, 종일 하락, 저점 −9.21%.
- **Diagnosis:** ISC도 갭 다운. **agent가 preopen_indication=None 인데도 P2 (preopen +4-8%) 페널티를 적용** — model이 hallucinated penalty. 더 큰 문제는 ISC도 6/12 +20.73% 급등 다음날이라 한미반도체/주성엔지니어링과 동일한 차익실현 위험을 안고 있었다는 점.

### v1-v1-v1 Track B 손실 (참고용)

v1 Track B는 1/5만 catchable로 평균 +1.80% 였지만 사실상 STX엔진의 ❌ gap (시초 +5% 넘어 entry 불가지만 +12.54% 도달) 운빨. 진짜 entry된 종목 5개 중 알테오젠만 +5% TP. 쎄트렉아이 −13.87%, 컨텍 −10.58% 처참. v1 Track B는 카운터파트 부재 (반도체 외 KOSDAQ mid 추출 어려움)의 구조적 약점.

---

## Best entry timing

오늘은 **"best entry = open"이 아닌 경우가 손실 케이스에 집중**. 패턴:

| Ticker | Best entry | Best PnL | Open entry result | 차이 |
|---|---|---|---|---|
| 042700 한미반도체 | 14:54 | +0.73% (HOLD) | SL −3% | 오후 4시 즈음 단기 반등 — 짧은 swing only |
| 005930 삼성전자 | 14:51 | +0.30% (HOLD) | HOLD −1.61% | 종일 분배, 마감 직전 미세 반등 |
| 036930 주성엔지니어링 | 14:31 | +1.26% (HOLD) | SL −3% | open SL 후 종일 하락, 장 후반 미세 반등 |
| 095340 ISC | 14:39 | +1.45% (HOLD) | SL −3% | 갭다운 + 종일 분배, 마감 직전 미세 반등 |
| 402340 SK스퀘어 | 10:16 | +3.54% (HOLD) | SL −3% | 갭+5.96% 후 10시 초반 추가 push, then 분배 |

**관찰:**
- 손실 종목 5개 중 4개의 best entry가 **장 후반 14:30 이후** — 즉 "오늘은 매수자가 아예 들어오지 않은 날". 모든 entry가 reactive scalping에 가까웠음.
- 유일한 비-개장 best entry로 의미있는 것은 **SK스퀘어 10:16 +3.54%** — 갭+5.96% 후 1시간 동안 +3.54% 추가 push 후 분배. 이건 "갭상승 → 추가 모멘텀 → 분배" 의 전형으로, **모멘텀 매도(취해놓고 빠지기) 전략**으로는 잡을 수 있었음. 하지만 우리 strategy는 TP까지 hold이므로 무관.
- 결론: **갭+5% 이상 종목은 open entry는 그냥 lose-loss**. open SL hit하거나 종일 분배되거나 둘 중 하나.

**Track B 첫 5분 dip 룰 재검증 (06-12 lesson):**

| Ticker | first5_min | open→SL/TP | 06-12 룰 적용 시 |
|---|---|---|---|
| 089030 테크윙 | −1.63% | TP@open | entry OK |
| 005290 동진쎄미켐 | **−3.30%** | SL | **defer entry → reentry @ 09:05 (close +0.33%)** = 손실 회피 |
| 036930 주성엔지니어링 | −0.84% | SL | entry OK but lost (다른 원인) |
| 031980 피에스케이홀딩스 | **−5.67%** | SL | **defer entry → reentry @ later** = 어차피 종일 하락이라 도움 안됨 |
| 095340 ISC | −1.75% | SL | entry OK but lost (다른 원인, 갭다운 자체가 신호) |

룰 검증: 동진쎄미켐에서는 명확히 작동. 피에스케이홀딩스는 룰이 작동하지만 종일 하락이라 무관. **첫 5분 dip 룰은 여전히 유효하지만 단독으로는 부족 — "갭다운 시초" 신호와 결합해야 함**.

---

## Top 30 winners we missed

오늘은 `top_30_movers` 데이터 수집이 실패 (`market_data_2026-06-15.json`의 `top_30_movers: []`). Naver scraping 측 이슈로 추정. 별도로 시장 분석 시 KOSPI 강한 상승 / KOSDAQ 약세이므로 catchable winners는 대부분 KOSPI에 몰렸을 것.

대신 **v1이 잡고 v2가 놓친 winning theme**으로 대체:

| Ticker | Name | Theme | v1 TP/SL | v2 picked? |
|---|---|---|---|---|
| 034020 | 두산에너빌리티 | 원전/SMR | HOLD −0.60% (close) but +0.80% high | ❌ |
| 064350 | 현대로템 | 방산 | SL −3% but high +3.32% — best entry TP | ❌ |
| 267260 | HD현대일렉트릭 | 전력 인프라 | **TP +5%** ✅ | ❌ |
| 105560 | KB금융 | 금융 (외국인 순매수 전환 수혜) | **TP +5%** ✅ | ❌ |

**v2가 못 잡은 가장 큰 패턴:**
1. **외국인 24거래일 순매도 → 첫 순매수 전환**이라는 브리프의 가장 중요한 사실을 v2 Track A picks가 활용 안 함. 외국인 매도세 종료 = 금융주 (KB금융, 신한지주) 직접 수혜인데 5종 모두 반도체. (v1 picked KB금융 ✅)
2. **AI 인프라 sub-theme** (HD현대일렉트릭)는 06-12 lesson에서 원전과 함께 universe에 넣었음에도 v2 Track A가 안 잡음. v1은 잡음.
3. **방산 multi-week trend**: 브리프 "Multi-week trend themes" 섹션에 명시했는데 v2가 무시. v1은 현대로템 picked.

→ **v2 universe 확장 (06-12 lesson)은 작동했음 — 06-12에 한전KPS 등 원전이 universe에 들어갔고 v2 brief에 sub-theme까지 등장.** 그런데 final picks 단계에서 research agent가 반도체 5종 압도적 선호로 sub-theme 다양성을 죽임. **문제는 universe가 아니라 final pick 다양성 룰**.

---

## Other observations

### 1. v2가 v1에 진 근본 원인: 다양성 룰 부재

v2 prompts는 06-12 lesson을 잘 반영했지만 **하나의 핵심 룰을 누락**: "한 테마 안에서 3종목 초과 금지" 또는 "final 5종 sub-theme 최소 3개". v2 Track A는 5종 중 4종이 반도체. v2 Track B는 5종 중 5종이 KOSDAQ 반도체 장비.

**제안 → research_agent_v3 추가 룰:**

```
FINAL-PICK DIVERSIFICATION REQUIREMENT (per track)
- 최종 5종 picks 중 동일 sub_theme 종목은 최대 2개.
- (예: 반도체-메모리, 반도체-HBM 후공정, 반도체-장비를 각기 다른 sub_theme로 카운트)
- 위반 시 동일 sub_theme 내 score 최저 종목을 drop하고 다음 sub_theme top 후보 promote.
```

### 2. Gap-magnitude surprise → defer 룰 부재

브리프 예상: "modest +0.5~1.0%". 실제 KOSPI 갭: **+4.95%** (5배 surprise).

agent가 brief 작성 시 갭 예상치를 명시했지만, **실제 시초 갭이 예상치를 3배 이상 초과하면 픽 전체 reconsider**하는 룰이 없음. v2 picks 5종 중 4종이 +5% 이상 갭상승 → 4종 모두 분배 또는 박스로 손실.

**제안 → run_morning_pipeline.py 실행시간 추가 룰:**
- 09:00 직후 30초 동안 KOSPI/KOSDAQ 실제 갭 측정
- `actual_gap / predicted_gap > 3.0` 이면 모든 갭상승 picks defer (entry skip, watch only)
- 이 신호가 발동하면 그날의 P&L 위험을 사용자에게 alert

### 3. E4 (SELF-CONTRADICTION) 룰의 prompt-following failure

**SK스퀘어 research reasoning 원문**: "지분가치 재평가 narrative는 sympathy play로 종목 고유 catalyst는 **부재**."

v2 research prompt에 "**부재**" 라는 단어가 들어가면 EXCLUDE 명시했음. 하지만 model은 P5 (down-rate −1)로 처리하고 final pick에 포함. 결과: SK스퀘어 SL.

**원인 추정:** Opus가 E4 룰을 인지는 하지만 ranking pressure (5종 채워야 함) > rule following 으로 trade-off 함. 

**제안:**
- Final pick aggregation 단계에서 mechanical check 추가 (코드로). research output의 reasoning text에 disqualifier 단어 정규식 매칭하여 자동 EXCLUDE.
- 또는 candidate 수를 12-15에서 18-20으로 더 늘려 model에게 "여유"를 주어 rule-following 우선시키게.

### 4. preopen_indication=None 인데 P2 잘못 적용 (ISC 케이스)

ISC의 v2 picks JSON에 `soft_penalties: ["P2"]` 표기. 그런데 `preopen_indication_pct: None`. P2는 "preopen +4-8%" 페널티 — preopen 데이터 없으면 적용 불가.

**원인:** model이 6/12 +20.73% 상승을 preopen indication으로 착각하여 P2 적용. 두 개념을 분리하지 못함.

**제안:** P2 룰 wording을 "preopen indication (장 시작 전 가집계/시간외 단일가) 가 +4-8%" 로 더 명확히. "전일 상승률"과 혼동 방지.

### 5. KOSPI vs KOSDAQ 시장 분리 시그널 부재

KOSPI +5.20% / KOSDAQ +0.48% 는 매우 큰 분리. KOSPI 강세 + KOSDAQ 약세 환경에서 KOSDAQ 종목 5종 노출 (Track B 100% KOSDAQ) = 구조적 손실. 

**제안 → context_agent_v3:**
- regime 태그에 `kospi_vs_kosdaq` divergence flag 추가:
  - `aligned`: 두 시장 같은 방향
  - `kospi_strong_kosdaq_weak`: KOSPI 갭+1.5%+ AND KOSDAQ 갭 −0.5% 이하 (06-15 패턴)
  - `kospi_weak_kosdaq_strong`: 반대
- divergence 발생 시 약세 시장 track 픽 수 조정 (Track B 5종 → 3종, 나머지 2종은 cash) 같은 룰 가능.

### 6. v1이 잘된 진짜 이유: 6/12 winner를 picks에서 제외

v1 Track A 5종 (두산에너빌리티, 한화오션, 현대로템, HD현대일렉트릭, KB금융) 중 6/12 +10% 이상 상승했던 종목은 **0개** (한화오션은 6/12에 강세였지만 KDDX 우협 발표가 6/11이라 fresh dated catalyst). v2 Track A 5종 중 6/12 +10% 이상 상승했던 종목은 **4개** (SK하이닉스, 한미반도체, 삼성전자, SK스퀘어). **이게 결과 차이의 전부.**

→ **단순 룰로 정량화 가능**: "전일 +10% 이상 상승한 종목은 final pick에서 제외" (또는 −1 페널티). 06-12와 06-15 데이터 모두 이 룰을 지지함.

**제안 → research_agent_v3 추가 룰:**

```
P6. 전일 종가 기준 +10% 이상 상승한 종목 → −1 score (차익실현 1순위 위험).
또는 E5 (HARD EXCLUSION): 전일 +15% 이상 상승 → EXCLUDE (한미반도체 6/12 +24.7% 케이스).
```

---

## Action items

| 우선순위 | 항목 | 영향 |
|---|---|---|
| **HIGH** | E5 추가: "전일 +15% 이상 상승 종목 EXCLUDE" | 한미반도체 (SL), SK스퀘어 (SL) 자동 제외 |
| **HIGH** | Diversification 룰: sub_theme 당 max 2종 | v2 Track A 반도체 4종 → 2종, 나머지 슬롯에 KB금융/HD현대일렉트릭 |
| **HIGH** | E4 mechanical check (코드에서 정규식 매칭) | SK스퀘어 E4 violation 자동 catch |
| **MEDIUM** | Gap-magnitude surprise alert (runtime) | 5x gap surprise 발동 시 entry defer |
| **MEDIUM** | KOSPI/KOSDAQ divergence flag in context | Track B 노출 조정 |
| **LOW** | P2 wording 명확화 (preopen vs 전일) | ISC 류 hallucinated penalty 방지 |
