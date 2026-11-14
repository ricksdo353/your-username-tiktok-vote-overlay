---
name: tjr-trading
description: TJR-style (ICT / smart-money) day-trading knowledge — market structure, liquidity, sweeps, BOS/CHoCH, fair value gaps, inverse FVGs, order blocks, SMT divergence, sessions/killzones, the sweep → shift → FVG entry model, and risk management. Use when the user asks about TJR, his bootcamp concepts, analysing a chart/setup with this method, building a trade checklist or journal, or quizzing them on these concepts.
---

# TJR-style trading (ICT / smart-money concepts)

Source note: built from TJR's free public content and secondhand summaries of it,
not from the paid bootcamp. Exact wording/rules in the course may differ. If the
user shares their own bootcamp notes, prefer those over this file.

Always: this is education, not financial advice. Most retail day traders lose
money. Push the user toward backtesting, demo/paper trading, and small fixed risk.

## 1. Market structure
- **Swing high / swing low**: a candle with a lower high (or higher low) on each side.
- **Bullish structure**: higher highs + higher lows. **Bearish**: lower highs + lower lows.
- **BOS (break of structure)**: candle *body closes* beyond the last swing in the
  direction of trend → continuation.
- **CHoCH / MSS (change of character / market structure shift)**: first break of
  the swing *against* the trend → possible reversal. Strongest when it happens
  with displacement (big, fast candles) right after a liquidity sweep.
- Wicks through a level without a close = a sweep, not a break.

## 2. Liquidity
Stops cluster above highs (buy-side liquidity, BSL) and below lows (sell-side, SSL).
Key pools to mark every day:
- Previous day high/low (PDH/PDL), previous week high/low (PWH/PWL)
- Session highs/lows: Asia, London, New York
- Equal highs / equal lows (EQH/EQL) — "obvious" double tops/bottoms
- Trendline liquidity, round numbers
Price is drawn from one pool to the next. A **sweep / raid** is when price takes a
pool (wicks through) and then reverses.

## 3. Price-delivery zones (points of interest)
- **Fair value gap (FVG)**: 3-candle pattern where candle 1's wick and candle 3's
  wick don't overlap — the gap is the imbalance. Bullish FVG = gap below price
  left by an up move; bearish = above price left by a down move. Price often
  returns to it. **Consequent encroachment (CE)** = 50% of the gap.
- **Inverse FVG (IFVG)**: an FVG that price closes fully through; it flips role
  (failed bullish FVG becomes resistance, failed bearish becomes support). Often
  used as the entry trigger after a sweep.
- **Order block (OB)**: last opposite-colored candle before a displacement move
  that breaks structure. Valid zone for a retrace entry.
- **Breaker**: an order block that failed and was traded through; flips role.
- **Premium / discount**: on a swing range, above 50% = premium (look to sell),
  below 50% = discount (look to buy).

## 4. Time — sessions & killzones (New York time)
- Asia ~ 20:00–00:00 → builds a range / liquidity
- London ~ 02:00–05:00 → often sweeps one side of Asia
- New York AM ~ 07:00/08:30–11:00 → main trading window for indices (NQ/ES)
- 09:30 cash open, 10:00 news; avoid trading into high-impact news (CPI, FOMC, NFP).
- Avoid lunch chop (~12:00–13:30). Fewer, better trades inside the window.

## 5. SMT divergence
Compare correlated markets (NQ vs ES, EURUSD vs GBPUSD; DXY inverse). If one makes a
new low and the other fails to (or vice-versa) at a liquidity sweep, that
divergence is extra confirmation of a reversal.

## 6. The model: bias → sweep → shift → entry
1. **Bias (HTF: daily / 4H / 1H)**: read structure, find which liquidity pool is
   the likely draw. Mark PDH/PDL, session highs/lows, HTF FVGs/OBs.
2. **Wait for a sweep** of a marked pool *into* an HTF zone, during a killzone,
   ideally aligned with bias (bullish bias → wait for a sell-side sweep).
3. **Confirmation (LTF: 15m → 5m → 1m)**: displacement + CHoCH/BOS in the new
   direction, and/or an IFVG close-through. SMT divergence = bonus.
4. **Entry**: on the retrace into the FVG created by the displacement (edge or
   CE) or the OB / IFVG.
5. **Stop**: beyond the sweep extreme (the wick that took liquidity).
6. **Targets**: next opposing liquidity pool (e.g. long → PDH / session high /
   EQH). Aim ≥ 2R. Take partials at 1–2R and move stop to breakeven if the plan
   says so.
Confluence checklist (more boxes = higher quality): HTF bias ✔ key level swept ✔
killzone ✔ displacement + CHoCH ✔ FVG/IFVG entry ✔ SMT ✔ ≥2R to clear target ✔.
If it isn't there, no trade.

## 7. Risk & psychology
- Risk a fixed small % per trade (commonly 0.5–1%) or a fixed $ on funded accounts.
- Max trades / max daily loss — stop after hitting it. No revenge trading.
- Size from stop distance: `contracts = risk$ / (stop points × $ per point)`
  (NQ $20/pt, MNQ $2/pt, ES $50/pt, MES $5/pt).
- Journal every trade: date, session, bias, liquidity swept, confirmation, entry
  zone, stop, target, R result, screenshot, emotions, rule breaks.
- Backtest the exact model (100+ samples) before going live; then demo, then small.

## 8. How to use this skill
- Explaining: define the term, then show where it sits in the model (section 6).
- Chart review: ask for/identify bias, which liquidity was swept, the shift, the
  entry zone, stop and target; grade against the checklist; point out what's missing.
- Quizzing: ask one concept question at a time, check the answer, then go harder.
- Never promise results or give "take this trade" signals on live markets.
