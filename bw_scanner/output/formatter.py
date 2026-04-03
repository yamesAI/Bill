"""
Report formatter for the Bill Williams 5D Scanner daily output.
"""
from datetime import datetime
from typing import Optional

from bw_scanner.signals.score import BWSignal


def _dim_check(label: str, active: bool) -> str:
    mark = "✅" if active else "⬜"
    return f"  {mark} {label}"


def _format_signal(sig: BWSignal) -> str:
    lines = []

    direction_icon = "🟢" if sig.direction == "LONG" else "🔴"
    lines.append(
        f"{direction_icon} {sig.symbol:<12} | Score: {sig.confluence_score}/5"
        f" | Price: {sig.price:,.6g}"
    )

    # Fractal
    if sig.fractal_signal:
        label = "Fractal BUY above Jaw (FIRST ENTRY)" if sig.first_entry else "Fractal BUY above Teeth"
        if sig.direction == "SHORT":
            label = "Fractal SELL below Jaw (FIRST ENTRY)" if sig.first_entry else "Fractal SELL below Teeth"
        lines.append(_dim_check(label, True))
    else:
        lines.append(_dim_check("Fractal signal", False))

    # AO
    ao_label = f"AO: {sig.ao_signal.replace('_', ' ').title()}" if sig.ao_signal else "AO: No signal"
    lines.append(_dim_check(ao_label, sig.ao_signal is not None))

    # AC
    ac_label = f"AC: {sig.ac_signal.replace('_', ' ').title()}" if sig.ac_signal else "AC: No signal"
    lines.append(_dim_check(ac_label, sig.ac_signal is not None))

    # Zone
    zone_label = f"ZONE: {sig.zone}"
    zone_active = (sig.direction == "LONG" and sig.zone == "GREEN") or (sig.direction == "SHORT" and sig.zone == "RED")
    lines.append(_dim_check(zone_label, zone_active))

    # Alligator
    alligator_active = "ALLIGATOR" in " ".join(sig.dimensions_active)
    alligator_label = f"Alligator: {sig.alligator_state.replace('_', ' ')}"
    lines.append(_dim_check(alligator_label, alligator_active))

    # Entry / Stop
    lines.append(f"  📍 Entry Stop:  {sig.entry_stop:,.6g}")
    lines.append(f"  🛑 Stop Loss:   {sig.alligator_stop:,.6g}")

    if sig.zone_exit_warning:
        lines.append("  ⚠️  Zone exit warning — 5 consecutive opposing-zone bars")

    return "\n".join(lines)


def format_report(
    signals: list[BWSignal],
    scan_time: Optional[datetime] = None,
    total_scanned: int = 0,
) -> str:
    if scan_time is None:
        from datetime import timezone
        scan_time = datetime.now(timezone.utc)

    date_str = scan_time.strftime("%Y-%m-%d %H:%M UTC")

    header = (
        "═══════════════════════════════════════════════════════\n"
        f"  BILL WILLIAMS 5D SCANNER — 4H Chart — {date_str}\n"
        "═══════════════════════════════════════════════════════"
    )

    high_longs  = [s for s in signals if s.direction == "LONG"  and s.confluence_score >= 4]
    high_shorts = [s for s in signals if s.direction == "SHORT" and s.confluence_score >= 4]
    medium      = [s for s in signals if s.confluence_score in (2, 3)]

    sections = [header]

    # High confluence longs
    sections.append("\n🟢 HIGH CONFLUENCE LONG SETUPS (Score 4-5)")
    sections.append("─" * 42)
    if high_longs:
        sections.extend(_format_signal(s) for s in high_longs)
    else:
        sections.append("  (none)")

    # High confluence shorts
    sections.append("\n🔴 HIGH CONFLUENCE SHORT SETUPS (Score 4-5)")
    sections.append("─" * 43)
    if high_shorts:
        sections.extend(_format_signal(s) for s in high_shorts)
    else:
        sections.append("  (none)")

    # Medium setups
    sections.append("\n🟡 MEDIUM SETUPS (Score 2-3) — Monitor Only")
    sections.append("─" * 43)
    if medium:
        for s in medium:
            direction_icon = "🟢" if s.direction == "LONG" else "🔴"
            sections.append(
                f"  {direction_icon} {s.symbol:<12} | Score: {s.confluence_score}/5"
                f" | {s.direction} | {', '.join(s.dimensions_active)}"
            )
    else:
        sections.append("  (none)")

    # Market overview stats
    green_count = sum(1 for s in signals if s.zone == "GREEN")
    red_count   = sum(1 for s in signals if s.zone == "RED")
    gray_count  = sum(1 for s in signals if s.zone == "GRAY")

    sections.append(
        f"\n📊 MARKET OVERVIEW\n"
        f"  Tokens scanned:    {total_scanned}\n"
        f"  Green Zone tokens: {green_count}\n"
        f"  Red Zone tokens:   {red_count}\n"
        f"  Gray Zone tokens:  {gray_count}\n"
        f"  High-score longs:  {len(high_longs)}\n"
        f"  High-score shorts: {len(high_shorts)}"
    )

    sections.append("═══════════════════════════════════════════════════════")

    return "\n".join(sections)
