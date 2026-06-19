# Improvement Notes — 2026-06-18

> **Headline:** 양 콤보 모두 손실 — 시장 자체가 **"갭상승 후 종일 분배"** 환경이었고, 모든 픽이 그 패턴에 휘말림. 종목 선정의 문제가 아니라 **시장 micro-structure (시초가 = 일중 고점) + sub-theme 군집 + entry timing**의 복합 실패.
>
> | Combo | Track A | Track B | 비고 |
> |---|---|---|---|
> | **v1-v1-v1** | **−3.00%** (catch 2/5) | **−1.40%** (catch 0/5) | 5종 다 중공업/cyclical 군집 |
> | **v3-v3-v3** | **−2.33%** (catch 3/5) | **−1.40%** (catch 2/5) | E6/E4/dedup 작동, but Track B 풀 고갈 → score 1~2 약한 픽 |
>
> v3가 v1 대비 Track A에서 **+0.67%p 우위** — KB금융 한 종(다른 sub-theme)이 D1 효과로 들어와서 살림. Track B는 동률이지만 **v3는 weaker pool에서 픽**한 결과.

---

## Macro context — 왜 오늘이 "갭상승 분배 day" 였나

- **US 6/17 마감**: Nasdaq −1.15%, 반도체 섹터 차익실현 (Nvidia −2.4%, Broadcom −4.4%, Micron −6.2%, AMD −7.3%, Intel −8.5%). 금융/가치주 강세 (JPM +3.72%).
- **FOMC 점도표 매파 상향**: 2026말 정책금리 3.8% (이전 대비 +25bp), Powell 회견에서 "추가 인상 가능성" 언급.
- **외국인 순매도 streak 재개**: 6/12 25거래일 만에 순매수 전환 후 즉시 −9,900억 순매도로 복귀 (6/17 한국장).
- **한국 시초**: 위 미국장이 야간에 반영되어 시초 +1~2% 갭상승. 가치주/사이클리컬 (조선/방산/원전/금융) 로테이션 narrative.

→ **시초가에 모든 매수 기대가 이미 반영된 상태**. 시초 직후부터 외국인/기관 매도 압력. **시초가 시장가 진입 = 고점 진입 = 종일 분배 위험**.

---

## Diagnosis 1: 시초가 = 일중 고점 (open-as-distribution)

20 picks 중 **17개**의 `high_time`이 **09:00~09:21**. 17/20 = 85% 픽이 시초가 부근이 그날 최고가.

| 콤보-Track | 픽 | high_time | low_time | first_5min | O→C |
|---|---|---|---|---|---|
| v1+v3 A | 두산에너빌리티 | **09:00** | 13:39 | **−2.58%** | −8.29% |
| v1 A | LS ELECTRIC | 09:01 | 09:56 | −0.58% | −6.56% |
| v1+v3 A | 한화에어로스페이스 | 09:04 | 14:44 | −0.97% | −3.72% |
| v1+v3 A | 한화오션 | 09:03 | 14:32 | −1.36% | −5.37% |
| v1+v3 A | HD현대중공업 | 09:02 | 13:40 | −0.57% | −3.12% |
| v3 A | KB금융 | **09:00** | 11:01 | −1.23% | **+0.37%** ← 유일 win |
| v1 B | 레인보우로보틱스 | **09:00** | 11:59 | **−2.52%** | −3.15% |
| v1 B | 산일전기 | 09:02 | 13:11 | +0.00% | −5.29% |
| v1 B | 제룡전기 | 09:02 | 13:37 | +0.00% | −4.04% |
| v1 B | 로보티즈 | **09:00** | 10:53 | **−2.67%** | −5.80% |
| v3 B | 비에이치아이 | **09:00** | 13:12 | **−3.95%** | **−11.56%** |
| v3 B | 우리기술 | 09:02 | 13:14 | **−2.78%** | **−12.49%** |
| v3 B | 한미반도체 | **09:00** | 10:01 | −2.00% | −2.77% |

**Implication**: 시초가 시장가 진입 entry rule이 이런 거시 분배 day에는 cookie-cutter로 실패. 픽의 quality가 문제가 아님.

---

## Diagnosis 2: `first_5min_min_pct ≤ −2.5%` SL predictor 다시 검증

| 종목 | first_5min | 결과 |
|---|---|---|
| 비에이치아이 | **−3.95%** | SL (−11.56%) |
| 우리기술 | **−2.78%** | SL (−12.49%) |
| 로보티즈 | **−2.67%** | SL (−5.80%) |
| 두산에너빌리티 | **−2.58%** | SL (−8.29%) |
| 레인보우로보틱스 | **−2.52%** | SL (−3.15%) |
| 한미반도체 | −2.00% | SL (−2.77%) — 보더라인 |
| 한화에어로스페이스 | −0.97% | SL (HOLD 마감 −3.72%) |
| KB금융 | −1.23% | **WIN** (+0.37%) |

