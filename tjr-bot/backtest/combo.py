import sys, json, numpy as np, pandas as pd
S = sys.argv[1]; rng = np.random.default_rng(11); out = {}
def ev(seq, days):
    bal = peak = 50000.0
    for k, (p, d) in enumerate(zip(seq, days)):
        bal += p
        if k + 1 == len(seq) or days[k+1] != d:          # end of day: trail the drawdown
            peak = max(peak, bal)
        if bal >= 53000: return "pass", k+1
        if bal <= min(peak - 2000, 50000): return "fail", k+1
    return "open", len(seq)
for cap in (2, 3):
    t = pd.concat([pd.read_pickle(f"{S}/t_NQ_{cap}.pkl"), pd.read_pickle(f"{S}/t_GJ_{cap}.pkl")]).sort_values("time")
    t = t[t.groupby("day").cumcount() < cap]
    pnl = t.pnl.to_numpy(); days = t.day.to_numpy()
    tpd = t.groupby("day").size()
    # 10,000 trades: resample whole trading days so the daily trade count stays realistic
    dg = [g.pnl.to_numpy() for _, g in t.groupby("day")]
    seq, dd = [], []
    while len(seq) < 10000:
        j = rng.integers(len(dg)); seq += list(dg[j]); dd += [len(dd) and dd[-1] + 1 or 1] * len(dg[j])
    seq = np.array(seq[:10000]); dd = np.array(dd[:10000])
    i = 0; res = []
    while i < len(seq):
        r, k = ev(seq[i:], dd[i:]); res.append(r); i += k
        if r == "open": break
    att = []
    for _ in range(10000):
        js = rng.integers(len(dg), size=600); s = np.concatenate([dg[j] for j in js]); d = np.concatenate([[x]*len(dg[j]) for x, j in enumerate(js)])
        att.append(ev(s, d)[0])
    i = 0; real = []
    while i < len(pnl):
        r, k = ev(pnl[i:], days[i:]); real.append(r); i += k
    by_mkt = t.groupby("mkt").agg(n=("pnl", "size"), win=("pnl", lambda x: (x > 0).mean()), R=("R", "mean"), usd=("pnl", "sum"))
    out[cap] = dict(trades=len(t), days=int(len(tpd)), per_day=tpd.value_counts().sort_index().to_dict(),
                    win=float((pnl > 0).mean()), avgR=float(t.R.mean()), total=float(pnl.sum()),
                    pf=float(pnl[pnl > 0].sum() / -pnl[pnl < 0].sum()),
                    by_mkt=by_mkt.round(3).to_dict("index"),
                    tenk_total=float(seq.sum()), tenk_pass=res.count("pass"), tenk_fail=res.count("fail"),
                    pass_rate=float(np.mean([a == "pass" for a in att])),
                    real_evals={x: real.count(x) for x in set(real)})
    print(cap, json.dumps(out[cap], default=str, indent=1))
# GBPJPY before costs (is there any raw edge?)
g = pd.read_pickle(f"{S}/t_GJ_3.pkl"); print("GJ trades with cost removed: avg R ~", round(g.R.mean() + 0.015 / 0.12, 3), "(approx, typical stop 12 pips)")
