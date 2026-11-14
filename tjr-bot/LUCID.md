# Lucid 50K: payout bot, step by step

## What it is
The bot uses the **"MNQ Lucid payout (16:30-17:30)"** preset. It is the same sweep → shift → FVG model, changed to:
- **1-minute chart**, MNQ, trading 16:30–17:30 Israel time
- **Target = fixed 1R.** Small, quick wins instead of far liquidity targets.
- **No 1-hour trend filter**, so more trades (about 80 a year)
- **Stop limits scaled to NQ's price.** Max stop is 0.3% of price, and the minimum fair value gap is 0.01% of price.
- **$400 risk per trade**, up to 10 MNQ

## Simulated results
Rules assumed (LucidFlex 50K, from review sites, not checked on Lucid's site):
- $2,000 end-of-day trailing drawdown; the floor locks at $50,100 once the balance reaches $52,100
- Payout after 5 days of +$150 or more, while in profit
- The payout is 50% of profit, max $2,000

Each number below is from 4,000 simulated one-year runs, built from the real 2015–2025 trade days.

| | Result |
|---|---|
| Win rate (real trades) | ~48% |
| Average per trade | **−0.085R (loses slightly)** |
| Funded account reaches a first payout within 1 year | **~60%** |
| Average first payout | ~$240 (before the split) |
| Eval passed within 1 year | ~5% at $400 risk (12–16% at $600–800 risk) |

**Why the payout chance is high even though the strategy loses:** the first payout only needs 5 days of +$150 before you lose $2,000. A 1R target at $400 risk gets there often. The trades still lose a little on average, so the longer the account runs, the more likely it is to blow.

**Best way to use it:** take the first payout. Then lower your risk, or stop.

## Steps
1. TradingView: open **MNQ1!** on the **1-minute** chart.
2. Paste `tjr_ny_open_bot.pine` into the Pine Editor, **Save**, then **Add to chart**.
3. Settings:
   - Market preset: **MNQ Lucid payout (16:30-17:30)**
   - Risk per trade: **400**
   - Max contracts: **10**
   - Max trades per day: **3**
   - Close at window end: **ON**
4. Strategy Tester: check the trades on the chart.
5. Paper trade first: connect TradersPost or PickMyTrade to a demo account, then create an alert:
   - Condition: "Order fills only"
   - Message: `{{strategy.order.alert_message}}`
   - Webhook: your connector's URL
6. **Before connecting the Lucid account:** confirm in Lucid's rules or support that automated trading through your connector is allowed. Also confirm the 50K drawdown, payout and consistency rules match the ones above.
7. Connect the Lucid account to the connector. Watch every session (16:30–17:30). Request the payout as soon as you're eligible.
