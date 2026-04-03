"""
APScheduler-based cron scheduler for the BW Scanner.

Runs main_scan() every day at SCAN_HOUR_UTC:SCAN_MINUTE UTC.

Usage:
  python -m bw_scanner.scheduler
  pm2 start bw_scanner/scheduler.py --interpreter python3 --name bw-scanner
"""
import asyncio
import logging
import sys

from apscheduler.schedulers.blocking import BlockingScheduler

from bw_scanner.config import SCAN_HOUR_UTC, SCAN_MINUTE, SCHEDULER_TIMEZONE
from bw_scanner.main import main_scan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def run_scheduled_scan() -> None:
    logger.info("Scheduled scan triggered")
    asyncio.run(main_scan(dry_run=False))


def start_scheduler() -> None:
    scheduler = BlockingScheduler(timezone=SCHEDULER_TIMEZONE)
    scheduler.add_job(
        run_scheduled_scan,
        trigger="cron",
        hour=SCAN_HOUR_UTC,
        minute=SCAN_MINUTE,
        id="bw_daily_scan",
        name="BW 5D Daily Scan",
        misfire_grace_time=300,  # 5-minute grace period if scan fires late
    )
    logger.info(
        "Scheduler started — BW scan runs daily at %02d:%02d %s",
        SCAN_HOUR_UTC,
        SCAN_MINUTE,
        SCHEDULER_TIMEZONE,
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    start_scheduler()
