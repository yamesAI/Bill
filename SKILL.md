# BW Scanner — Bill Williams 5D Crypto Scanner

A scheduled Python scanner that runs daily at 6:00 AM UTC, fetches 4H OHLCV data for the top 100 Binance USDT pairs by volume, and applies Bill Williams' complete *New Trading Dimensions* methodology across all five dimensions to surface LONG and SHORT setups.

---

## Project Layout

```
bw_scanner/
├── config.py                  # All settings (tokens, thresholds, alert creds)
├── main.py                    # Entry point — async main_scan(), --dry-run flag
├── scheduler.py               # APScheduler cron at 6AM UTC
├── data/
│   └── fetcher.py             # Async Binance API — top 100 symbols + OHLCV
├── indicators/
│   ├── alligator.py           # SMMA Jaw/Teeth/Lips + state classifier
│   ├── fractals.py            # 5-bar fractal detection + fractal_signal()
│   ├── ao.py                  # Awesome Oscillator + 3 buy/sell signal types
│   ├── ac.py                  # AC Oscillator + bar-count signal rules
│   └── zones.py               # GREEN/RED/GRAY zone + exit detection
├── signals/
│   ├── score.py               # BWSignal dataclass + confluence scorer (0-5)
│   ├── fractal_signals.py     # Re-exports from indicators/fractals.py
│   ├── ao_signals.py          # Re-exports from indicators/ao.py
│   ├── ac_signals.py          # Re-exports from indicators/ac.py
│   └── zone_signals.py        # Re-exports from indicators/zones.py
└── output/
    ├── formatter.py           # Daily report builder
    └── notifier.py            # Telegram, Discord, CSV log
tests/
├── conftest.py                # Synthetic OHLCV fixtures for all BW patterns
├── test_alligator.py
├── test_fractals.py
├── test_ao.py
├── test_ac.py
├── test_zones.py
└── test_score.py
```

---

## Running the Scanner

```bash
# Install dependencies
pip install -r requirements.txt

# Dry run — prints report to console, no alerts sent
python -m bw_scanner.main --dry-run

# Live run — sends Telegram + Discord alerts, appends signals_log.csv
python -m bw_scanner.main

# Start the daily 6AM UTC scheduler
python -m bw_scanner.scheduler

# Run tests
python -m pytest tests/ -v

# Deploy with PM2 (production)
pm2 start bw_scanner/scheduler.py --interpreter python3 --name bw-scanner
```

---

## Configuration (`bw_scanner/config.py`)

| Setting | Default | Description |
|---|---|---|
| `TOP_N_TOKENS` | 100 | Number of top-volume USDT pairs to scan |
| `INTERVAL` | `"4h"` | Binance klines interval |
| `LOOKBACK_BARS` | 200 | Bars fetched per symbol (drops last in-progress bar) |
| `HIGH_PRIORITY_SCORE` | 4 | Score threshold for HIGH priority signals |
| `MEDIUM_PRIORITY_SCORE` | 2 | Score threshold for MEDIUM priority signals |
| `SLEEPING_THRESHOLD` | 0.2 | Alligator spread < 0.2 × ATR → SLEEPING |
| `EATING_THRESHOLD` | 1.0 | Alligator spread > 1.0 × ATR → EATING |
| `SCAN_HOUR_UTC` | 6 | Cron hour |
| `FETCH_BATCH_SIZE` | 20 | Symbols per async batch |
| `FETCH_BATCH_DELAY` | 0.1s | Delay between batches (rate limiting) |

**Alert credentials** — set via environment variables:
```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
export DISCORD_WEBHOOK_URL="..."
```

---

## Signal Flow

```
Binance /api/v3/ticker/24hr   →   top 100 USDT symbols (by quoteVolume)
Binance /api/v3/klines        →   200 bars 4H OHLCV per symbol (last bar dropped)
                                         ↓
              indicators/alligator.py  — SMMA jaw/teeth/lips + state
              indicators/fractals.py  — confirmed 5-bar fractals
              indicators/ao.py        — AO + Saucer/ZeroCross/TwinPeaks
              indicators/ac.py        — AC + bar-count rules
              indicators/zones.py     — GREEN/RED/GRAY zone
                                         ↓
              signals/score.py        — score_symbol() → list[BWSignal]
                                         score_all()   → sorted list
                                         ↓
              output/formatter.py     — format_report()
              output/notifier.py      — send_telegram / send_discord / log_to_csv
```

