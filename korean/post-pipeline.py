#!/usr/bin/env python3
"""
Daily Korean stock market data collector — variant matrix edition.

Auto-discovers all data/{date}/{date}-picks-*.json files (one per (context, brief, research)
variant combination produced by pre-pipeline.py), runs the same TP/SL simulation
on each, and emits per-combo tables. Falls back to legacy {date}-picks.json if no
variant-suffixed files are present.

Also appends/updates two CSV files under data/:
  data/variant_performance.csv  — per-(date, combo) P&L summary
  data/market_history.csv       — per-date market overview & regime label

After running, generates a stub data/{date}/{date}-improvement.md template (if not present)
for human review notes.

Usage:
    python3 post-pipeline.py
    python3 post-pipeline.py --date 2026-06-09
    python3 post-pipeline.py --large 005930,000660,012330,042660,012450 \\
                             --mid 240810,084370,403870,095340,095610
    python3 post-pipeline.py --skip-top30
"""

import sys
import csv
import json
import re
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    import FinanceDataReader as fdr
    import pandas as pd
    import requests
    from bs4 import BeautifulSoup
    import yfinance as yf
    from tabulate import tabulate
except ImportError as e:
    print("Missing packages. Install with:")
    print("  pip3 install finance-datareader pandas requests beautifulsoup4 yfinance tabulate")
    print(f"Error: {e}")
    sys.exit(1)


# ============================================================
# Configuration
# ============================================================

# Trading parameters
TP_PCT = 5.0
SL_PCT = 3.0

TICKER_NAMES = {}  # populated from morning pipeline JSON at runtime

# Always anchor file IO to the script's own folder so the script works from any CWD.
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"


def _date_folder(target_date_str):
    return DATA_DIR / target_date_str


# ============================================================
# Morning pipeline loader — discovers all picks variants in {date}/
# ============================================================

PICKS_PATTERN_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-picks(?:-([^.]+))?\.json$")


def discover_picks_files(target_date_str):
    """
    Find every picks JSON in the date folder.

    Looks for `{date}-picks-{combo_id}.json` (variant-aware) and falls back to the
    legacy `{date}-picks.json` (treated as combo_id "legacy") if no variant files exist.

    Returns list of dicts: [{"combo_id": str, "path": Path, "data": dict, "variants": dict}, ...]
    Sorted alphabetically by combo_id for deterministic ordering.
    """
    folder = _date_folder(target_date_str)
    if not folder.is_dir():
        return []

    found = []
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        m = PICKS_PATTERN_RE.match(path.name)
        if not m or m.group(1) != target_date_str:
            continue
        combo_id = m.group(2) or "legacy"
        try:
            data = json.loads(path.read_text())
        except Exception as e:
            print(f"  WARN: failed to parse {path}: {e}", file=sys.stderr)
            continue
        variants = data.get("variants") or _split_combo_id(combo_id)
        found.append({
            "combo_id": combo_id,
            "path": path,
            "data": data,
            "variants": variants,
        })
    return found


def _split_combo_id(combo_id):
    """Best-effort split combo_id "v1-v2-v3" → variants dict. "legacy" → all "legacy"."""
    if combo_id == "legacy":
        return {"context": "legacy", "brief": "legacy", "research": "legacy"}
    parts = combo_id.split("-")
    if len(parts) == 3:
        return {"context": parts[0], "brief": parts[1], "research": parts[2]}
    return {"context": combo_id, "brief": combo_id, "research": combo_id}


def picks_to_track_lists(picks_data):
    """Extract (track_a_tickers, track_b_tickers, name_map) from a picks JSON dict."""
    track_a = []
    track_b = []
    names = {}
    for pick in picks_data.get("track_a_large_mega", {}).get("final_picks", []):
        t = pick.get("ticker")
        if not t:
            continue
        track_a.append(t)
        if pick.get("name"):
            names[t] = (pick["name"], pick.get("market", "KOSPI"))
    for pick in picks_data.get("track_b_mid", {}).get("final_picks", []):
        t = pick.get("ticker")
        if not t:
            continue
        track_b.append(t)
        if pick.get("name"):
            names[t] = (pick["name"], pick.get("market", "KOSDAQ"))
    return track_a, track_b, names


# ============================================================
# Helpers
# ============================================================

def safe_float(x):
    if x is None or pd.isna(x):
        return None
    return float(x)


def safe_int(x):
    if x is None or pd.isna(x):
        return None
    return int(x)


def get_name_and_market(ticker):
    if ticker in TICKER_NAMES:
        return TICKER_NAMES[ticker]
    try:
        url = f"https://finance.naver.com/item/main.naver?code={ticker}"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")
        name_tag = soup.select_one(".wrap_company h2 a")
        if name_tag:
            name = name_tag.text.strip()
            market_tag = soup.select_one(".description .code")
            market = "KOSPI"
            if market_tag and "코스닥" in market_tag.text:
                market = "KOSDAQ"
            return (name, market)
    except Exception:
        pass
    return (None, None)


def classify_pattern(prev_close, o, h, l, c, suspended=False):
    if suspended:
        return "정"
    if None in (o, h, l, c):
        return ""
    if prev_close and c >= prev_close * 1.295 and abs(c - h) / c < 0.001:
        return "상"
    if h == l:
        return "="

    high_pct = (h - o) / o * 100
    low_pct = (l - o) / o * 100
    close_pct = (c - o) / o * 100
    range_pct = (h - l) / o * 100

    if prev_close and o < prev_close * 0.97 and high_pct > 2 and close_pct > -high_pct * 0.3:
        return "V"
    if high_pct > 3 and close_pct < high_pct * 0.3:
        return "Λ"
    if close_pct > 2 and low_pct > -1:
        return "↑"
    if close_pct < -2 and high_pct < 1:
        return "↓"
    if range_pct > 5:
        return "~"
    return "="


def simulate_tp_sl(o_to_h, o_to_l, o_to_c, high_before_low, tp=TP_PCT, sl=SL_PCT):
    """Return (pnl_pct, exit_reason). Entry = open (09:00). Uses precomputed daily aggregates."""
    if None in (o_to_h, o_to_l, o_to_c):
        return None, "no-data"

    tp_hit = o_to_h >= tp
    sl_hit = o_to_l <= -sl

    if tp_hit and sl_hit:
        if high_before_low is True:
            return tp, "TP"
        elif high_before_low is False:
            return -sl, "SL"
        else:
            return -sl, "SL?"  # unknown order, assume worst case
    elif tp_hit:
        return tp, "TP"
    elif sl_hit:
        return -sl, "SL"
    else:
        return o_to_c, "HOLD"


def simulate_tp_sl_at_minute(df_minute, entry_minute_idx=5, tp=TP_PCT, sl=SL_PCT):
    """
    Entry-timing variant of `simulate_tp_sl`. Buys at the OPEN of `entry_minute_idx`-th
    one-minute bar (idx 5 = 09:05:00 KST), then scans forward for TP/SL hits.

    Why: Lets us A/B-compare "blind 09:00 market-buy" against "wait 5 minutes, then buy"
    on the same picks. Both run on the same pick list — only the entry timing differs.
    Over days of data this answers: "is the open-as-distribution problem reducible by
    deferring entry by 5 minutes?"

    Returns (pnl_pct, exit_reason, entry_price). entry_price is the open of the bar at
    entry_minute_idx — i.e. the actual fill price under this rule.
    """
    if df_minute is None or df_minute.empty:
        return None, "no-data", None
    if entry_minute_idx >= len(df_minute):
        return None, "no-data", None

    entry_row = df_minute.iloc[entry_minute_idx]
    entry_price = float(entry_row["Open"])
    if entry_price == 0:
        return None, "no-data", None

    # Scan from the entry bar onwards. Note: entry bar's own high/low can already
    # cross TP/SL — but only after we hold the position (entry is at the bar's open).
    scan = df_minute.iloc[entry_minute_idx:]
    last_close = None
    for ts, row in scan.iterrows():
        high = float(row["High"])
        low = float(row["Low"])
        last_close = float(row["Close"])
        high_pct = (high - entry_price) / entry_price * 100
        low_pct = (low - entry_price) / entry_price * 100

        tp_hit = high_pct >= tp
        sl_hit = low_pct <= -sl

        if tp_hit and sl_hit:
            # Both hit in same bar — order unknown, assume SL (worst case).
            return -sl, "SL?", entry_price
        if tp_hit:
            return tp, "TP", entry_price
        if sl_hit:
            return -sl, "SL", entry_price

    # Neither hit — return entry→last_close P&L.
    if last_close is None:
        return None, "no-data", entry_price
    close_pct = (last_close - entry_price) / entry_price * 100
    return close_pct, "HOLD", entry_price


