#!/usr/bin/env python3
"""
Daily US stock market data collector — variant matrix edition.

Auto-discovers all data/{date}/{date}-picks-*.json files (one per (context, brief, research)
variant combination produced by pre-pipeline.py), runs the same TP/SL simulation
on each, and emits per-combo tables. Falls back to legacy {date}-picks.json if no
variant-suffixed files are present.

Also appends/updates two CSV files under data/:
  data/variant_performance.csv  — per-(date, combo) P&L summary
  data/market_history.csv       — per-date market overview & regime label

After running, generates a stub data/{date}/{date}-improvement.md template (if not present)
for human review notes.

All timestamps are America/New_York. Regular session 09:30–16:00 ET only (pre/post excluded).

Usage:
    python3 post-pipeline.py
    python3 post-pipeline.py --date 2026-06-09
    python3 post-pipeline.py --large NVDA,AAPL,MSFT,META,AMZN \\
                             --mid PLTR,SOFI,RKLB,IONQ,AFRM
    python3 post-pipeline.py --skip-top30
"""

import sys
import csv
import json
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    import pandas as pd
    import requests
    import yfinance as yf
    from tabulate import tabulate
except ImportError as e:
    print("Missing packages. Install with:")
    print("  pip3 install pandas requests yfinance tabulate")
    print(f"Error: {e}")
    sys.exit(1)


# ============================================================
# Configuration
# ============================================================

TP_PCT = 5.0
SL_PCT = 3.0

# America/New_York regular session (09:30–16:00 ET)
US_MARKET_TZ = "America/New_York"
REG_OPEN_HHMM = "09:30"
REG_CLOSE_HHMM = "16:00"

TICKER_NAMES = {}  # populated from morning pipeline JSON at runtime: ticker -> (name, exchange)

# Always anchor file IO to the script's own folder so the script works from any CWD.
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"


def _date_folder(target_date_str):
    return DATA_DIR / target_date_str

# Reusable HTTP headers for NASDAQ API + Yahoo scraping
_REQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


# ============================================================
# Morning pipeline loader — discovers all picks variants in {date}/
# ============================================================

PICKS_PATTERN_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-picks(?:-([^.]+))?\.json$")


