# Korean Stock Day-Trading Agent System

Two-stage pipeline that produces day-trading candidates each morning and back-tests them against the day's actual intraday data after market close.

## Layout

```
.
├── README.md
├── pre-pipeline.py         # morning: context → brief → research → top-5 picks per track
├── post-pipeline.py           # 4:30 PM: TP/SL simulation + per-combo summary + CSV updates
├── prompts/
│   ├── context_agent_v1.txt
│   ├── brief_agent_v1.txt
│   ├── research_agent_v1.txt
│   ├── universe_track_a_v1.txt    # large/mega-cap universe paired with brief v1
│   └── universe_track_b_v1.txt    # mid-cap universe paired with brief v1
└── data/
    ├── variant_performance.csv         # appended after each post-pipeline.py run
    ├── market_history.csv              # appended after each post-pipeline.py run
    └── {YYYY-MM-DD}/                   # one folder per trading day
        ├── {date}-context-{cv}.txt                       # cached per context variant
        ├── {date}-picks-{cv}-{bv}-{rv}.json              # one per (context, brief, research) combo
        ├── {date}-reasoning-{cv}-{bv}-{rv}.md            # one per combo
        ├── market_data_{date}.json                       # combined market overview + per-combo daily data
        ├── {date}-summary.txt                            # printed tables (multi-combo)
        └── {date}-improvement.md                         # human review stub (don't overwrite)
```

## Daily flow

1. **Morning** — run `python3 pre-pipeline.py`
   - Each context variant fetches today's market briefing (Sonnet + web search) once and caches it to `{date}-context-{cv}.txt`. Re-runs reuse the cached file.
   - For each `(cv, bv, rv)` combination in the cartesian product of the variant lists at the top of the file, the brief and research agents run (Opus + web search) and emit `{date}-picks-{cv}-{bv}-{rv}.json` and `{date}-reasoning-{cv}-{bv}-{rv}.md`.
   - The default config is `["v1"] × ["v1"] × ["v1"]` → one combo, identical behaviour to the pre-refactor pipeline.

2. **After close (4:30 PM)** — run `python3 post-pipeline.py`
   - Discovers every `{date}-picks-*.json` file in the date folder and runs the TP+5 / SL-3 simulation for each combo's picks (per-ticker fetches are cached, so overlap between combos is free).
   - Prints per-combo tables to stdout and to `{date}-summary.txt`.
   - Appends/updates one row per `(date, combo_id)` in `variant_performance.csv`.
   - Appends/updates one row per `date` in `market_history.csv` (regime label, news summary, and foreign net flow are auto-extracted from the first available context file for that date).
   - Writes `{date}-improvement.md` if absent (existing files are preserved so notes don't get clobbered).

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

The same pattern works for `context_agent_v*` and `research_agent_v*`. Placeholders supported in prompt files:
- `{date}` — today's date in `YYYY-MM-DD`
- `{universe_filter}` — only in `brief_agent_*.txt`, replaced with the contents of `universe_track_{a,b}_{bv}.txt`

## Sources in picks JSON

Every brief and research entry includes a `sources` array:

```json
{
  "ticker": "012450",
  "reasoning": "...",
  "sources": [
    {"publisher": "한국경제", "url": "https://...", "date": "2026-06-12"}
  ]
}
```

In `final_picks` (post-aggregation), brief and research sources are concatenated, and original reasonings are preserved as `brief_reasoning` and `research_reasoning`.

## CSV schemas

`variant_performance.csv`:

| column | description |
|---|---|
| `date` | trading date `YYYY-MM-DD` |
| `context_variant`, `brief_variant`, `research_variant` | variant ids that produced this combo |
| `track_a_picks`, `track_b_picks` | comma-separated tickers |
| `track_a_avg_pnl`, `track_b_avg_pnl` | mean realized P&L % across the 5 picks (TP+5 / SL-3 from open) |
| `track_a_catchable_count`, `track_b_catchable_count` | # of picks flagged catchable (`✅ ok`) by the entry-window heuristic |
| `combo_id` | `{cv}-{bv}-{rv}` for grouping/joining |

`market_history.csv`:

| column | description |
|---|---|
| `date` | trading date |
| `kospi_open`, `kospi_close`, `kospi_change_pct` | from `FinanceDataReader` |
| `kosdaq_open`, `kosdaq_close`, `kosdaq_change_pct` | same |
| `regime_label` | category word from "Regime:" line in context (panic / bounce / continuation / normal / sideways) |
| `major_news_summary` | one-line auto-extract from "Key events:" section |
| `foreign_net_flow_billion_krw` | parsed from the context's foreign-flow line (negative = net selling). 1조원 ≈ 1000B KRW. |

Both CSVs are upserted: re-running the same date replaces the matching rows, never duplicates.

## Manual override

To bypass the morning pipeline entirely (e.g. you've already picked tickers manually):

```bash
python3 post-pipeline.py \
  --large 005930,000660,012330,042660,012450 \
  --mid   240810,084370,403870,095340,095610
```

This runs as a single combo with `combo_id="manual"` so it doesn't pollute the variant-performance comparison.

## Setup

```bash
pip3 install anthropic finance-datareader pandas requests beautifulsoup4 yfinance tabulate
```

Put your Anthropic key in `.env` at the **repo root** (one level up from `korean/`):

```
ANTHROPIC_API_KEY=sk-ant-...
```

The morning pipeline auto-loads `.env` so you don't need to `export`.

## Models

- **Context agent**: `claude-sonnet-4-6` (cheaper, supports `temperature=0.1`)
- **Brief + research agents**: `claude-opus-4-7` (no temperature parameter; web search enabled)

Don't change model selection casually — Opus 4.7 rejects `temperature`, Sonnet expects it.