# 09:05 entry timing — DEFER gate threshold
# ------------------------------------------------------------
# 06-18 lesson + JOURNEY universal rule: `first_5min_min_pct ≤ −2.5%` was a 100% SL
# predictor across 4 trading days. The "09:05 buy" alternate-entry simulation wraps
# `simulate_tp_sl_at_minute` with a DEFER gate — if the first 5 minutes already
# broke this threshold, skip the trade entirely (treat as 0.0% P&L) rather than
# entering anyway.
DEFER_FIRST_5MIN_THRESHOLD = -2.5


def assess_purchaseable(first_n_minutes, first_5min_max_pct, minutes_to_5pct, entry_window_minutes):
    """Return short label assessing execution feasibility."""
    if not first_n_minutes:
        return "?"

    # Check first minute behavior
    first_min_pct = first_n_minutes[0].get("pct_from_open", 0) if first_n_minutes else 0

    # Already jumped at first tick
    if first_min_pct >= 3:
        return "❌ gap"

    # Shot up to +5% within 1-2 minutes
    if minutes_to_5pct is not None and minutes_to_5pct <= 1:
        return "❌ fast"

    # Hit +3% in first minute
    if first_5min_max_pct is not None and first_5min_max_pct >= 5 and minutes_to_5pct is not None and minutes_to_5pct <= 2:
        return "⚠️ tight"

    # Very narrow entry window
    if entry_window_minutes is not None and entry_window_minutes < 2:
        return "⚠️ narrow"

    return "✅ ok"


# ============================================================
# Minute-level data fetcher
# ============================================================

def fetch_minute_data(ticker, market, target_date_str):
    try:
        suffix = ".KS" if market == "KOSPI" else ".KQ"
        yf_symbol = f"{ticker}{suffix}"

        target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
        start = target_dt.strftime("%Y-%m-%d")
        end = (target_dt + timedelta(days=1)).strftime("%Y-%m-%d")

        df = yf.download(
            yf_symbol, start=start, end=end, interval="1m",
            progress=False, auto_adjust=False,
        )

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_convert("Asia/Seoul")
        df_today = df[df.index.strftime("%Y-%m-%d") == target_date_str]

        if df_today.empty:
            return None
        return df_today
    except Exception:
        return None


MOMENTUM_TRIGGER_WINDOWS = (1, 3, 5, 10, 15, 30, 60)


def compute_momentum_trigger(prices, idx, windows=MOMENTUM_TRIGGER_WINDOWS):
    """At index idx, return (x_pct, y_minutes) — the largest absolute % price move
    ending at idx, scanning each lookback window in `windows`. Returns None when
    idx==0 or no valid window can be computed (insufficient history, zero prices)."""
    if idx <= 0 or len(prices) == 0:
        return None
    price_now = float(prices[idx])
    if price_now <= 0:
        return None
    best = None  # (x_pct, y_minutes)
    for y in windows:
        prev_idx = idx - y
        if prev_idx < 0:
            prev_idx = 0
        prev_price = float(prices[prev_idx])
        if prev_price <= 0:
            continue
        actual_y = idx - prev_idx
        if actual_y == 0:
            continue
        x = (price_now - prev_price) / prev_price * 100
        if best is None or abs(x) > abs(best[0]):
            best = (x, actual_y)
    return best


def compute_best_entry(df_minute, tp=TP_PCT, sl=SL_PCT):
    """
    For each minute as a hypothetical entry, simulate TP/SL outcome.
    Return the minute that gives the highest realized P&L, plus the momentum trigger
    (largest |x%| move in last y minutes for y in {1,3,5,10,15,30,60}) at that entry.

    Returns dict:
    - best_entry_time: "HH:MM"
    - best_entry_price: price at entry minute close
    - best_entry_pnl_pct: realized P&L %
    - best_entry_reason: "TP" / "SL" / "HOLD"
    - best_entry_trigger_pct: signed % move ending at the entry minute (None if N/A)
    - best_entry_trigger_min: window length (in minutes) of the trigger
    """
    null_result = {
        "best_entry_time": None,
        "best_entry_price": None,
        "best_entry_pnl_pct": None,
        "best_entry_reason": None,
        "best_entry_trigger_pct": None,
        "best_entry_trigger_min": None,
    }
    if df_minute is None or df_minute.empty or len(df_minute) < 2:
        return null_result

    closes = df_minute["Close"].values
    highs = df_minute["High"].values
    lows = df_minute["Low"].values
    times = df_minute.index
    n = len(df_minute)
    last_close = float(closes[-1])

    best_pnl = None
    best_entry_idx = None
    best_reason = None

    for i in range(n - 1):
        entry_price = float(closes[i])
        if entry_price <= 0:
            continue

        tp_target = entry_price * (1 + tp / 100)
        sl_target = entry_price * (1 - sl / 100)

        pnl = None
        reason = None
        for j in range(i + 1, n):
            h = float(highs[j])
            l = float(lows[j])
            tp_hit = h >= tp_target
            sl_hit = l <= sl_target

            if tp_hit and sl_hit:
                pnl = -sl
                reason = "SL"
                break
            elif tp_hit:
                pnl = tp
                reason = "TP"
                break
            elif sl_hit:
                pnl = -sl
                reason = "SL"
                break

        if pnl is None:
            pnl = (last_close - entry_price) / entry_price * 100
            reason = "HOLD"

        if best_pnl is None or pnl > best_pnl:
            best_pnl = pnl
            best_entry_idx = i
            best_reason = reason

    if best_entry_idx is None:
        return null_result

    trig = compute_momentum_trigger(closes, best_entry_idx)
    return {
        "best_entry_time": times[best_entry_idx].strftime("%H:%M"),
        "best_entry_price": float(closes[best_entry_idx]),
        "best_entry_pnl_pct": round(best_pnl, 2),
        "best_entry_reason": best_reason,
        "best_entry_trigger_pct": round(trig[0], 2) if trig else None,
        "best_entry_trigger_min": trig[1] if trig else None,
    }


def compute_best_buy_sell(df_minute):
    """Identify the day's absolute lowest minute (best moment to buy) and highest minute
    (best moment to sell), each annotated with a momentum trigger of form
    (x% move in last y minutes). Independent of TP/SL — purely hindsight low/high."""
    null_result = {
        "best_buy_time": None,
        "best_buy_pct_from_open": None,
        "best_buy_trigger_pct": None,
        "best_buy_trigger_min": None,
        "best_sell_time": None,
        "best_sell_pct_from_open": None,
        "best_sell_trigger_pct": None,
        "best_sell_trigger_min": None,
    }
    if df_minute is None or df_minute.empty:
        return null_result

    opens = df_minute["Open"].values
    if len(opens) == 0:
        return null_result
    open_price = float(opens[0])
    if open_price <= 0:
        return null_result

    closes = df_minute["Close"].values
    lows = df_minute["Low"].values
    highs = df_minute["High"].values
    times = df_minute.index

    low_idx = int(df_minute["Low"].values.argmin())
    high_idx = int(df_minute["High"].values.argmax())

    low_price = float(lows[low_idx])
    high_price = float(highs[high_idx])

    buy_trig = compute_momentum_trigger(closes, low_idx)
    sell_trig = compute_momentum_trigger(closes, high_idx)

    return {
        "best_buy_time": times[low_idx].strftime("%H:%M"),
        "best_buy_pct_from_open": round((low_price - open_price) / open_price * 100, 2),
        "best_buy_trigger_pct": round(buy_trig[0], 2) if buy_trig else None,
        "best_buy_trigger_min": buy_trig[1] if buy_trig else None,
        "best_sell_time": times[high_idx].strftime("%H:%M"),
        "best_sell_pct_from_open": round((high_price - open_price) / open_price * 100, 2),
        "best_sell_trigger_pct": round(sell_trig[0], 2) if sell_trig else None,
        "best_sell_trigger_min": sell_trig[1] if sell_trig else None,
    }


