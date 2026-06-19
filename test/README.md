# Test Scripts

Small checks for the automation layer. Run from the repository root:

```bash
python3 test/run_all.py
```

This dry-run suite does not call Anthropic, does not commit, and does not send Telegram by default.

To send a real Telegram test message:

```bash
python3 test/send_telegram_test.py
# or
python3 test/run_all.py --telegram
```

Required env vars for Telegram:

```bash
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Useful individual checks:

```bash
python3 test/worker_smoke_test.py
python3 test/report_link_test.py
```
