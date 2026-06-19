# 한국 시스템 — 걸어온 길

> 이 문서는 한국 시장 데이 트레이딩 에이전트가 **어떤 시행착오를 거쳐 현재 상태까지 왔는지** 시간 순으로 정리한 기록.
> 아키텍처/사용법은 `README.md`, 일별 손실 분석은 `{date}/{date}-improvement.md` 참고.

---

## 한눈에 보는 진화 곡선

| 시점 | 변화 | 트리거 |
|---|---|---|
| 06-10 ~ 06-11 | v1 파이프라인 구축 | 초기 개발 |
| **06-12 (Day 1)** | **v2 prompt** 생성 (E1~E4, P1~P5) | narrative-only 픽이 손실로 직결 |
| **06-15 (Day 2)** | **v3 prompt** 생성 (E5, P6, D1) | v2 prompt 룰을 LLM이 무시 |
| **06-16 (Day 3)** | **코드 enforcement** 도입 (mechanical filters) | v3 prompt도 무시 |
| **06-16 (저녁)** | **E6** (universal) + **cross-track dedup** + **Pick→Top30 overlap metric** 추가 | HD현대일렉트릭 반복 SL 발견 |
| **06-18 (Day 4)** | **gap_up_distribution_risk** 구조화 출력 + **09:05 entry sim** (DEFER gate) 추가 | "open-as-distribution" 패턴 첫 관측 — 17/20 픽 high_time이 09:00~09:21 |

---

## 시기별 상세

### 1단계 — v1 파이프라인 구축 (06-10 ~ 06-11)

기본 구조:
- **Context Agent** (Sonnet + web search): 시장 브리핑
- **Brief Agent** (Opus + web search): 후보 종목 스크리닝 (Track A 대형주 / Track B 중형주, 각 10개)
- **Research Agent** (Opus + web search): 후보 점수화 (1~5점)
- **Aggregator**: 점수순 상위 5종 픽

prompt 룰은 거의 없음. "좋은 종목 찾아라" 수준.

---

### 2단계 — Day 1: 06-12 (첫 실거래 + 첫 lesson)

**손실 종목**: SK하이닉스, HD현대일렉트릭, 한화오션 (모두 갭업 후 fade로 SL).

**발견된 패턴**:
- 셋 다 **fresh dated catalyst 없이 narrative만** 있는 종목
- 시장이 "bounce regime" (반등 일)인데도 모두 +3%↑ 갭업으로 진입
- `premarket_strength` 신호가 실제 KR pre-open 데이터가 아니라 **미국 시장에서 추론**된 거였음
- Track B는 비슷한 픽이라도 `low_time = 09:00`인 종목(HPSP/ISC/한미반도체)은 살고, `first_5min_min_pct ≤ -2.5%` 종목(원익IPS/테크윙)은 다 SL
- 놓친 winners: **원자력/전력 인프라 cluster** (한전KPS, 한전기술, 비에이치아이) — universe에 아예 없음

**대응 (v2 prompt 생성)**:
- **E1~E4** (Hard Exclusions):
  - E1: 시가 이미 소진 (+8% 이상 갭)
  - E2: CONTEXT-CONTRADICTION (brief가 섹터 부정적 플래그)
  - E3: STALE-CATALYST-ONLY (>5일 오래된 뉴스)
  - E4: SELF-CONTRADICTION (research reasoning에 "부재", "약함" 같은 hedging)
- **P1~P5** (Soft Penalties, -1점)
- **FINAL-PICK COMPOSITION REQUIREMENT**: 최소 3종은 fresh_catalyst (2일 내) 있어야 함
- `premarket_strength` 재정의: 실제 KR pre-open 데이터일 때만 인정
- `clean_narrative` weight 0.5로 깎고 primary_signal 못 됨
- `universe_track_a_v2` / `universe_track_b_v2`에 원전/SMR cluster 추가

---

### 3단계 — Day 2: 06-15 (v2 무시당함)

**결과**: v2 prompt가 v1보다 **더 나빴음**. v2가 반도체로 과집중하면서 v1의 자연적 다양화에 졌음.

**발견된 추가 패턴**:
- LLM이 **E4 self-contradiction** 룰을 prompt에 박아둬도 무시 — SK스퀘어 reasoning에 "고유 catalyst는 부재"라 쓰고도 픽함
- **P2 (preopen 갭 부재)** 페널티가 잘못 적용됨 — `preopen_indication_pct=None`이면 적용 안 해야 하는데 적용함
- **전일 +15% 급등 종목**이 다음 날 갭업 후 분배로 SL 자주 뜸 → `prev_day_change_pct` 필드 자체가 누락