def extract_timing(df_minute):
    null_result = {"high_time": None, "low_time": None, "high_before_low": None}
    if df_minute is None or df_minute.empty:
        return null_result
    high_idx = df_minute["High"].idxmax()
    low_idx = df_minute["Low"].idxmin()
    return {
        "high_time": high_idx.strftime("%H:%M"),
        "low_time": low_idx.strftime("%H:%M"),
        "high_before_low": bool(high_idx < low_idx),
    }


def extract_open_minutes(df_minute, n=10):
    empty_result = {
        "first_n_minutes": [], "entry_window_minutes": None,
        "first_5min_max_pct": None, "first_5min_min_pct": None,
        "minutes_to_3pct": None, "minutes_to_5pct": None,
    }
    if df_minute is None or df_minute.empty:
        return empty_result

    first_n = df_minute.head(n)
    if first_n.empty:
        return empty_result

    official_open = float(first_n.iloc[0]["Open"])
    if official_open == 0:
        return empty_result

    minutes = []
    entry_window_count = 0
    minutes_to_3pct = None
    minutes_to_5pct = None
    first_5min_max = None
    first_5min_min = None

    for i, (ts, row) in enumerate(first_n.iterrows()):
        close = float(row["Close"])
        high = float(row["High"])
        low = float(row["Low"])
        vol = int(row["Volume"]) if not pd.isna(row["Volume"]) else 0

        close_pct = (close - official_open) / official_open * 100
        high_pct = (high - official_open) / official_open * 100
        low_pct = (low - official_open) / official_open * 100

        minutes.append({
            "minute": i, "time": ts.strftime("%H:%M"),
            "close": close, "high": high, "low": low,
            "pct_from_open": round(close_pct, 3),
            "high_pct_from_open": round(high_pct, 3),
            "low_pct_from_open": round(low_pct, 3),
            "volume": vol,
        })

        if abs(close_pct) <= 0.5:
            entry_window_count += 1
        if minutes_to_3pct is None and high_pct >= 3:
            minutes_to_3pct = i
        if minutes_to_5pct is None and high_pct >= 5:
            minutes_to_5pct = i

        if i < 5:
            if first_5min_max is None or high_pct > first_5min_max:
                first_5min_max = high_pct
            if first_5min_min is None or low_pct < first_5min_min:
                first_5min_min = low_pct

    return {
        "first_n_minutes": minutes,
        "entry_window_minutes": entry_window_count,
        "first_5min_max_pct": round(first_5min_max, 3) if first_5min_max is not None else None,
        "first_5min_min_pct": round(first_5min_min, 3) if first_5min_min is not None else None,
        "minutes_to_3pct": minutes_to_3pct,
        "minutes_to_5pct": minutes_to_5pct,
    }


# ============================================================
# Daily fetchers
# ============================================================

def get_stock_ohlcv(ticker, target_date_str, prev_date_str):
    try:
        df = fdr.DataReader(ticker, prev_date_str, target_date_str)
        if df is None or df.empty:
            return None
        target_dt = pd.to_datetime(target_date_str)
        if target_dt not in df.index:
            return {"suspended": True}
        row = df.loc[target_dt]
        idx = df.index.get_loc(target_dt)
        prev_close = safe_float(df.iloc[idx - 1]["Close"]) if idx > 0 else None
        return {
            "prev_close": prev_close,
            "open": safe_float(row["Open"]), "high": safe_float(row["High"]),
            "low": safe_float(row["Low"]), "close": safe_float(row["Close"]),
            "volume": safe_int(row["Volume"]),
            "change_pct": safe_float(row.get("Change")) * 100 if "Change" in row else None,
            "suspended": False,
        }
    except Exception as e:
        print(f"  Error fetching {ticker}: {e}", file=sys.stderr)
        return None


def enrich_with_open_relative(data):
    if data is None or data.get("suspended"):
        return data
    o = data.get("open")
    if o is None or o == 0:
        data["open_to_close_pct"] = None
        data["open_to_high_pct"] = None
        data["open_to_low_pct"] = None
        return data
    h = data.get("high")
    l = data.get("low")
    c = data.get("close")
    data["open_to_close_pct"] = ((c - o) / o * 100) if c is not None else None
    data["open_to_high_pct"] = ((h - o) / o * 100) if h is not None else None
    data["open_to_low_pct"] = ((l - o) / o * 100) if l is not None else None
    return data


def get_index(symbol, target_date_str, prev_date_str):
    candidates = {"KOSPI": ["KS11", "KOSPI"], "KOSDAQ": ["KQ11", "KOSDAQ"]}
    for sym in candidates.get(symbol, [symbol]):
        try:
            df = fdr.DataReader(sym, prev_date_str, target_date_str)
            if df is None or df.empty:
                continue
            target_dt = pd.to_datetime(target_date_str)
            if target_dt not in df.index:
                continue
            row = df.loc[target_dt]
            return {
                "open": safe_float(row.get("Open")), "close": safe_float(row.get("Close")),
                "high": safe_float(row.get("High")), "low": safe_float(row.get("Low")),
                "change_pct": safe_float(row.get("Change")) * 100 if "Change" in row else None,
            }
        except Exception:
            continue
    return None


def get_usdkrw(target_date_str, prev_date_str):
    for sym in ["USD/KRW", "KRW=X"]:
        try:
            df = fdr.DataReader(sym, prev_date_str, target_date_str)
            if df is None or df.empty:
                continue
            target_dt = pd.to_datetime(target_date_str)
            if target_dt not in df.index:
                continue
            row = df.loc[target_dt]
            return {"open": safe_float(row.get("Open")), "close": safe_float(row.get("Close")),
                    "high": safe_float(row.get("High"))}
        except Exception:
            continue
    return None


def scrape_naver_top_movers(max_pages=4):
    tickers = []
    for sosok in [0, 1]:
        market = "KOSPI" if sosok == 0 else "KOSDAQ"
        for page in range(1, max_pages + 1):
            try:
                url = f"https://finance.naver.com/sise/sise_rise.naver?sosok={sosok}&page={page}"
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                soup = BeautifulSoup(resp.text, "html.parser")
                table = soup.select_one("table.type_2")
                if not table:
                    continue
                for row in table.select("tr"):
                    link = row.select_one("a.tltle")
                    if not link:
                        continue
                    href = link.get("href", "")
                    match = re.search(r"code=(\d{6})", href)
                    if match:
                        ticker = match.group(1)
                        name = link.text.strip()
                        tickers.append((ticker, name, market))
                time.sleep(0.3)
            except Exception as e:
                print(f"  Naver error: {e}", file=sys.stderr)
                continue
    return tickers


