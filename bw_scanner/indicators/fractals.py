"""
Bill Williams Fractals.

A fractal requires a 5-bar window. The signal bar is the middle bar (bar[2]).
A fractal is *confirmed* only after bar[4] (2 bars after the signal bar) closes.

Up fractal   (resistance / sell fractal): bar[2].high is the highest of the 5 bars.
Down fractal (support / buy fractal):     bar[2].low  is the lowest of the 5 bars.
"""
from typing import Optional

import pandas as pd


def fractals(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Scan df for confirmed up and down fractals.

    Returns:
        up_fractals   — DataFrame with columns ['bar_index', 'level'] (high values)
        down_fractals — DataFrame with columns ['bar_index', 'level'] (low values)

    bar_index is the positional integer index of the *signal bar* (bar[2]).
    A fractal at signal bar i is confirmed only when bar i+2 exists, so fractals
    are reported against i but only added to the result once i+2 is available.
    The most recent fractal that can appear is at position len(df)-3.
    """
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)

    up_indices = []
    up_levels = []
    down_indices = []
    down_levels = []

    # Signal bar is i; confirmation requires bars i-2..i+2 to exist
    for i in range(2, n - 2):
        h = highs[i]
        if h > highs[i - 2] and h > highs[i - 1] and h > highs[i + 1] and h > highs[i + 2]:
            up_indices.append(i)
            up_levels.append(h)

        l = lows[i]
        if l < lows[i - 2] and l < lows[i - 1] and l < lows[i + 1] and l < lows[i + 2]:
            down_indices.append(i)
            down_levels.append(l)

    up_fractals = pd.DataFrame({"bar_index": up_indices, "level": up_levels})
    down_fractals = pd.DataFrame({"bar_index": down_indices, "level": down_levels})

    return up_fractals, down_fractals


def last_confirmed_fractal(
    fractals_df: pd.DataFrame,
) -> Optional[tuple[int, float]]:
    """
    Return (bar_index, level) of the most recent confirmed fractal, or None.
    """
    if fractals_df.empty:
        return None
    row = fractals_df.iloc[-1]
    return int(row["bar_index"]), float(row["level"])


def fractal_signal(
    df: pd.DataFrame,
    up_fractals: pd.DataFrame,
    down_fractals: pd.DataFrame,
    jaw: pd.Series,
    teeth: pd.Series,
) -> dict:
    """
    Evaluate fractal-based entry signals.

    Rules:
    - BUY signal: most recent down fractal level is ABOVE the current Alligator Teeth.
      Entry stop is placed 1 tick (0.01%) above the fractal signal bar's high.
    - SELL signal: most recent up fractal level is BELOW the current Alligator Teeth.
      Entry stop is placed 1 tick below the fractal signal bar's low.
    - First-entry flag: fractal broke outside the Jaw (Blue line), not just Teeth.

    Returns a dict with keys:
        buy  (bool), buy_level (float), buy_stop (float), buy_first_entry (bool)
        sell (bool), sell_level (float), sell_stop (float), sell_first_entry (bool)
    """
    current_teeth = float(teeth.dropna().iloc[-1]) if not teeth.dropna().empty else None
    current_jaw = float(jaw.dropna().iloc[-1]) if not jaw.dropna().empty else None
    current_close = float(df["close"].iloc[-1])

    result = {
        "buy": False, "buy_level": None, "buy_stop": None, "buy_first_entry": False,
        "sell": False, "sell_level": None, "sell_stop": None, "sell_first_entry": False,
    }

    if current_teeth is None or current_jaw is None:
        return result

    # --- BUY fractal signal ---
    # Only if price is above Teeth (directional filter enforced by scorer, but level check here too)
    if not down_fractals.empty and current_close > current_teeth:
        last_down = down_fractals.iloc[-1]
        fractal_low = float(last_down["level"])
        bar_idx = int(last_down["bar_index"])

        if fractal_low > current_teeth:
            # Entry stop: 1 tick (0.01%) above the fractal bar's high
            fractal_bar_high = float(df["high"].iloc[bar_idx])
            tick = fractal_bar_high * 0.0001
            result["buy"] = True
            result["buy_level"] = fractal_low
            result["buy_stop"] = round(fractal_bar_high + tick, 8)
            # First entry: fractal broke outside Jaw
            result["buy_first_entry"] = fractal_low > current_jaw

    # --- SELL fractal signal ---
    if not up_fractals.empty and current_close < current_teeth:
        last_up = up_fractals.iloc[-1]
        fractal_high = float(last_up["level"])
        bar_idx = int(last_up["bar_index"])

        if fractal_high < current_teeth:
            fractal_bar_low = float(df["low"].iloc[bar_idx])
            tick = fractal_bar_low * 0.0001
            result["sell"] = True
            result["sell_level"] = fractal_high
            result["sell_stop"] = round(fractal_bar_low - tick, 8)
            result["sell_first_entry"] = fractal_high < current_jaw

    return result
