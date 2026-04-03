"""
Bill Williams Alligator indicator.

Three smoothed displaced moving averages computed on the midpoint (H+L)/2:
  Jaw   (Blue)  — 13-period SMMA displaced +8 bars
  Teeth (Red)   — 8-period  SMMA displaced +5 bars
  Lips  (Green) — 5-period  SMMA displaced +3 bars
"""
import numpy as np
import pandas as pd

from bw_scanner.config import EATING_THRESHOLD, SLEEPING_THRESHOLD


def smma(series: pd.Series, period: int) -> pd.Series:
    """
    Smoothed Moving Average (Wilder's smoothing).
    First value = SMA of first `period` bars.
    Subsequent: smma[i] = (smma[i-1] * (period - 1) + series[i]) / period
    """
    result = np.full(len(series), np.nan)
    values = series.values

    # Find first index with enough data
    start = period - 1
    if start >= len(values):
        return pd.Series(result, index=series.index)

    # Seed with simple average of first `period` bars
    result[start] = np.mean(values[:period])

    for i in range(start + 1, len(values)):
        result[i] = (result[i - 1] * (period - 1) + values[i]) / period

    return pd.Series(result, index=series.index)


def alligator(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Compute the three Alligator lines.
    Returns (jaw, teeth, lips) — each a pd.Series aligned to df's index.
    NaN values appear where displacement pushes data beyond available history.
    """
    mid = (df["high"] + df["low"]) / 2

    jaw = smma(mid, 13).shift(8)    # Blue  — 13-period SMMA + 8 bars forward
    teeth = smma(mid, 8).shift(5)   # Red   — 8-period SMMA + 5 bars forward
    lips = smma(mid, 5).shift(3)    # Green — 5-period SMMA + 3 bars forward

    return jaw, teeth, lips


def _atr(df: pd.DataFrame, period: int = 14) -> float:
    """Compute the latest ATR value."""
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    tr = np.maximum(
        high[1:] - low[1:],
        np.maximum(
            np.abs(high[1:] - close[:-1]),
            np.abs(low[1:] - close[:-1]),
        ),
    )
    if len(tr) < period:
        return float(np.mean(tr)) if len(tr) > 0 else 1.0

    # Wilder smoothing for ATR
    atr_val = np.mean(tr[:period])
    for v in tr[period:]:
        atr_val = (atr_val * (period - 1) + v) / period
    return float(atr_val)


def alligator_state(
    df: pd.DataFrame,
    jaw: pd.Series,
    teeth: pd.Series,
    lips: pd.Series,
) -> str:
    """
    Classify the current Alligator state based on line spread vs ATR.

    Returns one of:
        'SLEEPING'    — lines intertwined, spread < SLEEPING_THRESHOLD * ATR
        'AWAKENING'   — lines separating, spread between thresholds
        'EATING_BULL' — spread > EATING_THRESHOLD * ATR, lines bullishly ordered
        'EATING_BEAR' — spread > EATING_THRESHOLD * ATR, lines bearishly ordered
        'SATIATED'    — lines were spread but now converging
    """
    # Get current (last valid) values for each line
    j = jaw.dropna()
    t = teeth.dropna()
    lp = lips.dropna()

    if j.empty or t.empty or lp.empty:
        return "SLEEPING"

    j_val = float(j.iloc[-1])
    t_val = float(t.iloc[-1])
    l_val = float(lp.iloc[-1])

    spread = max(j_val, t_val, l_val) - min(j_val, t_val, l_val)
    atr = _atr(df)

    if atr == 0:
        return "SLEEPING"

    ratio = spread / atr

    if ratio < SLEEPING_THRESHOLD:
        return "SLEEPING"

    if ratio > EATING_THRESHOLD:
        # Bullish order: lips > teeth > jaw (momentum accelerating upward)
        if l_val > t_val > j_val:
            return "EATING_BULL"
        # Bearish order: jaw > teeth > lips (momentum accelerating downward)
        if j_val > t_val > l_val:
            return "EATING_BEAR"
        # Lines spread but not cleanly ordered — still awakening/satiated
        return "AWAKENING"

    # Spread is between thresholds — check direction of recent spread change
    # Compare spread at current bar vs. a few bars ago to detect convergence
    lookback = min(5, len(jaw.dropna()) - 1)
    if lookback > 0:
        j_prev = float(jaw.dropna().iloc[-1 - lookback])
        t_prev = float(teeth.dropna().iloc[-1 - lookback])
        l_prev = float(lips.dropna().iloc[-1 - lookback])
        prev_spread = max(j_prev, t_prev, l_prev) - min(j_prev, t_prev, l_prev)
        if spread < prev_spread * 0.85:
            return "SATIATED"

    return "AWAKENING"