def fetch_top_30_intraday(target_date_str, prev_date_str, skip_minute=False):
    print("  Scraping Naver for candidates...", file=sys.stderr)
    candidates = scrape_naver_top_movers(max_pages=4)
    print(f"  Got {len(candidates)} candidates, fetching daily OHLCV...", file=sys.stderr)

    results = []
    target_dt = pd.to_datetime(target_date_str)
    seen = set()

    for i, (ticker, name, market) in enumerate(candidates, 1):
        if ticker in seen:
            continue
        seen.add(ticker)
        if i % 50 == 0:
            print(f"    Progress: {i}/{len(candidates)}", file=sys.stderr)
        try:
            df = fdr.DataReader(ticker, prev_date_str, target_date_str)
            if df is None or df.empty or target_dt not in df.index:
                continue
            row = df.loc[target_dt]
            o = safe_float(row.get("Open"))
            h = safe_float(row.get("High"))
            l = safe_float(row.get("Low"))
            c = safe_float(row.get("Close"))
            if o is None or o == 0 or c is None:
                continue
            idx = df.index.get_loc(target_dt)
            prev_close = safe_float(df.iloc[idx - 1]["Close"]) if idx > 0 else None
            results.append({
                "ticker": ticker, "name": name, "market": market,
                "prev_close": prev_close,
                "open": o, "high": h, "low": l, "close": c,
                "change_pct": safe_float(row.get("Change")) * 100 if "Change" in row else None,
                "open_to_close_pct": (c - o) / o * 100,
                "open_to_high_pct": ((h - o) / o * 100) if h else None,
                "open_to_low_pct": ((l - o) / o * 100) if l else None,
                "volume": safe_int(row.get("Volume")),
                "pattern": classify_pattern(prev_close, o, h, l, c),
                "high_time": None, "low_time": None, "high_before_low": None,
                "first_n_minutes": [], "entry_window_minutes": None,
                "first_5min_max_pct": None, "first_5min_min_pct": None,
                "minutes_to_3pct": None, "minutes_to_5pct": None,
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["open_to_close_pct"], reverse=True)
    top_30 = results[:30]
    for rank, item in enumerate(top_30, 1):
        item["rank"] = rank

    if not skip_minute:
        print(f"  Fetching minute data for top 30...", file=sys.stderr)
        for i, item in enumerate(top_30, 1):
            if i % 10 == 0:
                print(f"    Minute progress: {i}/30", file=sys.stderr)
            df_minute = fetch_minute_data(item["ticker"], item["market"], target_date_str)
            timing = extract_timing(df_minute)
            item.update(timing)
            open_data = extract_open_minutes(df_minute, n=10)
            item.update(open_data)
    return top_30


def process_pick(ticker, cap_tier, target_date_str, prev_date_str, skip_minute):
    """Process one pick — daily + minute + open-minutes + best entry."""
    name, market = get_name_and_market(ticker)
    data = get_stock_ohlcv(ticker, target_date_str, prev_date_str)

    timing = {"high_time": None, "low_time": None, "high_before_low": None}
    open_data = {
        "first_n_minutes": [], "entry_window_minutes": None,
        "first_5min_max_pct": None, "first_5min_min_pct": None,
        "minutes_to_3pct": None, "minutes_to_5pct": None,
    }
    best_entry = {
        "best_entry_time": None, "best_entry_price": None,
        "best_entry_pnl_pct": None, "best_entry_reason": None,
        "best_entry_trigger_pct": None, "best_entry_trigger_min": None,
    }
    best_buy_sell = {
        "best_buy_time": None, "best_buy_pct_from_open": None,
        "best_buy_trigger_pct": None, "best_buy_trigger_min": None,
        "best_sell_time": None, "best_sell_pct_from_open": None,
        "best_sell_trigger_pct": None, "best_sell_trigger_min": None,
    }
    # Entry-timing variant: 09:05 buy P&L (the "wait 5 minutes" gate).
    entry_905 = {
        "tp_sl_at_905_pnl_pct": None,
        "tp_sl_at_905_reason": None,
        "tp_sl_at_905_entry_price": None,
    }
    if not skip_minute and data and not data.get("suspended"):
        df_minute = fetch_minute_data(ticker, market, target_date_str)
        timing = extract_timing(df_minute)
        open_data = extract_open_minutes(df_minute, n=10)
        best_entry = compute_best_entry(df_minute)
        best_buy_sell = compute_best_buy_sell(df_minute)

        # 09:05 entry simulation with DEFER gate.
        # If first 5 minutes already broke −2.5%, skip the trade entirely (DEFER → 0.0%
        # P&L). Otherwise run the standard 09:05 minute-by-minute TP/SL simulation.
        f5m = open_data.get("first_5min_min_pct")
        if f5m is not None and f5m <= DEFER_FIRST_5MIN_THRESHOLD:
            entry_905 = {
                "tp_sl_at_905_pnl_pct": 0.0,
                "tp_sl_at_905_reason": "DEFER",
                "tp_sl_at_905_entry_price": None,
            }
        else:
            pnl_905, reason_905, ep_905 = simulate_tp_sl_at_minute(df_minute, entry_minute_idx=5)
            entry_905 = {
                "tp_sl_at_905_pnl_pct": round(pnl_905, 3) if pnl_905 is not None else None,
                "tp_sl_at_905_reason": reason_905,
                "tp_sl_at_905_entry_price": ep_905,
            }

    base = {
        "ticker": ticker, "name": name, "market": market, "cap_tier": cap_tier,
        "in_top_30": False, "top_30_rank": None,
    }
    if data is None:
        return {**base, "prev_close": None, "open": None, "high": None, "low": None, "close": None,
                "change_pct": None, "open_to_close_pct": None, "open_to_high_pct": None,
                "open_to_low_pct": None, "volume": None, "pattern": "",
                **timing, **open_data, **best_entry, **best_buy_sell, **entry_905}
    if data.get("suspended"):
        return {**base, "prev_close": None, "open": None, "high": None, "low": None, "close": None,
                "change_pct": None, "open_to_close_pct": None, "open_to_high_pct": None,
                "open_to_low_pct": None, "volume": None, "pattern": "정",
                **timing, **open_data, **best_entry, **best_buy_sell, **entry_905}

    data = enrich_with_open_relative(data)
    pattern = classify_pattern(data["prev_close"], data["open"], data["high"], data["low"], data["close"])
    return {**base,
            "prev_close": data["prev_close"],
            "open": data["open"], "high": data["high"], "low": data["low"], "close": data["close"],
            "change_pct": data["change_pct"],
            "open_to_close_pct": data["open_to_close_pct"],
            "open_to_high_pct": data["open_to_high_pct"],
            "open_to_low_pct": data["open_to_low_pct"],
            "volume": data["volume"], "pattern": pattern,
            **timing, **open_data, **best_entry, **best_buy_sell, **entry_905}


# ============================================================
# Table printing
# ============================================================

# Global buffer for capturing summary text (so we can both print and save)
_SUMMARY_BUFFER = []


def out(line=""):
    """Print to stdout AND append to summary buffer."""
    print(line)
    _SUMMARY_BUFFER.append(line)


def fmt_price_krw(p):
    """Format a KRW price as a comma-separated integer (KRW has no fractional unit). "-" for missing."""
    if p is None:
        return "-"
    try:
        return f"{int(round(float(p))):,}"
    except (TypeError, ValueError):
        return "-"


def _fmt_trigger(x_pct, y_min):
    """Format momentum trigger as e.g. "↑5.5%/30m" or "↓1.2%/3m". Returns "" if missing."""
    if x_pct is None or y_min is None:
        return ""
    arrow = "↑" if x_pct >= 0 else "↓"
    return f"{arrow}{abs(x_pct):.2f}%/{y_min}m"


def format_pick_row(p, include_cap=True):
    """
    Row layout (post-improvement):
      Ticker | Name | Cap | PrevC | Open | OptPT | OptSL | TP/SL@open
            | O→C% | O→H% | O→L% | Pat | Catchable
            | Best entry | Best buy | Best sell

    PrevC  = 어제 종가 (price, KRW)
    Open   = 오늘 시가 (price, KRW)
    OptPT  = 당일 고가 — 시가에 매수했을 때 이상적인 익절 가격 (이 가격에 TP를 두면 체결됨)
    OptSL  = 당일 저가 — 이 가격 바로 아래에 손절을 두면 당일 손절을 피할 수 있음
    Best entry = TP=5%/SL=3% 룰 하에서 최적 매수 분 + 그 시점의 모멘텀 트리거
                 ("최근 y분간 x% 상승/하락")
    Best buy   = 당일 최저가 분 + 시가 대비 가격 + 직전 모멘텀 트리거
    Best sell  = 당일 최고가 분 + 시가 대비 가격 + 직전 모멘텀 트리거
    """
    pnl, reason = simulate_tp_sl(
        p.get("open_to_high_pct"), p.get("open_to_low_pct"),
        p.get("open_to_close_pct"), p.get("high_before_low"),
    )
    purchaseable = assess_purchaseable(
        p.get("first_n_minutes", []),
        p.get("first_5min_max_pct"),
        p.get("minutes_to_5pct"),
        p.get("entry_window_minutes"),
    )

    def fmt_pct(v):
        return f"{v:+.2f}%" if v is not None else "-"

    def fmt_pnl(pnl, reason):
        if pnl is None:
            return "-"
        return f"{pnl:+.2f}% ({reason})"

    be_time = p.get("best_entry_time")
    be_pnl = p.get("best_entry_pnl_pct")
    be_reason = p.get("best_entry_reason")
    if be_time and be_pnl is not None:
        trig_str = _fmt_trigger(p.get("best_entry_trigger_pct"), p.get("best_entry_trigger_min"))
        trig_suffix = f"  [{trig_str}]" if trig_str else ""
        best_entry_str = f"{be_time} {be_pnl:+.2f}% ({be_reason}){trig_suffix}"
    else:
        best_entry_str = "-"

    bb_time = p.get("best_buy_time")
    bb_pct = p.get("best_buy_pct_from_open")
    if bb_time and bb_pct is not None:
        trig_str = _fmt_trigger(p.get("best_buy_trigger_pct"), p.get("best_buy_trigger_min"))
        trig_suffix = f"  [{trig_str}]" if trig_str else ""
        best_buy_str = f"{bb_time} {bb_pct:+.2f}%{trig_suffix}"
    else:
        best_buy_str = "-"

    bs_time = p.get("best_sell_time")
    bs_pct = p.get("best_sell_pct_from_open")
    if bs_time and bs_pct is not None:
        trig_str = _fmt_trigger(p.get("best_sell_trigger_pct"), p.get("best_sell_trigger_min"))
        trig_suffix = f"  [{trig_str}]" if trig_str else ""
        best_sell_str = f"{bs_time} {bs_pct:+.2f}%{trig_suffix}"
    else:
        best_sell_str = "-"

    row = [
        p.get("ticker", "-"),
        (p.get("name") or "-")[:12],
    ]
    if include_cap:
        row.append(p.get("cap_tier") or "-")
    row.extend([
        fmt_price_krw(p.get("prev_close")),   # PrevC: 어제 종가
        fmt_price_krw(p.get("open")),         # Open:  오늘 시가
        fmt_price_krw(p.get("high")),         # OptPT: 당일 고가
        fmt_price_krw(p.get("low")),          # OptSL: 당일 저가
        fmt_pnl(pnl, reason),
        fmt_pct(p.get("open_to_close_pct")),
        fmt_pct(p.get("open_to_high_pct")),
        fmt_pct(p.get("open_to_low_pct")),
        p.get("pattern") or "-",
        purchaseable,
        best_entry_str,
        best_buy_str,
        best_sell_str,
    ])
    return row, pnl


def print_pick_table(picks, title):
    headers = [
        "Ticker", "Name", "Cap",
        "PrevC", "Open", "OptPT", "OptSL",
        "TP/SL@open", "O→C%", "O→H%", "O→L%",
        "Pat", "Catchable",
        "Best entry", "Best buy", "Best sell",
    ]
    rows = []
    pnls = []
    best_entry_pnls = []
    for p in picks:
        row, pnl = format_pick_row(p, include_cap=True)
        rows.append(row)
        if pnl is not None:
            pnls.append(pnl)
        if p.get("best_entry_pnl_pct") is not None:
            best_entry_pnls.append(p["best_entry_pnl_pct"])

    out(f"\n{'=' * 170}")
    out(f"  {title}")
    out(f"{'=' * 170}")
    out(tabulate(rows, headers=headers, tablefmt="simple"))
    if pnls:
        avg = sum(pnls) / len(pnls)
        catchable_count = sum(1 for p in picks
                              if assess_purchaseable(
                                  p.get("first_n_minutes", []),
                                  p.get("first_5min_max_pct"),
                                  p.get("minutes_to_5pct"),
                                  p.get("entry_window_minutes"),
                              ).startswith("✅"))
        out(f"\n  Average TP/SL P&L (09:00 buy): {avg:+.2f}%  |  Catchable: {catchable_count}/{len(picks)}")

    # 09:05 entry variant — A/B comparison data for the "wait 5 minutes" gate.
    pnls_905 = [p.get("tp_sl_at_905_pnl_pct") for p in picks
                if p.get("tp_sl_at_905_pnl_pct") is not None]
    if pnls_905:
        avg_905 = sum(pnls_905) / len(pnls_905)
        delta = (avg_905 - avg) if pnls else None
        d_str = f"  ({delta:+.2f}%p vs 09:00)" if delta is not None else ""
        out(f"  Average TP/SL P&L (09:05 buy): {avg_905:+.2f}%{d_str}")

    if best_entry_pnls:
        avg_best = sum(best_entry_pnls) / len(best_entry_pnls)
        out(f"  Average TP/SL P&L (best-entry hindsight): {avg_best:+.2f}%")


def print_top30_table(top_30):
    headers = [
        "#", "Ticker", "Name", "Mkt",
        "PrevC", "Open", "OptPT", "OptSL",
        "TP/SL", "O→C%", "O→H%", "O→L%",
        "High@", "Low@", "Pat", "Catchable",
    ]
    rows = []
    for p in top_30:
        pnl, reason = simulate_tp_sl(
            p.get("open_to_high_pct"), p.get("open_to_low_pct"),
            p.get("open_to_close_pct"), p.get("high_before_low"),
        )
        purchaseable = assess_purchaseable(
            p.get("first_n_minutes", []),
            p.get("first_5min_max_pct"),
            p.get("minutes_to_5pct"),
            p.get("entry_window_minutes"),
        )

        def fmt_pct(v):
            return f"{v:+.2f}%" if v is not None else "-"

        rows.append([
            p.get("rank", "-"),
            p.get("ticker", "-"),
            (p.get("name") or "-")[:12],
            p.get("market", "-"),
            fmt_price_krw(p.get("prev_close")),  # PrevC
            fmt_price_krw(p.get("open")),        # Open
            fmt_price_krw(p.get("high")),        # OptPT
            fmt_price_krw(p.get("low")),         # OptSL
            f"{pnl:+.2f}% ({reason})" if pnl is not None else "-",
            fmt_pct(p.get("open_to_close_pct")),
            fmt_pct(p.get("open_to_high_pct")),
            fmt_pct(p.get("open_to_low_pct")),
            p.get("high_time") or "-",
            p.get("low_time") or "-",
            p.get("pattern") or "-",
            purchaseable,
        ])

    out(f"\n{'=' * 160}")
    out(f"  TOP 30 INTRADAY MOVERS (sorted by open→close gain)")
    out(f"{'=' * 160}")
    out(tabulate(rows, headers=headers, tablefmt="simple"))

    catchable = [r for r in rows if "✅" in r[-1]]
    catchable_pnls = []
    for p in top_30:
        purchaseable = assess_purchaseable(
            p.get("first_n_minutes", []),
            p.get("first_5min_max_pct"),
            p.get("minutes_to_5pct"),
            p.get("entry_window_minutes"),
        )
        if not purchaseable.startswith("✅"):
            continue
        pnl, _ = simulate_tp_sl(
            p.get("open_to_high_pct"), p.get("open_to_low_pct"),
            p.get("open_to_close_pct"), p.get("high_before_low"),
        )
        if pnl is not None:
            catchable_pnls.append(pnl)
    if catchable_pnls:
        avg_catchable = sum(catchable_pnls) / len(catchable_pnls)
        out(f"\n  Catchable subset: {len(catchable_pnls)}/30  |  Avg TP/SL P&L of catchable: {avg_catchable:+.2f}%")


def print_pick_top30_overlap(combo_results, top_30):
    """
    Per-combo summary of how many picks landed in the day's top-30 intraday movers.

    NOTE on framing: this is NOT a hit-rate KPI. Our scoring criterion is TP at +5%,
    not "did we pick a top-30 mover". A pick that TP'd at +5% is already a good slot
    regardless of where it ranked in the day's intraday move list. Top-30 is useful
    as a RETROSPECTIVE REFERENCE for the SL'd slots — "this slot lost; what sub-themes
    were actually working today that our brief didn't consider?" Use it to identify
    universe blindspots, not to grade the day.
    """
    out(f"\n{'=' * 120}")
    out(f"  PICK → TOP30 OVERLAP (retrospective reference for SL'd slots — NOT a hit-rate KPI)")
    out(f"{'=' * 120}")

    rank_by_ticker = {t["ticker"]: t["rank"] for t in top_30}

    headers = ["Combo", "A hits", "A tickers (rank)", "B hits", "B tickers (rank)", "Total"]
    rows = []
    for cr in combo_results:
        a = cr["summary"]["track_a"]
        b = cr["summary"]["track_b"]
        a_hits = []
        for p in cr["track_a_data"]:
            r = rank_by_ticker.get(p.get("ticker"))
            if r is not None:
                a_hits.append(f"{p.get('name','-')[:8]}(#{r})")
        b_hits = []
        for p in cr["track_b_data"]:
            r = rank_by_ticker.get(p.get("ticker"))
            if r is not None:
                b_hits.append(f"{p.get('name','-')[:8]}(#{r})")
        total = a["top30_hit_count"] + b["top30_hit_count"]
        n_total = a["n"] + b["n"]
        rows.append([
            cr["combo_id"],
            f"{a['top30_hit_count']}/{a['n']}",
            ", ".join(a_hits) or "-",
            f"{b['top30_hit_count']}/{b['n']}",
            ", ".join(b_hits) or "-",
            f"{total}/{n_total}",
        ])
    out(tabulate(rows, headers=headers, tablefmt="simple"))

    # Aggregated misses: top-30 movers that no combo picked. Useful for universe expansion
    # when reviewing SL'd slots — what sub-themes did our brief miss today?
    all_picked = set()
    for cr in combo_results:
        for p in cr["track_a_data"] + cr["track_b_data"]:
            all_picked.add(p.get("ticker"))
    missed = [t for t in top_30 if t["ticker"] not in all_picked]
    if missed:
        out(f"\n  Alternative-slot candidates (top-30 movers our brief didn't pick) — review for SL'd slots only: {len(missed)}/{len(top_30)}")
        for t in missed[:15]:
            ol_close = t.get("open_to_close_pct")
            ol_str = f"{ol_close:+.2f}%" if ol_close is not None else "-"
            out(f"    #{t['rank']:>2}  {t['ticker']}  {(t.get('name') or '-')[:14]:<14}  {t.get('market','-'):<6} O→C {ol_str}")


# ============================================================
# Per-combo summary computation
# ============================================================

def _avg(xs):
    xs = [x for x in xs if x is not None]
    return (sum(xs) / len(xs)) if xs else None


def compute_combo_summary(track_a_data, track_b_data):
    """Return dict of summary stats used by both stdout output and CSV."""
    def stats(picks):
        pnls = []          # 09:00 buy
        pnls_905 = []      # 09:05 buy (entry-timing variant; DEFER counted as 0.0%)
        deferred_905 = 0   # picks skipped by 09:05 DEFER gate (first_5min ≤ −2.5%)
        catchable = 0
        top30_ranks = []  # ranks of picks that made top 30
        for p in picks:
            pnl, _ = simulate_tp_sl(
                p.get("open_to_high_pct"), p.get("open_to_low_pct"),
                p.get("open_to_close_pct"), p.get("high_before_low"),
            )
            if pnl is not None:
                pnls.append(pnl)
            p905 = p.get("tp_sl_at_905_pnl_pct")
            if p905 is not None:
                pnls_905.append(p905)
            if p.get("tp_sl_at_905_reason") == "DEFER":
                deferred_905 += 1
            tag = assess_purchaseable(
                p.get("first_n_minutes", []),
                p.get("first_5min_max_pct"),
                p.get("minutes_to_5pct"),
                p.get("entry_window_minutes"),
            )
            if tag.startswith("✅"):
                catchable += 1
            if p.get("in_top_30"):
                top30_ranks.append(p.get("top_30_rank"))
        return {
            "tickers": ",".join(p.get("ticker", "?") for p in picks),
            "avg_pnl": _avg(pnls),                  # alias: 09:00 buy
            "avg_pnl_900": _avg(pnls),
            "avg_pnl_905": _avg(pnls_905),
            "deferred_905": deferred_905,
            "catchable_count": catchable,
            "top30_hit_count": len(top30_ranks),
            "top30_hit_ranks": top30_ranks,
            "n": len(picks),
        }
    a = stats(track_a_data)
    b = stats(track_b_data)
    combined_hits = a["top30_hit_count"] + b["top30_hit_count"]
    combined_n = a["n"] + b["n"]
    return {
        "track_a": a,
        "track_b": b,
        "combined_top30_hit_count": combined_hits,
        "combined_top30_hit_rate": (combined_hits / combined_n) if combined_n else None,
    }


# ============================================================
# CSV helpers — idempotent append (drop existing matching rows, then write)
# ============================================================

VARIANT_PERFORMANCE_COLS = [
    "date", "context_variant", "brief_variant", "research_variant",
    "track_a_picks", "track_a_avg_pnl", "track_a_avg_pnl_905", "track_a_catchable_count",
    "track_b_picks", "track_b_avg_pnl", "track_b_avg_pnl_905", "track_b_catchable_count",
    "combo_id",
]

MARKET_HISTORY_COLS = [
    "date", "kospi_open", "kospi_close", "kospi_change_pct",
    "kosdaq_open", "kosdaq_close", "kosdaq_change_pct",
    "regime_label", "major_news_summary", "foreign_net_flow_billion_krw",
]


def _read_csv_rows(path, fieldnames):
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            rows.append({k: r.get(k, "") for k in fieldnames})
        return rows


def _write_csv_rows(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fieldnames})