def discover_picks_files(target_date_str):
    """
    Find every picks JSON in the date folder.

    Looks for `{date}-picks-{combo_id}.json` (variant-aware) and falls back to the
    legacy `{date}-picks.json` (treated as combo_id "legacy") if no variant files exist.
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
        t = t.upper()
        track_a.append(t)
        if pick.get("name"):
            names[t] = (pick["name"], pick.get("exchange") or pick.get("market") or "NASDAQ")
    for pick in picks_data.get("track_b_mid", {}).get("final_picks", []):
        t = pick.get("ticker")
        if not t:
            continue
        t = t.upper()
        track_b.append(t)
        if pick.get("name"):
            names[t] = (pick["name"], pick.get("exchange") or pick.get("market") or "NASDAQ")
    return track_a, track_b, names


# ============================================================
# Helpers
# ============================================================

def safe_float(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    try:
        f = float(x)
        if pd.isna(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def safe_int(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def to_yf_symbol(ticker):
    """yfinance uses dashes for class shares (BRK.B → BRK-B)."""
    return ticker.upper().replace(".", "-")


def get_name_and_exchange(ticker):
    """Lookup name + exchange via yfinance Ticker.info (cached in TICKER_NAMES)."""
    if ticker in TICKER_NAMES:
        return TICKER_NAMES[ticker]
    try:
        info = yf.Ticker(to_yf_symbol(ticker)).info or {}
        name = info.get("shortName") or info.get("longName")
        exch = info.get("exchange") or info.get("fullExchangeName") or ""
        # Normalize yfinance exchange codes
        if "NMS" in exch or "NGM" in exch or "NCM" in exch or "NASDAQ" in exch.upper():
            exchange = "NASDAQ"
        elif "NYQ" in exch or "NYSE" in exch.upper():
            exchange = "NYSE"
        elif "ASE" in exch or "AMEX" in exch.upper():
            exchange = "AMEX"
        else:
            exchange = exch or "?"
        if name:
            TICKER_NAMES[ticker] = (name, exchange)
            return (name, exchange)
    except Exception:
        pass
    return (None, None)


def classify_pattern(prev_close, o, h, l, c, suspended=False):
    """
    Intraday shape classifier (open-relative, no daily price limit).
    Codes: V, Λ, ↑, ↓, ~, =, "" (no data)
    """
    if suspended:
        return "H"  # halted
    if None in (o, h, l, c):
        return ""
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
    """Return (pnl_pct, exit_reason). Entry = open (09:30 ET). Uses daily aggregates."""
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
            return -sl, "SL?"
    elif tp_hit:
        return tp, "TP"
    elif sl_hit:
        return -sl, "SL"
    else:
        return o_to_c, "HOLD"


def simulate_tp_sl_at_minute(df_minute, entry_minute_idx=5, tp=TP_PCT, sl=SL_PCT):
    """
    Entry-timing variant of `simulate_tp_sl`. Buys at the OPEN of `entry_minute_idx`-th
    one-minute bar (idx 5 = 09:35:00 ET), then scans forward for TP/SL hits.

    Why: Lets us A/B-compare "blind 09:30 market-buy" against "wait 5 minutes, then buy"
    on the same picks. Over days of data this tells us whether the open-as-distribution
    problem is reducible by deferring entry.

    Returns (pnl_pct, exit_reason, entry_price).
    """
    if df_minute is None or df_minute.empty:
        return None, "no-data", None
    if entry_minute_idx >= len(df_minute):
        return None, "no-data", None

    entry_row = df_minute.iloc[entry_minute_idx]
    entry_price = float(entry_row["Open"])
    if entry_price == 0:
        return None, "no-data", None

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
            return -sl, "SL?", entry_price
        if tp_hit:
            return tp, "TP", entry_price
        if sl_hit:
            return -sl, "SL", entry_price

    if last_close is None:
        return None, "no-data", entry_price
    close_pct = (last_close - entry_price) / entry_price * 100
    return close_pct, "HOLD", entry_price


def assess_purchaseable(first_n_minutes, first_5min_max_pct, minutes_to_5pct, entry_window_minutes):
    """Return short label assessing execution feasibility."""
    if not first_n_minutes:
        return "?"

    first_min_pct = first_n_minutes[0].get("pct_from_open", 0) if first_n_minutes else 0

    if first_min_pct >= 3:
        return "❌ gap"

    if minutes_to_5pct is not None and minutes_to_5pct <= 1:
        return "❌ fast"

    if first_5min_max_pct is not None and first_5min_max_pct >= 5 and minutes_to_5pct is not None and minutes_to_5pct <= 2:
        return "⚠️ tight"

    if entry_window_minutes is not None and entry_window_minutes < 2:
        return "⚠️ narrow"

    return "✅ ok"


# ============================================================
# yfinance data fetchers
# ============================================================

def _filter_regular_session(df):
    """Keep only 09:30–16:00 ET rows. Assumes df.index is tz-aware in America/New_York."""
    if df is None or df.empty:
        return df
    return df.between_time(REG_OPEN_HHMM, REG_CLOSE_HHMM)


def fetch_minute_data(ticker, target_date_str):
    """1-minute bars for the regular US session on target_date."""
    try:
        target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
        start = target_dt.strftime("%Y-%m-%d")
        end = (target_dt + timedelta(days=1)).strftime("%Y-%m-%d")

        df = yf.download(
            to_yf_symbol(ticker), start=start, end=end, interval="1m",
            progress=False, auto_adjust=False, prepost=False,
            threads=False,
        )
        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index = pd.to_datetime(df.index)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert(US_MARKET_TZ)
        else:
            df.index = df.index.tz_convert(US_MARKET_TZ)
        df = df[df.index.strftime("%Y-%m-%d") == target_date_str]
        df = _filter_regular_session(df)
        if df.empty:
            return None
        return df
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
    """For each minute as a hypothetical entry, simulate TP/SL outcome. Return the best,
    along with the momentum trigger that preceded that entry minute."""
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
# Daily fetchers (yfinance)
# ============================================================

def get_stock_ohlcv(ticker, target_date_str, prev_date_str):
    """Daily OHLCV for target_date (and prev close from the row before)."""
    try:
        df = yf.download(
            to_yf_symbol(ticker), start=prev_date_str,
            end=(datetime.strptime(target_date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"),
            interval="1d", progress=False, auto_adjust=False, threads=False,
        )
        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        target_dt = pd.to_datetime(target_date_str)
        if target_dt not in df.index:
            # Halted / non-trading day / data lag
            return {"suspended": True}
        row = df.loc[target_dt]
        idx = df.index.get_loc(target_dt)
        prev_close = safe_float(df.iloc[idx - 1]["Close"]) if idx > 0 else None
        o = safe_float(row.get("Open"))
        c = safe_float(row.get("Close"))
        change_pct = ((c - prev_close) / prev_close * 100) if (c is not None and prev_close) else None
        return {
            "prev_close": prev_close,
            "open": o, "high": safe_float(row.get("High")),
            "low": safe_float(row.get("Low")), "close": c,
            "volume": safe_int(row.get("Volume")),
            "change_pct": change_pct,
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


def get_index(symbol_alias, target_date_str, prev_date_str):
    """
    symbol_alias: "SPY" | "QQQ" | "IWM" | "VIX" — we use ETF proxies where possible
    because yfinance's index endpoints are flaky for some tickers.

    Returns dict with open/high/low/close/change_pct.
    """
    aliases = {
        "SPY": ["SPY", "^GSPC"],
        "QQQ": ["QQQ", "^IXIC", "^NDX"],
        "IWM": ["IWM", "^RUT"],
        "VIX": ["^VIX"],
        "DXY": ["DX-Y.NYB", "UUP"],
    }
    target_dt = pd.to_datetime(target_date_str)
    end_dt = (target_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    for sym in aliases.get(symbol_alias, [symbol_alias]):
        try:
            df = yf.download(sym, start=prev_date_str, end=end_dt,
                             interval="1d", progress=False, auto_adjust=False, threads=False)
            if df is None or df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.index = pd.to_datetime(df.index)
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            if target_dt not in df.index:
                continue
            row = df.loc[target_dt]
            idx = df.index.get_loc(target_dt)
            prev_close = safe_float(df.iloc[idx - 1]["Close"]) if idx > 0 else None
            c = safe_float(row.get("Close"))
            change_pct = ((c - prev_close) / prev_close * 100) if (c is not None and prev_close) else None
            return {
                "symbol": sym,
                "open": safe_float(row.get("Open")),
                "close": c,
                "high": safe_float(row.get("High")),
                "low": safe_float(row.get("Low")),
                "change_pct": change_pct,
            }
        except Exception:
            continue
    return None


# ============================================================
# Top gainers source (NASDAQ API → Yahoo fallback)
# ============================================================

def _fetch_yahoo_gainers(limit=50):
    """
    Scrape Yahoo's predefined gainers screener.
    The previous selector (`data-symbol="..."` attribute) became unreliable in 2026 because
    Yahoo's React layout sprays that attribute across the entire page (related news cards,
    crypto/index widgets, etc.), so it pulls in BTC-USD/META/etc. as noise.
    Fix: scope extraction to inside the gainers `<tbody>` only — that's the actual table.
    """
    url = f"https://finance.yahoo.com/markets/stocks/gainers/?count={limit}"
    out = []
    try:
        resp = requests.get(url, headers=_REQ_HEADERS, timeout=10)
        if resp.status_code != 200:
            return out
        m = re.search(r"<tbody[^>]*>(.+?)</tbody>", resp.text, re.DOTALL)
        if not m:
            return out
        tbody = m.group(1)
        seen = set()
        for sym in re.findall(r'<a[^>]+href="/quote/([A-Z][A-Z0-9.\-]{0,7})', tbody):
            sym = sym.upper()
            if sym in seen:
                continue
            seen.add(sym)
            out.append((sym, "", ""))
            if len(out) >= limit:
                break
    except Exception as e:
        print(f"  Yahoo gainers error: {e}", file=sys.stderr)
    return out


def _fetch_stockanalysis_gainers(limit=50):
    """
    Fallback: scrape stockanalysis.com/markets/gainers/.
    Returns more candidates than Yahoo (often 40+) and includes ICCM-style small caps that
    Yahoo's gainers omits.
    """
    url = "https://stockanalysis.com/markets/gainers/"
    out = []
    try:
        resp = requests.get(url, headers=_REQ_HEADERS, timeout=10)
        if resp.status_code != 200:
            return out
        m = re.search(r"<tbody[^>]*>(.+?)</tbody>", resp.text, re.DOTALL)
        if not m:
            return out
        tbody = m.group(1)
        seen = set()
        for sym in re.findall(r'href="/stocks/([a-zA-Z][a-zA-Z0-9.\-]{0,7})/?"', tbody):
            sym = sym.upper()
            if sym in seen:
                continue
            seen.add(sym)
            out.append((sym, "", ""))
            if len(out) >= limit:
                break
    except Exception as e:
        print(f"  stockanalysis gainers error: {e}", file=sys.stderr)
    return out


def get_top_gainer_candidates(limit=50):
    """
    Try Yahoo first, then stockanalysis.com. (NASDAQ's marketmovers API endpoint went 404
    in 2026 — removed from the fallback chain.)
    Deduplicate, drop ETFs/leveraged where obvious.
    """
    out = _fetch_yahoo_gainers(limit=limit)
    if len(out) < 10:
        # Merge with stockanalysis to fill out the list (or use entirely if Yahoo failed).
        out_set = {s for s, _, _ in out}
        for entry in _fetch_stockanalysis_gainers(limit=limit):
            if entry[0] not in out_set:
                out.append(entry)
                out_set.add(entry[0])

    # Best-effort ETF/leverage filter on symbol (proper screening happens later via market_cap)
    leveraged_suffixes = ("3X", "2X")
    drop_exact = {"SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "TQQQ", "SQQQ", "SOXL",
                  "SOXS", "TZA", "TNA", "UPRO", "SPXU", "FAS", "FAZ", "TMF", "TMV"}
    cleaned = []
    seen = set()
    for sym, name, exch in out:
        if sym in seen:
            continue
        if sym in drop_exact:
            continue
        if any(sym.endswith(s) for s in leveraged_suffixes):
            continue
        cleaned.append((sym, name, exch))
        seen.add(sym)
    return cleaned


def fetch_top_30_intraday(target_date_str, prev_date_str, skip_minute=False):
    print("  Fetching top gainer candidates (NASDAQ / Yahoo)...", file=sys.stderr)
    candidates = get_top_gainer_candidates(limit=80)
    print(f"  Got {len(candidates)} candidates, fetching daily OHLCV...", file=sys.stderr)

    results = []
    target_dt = pd.to_datetime(target_date_str)

    for i, (ticker, name, exch) in enumerate(candidates, 1):
        if i % 25 == 0:
            print(f"    Progress: {i}/{len(candidates)}", file=sys.stderr)
        try:
            data = get_stock_ohlcv(ticker, target_date_str, prev_date_str)
            if data is None or data.get("suspended"):
                continue
            o = data["open"]
            c = data["close"]
            if o is None or o == 0 or c is None:
                continue
            data = enrich_with_open_relative(data)
            results.append({
                "ticker": ticker,
                "name": name or "",
                "exchange": exch or "",
                "prev_close": data["prev_close"],
                "open": o, "high": data["high"], "low": data["low"], "close": c,
                "change_pct": data["change_pct"],
                "open_to_close_pct": data["open_to_close_pct"],
                "open_to_high_pct": data["open_to_high_pct"],
                "open_to_low_pct": data["open_to_low_pct"],
                "volume": data["volume"],
                "pattern": classify_pattern(data["prev_close"], o, data["high"], data["low"], c),
                "high_time": None, "low_time": None, "high_before_low": None,
                "first_n_minutes": [], "entry_window_minutes": None,
                "first_5min_max_pct": None, "first_5min_min_pct": None,
                "minutes_to_3pct": None, "minutes_to_5pct": None,
            })
        except Exception:
            continue

    results.sort(key=lambda x: (x["open_to_close_pct"] or -1e9), reverse=True)
    top_30 = results[:30]
    for rank, item in enumerate(top_30, 1):
        item["rank"] = rank

    if not skip_minute:
        print(f"  Fetching minute data for top 30...", file=sys.stderr)
        for i, item in enumerate(top_30, 1):
            if i % 10 == 0:
                print(f"    Minute progress: {i}/30", file=sys.stderr)
            df_minute = fetch_minute_data(item["ticker"], target_date_str)
            timing = extract_timing(df_minute)
            item.update(timing)
            open_data = extract_open_minutes(df_minute, n=10)
            item.update(open_data)
    return top_30


def process_pick(ticker, cap_tier, target_date_str, prev_date_str, skip_minute):
    """Process one pick — daily + minute + open-minutes + best entry."""
    name, exchange = get_name_and_exchange(ticker)
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
    # Entry-timing variant: 09:35 ET buy P&L ("wait 5 minutes" gate, parallels Korean 09:05).
    entry_905 = {
        "tp_sl_at_905_pnl_pct": None,
        "tp_sl_at_905_reason": None,
        "tp_sl_at_905_entry_price": None,
    }
    if not skip_minute and data and not data.get("suspended"):
        df_minute = fetch_minute_data(ticker, target_date_str)
        timing = extract_timing(df_minute)
        open_data = extract_open_minutes(df_minute, n=10)
        best_entry = compute_best_entry(df_minute)
        best_buy_sell = compute_best_buy_sell(df_minute)
        pnl_905, reason_905, ep_905 = simulate_tp_sl_at_minute(df_minute, entry_minute_idx=5)
        entry_905 = {
            "tp_sl_at_905_pnl_pct": round(pnl_905, 3) if pnl_905 is not None else None,
            "tp_sl_at_905_reason": reason_905,
            "tp_sl_at_905_entry_price": ep_905,
        }

    base = {
        "ticker": ticker, "name": name, "exchange": exchange, "cap_tier": cap_tier,
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
                "open_to_low_pct": None, "volume": None, "pattern": "H",
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

_SUMMARY_BUFFER = []


def out(line=""):
    """Print to stdout AND append to summary buffer."""
    print(line)
    _SUMMARY_BUFFER.append(line)


def fmt_price_usd(p):
    """Format a USD price. Uses $ + 2 decimals; "-" for missing."""
    if p is None:
        return "-"
    try:
        return f"${float(p):,.2f}"
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

    PrevC  = yesterday's close (price)
    Open   = today's open (price)
    OptPT  = intraday high — the highest take-profit level that would have triggered
             if you bought at the open
    OptSL  = intraday low — the lowest level the stock dipped to; a stop placed just
             below this would have survived the day without being stopped out
    Best entry = optimal-PNL entry minute under TP=5%/SL=3% rules + momentum trigger
                 ("x% up/down in last y min") at that entry
    Best buy   = absolute day-low minute + price vs open + momentum trigger preceding it
    Best sell  = absolute day-high minute + price vs open + momentum trigger preceding it
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
        (p.get("name") or "-")[:14],
    ]
    if include_cap:
        row.append(p.get("cap_tier") or "-")
    row.extend([
        fmt_price_usd(p.get("prev_close")),   # PrevC: yesterday's close
        fmt_price_usd(p.get("open")),         # Open:  today's open
        fmt_price_usd(p.get("high")),         # OptPT: intraday high
        fmt_price_usd(p.get("low")),          # OptSL: intraday low
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
        out(f"\n  Average TP/SL P&L (09:30 buy): {avg:+.2f}%  |  Catchable: {catchable_count}/{len(picks)}")

    # 09:35 entry variant — A/B comparison data for the "wait 5 minutes" gate.
    pnls_905 = [p.get("tp_sl_at_905_pnl_pct") for p in picks
                if p.get("tp_sl_at_905_pnl_pct") is not None]
    if pnls_905:
        avg_905 = sum(pnls_905) / len(pnls_905)
        delta = (avg_905 - avg) if pnls else None
        d_str = f"  ({delta:+.2f}%p vs 09:30)" if delta is not None else ""
        out(f"  Average TP/SL P&L (09:35 buy): {avg_905:+.2f}%{d_str}")

    if best_entry_pnls:
        avg_best = sum(best_entry_pnls) / len(best_entry_pnls)
        out(f"  Average TP/SL P&L (best-entry hindsight): {avg_best:+.2f}%")


def print_top30_table(top_30):
    headers = [
        "#", "Ticker", "Name", "Exch",
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
            (p.get("name") or "-")[:14],
            p.get("exchange", "-"),
            fmt_price_usd(p.get("prev_close")),  # PrevC
            fmt_price_usd(p.get("open")),        # Open
            fmt_price_usd(p.get("high")),        # OptPT
            fmt_price_usd(p.get("low")),         # OptSL
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
    def stats(picks):
        pnls = []          # 09:30 ET buy
        pnls_905 = []      # 09:35 ET buy (entry-timing variant)
        catchable = 0
        top30_ranks = []
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
            "avg_pnl": _avg(pnls),                  # alias: 09:30 ET buy
            "avg_pnl_900": _avg(pnls),
            "avg_pnl_905": _avg(pnls_905),
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
    "date",
    "spy_open", "spy_close", "spy_change_pct",
    "qqq_open", "qqq_close", "qqq_change_pct",
    "iwm_open", "iwm_close", "iwm_change_pct",
    "vix_close", "vix_change_pct",
    "regime_label", "major_news_summary",
]


def _read_csv_rows(path, fieldnames):
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [{k: r.get(k, "") for k in fieldnames} for r in reader]


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
    """Idempotent — replaces all rows for any (date, combo_id) seen this run."""
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


def upsert_market_history(csv_path, target_date, spy, qqq, iwm, vix, regime, news_summary):
    """One row per date. Replaces existing row for `target_date`."""
    existing = _read_csv_rows(csv_path, MARKET_HISTORY_COLS)
    kept = [r for r in existing if r.get("date") != target_date]

    new_row = {
        "date": target_date,
        "spy_open": _fmt_float((spy or {}).get("open")),
        "spy_close": _fmt_float((spy or {}).get("close")),
        "spy_change_pct": _fmt_float((spy or {}).get("change_pct")),
        "qqq_open": _fmt_float((qqq or {}).get("open")),
        "qqq_close": _fmt_float((qqq or {}).get("close")),
        "qqq_change_pct": _fmt_float((qqq or {}).get("change_pct")),
        "iwm_open": _fmt_float((iwm or {}).get("open")),
        "iwm_close": _fmt_float((iwm or {}).get("close")),
        "iwm_change_pct": _fmt_float((iwm or {}).get("change_pct")),
        "vix_close": _fmt_float((vix or {}).get("close")),
        "vix_change_pct": _fmt_float((vix or {}).get("change_pct")),
        "regime_label": regime or "",
        "major_news_summary": news_summary or "",
    }
    rows = kept + [new_row]
    rows.sort(key=lambda r: r.get("date", ""))
    _write_csv_rows(csv_path, MARKET_HISTORY_COLS, rows)


# ============================================================
# Context parsing — regime label + news summary
# ============================================================

REGIME_RE = re.compile(r"Regime\s*[:\-]\s*([^\n]+)", re.IGNORECASE)


def extract_regime_label(context_text):
    """Pull the regime category word from the context briefing."""
    if not context_text:
        return ""
    m = REGIME_RE.search(context_text)
    if not m:
        return ""
    raw = m.group(1).strip()
    raw = re.sub(r"^[\*\s\[]+|[\*\s\]]+$", "", raw)
    cut = re.split(r"[,/\-—]| \(|\.\s", raw, maxsplit=1)[0]
    return cut.strip()[:60]


def _strip_markdown(text):
    cleaned = re.sub(r"^[\s\-*>+#]+", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"[*_`]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def extract_news_summary(context_text):
    """One-line summary of the day's biggest news. Heuristic: lines right after 'Key events:'."""
    if not context_text:
        return ""
    m = re.search(r"Key events\s*[:\-]\s*([^\n]*(?:\n[^\n]*){0,3})", context_text, re.IGNORECASE)
    if m:
        chunk = m.group(1).strip()
    else:
        m2 = re.search(r"Yesterday recap\s*[:\-]\s*([^\n]*(?:\n[^\n]*){0,5})", context_text, re.IGNORECASE)
        chunk = m2.group(1).strip() if m2 else context_text.strip()
    return _strip_markdown(chunk)[:300]


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
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (default: today, ET)")
    parser.add_argument("--large", default=None, help="Comma-separated large/mega-cap tickers (overrides pipeline; runs as single 'manual' combo)")
    parser.add_argument("--mid", default=None, help="Comma-separated mid-cap tickers (overrides pipeline; runs as single 'manual' combo)")
    parser.add_argument("--skip-top30", action="store_true")
    parser.add_argument("--skip-minute", action="store_true")
    return parser.parse_args()


