"""
Bill Williams Acceleration/Deceleration Oscillator (AC).

AC = AO - SMA(AO, 5)

Bar color same as AO: green if current > previous, red otherwise.

IMPORTANT rules:
  - Crossing zero on AC is NOT a signal — it only changes the bar count requirement.
  - Cannot have a BUY signal if the current AC bar is red.
  - Cannot have a SELL signal if the current AC bar is green.

BUY signal conditions (consecutive green bars ending on current):
  - AC above zero:           2 consecutive green bars
  - AC below zero:           3 consecutive green bars
  - AC crossing zero upward: 2 green bars once bar is above zero

SELL signal conditions (consecutive red bars ending on current):
  - AC below zero:            2 consecutive red bars
  - AC above zero:            3 consecutive red bars
  - AC crossing zero downward: 2 red bars once bar is below zero
"""
import numpy as np
import pandas as pd


def ac_oscillator(ao: pd.Series) -> tuple[pd.Series, list[str]]:
    """
    Compute AC and bar color sequence.

    Returns:
        ac     — pd.Series of AC values
        colors — list of 'green'/'red' strings, same length as ac
    """
    ac = ao - ao.rolling(5).mean()

    colors = ["red"]  # no previous bar for first
    ac_vals = ac.values
    for i in range(1, len(ac_vals)):
        if np.isnan(ac_vals[i]) or np.isnan(ac_vals[i - 1]):
            colors.append("red")
        elif ac_vals[i] > ac_vals[i - 1]:
            colors.append("green")
        else:
            colors.append("red")

    return ac, colors


def _count_consecutive(colors: list[str], target: str, from_end: int = 0) -> int:
    """
    Count how many consecutive `target` color bars end at position (last - from_end).
    """
    idx = len(colors) - 1 - from_end
    count = 0
    while idx >= 0 and colors[idx] == target:
        count += 1
        idx -= 1
    return count


def detect_ac_signals(ac: pd.Series, colors: list[str]) -> dict:
    """
    Detect AC buy/sell signals on the most recent bar.

    Returns:
        {
          'buy':  signal_type (str) or None,
                  e.g. 'BUY_ABOVE_ZERO', 'BUY_BELOW_ZERO', 'BUY_CROSS_ZERO'
          'sell': signal_type (str) or None,
                  e.g. 'SELL_BELOW_ZERO', 'SELL_ABOVE_ZERO', 'SELL_CROSS_ZERO'
        }
    """
    ac_vals = ac.values
    n = len(ac_vals)
    buy_signal = None
    sell_signal = None

    if n < 10:
        return {"buy": buy_signal, "sell": sell_signal}

    last = n - 1
    curr_val = ac_vals[last]
    prev_val = ac_vals[last - 1] if last >= 1 else np.nan
    curr_color = colors[last]

    if np.isnan(curr_val) or np.isnan(prev_val):
        return {"buy": buy_signal, "sell": sell_signal}

    # ── BUY signals — only on green AC bars ──────────────────────────────────
    if curr_color == "green":
        consecutive_green = _count_consecutive(colors, "green")

        # Zero cross upward: prev was below zero, current is above zero
        if prev_val < 0 and curr_val >= 0:
            # Need 2 green bars with current bar now above zero
            if consecutive_green >= 2:
                buy_signal = "BUY_CROSS_ZERO"

        elif curr_val > 0:
            # AC above zero: need 2 consecutive green bars
            if consecutive_green >= 2:
                buy_signal = "BUY_ABOVE_ZERO"

        else:
            # AC below zero: need 3 consecutive green bars
            if consecutive_green >= 3:
                buy_signal = "BUY_BELOW_ZERO"

    # ── SELL signals — only on red AC bars ───────────────────────────────────
    if curr_color == "red":
        consecutive_red = _count_consecutive(colors, "red")

        # Zero cross downward: prev was above zero, current is below zero
        if prev_val > 0 and curr_val <= 0:
            if consecutive_red >= 2:
                sell_signal = "SELL_CROSS_ZERO"

        elif curr_val < 0:
            # AC below zero: need 2 consecutive red bars
            if consecutive_red >= 2:
                sell_signal = "SELL_BELOW_ZERO"

        else:
            # AC above zero: need 3 consecutive red bars
            if consecutive_red >= 3:
                sell_signal = "SELL_ABOVE_ZERO"

    return {"buy": buy_signal, "sell": sell_signal}