def _fmt_float(x, digits=2):
    if x is None:
        return ""
    try:
        return f"{float(x):.{digits}f}"
    except (TypeError, ValueError):
        return ""


def upsert_variant_performance(csv_path, target_date, combo_results):
    """
    combo_results: list of dicts produced by run_one_combo (with `summary` and `variants`).
    Idempotent — replaces all rows for any (date, combo_id) seen this run.
    """
    existing = _read_csv_rows(csv_path, VARIANT_PERFORMANCE_COLS)
    seen_keys = {(target_date, c["combo_id"]) for c in combo_results}
    kept = [r for r in existing if (r.get("date"), r.get("combo_id")) not in seen_keys]

    new_rows = []
    for c in combo_results:
        s = c["summary"]
        v = c["variants"]
        new_rows.append({
            "date": target_date,
            "context_variant": v.get("context", ""),
            "brief_variant": v.get("brief", ""),
            "research_variant": v.get("research", ""),
            "track_a_picks": s["track_a"]["tickers"],
            "track_a_avg_pnl": _fmt_float(s["track_a"]["avg_pnl"]),
            "track_a_avg_pnl_905": _fmt_float(s["track_a"].get("avg_pnl_905")),
            "track_a_catchable_count": s["track_a"]["catchable_count"],
            "track_b_picks": s["track_b"]["tickers"],
            "track_b_avg_pnl": _fmt_float(s["track_b"]["avg_pnl"]),
            "track_b_avg_pnl_905": _fmt_float(s["track_b"].get("avg_pnl_905")),
            "track_b_catchable_count": s["track_b"]["catchable_count"],
            "combo_id": c["combo_id"],
        })

    rows = kept + new_rows
    rows.sort(key=lambda r: (r.get("date", ""), r.get("combo_id", "")))
    _write_csv_rows(csv_path, VARIANT_PERFORMANCE_COLS, rows)
    return len(new_rows)


