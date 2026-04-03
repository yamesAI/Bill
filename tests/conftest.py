"""
Shared pytest fixtures that generate synthetic OHLCV DataFrames
with known Bill Williams patterns for deterministic unit testing.
"""
import numpy as np
import pandas as pd
import pytest


def _make_df(highs, lows, closes=None, opens=None, n=None) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame from array inputs."""
    highs = np.array(highs, dtype=float)
    lows = np.array(lows, dtype=float)
    n = len(highs)
    closes = closes if closes is not None else (highs + lows) / 2
    opens = opens if opens is not None else (highs + lows) / 2
    closes = np.array(closes, dtype=float)
    opens = np.array(opens, dtype=float)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    return pd.DataFrame({
        "timestamp": timestamps,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": np.ones(n) * 1000.0,
    })


def _flat_ohlcv(n: int, base: float = 100.0, spread: float = 1.0) -> pd.DataFrame:
    """A flat sideways market with small oscillations."""
    highs = base + spread + np.sin(np.linspace(0, 4 * np.pi, n)) * 0.1
    lows = base - spread + np.sin(np.linspace(0, 4 * np.pi, n)) * 0.1
    closes = base + np.sin(np.linspace(0, 4 * np.pi, n)) * 0.05
    return _make_df(highs, lows, closes)


# ── Alligator fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def sleeping_alligator_df():
    """
    200 bars of a perfectly flat market (zero noise).
    All three Alligator lines will converge to the same value — state SLEEPING.
    """
    n = 200
    base = 100.0
    highs = np.full(n, base + 0.001)
    lows = np.full(n, base - 0.001)
    closes = np.full(n, base)
    return _make_df(highs, lows, closes)


@pytest.fixture
def bullish_trending_df():
    """
    200 bars of a strong uptrend.
    Alligator lines should be bullishly ordered: lips > teeth > jaw.
    """
    n = 200
    base = np.linspace(80, 200, n)
    noise = np.random.default_rng(42).normal(0, 0.3, n)
    closes = base + noise
    highs = closes + 1.5
    lows = closes - 1.5
    return _make_df(highs, lows, closes)


# ── Fractal fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def fractal_buy_df():
    """
    100 bars ending with a clear 5-bar DOWN fractal pattern at bar 97
    (bar[2] = index 97 has the lowest low of its 5-bar window).
    """
    n = 100
    lows = np.ones(n) * 100.0
    highs = np.ones(n) * 101.0
    # Create a down fractal at signal bar 97 (confirmed at bar 99)
    lows[95] = 99.5
    lows[96] = 99.3
    lows[97] = 98.0   # signal bar — lowest
    lows[98] = 99.3
    lows[99] = 99.5
    closes = (highs + lows) / 2
    return _make_df(highs, lows, closes)


@pytest.fixture
def fractal_unconfirmed_df():
    """
    100 bars where the potential down fractal signal bar is at index 98
    (only one bar has appeared after it — not yet confirmed).
    """
    n = 100
    lows = np.ones(n) * 100.0
    highs = np.ones(n) * 101.0
    # Down fractal at index 98 — bar 99 exists but bar 100 does not
    lows[96] = 99.5
    lows[97] = 99.3
    lows[98] = 98.0   # signal bar — but only bar 99 follows (not confirmed yet)
    lows[99] = 99.3
    closes = (highs + lows) / 2
    return _make_df(highs, lows, closes)


# ── AO fixtures ───────────────────────────────────────────────────────────────

def _make_ao_saucer_df(above_zero: bool = True) -> pd.DataFrame:
    """
    Build ~150-bar OHLCV where the last 3 AO bars form a Saucer pattern.
    above_zero=True  → buy saucer (AO above zero, pattern: red, red, green)
    above_zero=False → sell saucer (AO below zero, pattern: green, green, red)
    """
    n = 150
    rng = np.random.default_rng(0)

    if above_zero:
        # Rising midpoints ensure AO stays positive; dip then recover for saucer
        mid = 100 + np.linspace(0, 5, n) + rng.normal(0, 0.05, n)
        # Force the last 3 midpoint SMA5 values to create saucer:
        # red bar: mid[n-3] slightly below mid[n-4]
        # red bar: mid[n-2] slightly below mid[n-3]
        # green bar: mid[n-1] above mid[n-2]
        mid[-3] -= 0.3
        mid[-2] -= 0.1
        mid[-1] += 0.5
    else:
        # Falling midpoints ensure AO stays negative
        mid = 100 - np.linspace(0, 5, n) + rng.normal(0, 0.05, n)
        # green, green, red saucer sell
        mid[-3] += 0.3
        mid[-2] += 0.1
        mid[-1] -= 0.5

    highs = mid + 0.5
    lows = mid - 0.5
    closes = mid.copy()
    return _make_df(highs, lows, closes)


@pytest.fixture
def ao_saucer_buy_df():
    return _make_ao_saucer_df(above_zero=True)


@pytest.fixture
def ao_saucer_sell_df():
    return _make_ao_saucer_df(above_zero=False)


@pytest.fixture
def ao_zero_cross_buy_df():
    """
    150-bar OHLCV engineered so AO is exactly negative on bar[-2] and
    positive on bar[-1] (zero cross on final bar).

    Strategy:
      - Bars 0..148: steady decline 150 → 0, making AO deeply negative.
      - Bar 149: large spike to 300, so SMA5[-1] jumps well above SMA34[-1].
        AO goes from negative to positive in one bar → zero cross.
    """
    n = 150
    mid = np.linspace(150, 0, n - 1).tolist() + [300.0]
    mid = np.array(mid)
    highs = mid + 0.5
    lows = mid - 0.5
    closes = mid.copy()
    return _make_df(highs, lows, closes)


@pytest.fixture
def ao_twin_peaks_buy_df():
    """
    150-bar OHLCV where AO is below zero and shows two down-peaks,
    with the 2nd peak higher (less negative) — triggers Twin Peaks buy.
    """
    n = 150
    rng = np.random.default_rng(1)
    # Downtrend for AO to stay below zero, but with two dip-recovery patterns
    base = np.linspace(110, 98, n) + rng.normal(0, 0.1, n)
    # Inject two valleys with the 2nd less deep
    valley1_center = n - 60
    valley2_center = n - 20
    for i in range(n):
        base[i] -= 3 * np.exp(-((i - valley1_center) ** 2) / 30)
        base[i] -= 1.5 * np.exp(-((i - valley2_center) ** 2) / 20)
    highs = base + 0.5
    lows = base - 0.5
    closes = base.copy()
    return _make_df(highs, lows, closes)


# ── AC fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def ac_buy_above_zero_df():
    """
    150-bar uptrend where AC ends above zero with 2 consecutive green bars.
    """
    n = 150
    rng = np.random.default_rng(2)
    mid = 100 + np.linspace(0, 10, n) + rng.normal(0, 0.1, n)
    # Ensure last 2 bars accelerate upward
    mid[-2] += 0.2
    mid[-1] += 0.4
    highs = mid + 0.5
    lows = mid - 0.5
    return _make_df(highs, lows, mid.copy())


@pytest.fixture
def ac_buy_red_bar_df():
    """
    150-bar df where the last AC bar is red — BUY signal must be blocked.
    """
    n = 150
    rng = np.random.default_rng(3)
    mid = 100 + np.linspace(0, 5, n) + rng.normal(0, 0.1, n)
    # Force last bar to decelerate (red AC)
    mid[-1] -= 1.0
    highs = mid + 0.5
    lows = mid - 0.5
    return _make_df(highs, lows, mid.copy())


# ── Zone fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def zone_exit_long_df():
    """
    Provides color lists where the last 5 zones are all RED (exit signal for LONG).
    Not a DataFrame — returns pre-built color lists.
    """
    # Both AO and AC red for last 5 bars
    ao_colors = ["green"] * 10 + ["red"] * 5
    ac_colors = ["green"] * 10 + ["red"] * 5
    return ao_colors, ac_colors
