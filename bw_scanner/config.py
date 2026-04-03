"""
Configuration settings for the Bill Williams 5D Crypto Scanner.
"""
import os

# Binance API
BINANCE_BASE_URL = "https://api.binance.com"
INTERVAL = "4h"
LOOKBACK_BARS = 200
TOP_N_TOKENS = 100

# Stablecoins to exclude from symbol list
STABLE_BLACKLIST = ["USDC", "BUSD", "TUSD", "DAI", "USDP", "FDUSD", "USDT"]

# Fetch settings
FETCH_BATCH_SIZE = 20
FETCH_BATCH_DELAY = 0.1   # seconds between batches
FETCH_RETRY_COUNT = 3

# Scoring thresholds
HIGH_PRIORITY_SCORE = 4
MEDIUM_PRIORITY_SCORE = 2

# Alligator state ATR multipliers
SLEEPING_THRESHOLD = 0.2   # spread < 0.2 * ATR → sleeping
EATING_THRESHOLD = 1.0     # spread > 1.0 * ATR → eating

# Alert credentials — loaded from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

# Scheduler
SCAN_HOUR_UTC = 6
SCAN_MINUTE = 0
SCHEDULER_TIMEZONE = "UTC"

# Output
SIGNALS_LOG_PATH = "signals_log.csv"