def upsert_market_history(csv_path, target_date, kospi, kosdaq, regime, news_summary, foreign_flow_b_krw):
    """One row per date. Replaces existing row for `target_date`."""
    existing = _read_csv_rows(csv_path, MARKET_HISTORY_COLS)
    kept = [r for r in existing if r.get("date") != target_date]

    new_row = {
        "date": target_date,
        "kospi_open": _fmt_float((kospi or {}).get("open")),
        "kospi_close": _fmt_float((kospi or {}).get("close")),
        "kospi_change_pct": _fmt_float((kospi or {}).get("change_pct")),
        "kosdaq_open": _fmt_float((kosdaq or {}).get("open")),
        "kosdaq_close": _fmt_float((kosdaq or {}).get("close")),
        "kosdaq_change_pct": _fmt_float((kosdaq or {}).get("change_pct")),
        "regime_label": regime or "",
        "major_news_summary": news_summary or "",
        "foreign_net_flow_billion_krw": _fmt_float(foreign_flow_b_krw, digits=1),
    }
    rows = kept + [new_row]
    rows.sort(key=lambda r: r.get("date", ""))
    _write_csv_rows(csv_path, MARKET_HISTORY_COLS, rows)


# ============================================================
# Context parsing — regime label, news summary, foreign net flow
# ============================================================

