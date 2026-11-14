# TJR Session Bot (MNQ / NQ + GBPJPY)

Use the **Market preset** setting to pick the market:
- **MNQ / NQ:** trades 16:30–17:30 Israel time.
- **GBPJPY:** trades 10:00–12:00 Israel time (London open). It uses only the previous-day and Asia levels, because London is still forming during that window.

Run one chart per market. **Max trades per day** counts each chart separately. For 3 a day in total, set the GBPJPY chart to 2 and the MNQ chart to 1. For 2 in total, set both to 1.

A TradingView strategy that trades the TJR-style model **only between 16:30 and 17:30 Israel time**:

1. **Liquidity sweep:** price wicks through the previous day high/low, Asia high/low or London high/low, then closes back inside the range.
2. **Shift:** a strong candle (body ≥ 1.2 × ATR) closes through the last swing on the other side (CHoCH).
3. **FVG:** a fair value gap forms in that move after the sweep.
4. **Entry:** a limit order at the FVG edge (or its 50% level). The stop goes beyond the sweep wick. The target is the nearest opposite liquidity level that is at least 2R away.
5. **Quality filter:** the default grade **A** also requires the 1-hour structure bias to agree. Grade **A+** also requires SMT divergence with ES.
   - Max 1 trade per day.
   - A setup is skipped if the stop is too big or no clean target exists.
   - Any open trade is closed at 17:30.

It uses `Asia/Jerusalem` time, so Israel's daylight-saving changes are handled. Note: when Israel and the US change clocks on different dates, the window does not line up with the 9:30 NY open (e.g. 16:30 Israel = 8:30 or 10:30 New York).

## 1. Install and backtest
1. Open TradingView and load the chart `CME_MINI:MNQ1!` (or `NQ1!`) on the **1-minute** timeframe.
2. Open the Pine Editor, paste `tjr_ny_open_bot.pine`, click **Save**, then click **Add to chart**.
3. Read the **Strategy Tester** tab: net profit, win rate, profit factor, max drawdown and the list of trades. Check the trades on the chart to see whether they match how you would trade.
4. Adjust the settings (gear icon) and retest: minimum grade, R:R, displacement, risk per trade.

## 2. Paper trade (do this first, for weeks)
Connect the alerts to a **paper / demo** account. Do not use real money yet.
1. Create a free paper account on a connector such as TradersPost or PickMyTrade, linked to a Tradovate or NinjaTrader **demo**. Copy your webhook URL.
2. In TradingView, create an alert on the strategy:
   - Condition: *TJR NY Open Bot*, "Order fills only"
   - Message: `{{strategy.order.alert_message}}`
   - Webhook URL: paste your connector URL
3. Entry alerts send `buy`/`sell` with a stop-loss and take-profit bracket. Exits at window end send `exit`. Check that the JSON format matches what your connector expects.

TradingView webhook alerts require a paid TradingView plan. The chart has to load real-time CME data for the alerts to fire on time.

## 3. Going live (only after the paper results hold up)
Use micro contracts (MNQ, $2 per point) and a small `Risk per trade ($)`. Watch the bot during the window. Connectors, internet and TradingView can fail.

## Important
- This is an automated version of a discretionary method. TJR's own rules may differ from these, and the code makes choices a human would make differently.
- A good backtest does not mean future profits. Most retail day traders lose money. This is not financial advice.
- Prop-firm accounts often have rules about automated trading and news events. Check before connecting one.
