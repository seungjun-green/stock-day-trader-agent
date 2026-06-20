# Automation — scheduled pipelines + worker agent

Runs **pre-pipeline** and **post-pipeline** automatically on trading days, then a **worker agent** writes `improvement.md`, updates `JOURNEY.md` / `STRATEGY.md`, and sends a **Telegram** daily report.

## Schedule (Asia/Seoul)

| Market | Pre-pipeline | Post-pipeline + worker |
|--------|--------------|------------------------|
| Korean | 08:30 | 16:30 |
| US     | 22:00 | 07:00 |

Edit times in `automate/config.yaml`.

## Setup

```bash
cd "/Users/seungjunlee/stock day trade agent"
pip3 install -r requirements.txt
```

Add to repo root `.env`:

```
ANTHROPIC_API_KEY=...
TELEGRAM_BOT_TOKEN=...   # from @BotFather
TELEGRAM_CHAT_ID=...     # your chat id
```

### Telegram bot

1. Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy token.
2. Start a chat with your bot, send any message.
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` → find `"chat":{"id": ...}`.

## Run

**Daemon (both markets, recommended):**

```bash
python3 automate/scheduler.py
```

Leave this running (Terminal tab, `tmux`, or launchd — see below).

**Manual test:**

```bash
# Force Korean pre for a date
python3 automate/scheduler.py --market korean --once pre --date 2026-06-19

# Force post + worker only
python3 automate/worker.py --market us --date 2026-06-18

# Worker without Telegram
python3 automate/worker.py --market korean --date 2026-06-18 --skip-telegram
```

## What the worker agent does

After post-pipeline succeeds:

1. Validates outputs; **retries post-pipeline up to 3×** if broken.
2. Reads summary, market_data, CSV history, JOURNEY, STRATEGY.
3. Writes / updates:
   - `data/{date}/{date}-improvement.md`
   - `JOURNEY.md` (appends today's section)
   - `STRATEGY.md` (ACTIVE / WATCH / DROP for each combo)
   - `reports/{date}-daily-report.md`
4. Runs the observer agent on its configured cadence, which reviews recent improvement/JOURNEY history for rabbit holes and may update:
   - `OBSERVER_GUIDANCE.md`
   - market prompts/code through the same allowlist
   - `reports/{date}-observer-report.md`
5. Runs `git add`, `git commit`, and `git push` for that market folder.
6. Sends a short Telegram summary plus a link to `reports/{date}-daily-report.md` after push succeeds.

Git sync runs once per completed worker run, so normally once for Korean and once for US on trading days. The VM checkout must be a git repository with push credentials available. Use `--skip-git` for manual worker runs that should not commit/push.

Observer cadence defaults to weekly per market (`observer.interval_days: 7` in `automate/config.yaml`). Set it to `14` for every two weeks. Use `--force-observer` for manual observer runs or `--skip-observer` to disable it for a worker run.

## macOS auto-start (launchd)

```bash
# Edit paths in the plist if your repo path differs, then:
cp automate/launchd/com.stockdaytrade.scheduler.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.stockdaytrade.scheduler.plist
```

Logs: `automate/logs/scheduler.out.log`

## State

`automate/state/korean.json` and `us.json` track last pre/post dates so the same session is not run twice.

To re-run a session, delete the relevant key from the state file or use `--once --date`.

## Trading days

Uses `pandas_market_calendars` (XKRX / NYSE). See `automate/market_calendar.py`.
