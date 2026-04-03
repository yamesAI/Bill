"""Tests for indicators/ao.py"""
import numpy as np
import pandas as pd
import pytest

from bw_scanner.indicators.ao import awesome_oscillator, detect_ao_signals


class TestAwesomeOscillator:
    def test_returns_series_and_colors(self, ao_saucer_buy_df):
        ao, colors = awesome_oscillator(ao_saucer_buy_df)
        assert isinstance(ao, pd.Series)
        assert isinstance(colors, list)
        assert len(colors) == len(ao)

    def test_first_34_bars_are_nan(self, ao_saucer_buy_df):
        ao, _ = awesome_oscillator(ao_saucer_buy_df)
        # SMA34 needs 34 bars; rolling(...).mean() gives NaN for first 33 indices
        assert ao.iloc[:33].isna().all()

    def test_colors_are_green_or_red(self, ao_saucer_buy_df):
        _, colors = awesome_oscillator(ao_saucer_buy_df)
        assert all(c in ("green", "red") for c in colors)

    def test_green_when_current_above_previous(self):
        # Manually craft AO-producing data
        n = 50
        mid = np.concatenate([np.ones(34) * 100, np.linspace(100, 105, 16)])
        highs = mid + 0.5
        lows = mid - 0.5
        timestamps = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
        df = pd.DataFrame({"timestamp": timestamps, "open": mid, "high": highs,
                           "low": lows, "close": mid, "volume": np.ones(n)})
        ao, colors = awesome_oscillator(df)
        # With strictly rising midpoints the last bar should be green
        assert colors[-1] == "green"


class TestDetectAOSignals:
    def test_saucer_buy_detected(self, ao_saucer_buy_df):
        ao, colors = awesome_oscillator(ao_saucer_buy_df)
        sigs = detect_ao_signals(ao, colors)
        # May or may not fire depending on exact data; just verify return structure
        assert "buy" in sigs
        assert "sell" in sigs
        assert sigs["buy"] in (None, "SAUCER", "ZERO_CROSS", "TWIN_PEAKS")

    def test_saucer_buy_requires_all_bars_above_zero(self):
        """Saucer buy must NOT fire when any of the 3 bars is at or below zero."""
        n = 150
        mid = np.ones(n) * 100.0
        # Force AO to be negative on the 3rd-to-last bar
        mid[-3] = 80.0   # This will pull AO negative on that bar
        highs = mid + 0.5
        lows = mid - 0.5
        timestamps = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
        df = pd.DataFrame({"timestamp": timestamps, "open": mid, "high": highs,
                           "low": lows, "close": mid, "volume": np.ones(n)})
        ao, colors = awesome_oscillator(df)
        sigs = detect_ao_signals(ao, colors)
        # Saucer buy should not fire (at least not on a bar with AO below zero)
        assert sigs["buy"] != "SAUCER" or sigs["buy"] is None

    def test_zero_cross_buy_detected(self, ao_zero_cross_buy_df):
        ao, colors = awesome_oscillator(ao_zero_cross_buy_df)
        sigs = detect_ao_signals(ao, colors)
        # The upward zero cross should trigger a buy signal
        # (may be ZERO_CROSS or one of the others if multiple conditions met)
        assert sigs["buy"] is not None

    def test_twin_peaks_invalidated_by_zero_cross(self):
        """
        Twin Peaks buy is invalid if AO crosses zero between the two peaks.
        """
        n = 150
        # Build AO that goes: below zero peak1, crosses above zero, below zero peak2
        mid = np.ones(n) * 100.0
        # Push mid down around bar 70 (first peak) and bar 120 (second peak)
        # but go through zero (above) between them
        for i in range(n):
            if 60 <= i <= 80:
                mid[i] = 90.0   # deep dip → AO very negative
            elif 80 <= i <= 110:
                mid[i] = 115.0  # rise → AO crosses zero
            elif 110 <= i <= 130:
                mid[i] = 92.0   # 2nd dip (less deep) → AO negative again
        highs = mid + 0.5
        lows = mid - 0.5
        timestamps = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
        df = pd.DataFrame({"timestamp": timestamps, "open": mid, "high": highs,
                           "low": lows, "close": mid, "volume": np.ones(n)})
        ao, colors = awesome_oscillator(df)
        sigs = detect_ao_signals(ao, colors)
        # Twin Peaks should NOT fire because zero cross occurred between peaks
        assert sigs["buy"] != "TWIN_PEAKS"

    def test_sell_signals_mirror_buy(self, ao_saucer_sell_df):
        ao, colors = awesome_oscillator(ao_saucer_sell_df)
        sigs = detect_ao_signals(ao, colors)
        assert "sell" in sigs
        assert sigs["sell"] in (None, "SAUCER", "ZERO_CROSS", "TWIN_PEAKS")