---

## Key Data Structure

```python
@dataclass
class BWSignal:
    symbol: str
    direction: str              # 'LONG' | 'SHORT'
    confluence_score: int       # 0-5
    dimensions_active: list[str]
    alligator_state: str        # SLEEPING / AWAKENING / EATING_BULL / EATING_BEAR / SATIATED
    price: float
    entry_stop: float           # 1 tick above fractal high (long) / below low (short)
    alligator_stop: float       # just inside Teeth line
    zone: str                   # GREEN / RED / GRAY
    ao_signal: str | None       # SAUCER / ZERO_CROSS / TWIN_PEAKS
    ac_signal: str | None       # BUY_ABOVE_ZERO / BUY_BELOW_ZERO / BUY_CROSS_ZERO / SELL_*
    fractal_signal: bool
    first_entry: bool           # fractal broke outside Jaw (Blue line)
    zone_exit_warning: bool     # 5 consecutive opposing-zone bars
    timestamp: datetime
    priority: str               # HIGH / MEDIUM / LOW / SKIP
```

**Scoring (0–5):**

| Dimension | Condition for +1 |
|---|---|
| 1 — Fractal | Valid fractal signal in direction |
| 2 — AO | Any AO signal in direction |
| 3 — AC | Any AC signal in direction |
| 4 — Zone | Zone matches direction (GREEN=LONG, RED=SHORT) |
| 5 — Alligator | State is EATING_BULL/BEAR or AWAKENING in direction |

---

## Bill Williams Rules Enforced

1. **No signals while Alligator SLEEPING** — `score_symbol()` returns `[]`
2. **First entry outside Jaw** — fractal must break beyond Blue line; `first_entry=True` flag set
3. **Directional filter** — LONG only if `close > teeth`; SHORT only if `close < teeth`
4. **Closed bars only** — last klines bar dropped (`df.iloc[:-1]`)
5. **AO trigger bar color** — buy signal requires GREEN AO bar; sell requires RED
6. **AC bar rule** — cannot buy on red AC bar; cannot sell on green AC bar
7. **Twin Peaks** — zero cross between the two peaks invalidates the signal
8. **Zone exit** — 5 consecutive opposing-zone bars triggers `zone_exit_warning`
9. **AC crossing zero** — changes bar count (2→3), NOT itself a signal

---

## Indicator Quick Reference

### Alligator
- `mid = (high + low) / 2`
- Jaw (Blue): SMMA(13) shifted +8
- Teeth (Red): SMMA(8) shifted +5
- Lips (Green): SMMA(5) shifted +3
- SMMA uses Wilder smoothing: seed = SMA(period), then `(prev*(n-1) + val) / n`

### Fractals
- 5-bar window, signal bar = bar[2]
- Up fractal: bar[2].high > bars [0,1,3,4] highs
- Down fractal: bar[2].low < bars [0,1,3,4] lows
- Confirmed only after bar[4] closes → last valid signal bar = `len(df)-3`

### AO
- `SMA(mid, 5) - SMA(mid, 34)`
- Green bar: `ao[i] > ao[i-1]`; Red: `ao[i] <= ao[i-1]`

### AC
- `AO - SMA(AO, 5)`
- Buy above zero: 2 consecutive green bars
- Buy below zero: 3 consecutive green bars
- Buy cross-zero: 2 green bars once above zero

### Zones
- GREEN: both AO and AC last bar green
- RED: both red
- GRAY: mixed

---

## Tests

63 unit tests covering all critical BW rules. Notable tests:

- `test_sleeping_on_sideways` — flat market → SLEEPING state
- `test_no_signal_when_sleeping` — score_symbol returns `[]`
- `test_fractal_not_confirmed_without_two_following_bars` — bar[4] required
- `test_twin_peaks_invalidated_by_zero_cross` — zero cross between peaks = no signal
- `test_buy_blocked_on_red_bar` — AC buy must not fire on red bar
- `test_buy_above_zero_requires_two_green_bars` — enforces bar count
- `test_long_exit_on_five_red_zones` — zone exit trigger
