# Step by step: MNQ on the 5-minute chart (highest win rate tested)

Backtest 2015–2025: 37 trades, **57% wins**, +0.09R per trade on average, +$358 total at $200 risk.
That is only 3–4 trades a year, so the result is not reliable yet. Test it on demo first.

## Part A: Put the bot on the chart
1. Go to tradingview.com and log in.
2. Open a chart and search for **MNQ1!** (Micro E-mini Nasdaq).
3. Set the timeframe to **5 minutes** (type `5` and press Enter).
4. At the bottom, click **Pine Editor**.
5. Delete what's there and paste all of `tjr-bot/tjr_ny_open_bot.pine`.
6. Click **Save**, then **Add to chart**. If a red error appears, copy it and send it to me.

## Part B: Settings (gear icon next to the strategy name)
7. **Market preset:** `MNQ / NQ (16:30-17:30)`
8. **Minimum setup grade:** `A`
9. **Bias timeframe:** `60`
10. **Entry price:** `FVG edge`
11. **Minimum reward:risk:** `2`
12. **Risk per trade ($):** `200` (on a 50K account, don't go above this to start)
13. **Max trades per day:** `3`
14. **Close any open trade when the window ends:** ON
15. Leave everything else at its default and click **OK**.

## Part C: Check the backtest
16. Open the **Strategy Tester** tab at the bottom.
17. Look at net profit, win rate, number of trades and max drawdown.
18. Click a few trades in the **List of trades** and check them on the chart:
    - Did it sweep a level?
    - Was there a strong candle that broke the swing?
    - Did it enter at the gap?

## Part D: What the bot does by itself (each day)
19. It marks yesterday's high/low, the Asia high/low and the London high/low.
20. From 16:00 Israel time it waits for price to **sweep** one of those levels (poke through, then close back).
21. It waits for a **strong candle** that breaks the last swing in the other direction.
22. It finds the **fair value gap** in that move.
23. It only trades in the direction of the **1-hour trend**.
24. Between **16:30 and 17:30** it places a limit order at the gap:
    - stop beyond the sweep wick
    - target = next big level at least 2R away
25. If the order isn't filled within 10 candles, it cancels it. At 17:30 it closes anything still open.

## Part E: Paper trade (at least 1–2 months)
26. Open a free **TradersPost** (or PickMyTrade) account and connect a **Tradovate demo** account.
27. Create a strategy there and copy its **webhook URL**.
28. In TradingView click **Alerts (clock icon) → Create alert**:
    - Condition: `TJR Session Bot` → `Order fills only`
    - Message: `{{strategy.order.alert_message}}`
    - Notifications: tick **Webhook URL** and paste the URL
    - Expiration: open-ended
29. Keep TradingView's real-time CME data on (needs a paid plan for webhooks).
30. Every day, check that the demo account trades match the chart.

## Part F: Only then, the eval
31. Use micro contracts (MNQ) and $200 risk or less.
32. Watch 16:30–17:30. Turn the alert off if you can't watch it.
33. Expect few trades: about 3–4 a year in the backtest. At that pace it won't reach a $3,000 eval target quickly.