**룰 검증**: first_5min ≤ −2.5% → **5/5 SL (100%)**. 보더라인 −2.0% 한 종 더 SL. 06-12, 06-15, 06-16에 이어 **4일 연속 universal rule 확인**.

**구현 검토**: 첫 5분 게이트 = "09:00 진입 후 09:05 시점 OHLC 체크 → 임계 깨면 즉시 청산 (−2.5%에서 미리 SL)". 현재 강제 SL은 −3% 라인 도달 시점인데, 첫 5분에 임계 깨면 그 후 종일 분배라 SL은 시간 문제. 손실은 더 작게 끊을 수 있음.

| 픽 | 현 SL −3% 시점 손실 | 첫 5분 게이트 적용 시 손실 |
|---|---|---|
| 비에이치아이 | −3.00% (시초 직후 더 큰 갭다운으로 실측 ≈ −3.95%) | **−2.5%** (0.5%p 절약) |
| 우리기술 | 동일 | 동일 |

전체 시뮬레이션 시 v3 Track B 평균 손실이 −1.40% → −1.10%대로 추정.

---

## Diagnosis 3: Sub-theme 군집 — 한 cluster 무너지면 픽 다수가 같이 무너짐

| 콤보-Track | sub-theme 분포 | 결과 |
|---|---|---|
| v1 A | 조선 2 + 방산 1 + 원전 1 + 전력 인프라 1 = **5/5 중공업/cyclical** | 전 5종 SL/HOLD-loss |
| v1 B | 로봇 2 + 변압기 2 + 바이오 1 | 4 SL |
| v3 A | 조선 2 + 방산 1 + 원전 1 + **금융 1** | 4 SL + 1 WIN (KB금융) |
| v3 B | 원전 2 + 반도체 3 | 5 SL — 원전 cluster −11~12% 폭락 |

→ D1 (sub-theme max 2)이 발동했지만 **"max 2"는 cluster 무너질 때 보호 효과 약함**. 같은 sub-theme 2종 다 같은 sell-off에 노출.

**가설**: D1을 max 1로 강화 검토. 단점 — 후보 풀에서 같은 sub-theme 중복 후보가 8/15면 1종만 픽되어 슬롯 낭비.

**대안**: D1 max 2 유지, 단 **"cluster 신호" detection** 추가 — 시장 전체가 위 cluster를 sell-off하는 신호 (e.g. KOSPI 시초 +1% 이상 → 30분 이내 −0.5%로 후퇴)가 보이면 그 시점부터 신규 진입 보수화.

---

## Diagnosis 4: v3 mechanical filter 작동 기록 — pool 고갈 issue

v3 Track B의 filter audit:

| Filter | Cut된 종목 | 비고 |
|---|---|---|
| E6 recent_loser | 원익IPS | SK하이닉스도 별도 cut (Track A) |
| E4 self-contradiction ('부재') | 알테오젠, 주성엔지니어링, 이오테크닉스 | "고유 catalyst 부재" 표현 사용 |
| Cross-track dedup | LIG넥스원, HMM, HD현대중공업, 한화오션, 한화에어로스페이스 | Track A로 양보 |

**총 9종 cut** (E6 1 + E4 3 + dedup 5). Brief candidates 12~15종 중 9종이 cut되면 **남는 풀 3~6종** — final 5종 채우려고 약한 score (1~2) 픽까지 끌어다 씀.

남은 픽들의 reasoning에 자체 인정 hedge 다수:
- 우리기술: *"인용 catalyst가 3/31 자료로 5거래일 이상 경과, dated catalyst 미보유로 **E3 발동**"* ← LLM이 본인의 픽에 E3 라벨링하고도 픽함
- 한미반도체: *"인용 catalyst가 5/7로 5거래일 이상 경과하여 **E3 발동**"* ← 동일
- 하나머티리얼즈: *"종목 dated catalyst 없음으로 **P5**, preopen null로 **P4 적용**"*
- HPSP: *"6/15 catalyst는 6거래일 경과, momentum 구조 붕괴"*

→ **LLM이 본인의 픽에 직접 disqualifier를 적시했는데도 픽함**. E4 regex가 "부재", "후순위" 등은 잡지만 *"E3 발동"* 같은 **directly self-labeled** 표현은 안 잡힘.

