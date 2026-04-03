"""
Bill Williams Zone classifier.

A Zone is determined by the last bar colors of AO and AC:
  GREEN zone — both AO and AC last bar are green (very bullish, add to longs)
  RED zone   — both AO and AC last bar are red   (very bearish, add to shorts)
  GRAY zone  — mixed colors                      (transition, no zone adds)

Zone trading rules:
  GREEN zone: add to long on each new GREEN zone bar
    - Stop adding if a GRAY bar appears (hold existing position)
    - Exit long after 5 consecutive RED zone bars
  RED zone: mirror — add to short, exit after 5 consecutive GREEN zone bars
"""


def zone(ao_colors: list[str], ac_colors: list[str]) -> str:
    """
    Return the current zone based on the last bar colors of AO and AC.
    Returns 'GREEN', 'RED', or 'GRAY'.
    """
    if not ao_colors or not ac_colors:
        return "GRAY"

    ao_last = ao_colors[-1]
    ac_last = ac_colors[-1]

    if ao_last == "green" and ac_last == "green":
        return "GREEN"
    if ao_last == "red" and ac_last == "red":
        return "RED"
    return "GRAY"


def zone_sequence(ao_colors: list[str], ac_colors: list[str], n: int = 10) -> list[str]:
    """
    Return the last N zone strings (oldest first, most recent last).
    Uses parallel AO and AC color lists.
    """
    ao_tail = ao_colors[-n:]
    ac_tail = ac_colors[-n:]

    zones = []
    for ao_c, ac_c in zip(ao_tail, ac_tail):
        if ao_c == "green" and ac_c == "green":
            zones.append("GREEN")
        elif ao_c == "red" and ac_c == "red":
            zones.append("RED")
        else:
            zones.append("GRAY")
    return zones


def check_zone_exit(zone_seq: list[str], direction: str) -> bool:
    """
    Determine if the zone sequence triggers an exit signal.

    Rules:
      LONG  exit: 5 consecutive RED zones at the end of zone_seq
      SHORT exit: 5 consecutive GREEN zones at the end of zone_seq

    Returns True if the exit condition is met.
    """
    if len(zone_seq) < 5:
        return False

    exit_zone = "RED" if direction == "LONG" else "GREEN"
    return all(z == exit_zone for z in zone_seq[-5:])