REGIME_RE = re.compile(r"Regime\s*[:\-]\s*([^\n]+)", re.IGNORECASE)


def extract_regime_label(context_text):
    """
    Pull just the regime category word from the context briefing.
    Examples:
      "Regime: panic / continuation" → "panic"
      "Regime: Panic / 변동성 확대 ..." → "Panic"
    Returns "" if not found.
    """
    if not context_text:
        return ""
    m = REGIME_RE.search(context_text)
    if not m:
        return ""
    raw = m.group(1).strip()
    raw = re.sub(r"^[\*\s\[]+|[\*\s\]]+$", "", raw)
    # Cut at the first separator that typically introduces explanation
    cut = re.split(r"[,/\-—]| \(|\.\s", raw, maxsplit=1)[0]
    return cut.strip()[:60]


def _strip_markdown(text):
    """Remove markdown emphasis/heading/bullet markers WITHOUT eating internal hyphens."""
    cleaned = re.sub(r"^[\s\-*>+#]+", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"[*_`]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def extract_news_summary(context_text):
    """One-line summary of the day's biggest news. Heuristic: line right after 'Key events:'."""
    if not context_text:
        return ""
    m = re.search(r"Key events\s*[:\-]\s*([^\n]*(?:\n[^\n]*){0,3})", context_text, re.IGNORECASE)
    if m:
        chunk = m.group(1).strip()
    else:
        m2 = re.search(r"Yesterday recap\s*[:\-]\s*([^\n]*(?:\n[^\n]*){0,5})", context_text, re.IGNORECASE)
        chunk = m2.group(1).strip() if m2 else context_text.strip()

    return _strip_markdown(chunk)[:300]


_NUM_RE = r"([+-]?\d+(?:[\.,]\d+)?)"
FOREIGN_TRILLION_RE = re.compile(r"외국인[^\n]{0,40}?" + _NUM_RE + r"\s*조원", re.UNICODE)
FOREIGN_BILLION_RE = re.compile(r"외국인[^\n]{0,40}?" + _NUM_RE + r"\s*억원", re.UNICODE)
DIRECTION_NEG_RE = re.compile(r"외국인[^\n]{0,80}?(순매도|매도)", re.UNICODE)
DIRECTION_POS_RE = re.compile(r"외국인[^\n]{0,80}?(순매수|매수)", re.UNICODE)


def extract_foreign_net_flow(context_text):
    """
    Returns foreign net flow in billion KRW (10억원 단위).
    Negative = net selling, positive = net buying. Returns None if unclear.

    Conversions: 1조원 = 1000 billion KRW; 1억원 = 0.1 billion KRW.
    """
    if not context_text:
        return None

    def _to_float(s):
        return float(s.replace(",", ""))

    sign = 0
    if DIRECTION_NEG_RE.search(context_text):
        sign = -1
    elif DIRECTION_POS_RE.search(context_text):
        sign = 1

    m = FOREIGN_TRILLION_RE.search(context_text)
    if m:
        amt = _to_float(m.group(1))
        magnitude = abs(amt) * 1000.0
        if sign == 0:
            sign = -1 if amt < 0 else (1 if amt > 0 else -1)
        return sign * magnitude

    m = FOREIGN_BILLION_RE.search(context_text)
    if m:
        amt = _to_float(m.group(1))
        magnitude = abs(amt) * 0.1
        if sign == 0:
            sign = -1 if amt < 0 else (1 if amt > 0 else -1)
        return sign * magnitude

    return None


def load_first_context(target_date_str):
    """Pick the lexically first available context file for this date (any variant)."""
    folder = _date_folder(target_date_str)
    if not folder.is_dir():
        return ""
    candidates = sorted(folder.glob(f"{target_date_str}-context-*.txt")) + \
                 sorted(folder.glob(f"{target_date_str}-context.txt"))
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if text.strip():
            return text
    return ""


# ============================================================
# Improvement.md stub generator
# ============================================================

IMPROVEMENT_TEMPLATE = """# Improvement Notes — {date}

## Losers — why agent picked them
(Reference picks.json reasoning fields for each SL/HOLD-loss pick)

## Best entry timing
(Where best entry ≠ open, explain why)

## Top 30 winners we missed
(Stocks in top 30 not in our picks — why agent didn't catch them)

## Other observations
(Free-form)
"""


def write_improvement_stub(target_date_str, output_dir):
    """Write {date}-improvement.md if it doesn't already exist (don't overwrite human notes)."""
    path = output_dir / f"{target_date_str}-improvement.md"
    if path.exists():
        print(f"  Improvement notes already exist at {path} (preserving)", file=sys.stderr)
        return path
    path.write_text(IMPROVEMENT_TEMPLATE.format(date=target_date_str), encoding="utf-8")
    print(f"  Wrote improvement stub to {path}", file=sys.stderr)
    return path


# ============================================================
# Main
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--large", default=None, help="Comma-separated large/mega-cap tickers (overrides pipeline; runs as single 'manual' combo)")
    parser.add_argument("--mid", default=None, help="Comma-separated mid-cap tickers (overrides pipeline; runs as single 'manual' combo)")
    parser.add_argument("--skip-top30", action="store_true")
    parser.add_argument("--skip-minute", action="store_true")
    return parser.parse_args()


def _resolve_combos(args, target_date_str):
    """
    Returns list of combo dicts: [{"combo_id", "track_a", "track_b", "variants", "names"}, ...]

    --large / --mid override and produce a single "manual" combo.
    Otherwise, discover all {date}-picks-*.json (and legacy {date}-picks.json).
    """
    if args.large or args.mid:
        if not (args.large and args.mid):
            print("\nERROR: --large and --mid must be used together.", file=sys.stderr)
            sys.exit(1)
        return [{
            "combo_id": "manual",
            "track_a": [t.strip() for t in args.large.split(",")],
            "track_b": [t.strip() for t in args.mid.split(",")],
            "variants": {"context": "manual", "brief": "manual", "research": "manual"},
            "names": {},
        }]

    found = discover_picks_files(target_date_str)
    if not found:
        print(f"\nERROR: No picks files found for {target_date_str}.", file=sys.stderr)
        print(f"  Expected one or more of: {target_date_str}/{target_date_str}-picks-*.json", file=sys.stderr)
        print(f"  Either run pre-pipeline.py first, or pass --large t1,... --mid t1,...", file=sys.stderr)
        sys.exit(1)

    combos = []
    for f in found:
        ta, tb, names = picks_to_track_lists(f["data"])
        combos.append({
            "combo_id": f["combo_id"],
            "track_a": ta,
            "track_b": tb,
            "variants": f["variants"],
            "names": names,
            "source_path": f["path"],
        })
    return combos


def _flush_summary_buffer(output_dir, target_date_str):
    """Write captured summary buffer to disk and clear it."""
    summary_path = output_dir / f"{target_date_str}-summary.txt"
    summary_path.write_text("\n".join(_SUMMARY_BUFFER))
    return summary_path


def main():
    args = parse_args()

    if args.date:
        target_date_str = args.date
    else:
        target_date_str = datetime.now().strftime("%Y-%m-%d")

    target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
    prev_date_str = (target_dt - timedelta(days=7)).strftime("%Y-%m-%d")

    output_dir = _date_folder(target_date_str)
    output_dir.mkdir(parents=True, exist_ok=True)

    combos = _resolve_combos(args, target_date_str)

    # Aggregate ticker_names across all combos (used by get_name_and_market cache)
    for combo in combos:
        TICKER_NAMES.update(combo.get("names") or {})

    print(f"=== Collecting data for {target_date_str} ===", file=sys.stderr)
    print(f"  Discovered {len(combos)} combination(s):", file=sys.stderr)
    for c in combos:
        print(f"    - {c['combo_id']}: A={c['track_a']} B={c['track_b']}", file=sys.stderr)

    # Pre-fetch shared market overview (once)
    print("\nFetching market indices...", file=sys.stderr)
    kospi = get_index("KOSPI", target_date_str, prev_date_str)
    kosdaq = get_index("KOSDAQ", target_date_str, prev_date_str)
    usdkrw = get_usdkrw(target_date_str, prev_date_str)

    # Pre-fetch top 30 once (shared across combos)
    if args.skip_top30:
        print("Skipping top 30 fetch", file=sys.stderr)
        top_30 = []
    else:
        print("Fetching top 30 intraday movers...", file=sys.stderr)
        top_30 = fetch_top_30_intraday(target_date_str, prev_date_str, skip_minute=args.skip_minute)
    top_30_tickers = {t["ticker"]: t["rank"] for t in top_30}

    # Per-ticker fetch cache (process_pick is the expensive call). Many combos likely overlap.
    pick_cache = {}

    def get_pick(ticker, cap_tier):
        key = (ticker, cap_tier)
        if key not in pick_cache:
            pick_cache[key] = process_pick(ticker, cap_tier, target_date_str, prev_date_str, args.skip_minute)
        # Return a shallow copy so per-combo top_30_rank annotation doesn't leak
        return dict(pick_cache[key])

    # Print top-of-day banner once
    out(f"\n\n{'=' * 90}")
    out(f"  DAILY SUMMARY — {target_date_str}  (TP={TP_PCT}%, SL={SL_PCT}%)")
    out(f"{'=' * 90}")
    if kospi and kospi.get("change_pct") is not None:
        out(f"  KOSPI:  {kospi['close']:.2f}  ({kospi['change_pct']:+.2f}%)")
    if kosdaq and kosdaq.get("change_pct") is not None:
        out(f"  KOSDAQ: {kosdaq['close']:.2f}  ({kosdaq['change_pct']:+.2f}%)")
    out(f"  Combos: {len(combos)}")

    # Process each combo
    combo_results = []
    all_market_picks = {}  # ticker -> pick dict (for the JSON dump; first occurrence wins)
    for c in combos:
        combo_id = c["combo_id"]
        print(f"\nProcessing combo: {combo_id}", file=sys.stderr)

        track_a_data = []
        for i, ticker in enumerate(c["track_a"], 1):
            print(f"  [{combo_id}][A {i}/{len(c['track_a'])}] {ticker}", file=sys.stderr)
            track_a_data.append(get_pick(ticker, "large/mega"))

        track_b_data = []
        for i, ticker in enumerate(c["track_b"], 1):
            print(f"  [{combo_id}][B {i}/{len(c['track_b'])}] {ticker}", file=sys.stderr)
            track_b_data.append(get_pick(ticker, "mid"))

        for pick in track_a_data + track_b_data:
            if pick["ticker"] in top_30_tickers:
                pick["in_top_30"] = True
                pick["top_30_rank"] = top_30_tickers[pick["ticker"]]
            all_market_picks.setdefault(pick["ticker"], pick)

        out(f"\n\n{'#' * 90}")
        out(f"  COMBO: {combo_id}")
        out(f"{'#' * 90}")
        print_pick_table(track_a_data, f"TRACK A — LARGE/MEGA CAP  [{combo_id}]")
        print_pick_table(track_b_data, f"TRACK B — MID CAP  [{combo_id}]")

        summary = compute_combo_summary(track_a_data, track_b_data)
        combo_results.append({
            "combo_id": combo_id,
            "variants": c["variants"],
            "track_a_data": track_a_data,
            "track_b_data": track_b_data,
            "summary": summary,
        })

    if top_30:
        print_top30_table(top_30)
        print_pick_top30_overlap(combo_results, top_30)

    # Save shared market_data JSON (used to live alongside the legacy single picks)
    market_output = {
        "date": target_date_str,
        "tp_pct": TP_PCT,
        "sl_pct": SL_PCT,
        "market_overview": {
            "kospi": kospi or {"open": None, "close": None, "change_pct": None, "high": None, "low": None},
            "kosdaq": kosdaq or {"open": None, "close": None, "change_pct": None, "high": None, "low": None},
            "usdkrw": usdkrw or {"open": None, "close": None, "high": None},
        },
        "top_30_movers": top_30,
        "combos": [
            {
                "combo_id": cr["combo_id"],
                "variants": cr["variants"],
                "track_a": cr["track_a_data"],
                "track_b": cr["track_b_data"],
                "summary": cr["summary"],
            }
            for cr in combo_results
        ],
    }
    market_json_path = output_dir / f"market_data_{target_date_str}.json"
    market_json_path.write_text(json.dumps(market_output, ensure_ascii=False, indent=2))

    summary_path = _flush_summary_buffer(output_dir, target_date_str)

    # Append/update root-level CSVs
    perf_csv = DATA_DIR / "variant_performance.csv"
    n_perf = upsert_variant_performance(perf_csv, target_date_str, combo_results)
    print(f"\n  variant_performance.csv: wrote {n_perf} row(s)", file=sys.stderr)

    market_csv = DATA_DIR / "market_history.csv"
    context_text = load_first_context(target_date_str)
    regime = extract_regime_label(context_text)
    news_summary = extract_news_summary(context_text)
    foreign_flow = extract_foreign_net_flow(context_text)
    upsert_market_history(market_csv, target_date_str, kospi, kosdaq, regime, news_summary, foreign_flow)
    print(f"  market_history.csv: regime='{regime}', foreign_flow={foreign_flow}", file=sys.stderr)

    # Improvement.md stub
    write_improvement_stub(target_date_str, output_dir)

    # Per-combo CLI summary — entry-timing variants (09:00 vs 09:05 buy) shown side-by-side.
    print(f"\n{'=' * 100}")
    print(f"PER-COMBO PERFORMANCE — {target_date_str}")
    print(f"  09:00 = blind market buy at open (current default).")
    print(f"  09:05 = DEFER if first_5min ≤ −2.5%, else buy at 09:05 open. DEFER counted as 0.0%% P&L.")
    print(f"{'=' * 100}")
    print(f"{'combo_id':<14}  {'entry':<6} {'A avg':<14} {'A defer':<8} {'A catch':<8} "
          f"{'B avg':<14} {'B defer':<8} {'B catch':<8}")
    print(f"{'-' * 14}  {'-' * 6} {'-' * 14} {'-' * 8} {'-' * 8} {'-' * 14} {'-' * 8} {'-' * 8}")
    for cr in combo_results:
        s = cr["summary"]
        ta, tb = s["track_a"], s["track_b"]
        def fmt(v): return f"{v:+.2f}%" if v is not None else "-"
        # 09:00 row — DEFER column blank (rule doesn't apply at 09:00)
        print(f"{cr['combo_id']:<14}  {'09:00':<6} {fmt(ta['avg_pnl_900']):<14} {'-':<8} "
              f"{ta['catchable_count']}/{ta['n']:<6} {fmt(tb['avg_pnl_900']):<14} {'-':<8} "
              f"{tb['catchable_count']}/{tb['n']:<6}")
        # 09:05 row (only if data exists)
        if ta.get('avg_pnl_905') is not None or tb.get('avg_pnl_905') is not None:
            delta_a = (ta['avg_pnl_905'] - ta['avg_pnl_900']) if (ta.get('avg_pnl_905') is not None and ta.get('avg_pnl_900') is not None) else None
            delta_b = (tb['avg_pnl_905'] - tb['avg_pnl_900']) if (tb.get('avg_pnl_905') is not None and tb.get('avg_pnl_900') is not None) else None
            d_a = f" ({delta_a:+.2f}p)" if delta_a is not None else ""
            d_b = f" ({delta_b:+.2f}p)" if delta_b is not None else ""
            def_a = f"{ta.get('deferred_905', 0)}/{ta['n']}"
            def_b = f"{tb.get('deferred_905', 0)}/{tb['n']}"
            print(f"{'':<14}  {'09:05':<6} {fmt(ta.get('avg_pnl_905')) + d_a:<14} {def_a:<8} "
                  f"{'':<8} {fmt(tb.get('avg_pnl_905')) + d_b:<14} {def_b:<8}")

    print(f"\n✓ Saved market data to {market_json_path}")
    print(f"✓ Saved summary to {summary_path}")
    print(f"✓ Updated {perf_csv.name} and {market_csv.name}")


if __name__ == "__main__":
    main()