**Fix 후보**: E4 패턴에 직접 라벨링 표현 추가:
```python
E4_DISQUALIFIER_PATTERNS_KR += [
    "E3 발동", "E2 발동", "E1 발동", "E5 발동",
    "P3 적용", "P4 적용", "P5 적용", "P6 적용",
    "dated catalyst 미보유", "5거래일 경과", "구조 붕괴",
]
```

이 5종 픽 중 최소 3종이 추가 cut → final 5종 채우기 더 어려워짐. 즉 **upstream brief가 candidate 풀을 더 많이 (지금 12-15 → 18-20) 보내줘야** filter 작동 후에도 quality 픽 5종이 남음.

---

## Diagnosis 5: 종목은 narrative 견조했음 — entry timing이 잘못

뽑은 종목들의 fundamentals + multi-week trend 자체는 합리적:
- 두산에너빌리티: 14조원 메가 프로젝트 + xAI 가스터빈 6/17 발표
- 한화오션: KDDX 우선협상자 6/11 발표 (drift window 내)
- 비에이치아이: LNG 복합화력 수주 + 1Q 영업이익 +184%
- HD현대중공업: 조선 슈퍼사이클 + 6/17 +3.01%

→ 모두 **dated fresh_catalyst + multi-week structural trend**. v1/v3 prompt 입장에서 score 4~5는 정당함.

**그런데** 종일 분배 환경에서는 어떤 narrative도 안 통함. 이건:
1. **Macro overlay 부재**: context_agent가 "FOMC 매파 + 외국인 순매도 streak" 신호를 받았지만 brief에 강한 가이드를 안 줌. brief는 narrative-strong 픽으로 갔음.
2. **Open-distribution detection 부재**: 시초가 갭상승 +1% 이상 + 시초 직후 즉시 매도 압력 = "오늘 진입 보수화" 신호. 우리는 매일 5종 슬롯을 꽉 채우는 가정.

---

## Other observations

### A. Cross-track dedup 효과 확인 ✓
오늘 Track B candidates 중 5종 (LIG넥스원, HMM, HD현대중공업, 한화오션, 한화에어로스페이스)이 Track A 우선으로 자동 cut. 06-16 HD현대일렉트릭 사태(양 트랙 SL 동시 hit) 재발 방지. **Strategy improvement가 명확히 효과 발휘한 사례.**

### B. E6 (recent loser) 효과 확인 ✓
SK하이닉스 (직전 5일 SL 2일), 원익IPS (SL 2일) 자동 제외. 만약 픽됐다면 SK하이닉스는 06-18에도 약세 (반도체 차익실현 직격) → 추가 손실. **E6 firing 잘 됐음.**

### C. D1 (sub-theme max 2) 효과 미묘 — v3 Track A의 KB금융이 핵심
v3 Track A에서 KB금융 1종이 +0.37%로 유일하게 살아남음. 다른 4종 모두 중공업 cluster라 동시 sell-off. KB금융이 들어온 이유:
- v3 brief가 sub_theme="금융-은행" 분류 → D1 cap에 걸리지 않음
- research_reasoning: "FOMC 점도표 매파 상향 → 은행 NIM 수혜"
- → v3 prompt가 의도한 대로 작동

v1은 KB금융 없이 5종 다 중공업 → 더 큰 손실. **D1 정량 효과 검증.**

### D. 오늘은 "low-conviction day" — 메타룰 검토 후보

자세히 보면 v3 Track B 픽 5종 모두 score ≤ 2. 정상 day는 score 3-5 픽이 대부분이었음. **score 평균 < 3인 날은 "low-conviction day"로 분류하고 픽 수 축소 (5→3) 또는 skip이 합리적.**

```python
# 검토용 메타룰 — final picks의 avg score < 3.0 이면 track 슬롯 축소
if sum(p['score'] for p in picks) / len(picks) < 3.0:
    # 옵션 1: top 3만 픽 (size 축소)
    # 옵션 2: 그날 그 트랙 skip 권고
```

오늘 v3 Track B는 평균 score = 1.8 → 명확한 low-conviction. 5종 다 픽한 것 자체가 risk.

---

## Top 30 winners we missed — Track C 논의 (별도 정리)

오늘 top 30 catchable 8/30 평균 +3.00%. 우리 picks 21종 중 top 30 hit = **0**. Top mover들은 거의 다 KOSDAQ 소형주 (시총 500억~3000억) 상한가 군집:

