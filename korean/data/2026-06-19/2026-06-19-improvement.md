# Improvement Notes — 2026-06-19

> **Headline:** 두 콤보 모두 손실. 핵심은 **KOSPI 대형주 반등 내러티브를 과신했고, KOSDAQ/중형주 수급 붕괴를 충분히 반영하지 못한 것**. 09:05 진입은 Track B에서는 손실을 크게 줄였지만, Track A에서는 오히려 악화.

| Combo | Track A 09:00 | Track A 09:05 | Track B 09:00 | Track B 09:05 | 요약 |
|---|---:|---:|---:|---:|---|
| v1-v1-v1 | -0.68% | -0.80% | -1.40% | **+1.00%** | 삼성SDI TP가 Track A를 방어, Track B는 09:05가 크게 개선 |
| v3-v3-v3 | -2.17% | -2.50% | -3.00% | **-1.20%** | v3는 KOSPI/KOSDAQ divergence 판단은 했지만 실제 pick이 전반 약함 |

시장 배경:
- KOSPI: 9052.42, -0.13%
- KOSDAQ: 966.59, **-3.43%**
- Top30 intraday movers와 pick overlap: **0/20**
- Top30 catchable subset: 14/30, 평균 TP/SL +1.57%

---

## 1. Losers — why agent picked them

### v1-v1-v1 Track A

| 종목 | 결과 | 왜 골랐나 | 실패 원인 |
|---|---:|---|---|
| HD현대중공업 | -3.00% SL | 조선 theme leader, 수주 모멘텀, clean narrative | 이미 multi-week crowded winner. 당일 고점이 09:00, O→H +0.00%로 진입 직후 upside가 없었음 |
| NAVER | -3.00% SL | oversold bounce + Nasdaq 기술주 반등 + AI 광고 기대 | oversold 내러티브는 있었지만 당일 장중 Λ 패턴. O→H +3.81% 후 fade, 5% TP에는 부족 |
| KB금융 | -3.00% SL | 밸류업 정책, PBR 1배 돌파, 자사주 소각 | 전일/최근 강세 후 금융주 차익실현. O→H +1.10%, O→L -5.55% |
| LG에너지솔루션 | +0.62% HOLD | K-배터리 재평가, ESS/전고체 내러티브 | SL은 피했지만 O→H +4.98%로 TP에 0.02%p 부족. 섹터 모멘텀은 제한적 |
| 삼성SDI | +5.00% TP | AI 데이터센터 BBU/ESS + 실적 전망 | 오늘 v1 Track A의 유일한 명확한 성공. 09:00 진입이 정답 |

**Lesson:** v1 Track A는 일부 대형주를 잘 잡았지만, `theme_leader` / `oversold_bounce` / `policy_tailwind`가 **당일 fresh flow**를 보장하지 않았다. 대형주에서도 `O→H < 2%` 또는 `high_time = 09:00`이면 손실 가능성이 높다.

### v1-v1-v1 Track B

| 종목 | 결과 | 왜 골랐나 | 실패 원인 |
|---|---:|---|---|
| 솔브레인 | -3.00% SL | 반도체 소재 top pick, 삼성/SK HBM 투자 수혜 | KOSDAQ -3.43% 환경에서 소재주가 동반 투매. O→C -8.27% |
| ISC | -3.00% SL | 반도체 테스트/소켓 테마 | 같은 반도체 mid-cap cluster. O→C -5.10% |
| 코미코 | -3.00% SL | 반도체 장비/부품 cycle | 시초가가 고점. O→H +0.00%, O→L -9.69% |
| 피에스케이 | -3.00% SL | 반도체 장비 회복 기대 | 09:00 진입은 실패, 09:05는 DEFER/재진입 시뮬에서 TP 가능. timing 문제가 컸음 |
| 제주반도체 | +5.00% TP | 반도체/온디바이스 AI 민감주 | 유일한 Track B 성공. 하지만 종가는 O→C -6.62%로 intraday TP 후 급락 |

**Lesson:** v1 Track B는 반도체 소재/장비 cluster가 과밀했다. 대형 반도체 강세를 중형 반도체에 그대로 전이시킨 것이 실패. KOSDAQ이 전일 -3.01%, 당일 -3.43%로 무너지는 중에는 mid-cap beta가 대형주보다 훨씬 위험했다.

### v3-v3-v3 Track A

| 종목 | 결과 | 왜 골랐나 | 실패 원인 |
|---|---:|---|---|
| 대한항공 | -3.00% SL | 미-이란 MOU, 유가 하락 수혜, 항공 fuel cost 감소 | 테마 자체는 합리적이지만 당일 수급은 항공/운송으로 오지 않음. O→H +3.50% 후 fade |
| HMM | -3.00% SL | 호르무즈 재개방, 해상 운임/연료비 수혜 | 유사한 지정학 완화 테마. O→H +0.24%로 upside 거의 없음 |
| 기아 | -3.00% SL | 원화 약세 수출주 수혜 | 수출주 내러티브는 있었지만 당일 차익실현. O→L -3.33% |
| KB금융 | -3.00% SL | KOSPI 외국인 순매수/밸류업 수혜 | v1과 동일. 금융 defensive thesis가 당일 손실 방어 실패 |
| 현대차 | +1.16% HOLD | 원화 약세, 대형 수출주 | 손실은 피했지만 TP에는 부족. best-entry hindsight는 09:01 TP |

