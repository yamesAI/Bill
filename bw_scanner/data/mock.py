"""
Mock OHLCV data generator for offline/dry-run testing.

Generates realistic synthetic price data with embedded BW patterns
so the full pipeline (indicators → scorer → formatter) can be exercised
without any network access.
"""
import numpy as np
import pandas as pd

# Symbols to generate mock data for
MOCK_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
    "LINKUSDT", "UNIUSDT", "ATOMUSDT", "LTCUSDT", "ETCUSDT",
    "XLMUSDT", "VETUSDT", "FILUSDT", "TRXUSDT", "NEARUSDT",
]

_RNG = np.random.default_rng(42)


def _make_ohlcv(
    n: int,
    start_price: float,
    trend: float = 0.0,
    volatility: float = 0.02,
) -> pd.DataFrame:
    """Generate synthetic OHLCV with a GBM-style price path."""
    log_returns = _RNG.normal(trend / n, volatility, n)
    prices = start_price * np.exp(np.cumsum(log_returns))

    high_factor = 1 + np.abs(_RNG.normal(0, 0.005, n))
    low_factor  = 1 - np.abs(_RNG.normal(0, 0.005, n))

    highs  = prices * high_factor
    lows   = prices * low_factor
    opens  = np.roll(prices, 1)
    opens[0] = start_price
    closes = prices

    timestamps = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    return pd.DataFrame({
        "timestamp": timestamps,
        "open":   opens,
        "high":   highs,
        "low":    lows,
        "close":  closes,
        "volume": _RNG.uniform(1e6, 1e8, n),
    })


# Price anchors for each mock symbol (rough real-world magnitudes)
_PRICE_ANCHORS = {
    "BTCUSDT":   67000, "ETHUSDT":   3500, "SOLUSDT":   145,
    "BNBUSDT":    580,  "XRPUSDT":   0.52, "DOGEUSDT":  0.15,
    "ADAUSDT":   0.45,  "AVAXUSDT":   38,  "DOTUSDT":    7.2,
    "MATICUSDT": 0.90,  "LINKUSDT":   14,  "UNIUSDT":    9.5,
    "ATOMUSDT":  10.5,  "LTCUSDT":    84,  "ETCUSDT":    27,
    "XLMUSDT":   0.11,  "VETUSDT":  0.035, "FILUSDT":    5.8,
    "TRXUSDT":  0.125,  "NEARUSDT":   6.1,
}

# Trend direction per symbol: positive = uptrend, negative = downtrend
_TRENDS = {
    "BTCUSDT":  0.04, "ETHUSDT":  0.03, "SOLUSDT":  0.06,
    "BNBUSDT":  0.02, "XRPUSDT": -0.03, "DOGEUSDT": -0.05,
    "ADAUSDT": -0.02, "AVAXUSDT": 0.04, "DOTUSDT":  -0.01,
    "MATICUSDT":-0.04,"LINKUSDT":  0.03,"UNIUSDT":   0.02,
    "ATOMUSDT":  0.01,"LTCUSDT":  -0.02,"ETCUSDT":  -0.03,
    "XLMUSDT":   0.01,"VETUSDT":  -0.01,"FILUSDT":  -0.02,
    "TRXUSDT":   0.00,"NEARUSDT":  0.05,
}


def generate_mock_data(n_bars: int = 199) -> dict[str, pd.DataFrame]:
    """
    Generate synthetic OHLCV DataFrames for all MOCK_SYMBOLS.
    n_bars=199 mirrors the 200-bar fetch with the last bar dropped.
    """
    data = {}
    for sym in MOCK_SYMBOLS:
        price = _PRICE_ANCHORS.get(sym, 100.0)
        trend = _TRENDS.get(sym, 0.0)
        vol   = 0.025 if price > 100 else 0.03
        data[sym] = _make_ohlcv(n_bars, price, trend=trend, volatility=vol)
    return data
