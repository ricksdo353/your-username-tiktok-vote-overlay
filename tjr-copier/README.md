# TJR stream copier (demo / backtest only)

It listens to TJR's Kick streams, turns his speech into text and picks out when he says he's in a trade:
- **Entry:** "I'm long", "we're short", "just entered a long", "I shorted"
- **Exit:** "stopped out", "I'm out", "hit my TP", "closed it"

It ignores phrases like "if I'm long", "looking to get short" or "I was long".

**Modes:**
1. **Backtest (`replay` → `review` → `evaluate`):** transcribes past streams (VODs), lets you confirm each detected trade, then simulates copying them on 1-minute NQ data.
2. **Forward test (`live`):** listens live and sends **demo** orders by webhook (TradersPost / PickMyTrade), logging everything.

> Not for a funded account. Kick streams are several seconds behind real time, the speech detection will miss or misread trades, and prop firms (Lucid included) may refuse payouts for copy trading. Kick's terms may also restrict automated access to streams.

## Setup on your computer (Windows / Mac)
1. Install **Python 3.10+** from python.org (on Windows, tick "Add to PATH").
2. Install **ffmpeg**:
   - Windows: `winget install ffmpeg`
   - Mac: `brew install ffmpeg`
3. In a terminal, inside this folder:
   ```
   pip install -r requirements.txt
   copy config.example.json config.json      (Mac: cp config.example.json config.json)
   ```
4. Open `config.json` and check `"channel"`. It must match his Kick URL: for `kick.com/xyz`, put `"xyz"`.

The first run downloads the speech model (`small.en`, about 500 MB). If your PC is slow, change `"whisper_model"` to `"base.en"`.

## 1. Backtest on past streams
```
python copier.py replay https://kick.com/<channel>/videos/<id>
```
This creates `signals/<date>_<id>.csv` (detected trades) and `..._transcript.txt` (the full transcript with times). A 3-hour stream can take 20–60 minutes to transcribe on a normal CPU.

If it says it can't read the start time, find when the stream went live and add `--start 2025-06-03T13:30:00Z` (UTC).

```
python copier.py review signals/*.csv
```
For each detection it shows what he said around it. Type `y` if he really entered or exited, `n` if not. **This step matters:** the auto-detection is not reliable on its own.

```
python copier.py evaluate signals/*.csv --data <price data>
```
`<price data>` is 1-minute NQ prices covering the stream dates. Either:
- a folder of `.parquet` files (free 2015–July 2025 set on Hugging Face: `mdelcristo/NQ-F_1min_OHLCV_Parquet`), or
- a CSV with `time,open,high,low,close` columns (UTC), e.g. exported from your broker for newer dates.

It prints every copied trade, the win rate, total $ and max drawdown, and saves `results/copied_trades.csv`.

Settings under `"eval"` in `config.json`:
- `delay_seconds` (15): how far behind him you'd enter
- `stop_points` / `target_points` (30 / 60): safety stop and target, used unless his exit comes first
- `contracts`, `point_value` (2 = MNQ), `commission_rt`

Run it again with `delay_seconds` set to 5, 15 and 30 to see how much the delay costs.

## 2. Forward test live on demo
1. Make a TradersPost (or PickMyTrade) strategy connected to a **Tradovate demo**.
2. Put its webhook URL in `"webhook_url"`. Leave `"account_label"` containing the word "demo".
3. Check your connector's docs for automatic stop/target fields and add them under `"extra_fields"`. Without them, the copier only exits on his exit phrase or after `max_hold_minutes`.
4. Start it:
   ```
   python copier.py live --verbose
   ```
   It waits until he goes live and listens. When he enters it sends a buy/sell; on his exit, it sends exit.
   - It only acts during `active_hours` (Israel time), at most `max_trades_per_day`.
   - With no webhook set, it runs dry and only logs what it would send.
5. Everything goes to `logs/live_<date>.csv`, including what he said. Compare it with your demo fills after each session.

## Tuning
- **Missed or wrong detections:** add or remove phrases in `signals.py`, then run `python -m unittest test_signals`.
- **Too slow live:** use `base.en`, or lower `chunk_seconds` (faster, but less accurate).
