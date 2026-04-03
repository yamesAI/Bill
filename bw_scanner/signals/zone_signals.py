"""
Dimension 4 — Zone signals.
Delegates to indicators.zones.
"""
from bw_scanner.indicators.zones import check_zone_exit, zone, zone_sequence

__all__ = ["zone", "zone_sequence", "check_zone_exit"]