**대응 (v3 prompt 생성)**:
- **E5** (Hard): `prev_day_change_pct >= 15%`면 무조건 제외
- **P6** (Soft): `prev_day_change_pct` 10~15%면 -1점
- **D1** (Diversification): 한 sub_theme당 final 5종 중 최대 2종
- Brief output에 `prev_day_change_pct`, `sub_theme`, `preopen_indication_pct` 필드 의무화
- KOSPI/KOSDAQ divergence 플래그 추가 (context agent)

---

### 4단계 — Day 3: 06-16 (v3도 무시 → 코드 강제로 전환)

**결과**: v3 prompt도 LLM이 무시. 특히 다음 두 가지가 결정적:
- **HD현대일렉트릭이 Track A + Track B 양쪽에 동시 등장** → 양쪽 다 SL (06-12에도 SL 났던 종목인데 또 픽함)
- **놓친 cluster**: 풍력/태양광 (씨에스베어링, 씨에스윈드, 태웅, 동국S&C), 건설 (일성건설, SK오션플랜트, 대우건설) — universe에 없음

**핵심 깨달음**: prompt에 "X 하지 마" 박아둬도 LLM이 narrative attachment로 무시함. **코드로 강제해야 함.**

**대응 (코드 enforcement 도입)**:

`pre-pipeline.py`에 mechanical filter 추가:
- **E4 mechanical regex**: research_reasoning에서 hedging 단어 자동 감지 → 제외 (v3+)
- **E5 mechanical threshold**: `prev_day_change_pct >= 15.0` → 제외 (v3+)
- **D1 mechanical counter**: 같은 sub_theme 2종 초과 시 점수 낮은 쪽 자동 drop (v3+)

저녁에 추가로:
- **Cross-track dedup** (universal): Track A에 있는 ticker는 Track B에서 자동 cut. Track A 우선.
- **E6 recent_loser** (universal): 직전 5거래일 동안 SL을 **2일 이상** hit한 ticker는 무조건 제외. 변종 prompt와 무관하게 적용. 현재 차단 대상: **SK하이닉스, HD현대일렉트릭, 테크윙, 원익IPS**.

`post-pipeline.py`에:
- **Pick → Top30 overlap metric** 추가: combo별 hit 수 + 미선택 상위 종목 15개. **이건 hit-rate KPI가 아니라 retrospective 참고 자료**임. TP +5%만 쳤으면 그 slot은 충분히 좋은 거고, top-30은 *SL 친 slot의 대안 후보*를 찾을 때 — "그 slot에 어떤 sub-theme을 넣었으면 좋았을까"의 universe 확장 근거로만 활용.
- picks JSON에 `filter_audit` / `cross_track_dedup` 필드 기록 (무엇이/왜 잘렸는지 추적).

---

## 현재 활성 룰 시스템

### Prompt 변종

| 변종 | 상태 | 용도 |
|---|---|---|
| v1 | 활성 | baseline (룰 거의 없음, 자연적 다양화) |
| v2 | 보관 | E1~E4 첫 시도, v1보다 나빴음. 거의 안 씀. |
| v3 | 활성 | E1~E6 + P1~P6 + D1 — 가장 정교한 prompt |

`PAIRED_ONLY = True` 라서 **v1-v1-v1 + v3-v3-v3** 두 combo만 매일 돌림.

### Hard Exclusions (E)

| 룰 | 정의 | 코드 강제 | 적용 |
|---|---|---|---|
| E1 | 갭업 +8% 이상 | ✗ (prompt only) | v2+ |
| E2 | context contradiction | ✗ | v2+ |
| E3 | 5일+ 오래된 catalyst only | ✗ | v2+ |
| E4 | research reasoning hedging 단어 | ✓ regex | v3+ |
| E5 | 전일 +15% 이상 급등 | ✓ threshold | v3+ |
| **E6** | **5거래일 내 SL 2일+ hit** | ✓ history scan | **v1 + v3 (universal)** |

### Soft Penalties (P, -1점)

| 룰 | 정의 | 적용 |
|---|---|---|
| P1 | context 경고 무시 | v2+ |
| P2 | pre-open 갭이 modest | v2+ |
| P3 | bounce/foreign_unwind regime + 3%↑ 갭업 | v2+ |
| P4 | backward-looking 신호 (어제 강했다) | v2+ |
| P5 | theme_alignment / clean_narrative만, fresh catalyst 없음 | v2+ |
| P6 | 전일 +10~15% 급등 | v3+ |

### Diversification (D)

| 룰 | 정의 | 코드 강제 | 적용 |
|---|---|---|---|
| D1 | 한 sub_theme당 final 5종 중 최대 2종 | ✓ counter | v3+ |

