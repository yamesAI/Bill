"""Tests for indicators/fractals.py"""
import numpy as np
import pandas as pd
import pytest

from bw_scanner.indicators.fractals import fractal_signal, fractals, last_confirmed_fractal


class TestFractals:
    def test_detects_down_fractal(self, fractal_buy_df):
        _, down_fracs = fractals(fractal_buy_df)
        assert not down_fracs.empty, "Expected at least one down fractal"
        # Signal bar should be at index 97
        assert 97 in down_fracs["bar_index"].values

    def test_down_fractal_level_is_correct(self, fractal_buy_df):
        _, down_fracs = fractals(fractal_buy_df)
        row = down_fracs[down_fracs["bar_index"] == 97]
        assert not row.empty
        assert row.iloc[0]["level"] == pytest.approx(98.0)

    def test_fractal_not_confirmed_without_two_following_bars(self, fractal_unconfirmed_df):
        """
        Signal bar at index 98; only bar 99 exists after it.
        Bar 100 doesn't exist, so the fractal at index 98 should NOT appear.
        The confirmed fractal at index 97 should not exist either since
        the setup is specifically designed with only bar 99 as the last bar.
        """
        _, down_fracs = fractals(fractal_unconfirmed_df)
        # Index 98 cannot be confirmed (need bar 100 which doesn't exist)
        assert 98 not in (down_fracs["bar_index"].values if not down_fracs.empty else [])

    def test_up_fractal_detection(self):
        n = 100
        highs = np.ones(n) * 100.0
        lows = np.ones(n) * 99.0
        # Create clear up fractal at bar 50
        highs[48] = 101.0
        highs[49] = 102.0
        highs[50] = 105.0  # signal bar — highest
        highs[51] = 102.0
        highs[52] = 101.0
        closes = (highs + lows) / 2
        timestamps = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
        df = pd.DataFrame({"timestamp": timestamps, "open": closes, "high": highs,
                           "low": lows, "close": closes, "volume": np.ones(n)})
        up_fracs, _ = fractals(df)
        assert 50 in up_fracs["bar_index"].values
        assert up_fracs[up_fracs["bar_index"] == 50].iloc[0]["level"] == pytest.approx(105.0)

    def test_last_confirmed_fractal_returns_most_recent(self, fractal_buy_df):
        _, down_fracs = fractals(fractal_buy_df)
        result = last_confirmed_fractal(down_fracs)
        assert result is not None
        idx, level = result
        assert idx == 97
        assert level == pytest.approx(98.0)

    def test_last_confirmed_fractal_returns_none_on_empty(self):
        empty = pd.DataFrame(columns=["bar_index", "level"])
        assert last_confirmed_fractal(empty) is None


class TestFractalSignal:
    def test_no_buy_signal_when_below_teeth(self, fractal_buy_df):
        """Fractal buy signal should not fire when price is below Teeth."""
        from bw_scanner.indicators.alligator import alligator
        jaw, teeth, lips = alligator(fractal_buy_df)
        # Manipulate close to be below teeth
        df = fractal_buy_df.copy()
        teeth_val = teeth.dropna().iloc[-1]
        df["close"] = teeth_val * 0.99  # below Teeth
        up_f, down_f = fractals(df)
        sigs = fractal_signal(df, up_f, down_f, jaw, teeth)
        assert sigs["buy"] is False
