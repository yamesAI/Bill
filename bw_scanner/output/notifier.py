"""
Notification channels for the BW Scanner:
  - Telegram Bot API
  - Discord Webhook
  - CSV log for backtesting
"""
import csv
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import requests

from bw_scanner.config import SIGNALS_LOG_PATH
from bw_scanner.signals.score import BWSignal

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
_MAX_TELEGRAM_LEN = 4096  # Telegram message character limit


def send_telegram(
    report_text: str,
    token: str,
    chat_id: str,
    dry_run: bool = False,
) -> bool:
    """
    Send report_text to a Telegram chat via Bot API.
    Splits messages longer than 4096 characters automatically.
    Returns True on success.
    """
    if dry_run:
        logger.info("[DRY-RUN] Telegram message (%d chars)", len(report_text))
        return True

    if not token or not chat_id:
        logger.warning("Telegram credentials not configured — skipping")
        return False

    url = _TELEGRAM_API.format(token=token)
    chunks = [
        report_text[i: i + _MAX_TELEGRAM_LEN]
        for i in range(0, len(report_text), _MAX_TELEGRAM_LEN)
    ]

    success = True
    for chunk in chunks:
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if not resp.ok:
                logger.error("Telegram API error: %s %s", resp.status_code, resp.text[:200])
                success = False
        except Exception as exc:
            logger.error("Telegram send failed: %s", exc)
            success = False

    return success


def send_discord(
    report_text: str,
    webhook_url: str,
    dry_run: bool = False,
) -> bool:
    """
    Send report_text to a Discord channel via webhook.
    Discord message limit is 2000 chars; long messages are split into multiple posts.
    Returns True on success.
    """
    if dry_run:
        logger.info("[DRY-RUN] Discord message (%d chars)", len(report_text))
        return True

    if not webhook_url:
        logger.warning("Discord webhook not configured — skipping")
        return False

    max_len = 1900  # leave headroom for code block markers
    chunks = [
        report_text[i: i + max_len]
        for i in range(0, len(report_text), max_len)
    ]

    success = True
    for chunk in chunks:
        payload = {"content": f"```\n{chunk}\n```"}
        try:
            resp = requests.post(webhook_url, json=payload, timeout=15)
            if resp.status_code not in (200, 204):
                logger.error("Discord webhook error: %s %s", resp.status_code, resp.text[:200])
                success = False
        except Exception as exc:
            logger.error("Discord send failed: %s", exc)
            success = False

    return success


_CSV_FIELDS = [
    "timestamp", "symbol", "direction", "confluence_score", "priority",
    "price", "entry_stop", "alligator_stop", "zone",
    "ao_signal", "ac_signal", "fractal_signal", "first_entry",
    "alligator_state", "zone_exit_warning", "dimensions_active",
]


def log_to_csv(
    signals: list[BWSignal],
    path: Optional[str] = None,
) -> None:
    """
    Append all signals to a CSV log file for later backtesting analysis.
    Creates the file with a header row if it does not exist.
    """
    csv_path = path or SIGNALS_LOG_PATH
    file_exists = os.path.isfile(csv_path)

    try:
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
            if not file_exists:
                writer.writeheader()

            for sig in signals:
                writer.writerow({
                    "timestamp": sig.timestamp.isoformat(),
                    "symbol": sig.symbol,
                    "direction": sig.direction,
                    "confluence_score": sig.confluence_score,
                    "priority": sig.priority,
                    "price": sig.price,
                    "entry_stop": sig.entry_stop,
                    "alligator_stop": sig.alligator_stop,
                    "zone": sig.zone,
                    "ao_signal": sig.ao_signal or "",
                    "ac_signal": sig.ac_signal or "",
                    "fractal_signal": sig.fractal_signal,
                    "first_entry": sig.first_entry,
                    "alligator_state": sig.alligator_state,
                    "zone_exit_warning": sig.zone_exit_warning,
                    "dimensions_active": "|".join(sig.dimensions_active),
                })
        logger.info("Logged %d signals to %s", len(signals), csv_path)
    except Exception as exc:
        logger.error("CSV logging failed: %s", exc)
