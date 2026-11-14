# Backtest

A Python port of `tjr_ny_open_bot.pine`. Data: 1-minute NQ, 2015-01 to 2025-07, from Hugging Face `mdelcristo/NQ-F_1min_OHLCV_Parquet`. Trades are priced as MNQ ($2 per point) with $1.24 round-turn commission and 2 ticks of slippage on stops and market exits.

    python3 backtest.py <data_dir> trades.csv A        # grade A (default bot settings)
    python3 mc.py <dir containing out_A.csv>           # 10,000-trade bootstrap + 50K eval simulation

Grade A result: 160 trades, 34% wins, -0.10R per trade on average, profit factor 0.85, -$2,238 total.

## Two markets (bt2.py, combo.py)
GBPJPY 1-minute data comes from Hugging Face `Analyxis/histdata_fx_1m`, 2015 to 2025-03. Costs: 1.5 pips round trip plus 0.5 pip slippage on stops and market exits. Sized to $200 risk per trade.

| | Trades | Win % | Avg R | Total ($200 risk) |
|---|---|---|---|---|
| MNQ 16:30–17:30 | 163 | 34% | −0.10 | −$2,444 |
| GBPJPY 10:00–12:00 | 291 | 32% | −0.17 | −$9,610 |
| Both, max 3 per day | 454 | 33% | −0.14 | −$12,054 |

50K eval (+$3k target, $2k end-of-day trailing drawdown): 6% pass rate.