| Rank | Ticker | Name | Mkt | O→C | 비고 |
|---|---|---|---|---|---|
| 1 | 009470 | 삼화전기 | KOSPI | **+31.60%** | 상한가, 콘덴서/전기 |
| 2 | 046970 | 우리로 | KOSDAQ | **+30.19%** | 상한가, 전기/전자 |
| 3 | 009620 | 삼보산업 | KOSDAQ | +30.00% | 상한가, 건설 소재 |
| 4 | 046390 | 삼화네트웍스 | KOSDAQ | +30.00% | 상한가, 콘텐츠 |
| 5 | 024890 | 대원화성 | KOSPI | +29.98% | 상한가, 건설 소재 |
| 6 | 290560 | 파라택시스이더리움 | KOSDAQ | +29.88% | 상한가, crypto |
| 7 | 091590 | 남화토건 | KOSDAQ | +28.89% | 상한가, 건설 |
| 8 | 011230 | 삼화전자 | KOSPI | +27.21% | 상한가, 전기/전자 |
| 9 | 001820 | 삼화콘덴서 | KOSPI | +27.16% | 상한가, 콘덴서 |

→ **"삼화 그룹" 콘덴서/전기 군집 5종이 동시 상한가**. KOSDAQ 건설 소재 3종도 상한가. 우리 universe 완전 바깥.

**Reframe (전번 wording 교정 적용)**: top-30 hit은 KPI가 아니라 **SL 친 slot 회고용**. 즉 위 종목들로 우리 SL slot을 대체했더라면 좋았을 후보. 진입 가능성도 검토:
- 상한가 종목들은 catchable subset에서 빠짐 (시초 +30% 갭 또는 09:01 ±5분 상한가 lock) → 실제 진입 어려움
- catchable 8/30 중 어느 것도 우리 universe에 부재 → universe 정의 확장 필요한 시그널

Track C (small cap KOSDAQ) 추가가 자연스러운 다음 단계지만, **오늘 데이터 부족 (단 1일치)** 으로 본격 결정 보류. 다음 주 며칠 동안 비슷한 day가 반복되면 본격 도입.

---

## Action items (우선순위 순)

| 우선순위 | 항목 | 영향 추정 |
|---|---|---|
| **CRITICAL** | E4 패턴에 **self-labeled disqualifier** 추가 ("E3 발동", "P4 적용", "5거래일 경과", "구조 붕괴" 등) | v3 Track B 약한 픽 3-4종 추가 cut → upstream brief 풀 확장 필요 |
| **HIGH** | Brief candidates 수 증가 (12-15 → 18-20) | filter 후 quality 풀 유지 |
| **HIGH** | **첫 5분 게이트 mechanical rule**: 09:05 시점 first_5min ≤ −2.5%면 즉시 청산 (현재 SL line -3% 대기) | 0.5%p 절약, 100% predictor 검증 |
| **HIGH** | **Open-as-distribution detection**: 시초 +1% 갭상승 후 시초 30분 내 −0.5% 후퇴 신호 발동 → 신규 진입 보수화 | 갭상승 분배 day 직접 회피 |
| **MEDIUM** | **Low-conviction day 메타룰**: final picks 평균 score < 3.0이면 픽 수 축소 (5→3) 또는 트랙 skip 권고 | 오늘 v3 Track B (avg 1.8) 사례 적용 |
| **MEDIUM** | context_agent에 "FOMC/매파 이벤트 직후 갭상승 day" 전용 flag + brief에 "narrative-strong 픽 보수화" 가이드 | macro overlay 강화 |
| **LOW** | D1 max 2 → max 1 강화 검토 (백테스트 필요) | sub-theme cluster 무너질 때 보호 |
| **LOW (보류)** | Track C (small cap) 추가 — 데이터 1일치라 아직 도입 보류 | 콘덴서/건설/crypto 군집 cluster 포착 |

---

## Strategy improvement 효과 누적 검증 (06-12 → 06-18)

| 개선 항목 | 도입일 | 확인된 효과 |
|---|---|---|
| Cross-track dedup | 06-16 저녁 | 06-17 UAL 1종 cut, **06-18 5종 cut** ✓ |
| E6 recent_loser | 06-16 저녁 | 06-17 CRDO cut, **06-18 SK하이닉스/원익IPS cut** ✓ |
| E4 self-contradiction (regex) | 06-15 v3 | 06-16 1건, **06-18 3건 cut** ✓ |
| E5 prev-day spike | 06-15 v3 | 06-16 작동, 06-18 미발동 (해당 종목 없음) |
| D1 sub_theme max 2 | 06-15 v3 | 06-17 미작동, **06-18 KB금융 효과로 +0.67%p 우위** ✓ |
| 파싱 agent fallback + stage checkpoint | 06-18 | 오늘 발동 안 함 (정상 흐름) — 다음 실패 시 검증 |
| Pick→Top30 reframing | 06-18 | docstring/UI에 명시 ✓ |

→ **strategy improvements가 mechanical 차원에서는 잘 작동**. 다음 단계는 **거시 macro overlay + entry timing micro structure** 도입.