**Lesson:** v3는 KOSPI/KOSDAQ divergence 위험을 더 잘 인식했지만, 실제 Track A가 항공/해운/자동차/금융으로 분산되면서 강한 당일 주도주를 잡지 못했다. `fresh_catalyst`가 있어도 **시장 수급이 그 테마로 이동했는지** 확인하는 pre-open/early confirmation이 필요.

### v3-v3-v3 Track B

전 종목이 09:00 기준 -3.00% SL:
- LIG넥스원: O→C -2.07%, O→L -4.48%
- 하나머티리얼즈: O→C -7.46%, O→L -10.62%
- ISC: O→C -5.10%, O→L -7.09%
- 알테오젠: O→C -3.68%, O→L -5.99%
- 디아이: O→C -6.29%, O→L -9.86%

**Lesson:** v3 Track B는 KOSDAQ/mid-cap risk를 알면서도 충분히 회피하지 못했다. 특히 하나머티리얼즈/디아이/ISC는 반도체 mid-cap cluster이고, 알테오젠은 KOSDAQ 바이오 beta에 노출. KOSDAQ -3%대 환경에서는 Track B pick 수를 줄이거나 09:05 confirmation을 기본값으로 두는 편이 낫다.

---

## 2. Best entry timing

### 결론

- **Track A:** 09:00 유지가 더 나았다.
  - v1 A: -0.68% → -0.80% (**-0.12%p 악화**)
  - v3 A: -2.17% → -2.50% (**-0.33%p 악화**)
- **Track B:** 09:05/DEFER가 의미 있게 개선했다.
  - v1 B: -1.40% → **+1.00%** (**+2.40%p 개선**)
  - v3 B: -3.00% → **-1.20%** (**+1.80%p 개선**)

### 해석

Track B는 KOSDAQ/mid-cap 특성상 첫 5분 급락/분배 신호가 훨씬 강했다. 09:05 진입 또는 DEFER gate가 약한 slot을 피하는 효과가 있었다. 반대로 Track A는 삼성SDI처럼 09:00부터 바로 TP를 치는 종목이 있어 09:05로 늦추면 기회를 잃었다.

**Action:** 09:05 실험을 전체 적용하지 말고, **Track B 전용 rule**로 계속 관찰한다.

제안 rule:
- Track A: 09:00 기본 유지. 단 `gap_up_distribution_risk=HIGH`일 때만 09:05/confirmation 검토.
- Track B: KOSDAQ 전일 -2% 이하 또는 당일 KOSDAQ 약세 예상이면 09:05 + DEFER gate 우선.
- `first_5min_min_pct ≤ -2.5%`는 계속 강한 위험 신호로 유지.

---

## 3. Top 30 winners we missed

오늘 pick → top30 overlap:

| Combo | Track A hits | Track B hits | Total |
|---|---:|---:|---:|
| v1-v1-v1 | 0/5 | 0/5 | 0/10 |
| v3-v3-v3 | 0/5 | 0/5 | 0/10 |

상위권 예시:

| Rank | 종목 | 시장 | O→C | 패턴 |
|---:|---|---|---:|---|
| 1 | 삼익제약 | KOSDAQ | +29.98% | 상 |
| 2 | 다스코 | KOSPI | +29.72% | 상 |
| 3 | 형지I&C | KOSDAQ | +29.70% | 상 |
| 4 | 보해양조 | KOSPI | +25.96% | 상 |
| 5 | 피앤에스로보틱스 | KOSDAQ | +23.15% | ~ |
| 8 | 경동인베스트 | KOSPI | +16.13% | ↑ |
| 13 | 아미코젠 | KOSDAQ | +13.33% | ~ |

### 왜 못 잡았나

1. **Morning briefing의 active theme이 너무 mega/known theme 중심**
   - 반도체/HBM, 방산, 조선, 금융, 자동차, 항공/해운 중심.
   - 실제 top30은 제약/로봇/소형 이벤트성 급등/인버스 ETF/건설·개별주가 많았다.

2. **KOSDAQ 위험을 회피하면서도 KOSDAQ winner discovery는 못 함**
   - KOSDAQ 지수는 -3.43%였지만 top30의 상당수는 KOSDAQ 개별 급등주.
   - 현재 시스템은 KOSDAQ beta를 피해야 할 때와 KOSDAQ 개별 event를 찾아야 할 때를 분리하지 못한다.

3. **상한가/급등 후보 탐색 레이어 부족**
   - 삼익제약, 형지I&C, 보해양조, 피앤에스로보틱스 같은 이름은 기존 macro/theme flow보다 당일 개별 수급/뉴스/테마 rotation이 중요.
   - pre-pipeline의 universe/brief 단계가 mega/mid quality narrative에 치우쳐 이런 event-driven tails를 잘 못 본다.

### Action

