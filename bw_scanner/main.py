"""
Entry point for the Bill Williams 5D Crypto Scanner.

Usage:
  python -m bw_scanner.main           # Run once (live Binance data, sends alerts)
  python -m bw_scanner.main --dry-run  # Run once, print to console only (no alerts)
"""
import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone

from bw_scanner.config import (
    DISCORD_WEBHOOK_URL,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from bw_scanner.data.fetcher import get_market_data
from bw_scanner.output.formatter import format_report
from bw_scanner.output.notifier import log_to_csv, send_discord, send_telegram
from bw_scanner.signals.score import score_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main_scan(dry_run: bool = False) -> None:
    scan_time = datetime.now(timezone.utc)
    logger.info("BW Scanner starting — %s", scan_time.isoformat())

    # 1. Fetch top 100 symbols + OHLCV data
    data = await get_market_data()
    total_scanned = len(data)
    logger.info("Data fetched for %d symbols", total_scanned)

    # 2. Score all symbols
    signals = score_all(data)
    logger.info(
        "Signals found: %d total (%d HIGH, %d MEDIUM, %d LOW)",
        len(signals),
        sum(1 for s in signals if s.priority == "HIGH"),
        sum(1 for s in signals if s.priority == "MEDIUM"),
        sum(1 for s in signals if s.priority == "LOW"),
    )

    # 3. Format report
    report = format_report(signals, scan_time=scan_time, total_scanned=total_scanned)

    # 4. Output
    if dry_run:
        print(report)
        logger.info("[DRY-RUN] No alerts sent. Signals logged to CSV.")
    else:
        send_telegram(report, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        send_discord(report, DISCORD_WEBHOOK_URL)

    log_to_csv(signals)
    logger.info("Scan complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bill Williams 5D Crypto Scanner")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print report to console without sending alerts",
    )
    args = parser.parse_args()
    asyncio.run(main_scan(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
