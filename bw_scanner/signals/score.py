"""
Multi-dimension confluence scorer.

Aggregates signals from all five Bill Williams dimensions into a BWSignal
dataclass with a 0-5 confluence score and a priority level.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from bw_scanner.config import HIGH_PRIORITY_SCORE, MEDIUM_PRIORITY_SCORE
from bw_scanner.indicators.ac import ac_oscillator, detect_ac_signals
from bw_scanner.indicators.alligator import alligator, alligator_state
from bw_scanner.indicators.ao import awesome_oscillator, detect_ao_signals
from bw_scanner.indicators.fractals import fractal_signal, fractals
from bw_scanner.indicators.zones import check_zone_exit, zone, zone_sequence

logger = logging.getLogger(__name__)


@dataclass
class BWSignal:
    symbol: str
    direction: str              # 'LONG' | 'SHORT'
    confluence_score: int       # 0-5
    dimensions_active: list[str] = field(default_factory=list)
    alligator_state: str = "UNKNOWN"
    price: float = 0.0
    entry_stop: float = 0.0     # 1 tick above fractal high (long) / below low (short)
    alligator_stop: float = 0.0 # just inside Teeth line
    zone: str = "GRAY"
    ao_signal: Optional[str] = None
    ac_signal: Optional[str] = None
    fractal_signal: bool = False
    first_entry: bool = False   # fractal broke outside Jaw
    zone_exit_warning: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: str = "SKIP"      # 'HIGH' | 'MEDIUM' | 'LOW' | 'SKIP'


def _priority(score: int) -> str:
    if score >= HIGH_PRIORITY_SCORE:
        return "HIGH"
    if score >= MEDIUM_PRIORITY_SCORE:
        return "MEDIUM"
    if score >= 1:
        return "LOW"
    return "SKIP"


def score_symbol(symbol: str, df: pd.DataFrame) -> list[BWSignal]:
    """
    Compute all BW indicators for df and return a list of BWSignals —
    one per qualifying direction (LONG and/or SHORT).

    Per BW rules, a symbol can only qualify for one direction at a time
    (price is either above or below the Teeth line), so the list will
    normally contain 0 or 1 items. Both directions are always evaluated
    independently and all qualifying signals are returned.

    Returns an empty list when the Alligator is sleeping or data is insufficient.
    """
    if len(df) < 50:
        return []

    try:
        jaw, teeth, lips = alligator(df)
        state = alligator_state(df, jaw, teeth, lips)

        # No new entries while Alligator is sleeping
        if state == "SLEEPING":
            return []

        teeth_val = teeth.dropna().iloc[-1] if not teeth.dropna().empty else None
        jaw_val = jaw.dropna().iloc[-1] if not jaw.dropna().empty else None
        if teeth_val is None or jaw_val is None:
            return []

        current_close = float(df["close"].iloc[-1])
        ao, ao_colors = awesome_oscillator(df)
        ac, ac_colors = ac_oscillator(ao)
        ao_sigs = detect_ao_signals(ao, ao_colors)
        ac_sigs = detect_ac_signals(ac, ac_colors)
        up_fracs, down_fracs = fractals(df)
        frac_sigs = fractal_signal(df, up_fracs, down_fracs, jaw, teeth)
        current_zone = zone(ao_colors, ac_colors)
        zone_seq = zone_sequence(ao_colors, ac_colors, n=10)

        results: list[BWSignal] = []

        for direction in ("LONG", "SHORT"):
            # BW directional filter — enforced strictly
            if direction == "LONG" and current_close <= float(teeth_val):
                continue
            if direction == "SHORT" and current_close >= float(teeth_val):
                continue

            score = 0
            dims: list[str] = []

            # Dimension 1: Fractal
            frac_active = frac_sigs["buy"] if direction == "LONG" else frac_sigs["sell"]
            if frac_active:
                score += 1
                dims.append("FRACTAL")

            # Dimension 2: AO
            ao_sig = ao_sigs["buy"] if direction == "LONG" else ao_sigs["sell"]
            if ao_sig:
                score += 1
                dims.append(f"AO:{ao_sig}")

            # Dimension 3: AC
            ac_sig = ac_sigs["buy"] if direction == "LONG" else ac_sigs["sell"]
            if ac_sig:
                score += 1
                dims.append(f"AC:{ac_sig}")

            # Dimension 4: Zone
            if direction == "LONG" and current_zone == "GREEN":
                score += 1
                dims.append("ZONE:GREEN")
            elif direction == "SHORT" and current_zone == "RED":
                score += 1
                dims.append("ZONE:RED")

            # Dimension 5: Alligator state
            alligator_bullish = state in ("EATING_BULL", "AWAKENING")
            alligator_bearish = state in ("EATING_BEAR", "AWAKENING")
            if direction == "LONG" and alligator_bullish:
                score += 1
                dims.append(f"ALLIGATOR:{state}")
            elif direction == "SHORT" and alligator_bearish:
                score += 1
                dims.append(f"ALLIGATOR:{state}")

            if score == 0:
                continue

            # Build entry stop and alligator stop
            if direction == "LONG":
                entry_stop = frac_sigs.get("buy_stop") or current_close * 1.001
                alligator_stop = round(float(teeth_val) * 0.9995, 8)
                first_entry = frac_sigs.get("buy_first_entry", False)
            else:
                entry_stop = frac_sigs.get("sell_stop") or current_close * 0.999
                alligator_stop = round(float(teeth_val) * 1.0005, 8)
                first_entry = frac_sigs.get("sell_first_entry", False)

            zone_exit = check_zone_exit(zone_seq, direction)

            results.append(BWSignal(
                symbol=symbol,
                direction=direction,
                confluence_score=score,
                dimensions_active=dims,
                alligator_state=state,
                price=current_close,
                entry_stop=entry_stop,
                alligator_stop=alligator_stop,
                zone=current_zone,
                ao_signal=ao_sig,
                ac_signal=ac_sig,
                fractal_signal=bool(frac_active),
                first_entry=first_entry,
                zone_exit_warning=zone_exit,
                priority=_priority(score),
            ))

        return results

    except Exception as exc:
        logger.warning("Error scoring %s: %s", symbol, exc, exc_info=True)
        return []


def score_all(data_dict: dict[str, pd.DataFrame]) -> list[BWSignal]:
    """
    Score all symbols for both LONG and SHORT, return all qualifying signals
    sorted by confluence score descending, excluding SKIP-priority results.
    """
    signals = []
    for symbol, df in data_dict.items():
        for sig in score_symbol(symbol, df):
            if sig.priority != "SKIP":
                signals.append(sig)

    signals.sort(key=lambda s: s.confluence_score, reverse=True)
    return signals
