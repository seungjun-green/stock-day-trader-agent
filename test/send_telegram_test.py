#!/usr/bin/env python3
"""Send a real Telegram test message using the automation Telegram helper."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from automate.env_loader import load_dotenv
from automate.telegram import send_message


def main() -> int:
    load_dotenv()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = (
        "[TEST] Automation test message\n\n"
        f"Time: {now}\n"
        "If you received this, TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID are working."
    )
    ok = send_message(text, parse_mode="")
    print("telegram_send=ok" if ok else "telegram_send=failed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
