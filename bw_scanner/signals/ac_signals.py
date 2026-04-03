"""
Dimension 3 — Acceleration/Deceleration signals.
Delegates to indicators.ac.detect_ac_signals().
"""
from bw_scanner.indicators.ac import ac_oscillator, detect_ac_signals

__all__ = ["ac_oscillator", "detect_ac_signals"]
