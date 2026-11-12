"""
Monte Carlo simulator for a LucidFlex 50K evaluation + first funded payout.

Rules modelled (from public third-party summaries, Nov 2026 - verify on Lucid's site):
  Evaluation : +$3,000 target, $2,000 EOD trailing drawdown (floor starts at $48,000
               and stops trailing at $50,000), 40% consistency (best day <= 40% of
               total profit), optional $1,200 daily loss limit.
  Funded     : floor $48,000 EOD trailing (stops at $50,100), payout needs 5 days
               with >= $150 profit and net profit; payout = min(50% of profit, $2,000),
               minimum request $500 (so >= $1,000 profit needed).

The strategy is modelled per trade: risk R dollars, win k*R, win probability p.
"Edge" is the gross expectancy per trade in R units: edge = p*k - (1-p).
Costs (commission + slippage) are subtracted per trade.

Usage:
  python3 simulate_lucid.py                      # built-in scenarios
  python3 simulate_lucid.py --winrate 0.42 --rr 1.5 --risk 300   # your backtest numbers
"""
import argparse
import random
from dataclasses import dataclass


@dataclass
class Sizing:
    risk: float          # $ risked per trade
    rr: float            # reward : risk
    day_target: float    # stop trading for the day once day P&L >= this
    day_stop: float      # stop trading for the day once day P&L <= -this
    max_trades: int      # max trades per day
    cost: float          # $ commission + slippage per trade


def trade(p, s: Sizing, room):
    """One trade. Risk is cut so a full stop-out can never cross the drawdown floor."""
    risk = min(s.risk, max(room - 50, 0))
    if risk < 40:
        return None
    win = random.random() < p
    return (risk * s.rr if win else -risk) - s.cost * (risk / s.risk)


def run_eval(p, s: Sizing, max_days=60, target=3000, dd=2000, consistency=0.40, dll=1200):
    bal, start = 50000.0, 50000.0
    floor = start - dd
    days = []
    for d in range(1, max_days + 1):
        day = 0.0
        for _ in range(s.max_trades):
            if day >= s.day_target or day <= -s.day_stop or day <= -dll:
                break
            # never let one day exceed the consistency cap once near the target
            r = trade(p, s, bal - floor)
            if r is None:
                break
            day += r
            bal += r
            if bal <= floor:
                return ("fail", d)
        days.append(day)
        profit = bal - start
        if profit >= target and max(days) <= consistency * profit:
            return ("pass", d)
        floor = min(max(floor, bal - dd), start)  # EOD trailing, locks at start balance
    return ("timeout", max_days)


def run_funded(p, s: Sizing, max_days=60, dd=2000):
    bal, start = 50000.0, 50000.0
    floor = start - dd
    good_days = 0
    for d in range(1, max_days + 1):
        day = 0.0
        for _ in range(s.max_trades):
            if day >= s.day_target or day <= -s.day_stop:
                break
            r = trade(p, s, bal - floor)
            if r is None:
                break
            day += r
            bal += r
            if bal <= floor:
                return ("blown", d, 0)
        if day >= 150:
            good_days += 1
        profit = bal - start
        if good_days >= 5 and profit >= 1000:
            return ("payout", d, min(0.5 * profit, 2000) * 0.9)
        floor = min(max(floor, bal - dd), start + 100)
    return ("timeout", max_days, 0)


def scenario(name, edge, rr, ev_s: Sizing, fu_s: Sizing, n=40000, seed=1):
    random.seed(seed)
    p = (1 + edge) / (1 + rr)  # solves p*rr - (1-p) = edge
    pass3 = passed = 0
    days_to_pass = []
    for _ in range(n):
        res, d = run_eval(p, ev_s)
        if res == "pass":
            passed += 1
            days_to_pass.append(d)
            if d <= 3:
                pass3 += 1
    random.seed(seed + 1)
    payouts, amt = 0, 0.0
    m = n // 2
    for _ in range(m):
        res, d, a = run_funded(p, fu_s)
        if res == "payout":
            payouts += 1
            amt += a
    pp = passed / n
    pf = payouts / m
    days_to_pass.sort()
    med = days_to_pass[len(days_to_pass) // 2] if days_to_pass else 0
    return {
        "name": name, "edge": edge, "winrate": p,
        "pass_3d": pass3 / n, "pass_60d": pp, "median_days": med,
        "payout_given_pass": pf, "payout_total": pp * pf,
        "avg_payout": amt / payouts if payouts else 0,
    }


def show(r):
    print(f"\n== {r['name']}  (edge {r['edge']:+.2f}R, win rate {r['winrate']:.0%})")
    print(f"  Pass evaluation within 3 days : {r['pass_3d']:6.1%}")
    print(f"  Pass evaluation within 60 days: {r['pass_60d']:6.1%}   (median {r['median_days']} days)")
    print(f"  First payout, once funded     : {r['payout_given_pass']:6.1%}")
    print(f"  Pass AND first payout         : {r['payout_total']:6.1%}   (avg payout ${r['avg_payout']:,.0f} after 90/10 split)")


# Sizing plans ---------------------------------------------------------------
COST = 12.0  # ~7 MNQ round trip: commissions + 1 tick slippage
FAST = Sizing(risk=600, rr=2.0, day_target=1200, day_stop=600, max_trades=1, cost=COST)   # "pass in 3 days"
STEADY = Sizing(risk=250, rr=2.0, day_target=500, day_stop=500, max_trades=2, cost=COST * 250 / 600)
FUNDED = Sizing(risk=200, rr=2.0, day_target=400, day_stop=400, max_trades=2, cost=COST * 200 / 600)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--winrate", type=float, help="win rate from your backtest, e.g. 0.42")
    ap.add_argument("--rr", type=float, default=2.0, help="average win / average loss")
    ap.add_argument("--risk", type=float, default=250, help="$ risk per trade in the evaluation")
    ap.add_argument("--n", type=int, default=40000)
    a = ap.parse_args()
    if a.winrate:
        edge = a.winrate * a.rr - (1 - a.winrate)
        ev = Sizing(a.risk, a.rr, min(1200, 2 * a.risk * a.rr), 2 * a.risk, 2, COST * a.risk / 600)
        show(scenario("Your backtest", edge, a.rr, ev, FUNDED, n=a.n))
    else:
        for edge in (0.0, 0.10, 0.25):
            show(scenario(f"FAST 3-day plan", edge, 2.0, FAST, FUNDED))
            show(scenario(f"STEADY plan", edge, 2.0, STEADY, FUNDED))