def _resolve_combos(args, target_date_str):
    """--large/--mid override; otherwise discover all {date}-picks-*.json."""
    if args.large or args.mid:
        if not (args.large and args.mid):
            print("\nERROR: --large and --mid must be used together.", file=sys.stderr)
            sys.exit(1)
        return [{
            "combo_id": "manual",
            "track_a": [t.strip().upper() for t in args.large.split(",")],
            "track_b": [t.strip().upper() for t in args.mid.split(",")],
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
    prev_date_str = (target_dt - timedelta(days=10)).strftime("%Y-%m-%d")

    output_dir = _date_folder(target_date_str)
    output_dir.mkdir(parents=True, exist_ok=True)

    combos = _resolve_combos(args, target_date_str)

    for combo in combos:
        TICKER_NAMES.update(combo.get("names") or {})

    print(f"=== Collecting US market data for {target_date_str} ===", file=sys.stderr)
    print(f"  Discovered {len(combos)} combination(s):", file=sys.stderr)
    for c in combos:
        print(f"    - {c['combo_id']}: A={c['track_a']} B={c['track_b']}", file=sys.stderr)

    print("\nFetching market indices (SPY/QQQ/IWM/VIX)...", file=sys.stderr)
    spy = get_index("SPY", target_date_str, prev_date_str)
    qqq = get_index("QQQ", target_date_str, prev_date_str)
    iwm = get_index("IWM", target_date_str, prev_date_str)
    vix = get_index("VIX", target_date_str, prev_date_str)

    if args.skip_top30:
        print("Skipping top 30 fetch", file=sys.stderr)
        top_30 = []
    else:
        print("Fetching top 30 intraday gainers...", file=sys.stderr)
        top_30 = fetch_top_30_intraday(target_date_str, prev_date_str, skip_minute=args.skip_minute)
    top_30_tickers = {t["ticker"]: t["rank"] for t in top_30}

    pick_cache = {}

    def get_pick(ticker, cap_tier):
        key = (ticker, cap_tier)
        if key not in pick_cache:
            pick_cache[key] = process_pick(ticker, cap_tier, target_date_str, prev_date_str, args.skip_minute)
        return dict(pick_cache[key])

    out(f"\n\n{'=' * 95}")
    out(f"  US DAILY SUMMARY — {target_date_str}  (TP={TP_PCT}%, SL={SL_PCT}%)")
    out(f"{'=' * 95}")
    if spy and spy.get("change_pct") is not None:
        out(f"  SPY: {spy['close']:.2f}  ({spy['change_pct']:+.2f}%)")
    if qqq and qqq.get("change_pct") is not None:
        out(f"  QQQ: {qqq['close']:.2f}  ({qqq['change_pct']:+.2f}%)")
    if iwm and iwm.get("change_pct") is not None:
        out(f"  IWM: {iwm['close']:.2f}  ({iwm['change_pct']:+.2f}%)")
    if vix and vix.get("close") is not None:
        vix_chg = f" ({vix['change_pct']:+.2f}%)" if vix.get("change_pct") is not None else ""
        out(f"  VIX: {vix['close']:.2f}{vix_chg}")
    out(f"  Combos: {len(combos)}")

    combo_results = []
    all_market_picks = {}
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

        out(f"\n\n{'#' * 95}")
        out(f"  COMBO: {combo_id}")
        out(f"{'#' * 95}")
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

    market_output = {
        "date": target_date_str,
        "market": "US",
        "tp_pct": TP_PCT,
        "sl_pct": SL_PCT,
        "market_overview": {
            "spy": spy or {"open": None, "close": None, "change_pct": None, "high": None, "low": None},
            "qqq": qqq or {"open": None, "close": None, "change_pct": None, "high": None, "low": None},
            "iwm": iwm or {"open": None, "close": None, "change_pct": None, "high": None, "low": None},
            "vix": vix or {"open": None, "close": None, "change_pct": None, "high": None, "low": None},
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

    perf_csv = DATA_DIR / "variant_performance.csv"
    n_perf = upsert_variant_performance(perf_csv, target_date_str, combo_results)
    print(f"\n  variant_performance.csv: wrote {n_perf} row(s)", file=sys.stderr)

    market_csv = DATA_DIR / "market_history.csv"
    context_text = load_first_context(target_date_str)
    regime = extract_regime_label(context_text)
    news_summary = extract_news_summary(context_text)
    upsert_market_history(market_csv, target_date_str, spy, qqq, iwm, vix, regime, news_summary)
    print(f"  market_history.csv: regime='{regime}'", file=sys.stderr)

    write_improvement_stub(target_date_str, output_dir)

    print(f"\n{'=' * 90}")
    print(f"PER-COMBO PERFORMANCE — {target_date_str}")
    print(f"  (09:30 = blind market buy at open. 09:35 = wait 5 minutes, then buy at 09:35 open.)")
    print(f"{'=' * 90}")
    print(f"{'combo_id':<14}  {'entry':<6} {'A avg':<10} {'A catch':<8} {'B avg':<10} {'B catch':<8}")
    print(f"{'-' * 14}  {'-' * 6} {'-' * 10} {'-' * 8} {'-' * 10} {'-' * 8}")
    for cr in combo_results:
        s = cr["summary"]
        ta, tb = s["track_a"], s["track_b"]
        def fmt(v): return f"{v:+.2f}%" if v is not None else "-"
        print(f"{cr['combo_id']:<14}  {'09:30':<6} {fmt(ta['avg_pnl_900']):<10} "
              f"{ta['catchable_count']}/{ta['n']:<6} {fmt(tb['avg_pnl_900']):<10} "
              f"{tb['catchable_count']}/{tb['n']:<6}")
        if ta.get('avg_pnl_905') is not None or tb.get('avg_pnl_905') is not None:
            delta_a = (ta['avg_pnl_905'] - ta['avg_pnl_900']) if (ta.get('avg_pnl_905') is not None and ta.get('avg_pnl_900') is not None) else None
            delta_b = (tb['avg_pnl_905'] - tb['avg_pnl_900']) if (tb.get('avg_pnl_905') is not None and tb.get('avg_pnl_900') is not None) else None
            d_a = f" ({delta_a:+.2f}p)" if delta_a is not None else ""
            d_b = f" ({delta_b:+.2f}p)" if delta_b is not None else ""
            print(f"{'':<14}  {'09:35':<6} {fmt(ta.get('avg_pnl_905')) + d_a:<18} {'':<8} "
                  f"{fmt(tb.get('avg_pnl_905')) + d_b:<18}")

    print(f"\n✓ Saved market data to {market_json_path}")
    print(f"✓ Saved summary to {summary_path}")
    print(f"✓ Updated {perf_csv.name} and {market_csv.name}")


if __name__ == "__main__":
    main()
