"""
Binance data fetcher — async OHLCV retrieval for top 100 USDT pairs.
"""
import asyncio
import logging
from typing import Optional

import aiohttp
import pandas as pd

from bw_scanner.config import (
    BINANCE_BASE_URL,
    FETCH_BATCH_DELAY,
    FETCH_BATCH_SIZE,
    FETCH_RETRY_COUNT,
    INTERVAL,
    LOOKBACK_BARS,
    STABLE_BLACKLIST,
    TOP_N_TOKENS,
)

logger = logging.getLogger(__name__)


async def get_top_100_symbols(session: aiohttp.ClientSession) -> list[str]:
    """Return top TOP_N_TOKENS USDT symbols by 24h quote volume, excluding stablecoins."""
    url = f"{BINANCE_BASE_URL}/api/v3/ticker/24hr"
    async with session.get(url) as resp:
        resp.raise_for_status()
        tickers = await resp.json()

    filtered = [
        t for t in tickers
        if t["symbol"].endswith("USDT")
        and not any(t["symbol"].startswith(s) for s in STABLE_BLACKLIST)
    ]
    filtered.sort(key=lambda t: float(t["quoteVolume"]), reverse=True)
    return [t["symbol"] for t in filtered[:TOP_N_TOKENS]]


async def _fetch_ohlcv_once(
    session: aiohttp.ClientSession,
    symbol: str,
    interval: str = INTERVAL,
    limit: int = LOOKBACK_BARS,
) -> Optional[pd.DataFrame]:
    """Fetch raw OHLCV for one symbol. Returns None on failure."""
    url = f"{BINANCE_BASE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            raw = await resp.json()
    except Exception as exc:
        logger.warning("Fetch failed for %s: %s", symbol, exc)
        return None

    if not raw:
        logger.warning("Empty klines response for %s", symbol)
        return None

    df = pd.DataFrame(
        raw,
        columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades",
            "taker_buy_base", "taker_buy_quote", "ignore",
        ],
    )
    df = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    df[["open", "high", "low", "close", "volume"]] = df[
        ["open", "high", "low", "close", "volume"]
    ].astype(float)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df.reset_index(drop=True, inplace=True)

    # Drop the last (in-progress) bar — only use closed bars
    return df.iloc[:-1].copy()


async def fetch_ohlcv(
    session: aiohttp.ClientSession,
    symbol: str,
    interval: str = INTERVAL,
    limit: int = LOOKBACK_BARS,
) -> Optional[pd.DataFrame]:
    """Fetch OHLCV with retries and exponential backoff."""
    for attempt in range(FETCH_RETRY_COUNT):
        df = await _fetch_ohlcv_once(session, symbol, interval, limit)
        if df is not None:
            return df
        wait = 2 ** attempt  # 1s, 2s, 4s
        logger.info("Retrying %s in %ss (attempt %d)", symbol, wait, attempt + 1)
        await asyncio.sleep(wait)

    logger.error("Skipping %s after %d retries", symbol, FETCH_RETRY_COUNT)
    return None


async def fetch_all(symbols: list[str]) -> dict[str, pd.DataFrame]:
    """
    Fetch OHLCV for all symbols in batches to respect Binance rate limits.
    Returns a dict of symbol -> DataFrame (failed symbols are omitted).
    """
    results: dict[str, pd.DataFrame] = {}

    async with aiohttp.ClientSession() as session:
        for batch_start in range(0, len(symbols), FETCH_BATCH_SIZE):
            batch = symbols[batch_start: batch_start + FETCH_BATCH_SIZE]
            tasks = [fetch_ohlcv(session, sym) for sym in batch]
            batch_results = await asyncio.gather(*tasks)

            for sym, df in zip(batch, batch_results):
                if df is not None and len(df) >= 50:
                    results[sym] = df
                elif df is not None:
                    logger.warning("%s has only %d bars — skipping", sym, len(df))

            if batch_start + FETCH_BATCH_SIZE < len(symbols):
                await asyncio.sleep(FETCH_BATCH_DELAY)

    logger.info("Fetched data for %d/%d symbols", len(results), len(symbols))
    return results


async def get_market_data() -> dict[str, pd.DataFrame]:
    """Top-level entry point: discover symbols then fetch all OHLCV data."""
    async with aiohttp.ClientSession() as session:
        symbols = await get_top_100_symbols(session)
    logger.info("Top %d symbols by volume: %s", len(symbols), symbols[:5])
    return await fetch_all(symbols)
