import sys, numpy as np, pandas as pd
S = sys.argv[1]; g = pd.read_pickle(f"{S}/grid2.pkl"); rng = np.random.default_rng(3)
nq = pd.concat([pd.read_parquet(f"{S}/data/NQ_{y}.parquet", columns=["timestamp"]) for y in range(2015, 2026)])
alldays = pd.DatetimeIndex(nq.timestamp).tz_localize("UTC").tz_convert("Asia/Jerusalem").normalize()
alldays = pd.Index(sorted(set(d for d in alldays.date if d.weekday() < 5))).astype(str)
def sim_funded(day_pnl, H=252):
    bal = peak = 50000.0; good = 0
    for p in day_pnl[:H]:
        bal += p; peak = max(peak, bal); floor = 50100 if peak >= 52100 else peak - 2000
        if bal <= floor: return 0, 0
        if p >= 150: good += 1
        if good >= 5 and bal > 50000: return 1, min(0.5*(bal-50000), 2000)
    return 0, 0
def sim_eval(day_pnl, H=252):
    bal = peak = 50000.0; best = 0
    for p in day_pnl[:H]:
        bal += p; peak = max(peak, bal); best = max(best, p)
        if bal <= peak - 2000: return 0
        if bal >= 53000 and best <= 0.5*(bal-50000): return 1
    return 0
for cfg in ["1min|RR2.0|liquidity|bias", "5min|RR2.0|liquidity|bias", "1min|RR2.0|liquidity|nobias", "1min|RR1.0|fixedR|nobias"]:
    t = g[g.cfg == cfg]; dp = t.groupby("day").pnl.sum().reindex(alldays, fill_value=0).to_numpy()
    out = []
    for risk in (200, 400, 600, 800):
        m = risk/200; F = []; E = []
        for _ in range(4000):
            seq = rng.choice(dp, 252)*m
            F.append(sim_funded(seq)); E.append(sim_eval(seq))
        pr = np.mean([f[0] for f in F]); amt = np.mean([f[1] for f in F if f[0]] or [0])
        out.append(f"${risk}: eval {100*np.mean(E):4.1f}% | funded payout {100*pr:4.1f}% (avg ${amt:,.0f})")
    print(f"{cfg:30} trades/yr {len(t)/10.5:5.1f}  R {t.R.mean():+.3f}\n   " + "\n   ".join(out), flush=True)
