"""
Entry point for the Bill Williams 5D Crypto Scanner.

Usage:
  python -m bw_scanner.main                   # Live run — fetches Binance data, sends alerts
  python -m bw_scanner.main --dry-run          # Live data, prints to console only (no alerts)
  python -m bw_scanner.main --dry-run --mock   # Offline test — synthetic data, no network needed
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
from bw_scanner.output.formatter import format_report
from bw_scanner.output.notifier import log_to_csv, send_discord, send_telegram
from bw_scanner.signals.score import score_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def _fetch_live() -> dict:
    from bw_scanner.data.fetcher import get_market_data
    return await get_market_data()


def _fetch_mock() -> dict:
    from bw_scanner.data.mock import generate_mock_data
    logger.info("[MOCK] Generating synthetic OHLCV data — no network required")
    return generate_mock_data()


async def main_scan(dry_run: bool = False, mock: bool = False) -> None:
    scan_time = datetime.now(timezone.utc)
    logger.info("BW Scanner starting — %s", scan_time.isoformat())

    # 1. Fetch data
    if mock:
        data = _fetch_mock()
    else:
        try:
            data = await _fetch_live()
        except Exception as exc:
            logger.error(
                "Failed to fetch live data: %s\n"
                "  → Check your internet connection and that api.binance.com is reachable.\n"
                "  → For offline testing run: python -m bw_scanner.main --dry-run --mock",
                exc,
            )
            sys.exit(1)

    total_scanned = len(data)
    logger.info("Data ready for %d symbols", total_scanned)

    # 2. Score
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
        logger.info("[DRY-RUN] No alerts sent.")
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
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use synthetic data instead of live Binance API (no network needed)",
    )
    args = parser.parse_args()

    if args.mock and not args.dry_run:
        parser.error("--mock requires --dry-run")

    asyncio.run(main_scan(dry_run=args.dry_run, mock=args.mock))


if __name__ == "__main__":
    main()