### Cross-track / 기타 universal

- **Cross-track dedup**: Track A에 있는 ticker는 Track B에서 cut (universal)
- **Pick → Top30 overlap metric**: `post-pipeline.py` 결과에 자동 표시

---

## 일관된 lesson — 4일치 데이터에서 반복 확인된 패턴

1. **narrative-only 픽 = 손실** — fresh dated catalyst 없는 종목은 갭업 후 fade
2. **first_5min_min_pct ≤ -2.5%** = 강력한 SL 예측 신호 (Track B 특히)
3. **`high_time = 09:00~09:01`** = 분배 신호. **`low_time = 09:00`** = bullish (open 직후 매수가 활발)
4. **bounce regime + 3%↑ 갭업** = gap fade 거의 확정
5. **`clean_narrative`** = 과사용된 약한 신호 — 단독으로 픽 정당화 못 함
6. **LLM은 prompt 룰을 자주 무시한다** → 중요한 건 코드로 강제해야 함

---

### 5단계 — Day 4: 06-18 (open-as-distribution + entry-timing 실험)

#### lesson — 시초가 = 일중 고점 패턴

06-18 결과:
- Track A v1: −3.00%, Track B v1: −1.40% (combined −2.20%)
- Track A v3: −2.33%, Track B v3: −1.40% (combined −1.87%)
- **20개 픽 중 17개의 `high_time`이 09:00~09:21** — 시초가 = 일중 고점 = "open-as-distribution".

원인: 미 FOMC 매파 + Nasdaq −1.15% + 외국인 순매도 streak 가 누적된 상태에서 갭상승 → 시초가에 즉시 분배. picks 내용 자체는 합리적이었으나 매수 timing이 모두 일중 고점이었음. 즉 **macro regime이 micro pick quality를 압도한 day**.

#### 변경 — 두 가지

**(1) `gap_up_distribution_risk` 구조화 출력** (`context_agent_v3.txt`):
- 4가지 조건을 yes/no 체크리스트로 강제 (FOMC 매파 / Nasdaq SOX 약세 / 외국인 streak / 갭 +1% 예상)
- 합산 N/4 → LOW/MED/HIGH 자동 분류
- **HIGH 발동 시** `brief_agent_v3.txt`에 새 룰 0번 적용: pick 수 5→3, D1 cap 1, narrative-only 자동 제외, `first_5min ≥ −1% 회복 확인 후 진입` 가이드

**(2) 09:05 entry-timing 변형 시뮬레이션** (`post-pipeline.py`):
- `simulate_tp_sl_at_minute(entry_minute_idx=5)` — 09:05 시점 진입 후 TP/SL forward scan
- **DEFER gate**: `first_5min_min_pct ≤ −2.5%`이면 진입 skip (P&L 0%로 처리)
- 결과적으로 매일 8 series 데이터 자동 누적:
  ```
  v1-trackA-0900, v1-trackA-0905
  v1-trackB-0900, v1-trackB-0905
  v3-trackA-0900, v3-trackA-0905
  v3-trackB-0900, v3-trackB-0905
  ```
- CSV에 `track_a_avg_pnl_905`, `track_b_avg_pnl_905` 열 추가
- per-combo print에 09:00 vs 09:05 + DEFER count 동시 표시

#### 06-18 검증

| Combo | 09:00 A | 09:00 B | 09:05 A | 09:05 B | DEFER A/B |
|-------|---------|---------|---------|---------|-----------|
| v1-v1-v1 | −3.00% | −1.40% | **−2.40% (+0.60p)** | −1.50% (−0.10p) | 1/5, 2/5 |
| v3-v3-v3 | −2.33% | −1.40% | **−1.79% (+0.53p)** | −1.80% (−0.40p) | 1/5, 2/5 |

1일 데이터 한계는 있지만 **Track A는 09:05 진입이 일관되게 우월**. Track B는 mixed.

---

## 다음 단계 (미해결)

1. **풍력/태양광, 건설 sub-theme cluster를 universe v4에 추가** — 06-16 missed winners 1~13위가 이쪽이었음
2. **09:00 vs 09:05 누적 데이터** — 며칠 더 쌓아서 entry rule 변경 가능 시점 판단 (5+ trading days 권장)
3. **gap_up_distribution_risk HIGH day 검증** — HIGH 발동된 day에 brief가 실제로 보수화하는지, 픽 quality가 개선되는지 관찰
4. **E1~E3, P1~P6도 코드 강제** — 아직 prompt only이라 LLM이 무시할 수 있음
5. **Pre-open re-score loop** — 픽 확정 후 실제 갭/VIX/뉴스 들어왔을 때 점수 재계산
