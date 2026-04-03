"""Tests for indicators/ac.py"""
import numpy as np
import pandas as pd
import pytest

from bw_scanner.indicators.ac import ac_oscillator, detect_ac_signals
from bw_scanner.indicators.ao import awesome_oscillator


class TestACOscillator:
    def test_returns_series_and_colors(self, ac_buy_above_zero_df):
        ao, _ = awesome_oscillator(ac_buy_above_zero_df)
        ac, colors = ac_oscillator(ao)
        assert isinstance(ac, pd.Series)
        assert isinstance(colors, list)
        assert len(ac) == len(colors)

    def test_colors_are_green_or_red(self, ac_buy_above_zero_df):
        ao, _ = awesome_oscillator(ac_buy_above_zero_df)
        _, colors = ac_oscillator(ao)
        assert all(c in ("green", "red") for c in colors)


class TestDetectACSignals:
    def test_buy_blocked_on_red_bar(self, ac_buy_red_bar_df):
        """AC buy signal must NOT fire when the current AC bar is red."""
        ao, _ = awesome_oscillator(ac_buy_red_bar_df)
        ac, colors = ac_oscillator(ao)
        sigs = detect_ac_signals(ac, colors)
        assert sigs["buy"] is None, f"Expected no buy on red AC bar, got {sigs['buy']}"

    def test_sell_blocked_on_green_bar(self, ac_buy_above_zero_df):
        """AC sell signal must NOT fire when the current AC bar is green."""
        ao, _ = awesome_oscillator(ac_buy_above_zero_df)
        ac, colors = ac_oscillator(ao)
        # Force last color to green
        colors_patched = colors[:-1] + ["green"]
        sigs = detect_ac_signals(ac, colors_patched)
        assert sigs["sell"] is None

    def test_buy_above_zero_requires_two_green_bars(self):
        """BUY_ABOVE_ZERO needs exactly 2 consecutive green bars (not 1)."""
        # Build a color list with only 1 green bar at end, AC above zero
        n = 50
        ac_vals = np.concatenate([np.zeros(45), [0.1, 0.2, 0.3, 0.2, 0.1]])
        # 1 green bar (last)
        colors = ["red"] * 49 + ["green"]
        ac = pd.Series(ac_vals)
        sigs = detect_ac_signals(ac, colors)
        assert sigs["buy"] is None

    def test_buy_above_zero_fires_with_two_green_bars(self):
        """BUY_ABOVE_ZERO fires with 2 consecutive green bars."""
        n = 50
        ac_vals = np.concatenate([np.zeros(45), [0.1, 0.2, 0.3, 0.4, 0.5]])
        colors = ["red"] * 48 + ["green", "green"]
        ac = pd.Series(ac_vals)
        sigs = detect_ac_signals(ac, colors)
        assert sigs["buy"] == "BUY_ABOVE_ZERO"

    def test_buy_below_zero_requires_three_green_bars(self):
        """BUY_BELOW_ZERO requires 3 consecutive green bars."""
        n = 50
        ac_vals = np.concatenate([np.zeros(45), [-0.5, -0.4, -0.3, -0.2, -0.1]])
        # Only 2 green bars
        colors = ["red"] * 48 + ["green", "green"]
        ac = pd.Series(ac_vals)
        sigs = detect_ac_signals(ac, colors)
        assert sigs["buy"] is None

    def test_buy_below_zero_fires_with_three_green_bars(self):
        """BUY_BELOW_ZERO fires with 3 consecutive green bars while AC < 0."""
        n = 50
        ac_vals = np.concatenate([np.zeros(45), [-0.5, -0.4, -0.3, -0.2, -0.1]])
        colors = ["red"] * 47 + ["green", "green", "green"]
        ac = pd.Series(ac_vals)
        sigs = detect_ac_signals(ac, colors)
        assert sigs["buy"] == "BUY_BELOW_ZERO"

    def test_return_structure(self, ac_buy_above_zero_df):
        ao, _ = awesome_oscillator(ac_buy_above_zero_df)
        ac, colors = ac_oscillator(ao)
        sigs = detect_ac_signals(ac, colors)
        assert "buy" in sigs
        assert "sell" in sigs