- Top30 missed winner review를 다음 brief에 반영:
  - 제약/바이오 low-float 급등
  - 로봇/소형 정책 테마
  - KOSPI 개별 재료주
  - 인버스/레버리지 ETF는 연구 참고만 하고 pick 대상에서는 제외 유지
- Track B 후보군에 “index weak but individual event strong” 조건을 별도 추가할지 검토.
- 단, 오늘 top30 중 `❌ fast`, `❌ gap`도 많으므로 전부 잡으려 하면 추격매수 위험이 커진다. catchable subset 14/30 중심으로만 학습해야 한다.

---

## 4. What worked

1. **09:05 Track B 실험**
   - v1 B +2.40%p, v3 B +1.80%p 개선.
   - KOSDAQ/mid-cap 약세장에서 timing filter의 가치가 확인됨.

2. **v1 Track A의 삼성SDI**
   - 09:00 진입 기준 +5.00% TP.
   - AI 데이터센터/ESS/BBU 내러티브가 실제 수급으로 연결된 사례.

3. **v3 context의 divergence 인식**
   - KOSPI/KOSDAQ divergence flag와 KOSDAQ mid risk 경고 자체는 방향이 맞았다.
   - 문제는 경고가 실제 pick 수/entry rule에 충분히 강하게 반영되지 않은 것.

---

## 5. What failed

1. **KOSDAQ -3% 환경에서 Track B를 5개씩 유지**
   - v3 Track B는 5/5가 09:00 기준 SL.
   - KOSDAQ 전일 -3.01%, 당일 -3.43%라는 구조적 약세를 생각하면 너무 공격적이었다.

2. **대형 반도체 강세를 중형 반도체로 단순 전이**
   - 솔브레인, ISC, 코미코, 피에스케이, 하나머티리얼즈, 디아이 등 반도체 mid-cap이 대거 손실.
   - 삼성전자/SK하이닉스 강세와 KOSDAQ 장비/소재 동조는 분리해서 봐야 한다.

3. **Top30 winner discovery 실패**
   - 0/20 overlap.
   - macro/theme pick은 합리적이었지만, 당일 시장의 실제 급등주는 다른 레이어에 있었다.

4. **fresh catalyst의 수급 검증 부족**
   - 항공/해운은 유가 하락 수혜 논리는 명확했지만 실제 장중 수급은 오지 않았다.
   - `fresh_catalyst` 단독으로 최종 pick을 정당화하면 안 되고, pre-open/first-minute confirmation이 필요하다.

---

## 6. Action items

### CRITICAL

1. **Track B risk throttle**
   - KOSDAQ 전일 -2% 이하 또는 당일 KOSDAQ 약세 예상이면 Track B pick 수를 5 → 3 이하로 줄이거나 cash slot 허용.
   - v3 context가 이미 `KOSDAQ mid 픽은 분배 위험 증가`라고 경고했는데 실제 brief/pick 단계가 충분히 줄이지 못했다.

2. **Track B 09:05/DEFER rule 계속 테스트**
   - 오늘 결과만 보면 Track B는 09:05가 명확히 우월.
   - 아직 표본이 부족하므로 즉시 전면 변경하지 말고 5+ trading days 누적 후 결정.

### HIGH

3. **KOSPI 대형 반도체와 KOSDAQ 반도체 소재/장비를 분리**
   - 대형 HBM winner flow가 KOSDAQ 소재/장비로 자동 확산된다고 가정하지 말 것.
   - KOSDAQ 지수/수급이 약하면 반도체 mid-cap도 감점.

4. **Top30 missed-winner taxonomy 추가**
   - 제약/바이오, 로봇, 소형 이벤트주, 건설/개별 재료주가 반복적으로 top30에 들어오는지 확인.
   - 단, `fast/gap` 종목은 제외하고 catchable subset 중심으로 학습.

### MED

5. **fresh catalyst confirmation**
   - 항공/해운처럼 논리는 맞지만 수급이 안 온 테마는 09:00 시장가 진입보다 confirmation 필요.
   - `fresh_catalyst + O→H early < 1%` 또는 `first_5min_min_pct < -1.5%`면 skip/defer 후보.

6. **JOURNEY 업데이트 후보**
   - “09:05는 전체 rule이 아니라 Track B/KOSDAQ 약세장 전용 rule로 볼 것”
   - “KOSPI 대형주 strength ≠ KOSDAQ mid-cap strength”
   - “Top30 discovery layer가 macro/theme layer와 별도로 필요”

---

## 7. Decision

- `v1-v1-v1`: **WATCH**
  - Track A는 삼성SDI 덕분에 방어. Track B는 09:05 적용 시 개선.
  - 아직 drop할 수준은 아님.

- `v3-v3-v3`: **WATCH / needs adjustment**
  - context 진단은 v1보다 정교했지만 실제 pick 결과는 더 나쁨.
  - v3는 drop이 아니라 **경고를 pick 수/entry rule에 강제 반영**하는 쪽으로 수정 필요.

- `09:05 experiment`: **KEEP TESTING, Track B 중심**
  - 오늘은 Track B에서 강하게 유효.
  - Track A에는 무조건 적용 금지.
