# US Stock Day-Trading Agent System

Two-stage pipeline that produces day-trading candidates each morning (before US open) and back-tests them against the day's actual intraday data after market close.

US edition — uses yfinance for all OHLCV/minute data and NASDAQ's market-movers API (Yahoo fallback) for the daily top-30 gainers screener. All timestamps are America/New_York; regular session 09:30–16:00 ET only.

## Layout

```
.
├── README.md
├── pre-pipeline.py         # pre-open: context → brief → research → top-5 picks per track
├── post-pipeline.py           # after close (~4:30 PM ET): TP/SL simulation + per-combo summary + CSV updates
├── prompts/
│   ├── context_agent_v1.txt
│   ├── brief_agent_v1.txt
│   ├── research_agent_v1.txt
│   ├── universe_track_a_v1.txt    # large/mega-cap universe paired with brief v1
│   └── universe_track_b_v1.txt    # mid-cap universe paired with brief v1
└── data/
    ├── variant_performance.csv         # appended after each post-pipeline.py run
    ├── market_history.csv              # appended after each post-pipeline.py run
    └── {YYYY-MM-DD}/                   # one folder per US trading day
        ├── {date}-context-{cv}.txt                       # cached per context variant
        ├── {date}-picks-{cv}-{bv}-{rv}.json              # one per (context, brief, research) combo
        ├── {date}-reasoning-{cv}-{bv}-{rv}.md            # one per combo
        ├── market_data_{date}.json                       # combined market overview + per-combo daily data
        ├── {date}-summary.txt                            # printed tables (multi-combo)
        └── {date}-improvement.md                         # human review stub (don't overwrite)
```

## Daily flow

1. **Pre-open (run before 09:30 ET)** — `python3 pre-pipeline.py`
   - Each context variant fetches today's market briefing (Sonnet + web search) once and caches it to `{date}-context-{cv}.txt`. Re-runs reuse the cached file.
   - For each `(cv, bv, rv)` combination in the cartesian product of the variant lists at the top of the file, the brief and research agents run (Opus + web search) and emit `{date}-picks-{cv}-{bv}-{rv}.json` and `{date}-reasoning-{cv}-{bv}-{rv}.md`.
   - Default config: `["v1"] × ["v1"] × ["v1"]` → one combo.

2. **After close (~16:30 ET)** — `python3 post-pipeline.py`
   - Discovers every `{date}-picks-*.json` in the date folder and runs the TP+5 / SL-3 simulation for each combo's picks (per-ticker fetches are cached, so overlap between combos is free).
   - Pulls 1-minute bars via yfinance for each pick, filters to 09:30–16:00 ET, and computes:
     - Intraday `high@`, `low@`, pattern, `O→C/H/L%`
     - Catchable label (entry-window heuristic on the first 10 minutes)
     - Best-entry-in-hindsight P&L for each minute as a hypothetical entry
   - Pulls top-30 gainers (NASDAQ API → Yahoo fallback) and runs the same simulation.
   - Prints per-combo tables to stdout and to `{date}-summary.txt`.
   - Appends/updates one row per `(date, combo_id)` in `variant_performance.csv`.
   - Appends/updates one row per `date` in `market_history.csv` (SPY/QQQ/IWM/VIX OHLC + regime + news summary auto-extracted from the context file).
   - Writes `{date}-improvement.md` if absent (existing files preserved).

## Configuring variants

Open `pre-pipeline.py` and edit the lists at the top:

```python
CONTEXT_VARIANTS = ["v1"]
BRIEF_VARIANTS = ["v1"]
RESEARCH_VARIANTS = ["v1"]
```

Set `["v1", "v2"]` on any of these to run multiple combinations.
For example `["v1"] × ["v1", "v2"] × ["v1"]` runs 2 combinations and reuses the same cached context.

## Adding a new prompt variant

To create a new brief variant `v2`:

1. Copy `prompts/brief_agent_v1.txt` → `prompts/brief_agent_v2.txt` and edit.
2. Copy both universe files: `universe_track_a_v1.txt` → `universe_track_a_v2.txt`, same for track B. (The universe file's variant suffix is **paired with the brief variant** — when brief `v2` runs, it loads `universe_track_a_v2.txt`.)
3. Add `"v2"` to `BRIEF_VARIANTS`.

Same pattern works for `context_agent_v*` and `research_agent_v*`. Placeholders supported in prompt files:
- `{date}` — today's date in `YYYY-MM-DD`
- `{universe_filter}` — only in `brief_agent_*.txt`, replaced with the contents of `universe_track_{a,b}_{bv}.txt`

## Sources in picks JSON

Every brief and research entry includes a `sources` array:

```json
{
  "ticker": "NVDA",
  "reasoning": "...",
  "sources": [
    {"publisher": "Bloomberg", "url": "https://...", "date": "2026-06-12"}
  ]
}
```

In `final_picks` (post-aggregation), brief and research sources are concatenated, and original reasonings are preserved as `brief_reasoning` and `research_reasoning`.

## CSV schemas

`variant_performance.csv`:

| column | description |
|---|---|
| `date` | trading date `YYYY-MM-DD` (ET) |
| `context_variant`, `brief_variant`, `research_variant` | variant ids that produced this combo |
| `track_a_picks`, `track_b_picks` | comma-separated tickers |
| `track_a_avg_pnl`, `track_b_avg_pnl` | mean realized P&L % across the 5 picks (TP+5 / SL-3 from open) |
| `track_a_catchable_count`, `track_b_catchable_count` | # of picks flagged catchable (`✅ ok`) by the entry-window heuristic |
| `combo_id` | `{cv}-{bv}-{rv}` for grouping/joining |

`market_history.csv`:

| column | description |
|---|---|
| `date` | trading date (ET) |
| `spy_open`, `spy_close`, `spy_change_pct` | from yfinance |
| `qqq_open`, `qqq_close`, `qqq_change_pct` | same |
| `iwm_open`, `iwm_close`, `iwm_change_pct` | same |
| `vix_close`, `vix_change_pct` | spot VIX (close-to-close % change) |
| `regime_label` | category word from "Regime:" line in context (panic / bounce / continuation / normal / sideways / risk-off / risk-on) |
| `major_news_summary` | one-line auto-extract from "Key events:" section |

Both CSVs are upserted: re-running the same date replaces the matching rows, never duplicates.

## Manual override

To bypass the morning pipeline entirely (e.g. you've already picked tickers manually):

```bash
python3 post-pipeline.py \
  --large NVDA,AAPL,MSFT,META,AMZN \
  --mid   PLTR,SOFI,RKLB,IONQ,AFRM
```

This runs as a single combo with `combo_id="manual"` so it doesn't pollute the variant-performance comparison.

## Setup

```bash
pip3 install anthropic pandas requests yfinance tabulate
```

Put your Anthropic key in `.env` at the **repo root** (one level up from `us/`):

```
ANTHROPIC_API_KEY=sk-ant-...
```

The morning pipeline auto-loads `.env` so you don't need to `export`.

## Models

- **Context agent**: `claude-sonnet-4-6` (cheaper, supports `temperature=0.1`)
- **Brief + research agents**: `claude-opus-4-7` (no temperature parameter; web search enabled)

Don't change model selection casually — Opus 4.7 rejects `temperature`, Sonnet expects it.

## Notes & gotchas

- **yfinance 1-minute data** is only available for the last ~7 calendar days. If you need to back-fill further back, plug in a paid provider (Polygon, Alpaca, Tiingo) inside `fetch_minute_data`.
- **Class-share tickers** (e.g. `BRK.B`) are mapped to `BRK-B` for yfinance automatically via `to_yf_symbol()`.
- **Pre/post-market** data is excluded — TP/SL simulation uses regular session only.
- **Top-30 gainers** uses NASDAQ's public API first (`api.nasdaq.com/api/marketmovers/...`) and falls back to scraping `finance.yahoo.com/markets/stocks/gainers`. Both are unauthenticated public endpoints and may rate-limit or change format; degrade gracefully.
- **Indices** use ETF proxies (SPY/QQQ/IWM) over raw index symbols (^GSPC/^IXIC/^RUT) because yfinance is more reliable on ETFs.
- **Halts**: tickers that didn't trade on `target_date` get pattern `H` and null OHLC fields.

## Parallel to the Korean system

This folder mirrors `../korean/` one-for-one. The orchestration in `pre-pipeline.py` is essentially identical; differences are in:
- Prompts (English, NYSE/NASDAQ universe, US sources)
- Market data layer in `post-pipeline.py` (yfinance + NASDAQ API instead of FinanceDataReader + Naver)
- `market_history.csv` columns (SPY/QQQ/IWM/VIX instead of KOSPI/KOSDAQ + foreign flow)
