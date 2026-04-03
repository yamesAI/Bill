"""
Bill Williams Awesome Oscillator (AO).

AO = SMA(midpoint, 5) - SMA(midpoint, 34)
where midpoint = (High + Low) / 2

Bar color:
  Green — current AO value > previous AO value
  Red   — current AO value <= previous AO value

Three BUY signals:
  1. Saucer    — AO above zero; last 3 bars: red, red, green; all 3 above zero
  2. Zero Cross — AO crosses from negative to positive (prev < 0, current >= 0, green bar)
  3. Twin Peaks — AO below zero; two down-peaks with 2nd peak higher (less negative)
                  than 1st; trigger bar green; NO zero crossing between peaks

Three SELL signals (mirror):
  1. Saucer    — AO below zero; last 3 bars: green, green, red; all 3 below zero
  2. Zero Cross — AO crosses from positive to negative
  3. Twin Peaks — AO above zero; two up-peaks with 2nd peak lower; trigger bar red; no cross
"""
import numpy as np
import pandas as pd


def awesome_oscillator(df: pd.DataFrame) -> tuple[pd.Series, list[str]]:
    """
    Compute AO and bar color sequence.

    Returns:
        ao     — pd.Series of AO values (NaN for first 33 bars)
        colors — list of 'green'/'red' strings, same length as ao.
                 Index 0 is always 'red' (no previous bar to compare).
    """
    mid = (df["high"] + df["low"]) / 2
    ao = mid.rolling(5).mean() - mid.rolling(34).mean()

    colors = ["red"]  # no previous for first bar
    ao_vals = ao.values
    for i in range(1, len(ao_vals)):
        if np.isnan(ao_vals[i]) or np.isnan(ao_vals[i - 1]):
            colors.append("red")
        elif ao_vals[i] > ao_vals[i - 1]:
            colors.append("green")
        else:
            colors.append("red")

    return ao, colors


def _find_local_minima(ao_vals: np.ndarray, start: int, end: int) -> list[tuple[int, float]]:
    """Find all local minima within ao_vals[start:end] (exclusive end)."""
    minima = []
    for i in range(start + 1, end - 1):
        if ao_vals[i] < ao_vals[i - 1] and ao_vals[i] < ao_vals[i + 1]:
            minima.append((i, ao_vals[i]))
    return minima


def _find_local_maxima(ao_vals: np.ndarray, start: int, end: int) -> list[tuple[int, float]]:
    """Find all local maxima within ao_vals[start:end] (exclusive end)."""
    maxima = []
    for i in range(start + 1, end - 1):
        if ao_vals[i] > ao_vals[i - 1] and ao_vals[i] > ao_vals[i + 1]:
            maxima.append((i, ao_vals[i]))
    return maxima


def _has_zero_cross(ao_vals: np.ndarray, from_idx: int, to_idx: int) -> bool:
    """Check if AO crossed zero between from_idx and to_idx (exclusive bounds)."""
    for i in range(from_idx, to_idx):
        if (ao_vals[i] < 0 and ao_vals[i + 1] >= 0) or (ao_vals[i] > 0 and ao_vals[i + 1] <= 0):
            return True
    return False


def detect_ao_signals(ao: pd.Series, colors: list[str]) -> dict:
    """
    Detect all AO buy and sell signals on the most recent bar.

    Returns:
        {
          'buy':  signal_name (str) or None,   e.g. 'SAUCER', 'ZERO_CROSS', 'TWIN_PEAKS'
          'sell': signal_name (str) or None,
        }
    Only the highest-priority signal per direction is returned (Zero Cross > Saucer > Twin Peaks).
    """
    ao_vals = ao.values
    n = len(ao_vals)

    buy_signal = None
    sell_signal = None

    # Need at least 34 bars of valid data
    if n < 40:
        return {"buy": buy_signal, "sell": sell_signal}

    # Find last valid bar index
    last = n - 1
    if np.isnan(ao_vals[last]) or np.isnan(ao_vals[last - 1]):
        return {"buy": buy_signal, "sell": sell_signal}

    curr = ao_vals[last]
    prev = ao_vals[last - 1]
    curr_color = colors[last]
    prev_color = colors[last - 1] if last >= 1 else "red"

    # ── Zero Cross Buy ──────────────────────────────────────────────────────────
    if prev < 0 and curr >= 0 and curr_color == "green":
        buy_signal = "ZERO_CROSS"

    # ── Zero Cross Sell ─────────────────────────────────────────────────────────
    if prev > 0 and curr <= 0 and curr_color == "red":
        sell_signal = "ZERO_CROSS"

    # ── Saucer Buy ──────────────────────────────────────────────────────────────
    if buy_signal is None and last >= 2:
        b0 = ao_vals[last - 2]
        b1 = ao_vals[last - 1]
        b2 = ao_vals[last]
        c0 = colors[last - 2]
        c1 = colors[last - 1]
        c2 = colors[last]
        if (not np.isnan(b0)) and b0 > 0 and b1 > 0 and b2 > 0:
            if c0 == "red" and c1 == "red" and c2 == "green":
                buy_signal = "SAUCER"

    # ── Saucer Sell ─────────────────────────────────────────────────────────────
    if sell_signal is None and last >= 2:
        b0 = ao_vals[last - 2]
        b1 = ao_vals[last - 1]
        b2 = ao_vals[last]
        c0 = colors[last - 2]
        c1 = colors[last - 1]
        c2 = colors[last]
        if (not np.isnan(b0)) and b0 < 0 and b1 < 0 and b2 < 0:
            if c0 == "green" and c1 == "green" and c2 == "red":
                sell_signal = "SAUCER"

    # ── Twin Peaks Buy (AO below zero) ──────────────────────────────────────────
    if buy_signal is None and curr_color == "green" and curr < 0:
        # Look back up to 50 bars for two down-peaks below zero
        lookback_start = max(0, last - 50)
        minima = _find_local_minima(ao_vals, lookback_start, last)
        # Keep only those below zero
        minima_below = [(idx, val) for idx, val in minima if val < 0]
        if len(minima_below) >= 2:
            # Take the two most recent
            p1_idx, p1_val = minima_below[-2]
            p2_idx, p2_val = minima_below[-1]
            # 2nd peak must be higher (less negative) than 1st
            if p2_val > p1_val:
                # No zero cross between the two peaks
                if not _has_zero_cross(ao_vals, p1_idx, p2_idx):
                    buy_signal = "TWIN_PEAKS"

    # ── Twin Peaks Sell (AO above zero) ─────────────────────────────────────────
    if sell_signal is None and curr_color == "red" and curr > 0:
        lookback_start = max(0, last - 50)
        maxima = _find_local_maxima(ao_vals, lookback_start, last)
        maxima_above = [(idx, val) for idx, val in maxima if val > 0]
        if len(maxima_above) >= 2:
            p1_idx, p1_val = maxima_above[-2]
            p2_idx, p2_val = maxima_above[-1]
            # 2nd peak must be lower than 1st
            if p2_val < p1_val:
                if not _has_zero_cross(ao_vals, p1_idx, p2_idx):
                    sell_signal = "TWIN_PEAKS"

    return {"buy": buy_signal, "sell": sell_signal}
