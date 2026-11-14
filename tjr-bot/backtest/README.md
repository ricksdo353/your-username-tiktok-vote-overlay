# Backtest

A Python port of `tjr_ny_open_bot.pine`. Data: 1-minute NQ, 2015-01 to 2025-07, from Hugging Face `mdelcristo/NQ-F_1min_OHLCV_Parquet`. Trades are priced as MNQ ($2 per point) with $1.24 round-turn commission and 2 ticks of slippage on stops and market exits.

    python3 backtest.py <data_dir> trades.csv A        # grade A (default bot settings)
    python3 mc.py <dir containing out_A.csv>           # 10,000-trade bootstrap + 50K eval simulation

Grade A result: 160 trades, 34% wins, -0.10R per trade on average, profit factor 0.85, -$2,238 total.
