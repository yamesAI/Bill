"""Tests for signals/score.py"""
import numpy as np
import pandas as pd
import pytest

from bw_scanner.signals.score import BWSignal, score_all, score_symbol


class TestBWSignal:
    def test_dataclass_default_priority(self):
        sig = BWSignal(symbol="TESTUSDT", direction="LONG", confluence_score=0)
        assert sig.priority == "SKIP"
        assert sig.zone == "GRAY"
        assert sig.fractal_signal is False

    def test_priority_high_at_four(self):
        from bw_scanner.signals.score import _priority
        assert _priority(4) == "HIGH"
        assert _priority(5) == "HIGH"

    def test_priority_medium_at_two(self):
        from bw_scanner.signals.score import _priority
        assert _priority(2) == "MEDIUM"
        assert _priority(3) == "MEDIUM"

    def test_priority_low_at_one(self):
        from bw_scanner.signals.score import _priority
        assert _priority(1) == "LOW"

    def test_priority_skip_at_zero(self):
        from bw_scanner.signals.score import _priority
        assert _priority(0) == "SKIP"


class TestScoreSymbol:
    def test_returns_empty_list_for_sleeping_alligator(self, sleeping_alligator_df):
        result = score_symbol("SLEEPUSDT", sleeping_alligator_df)
        assert result == []

    def test_returns_empty_list_for_insufficient_data(self):
        n = 30  # too few bars
        mid = np.ones(n) * 100.0
        timestamps = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
        df = pd.DataFrame({
            "timestamp": timestamps,
            "open": mid, "high": mid + 0.5,
            "low": mid - 0.5, "close": mid,
            "volume": np.ones(n),
        })
        result = score_symbol("SHORTUSDT", df)
        assert result == []

    def test_returns_list_of_bwsignals(self, bullish_trending_df):
        result = score_symbol("BULLUSDT", bullish_trending_df)
        assert isinstance(result, list)
        assert all(isinstance(s, BWSignal) for s in result)

    def test_direction_filter_long_above_teeth(self, bullish_trending_df):
        """On a bullish uptrend, all signals should be LONG (close > teeth)."""
        result = score_symbol("BULLLONG", bullish_trending_df)
        for sig in result:
            assert sig.direction == "LONG"

    def test_score_is_0_to_5(self, bullish_trending_df):
        result = score_symbol("RANGEUSDT", bullish_trending_df)
        for sig in result:
            assert 0 <= sig.confluence_score <= 5

    def test_dimensions_active_matches_score(self, bullish_trending_df):
        result = score_symbol("DIMTEST", bullish_trending_df)
        for sig in result:
            assert len(sig.dimensions_active) == sig.confluence_score

    def test_both_directions_evaluated_independently(self, bullish_trending_df):
        """score_symbol returns a list so both LONG and SHORT are considered."""
        result = score_symbol("BOTHTEST", bullish_trending_df)
        # BW filter means at most one direction qualifies, but result is always a list
        assert isinstance(result, list)


class TestScoreAll:
    def test_returns_list(self, bullish_trending_df):
        data = {"BTCUSDT": bullish_trending_df, "ETHUSDT": bullish_trending_df.copy()}
        results = score_all(data)
        assert isinstance(results, list)

    def test_sorted_by_score_descending(self, bullish_trending_df):
        data = {f"SYM{i}USDT": bullish_trending_df.copy() for i in range(5)}
        results = score_all(data)
        scores = [r.confluence_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_no_skip_priority_in_results(self, bullish_trending_df):
        data = {"BTCUSDT": bullish_trending_df}
        results = score_all(data)
        assert all(r.priority != "SKIP" for r in results)

    def test_handles_empty_dict(self):
        results = score_all({})
        assert results == []
