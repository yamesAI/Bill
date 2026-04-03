"""Tests for indicators/zones.py"""
import pytest

from bw_scanner.indicators.zones import check_zone_exit, zone, zone_sequence


class TestZone:
    def test_green_zone_when_both_green(self):
        assert zone(["green"], ["green"]) == "GREEN"

    def test_red_zone_when_both_red(self):
        assert zone(["red"], ["red"]) == "RED"

    def test_gray_when_ao_green_ac_red(self):
        assert zone(["green"], ["red"]) == "GRAY"

    def test_gray_when_ao_red_ac_green(self):
        assert zone(["red"], ["green"]) == "GRAY"

    def test_empty_lists_return_gray(self):
        assert zone([], []) == "GRAY"

    def test_uses_last_bar_only(self):
        ao = ["green", "green", "red"]
        ac = ["green", "green", "red"]
        assert zone(ao, ac) == "RED"


class TestZoneSequence:
    def test_returns_n_zones(self):
        ao = ["green"] * 5 + ["red"] * 5
        ac = ["green"] * 5 + ["red"] * 5
        seq = zone_sequence(ao, ac, n=5)
        assert len(seq) == 5

    def test_correct_zone_values(self):
        ao = ["green", "red", "green"]
        ac = ["green", "red", "red"]
        seq = zone_sequence(ao, ac, n=3)
        assert seq[0] == "GREEN"  # both green
        assert seq[1] == "RED"    # both red
        assert seq[2] == "GRAY"   # mixed


class TestCheckZoneExit:
    def test_long_exit_on_five_red_zones(self, zone_exit_long_df):
        ao_colors, ac_colors = zone_exit_long_df
        seq = zone_sequence(ao_colors, ac_colors, n=10)
        assert check_zone_exit(seq, "LONG") is True

    def test_no_long_exit_on_four_red_zones(self):
        seq = ["GREEN", "GREEN", "RED", "RED", "RED", "RED"]
        assert check_zone_exit(seq, "LONG") is False  # only 4 consecutive RED at end

    def test_short_exit_on_five_green_zones(self):
        seq = ["RED"] * 5 + ["GREEN"] * 5
        assert check_zone_exit(seq, "SHORT") is True

    def test_no_exit_on_insufficient_bars(self):
        seq = ["RED", "RED", "RED"]
        assert check_zone_exit(seq, "LONG") is False

    def test_long_no_exit_when_interrupted(self):
        seq = ["RED", "RED", "GREEN", "RED", "RED"]
        assert check_zone_exit(seq, "LONG") is False
