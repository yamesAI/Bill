"""Tests for indicators/alligator.py"""
import numpy as np
import pandas as pd
import pytest

from bw_scanner.indicators.alligator import alligator, alligator_state, smma


class TestSMMA:
    def test_first_value_is_sma(self):
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        result = smma(series, 3)
        # First valid value at index 2 = mean(1,2,3) = 2.0
        assert result.iloc[2] == pytest.approx(2.0)

    def test_subsequent_values_wilder_smoothing(self):
        series = pd.Series([2.0, 2.0, 2.0, 4.0])  # period=3
        result = smma(series, 3)
        # index 2: (2+2+2)/3 = 2.0
        # index 3: (2.0 * 2 + 4.0) / 3 = 8/3
        assert result.iloc[2] == pytest.approx(2.0)
        assert result.iloc[3] == pytest.approx(8.0 / 3.0)

    def test_nan_before_period(self):
        series = pd.Series([1.0, 2.0, 3.0, 4.0])
        result = smma(series, 3)
        assert np.isnan(result.iloc[0])
        assert np.isnan(result.iloc[1])
        assert not np.isnan(result.iloc[2])

    def test_short_series_returns_all_nan(self):
        series = pd.Series([1.0, 2.0])
        result = smma(series, 5)
        assert result.isna().all()


class TestAlligator:
    def test_returns_three_series(self, bullish_trending_df):
        jaw, teeth, lips = alligator(bullish_trending_df)
        assert isinstance(jaw, pd.Series)
        assert isinstance(teeth, pd.Series)
        assert isinstance(lips, pd.Series)

    def test_series_length_matches_df(self, bullish_trending_df):
        jaw, teeth, lips = alligator(bullish_trending_df)
        n = len(bullish_trending_df)
        assert len(jaw) == n
        assert len(teeth) == n
        assert len(lips) == n

    def test_bullish_ordering_on_uptrend(self, bullish_trending_df):
        """In a strong uptrend, lips > teeth > jaw on the last valid bar."""
        jaw, teeth, lips = alligator(bullish_trending_df)
        j = jaw.dropna().iloc[-1]
        t = teeth.dropna().iloc[-1]
        lp = lips.dropna().iloc[-1]
        assert lp > t > j, f"Expected lips({lp:.2f}) > teeth({t:.2f}) > jaw({j:.2f})"


class TestAlligatorState:
    def test_sleeping_on_sideways(self, sleeping_alligator_df):
        jaw, teeth, lips = alligator(sleeping_alligator_df)
        state = alligator_state(sleeping_alligator_df, jaw, teeth, lips)
        assert state == "SLEEPING"

    def test_eating_bull_on_uptrend(self, bullish_trending_df):
        jaw, teeth, lips = alligator(bullish_trending_df)
        state = alligator_state(bullish_trending_df, jaw, teeth, lips)
        assert state in ("EATING_BULL", "AWAKENING"), f"Got {state}"

    def test_no_signal_when_sleeping(self, sleeping_alligator_df):
        """score_symbol must return None when Alligator is sleeping."""
        from bw_scanner.signals.score import score_symbol
        result = score_symbol("TESTUSDT", sleeping_alligator_df)
        assert result is None
