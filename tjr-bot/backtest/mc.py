import sys, json, numpy as np, pandas as pd
S = sys.argv[1]
t = pd.read_csv(f"{S}/out_A.csv"); pnl = t.pnl.to_numpy()
rng = np.random.default_rng(7)
def run_eval(seq, mult=1.0):
    bal, peak = 50000.0, 50000.0
    for k, p in enumerate(seq):
        bal += p*mult; peak = max(peak, bal)
        floor = min(peak - 2000, 50000)
        if bal >= 53000: return "pass", k+1
        if bal <= floor: return "fail", k+1
    return "open", len(seq)

# 1) 10,000 trades in a row, bootstrapped from the 160 real trades
seq = rng.choice(pnl, 10000)
curve = 50000 + np.cumsum(seq)
evals = []; i = 0
while i < len(seq):
    res, k = run_eval(seq[i:]); evals.append((res, k, i)); i += k
    if res == "open": break
passes = sum(r == "pass" for r, *_ in evals); fails = sum(r == "fail" for r, *_ in evals)
out = dict(n_real=len(t), win=float((pnl > 0).mean()), avgR=float(t.R.mean()), pnl_real=float(pnl.sum()),
           pf=float(pnl[pnl > 0].sum()/-pnl[pnl < 0].sum()), exp=float(pnl.mean()),
           tenk_total=float(seq.sum()), tenk_maxdd=float((np.maximum.accumulate(curve)-curve).max()),
           tenk_curve=[round(float(x)) for x in curve[::20]], tenk_passes=passes, tenk_fails=fails,
           tenk_wins=int((seq > 0).sum()))
# 2) pass rate over 10,000 separate eval attempts, at several risk sizes
out["attempts"] = {}
for mult in (1.0, 2.0, 3.0):
    rs = [run_eval(rng.choice(pnl, 2000), mult) for _ in range(10000)]
    out["attempts"][str(int(200*mult))] = dict(pass_rate=float(np.mean([r == "pass" for r, _ in rs])),
        median_trades=float(np.median([k for _, k in rs])))
# 3) the real 2015-2025 trade sequence, eval after eval
i = 0; real = []
while i < len(pnl):
    r, k = run_eval(pnl[i:]); real.append(r); i += k
out["real_evals"] = {x: real.count(x) for x in set(real)}
t["year"] = t.time.str[:4]
out["by_year"] = t.groupby("year").pnl.agg(["size", "sum"]).round(0).reset_index().values.tolist()
out["why"] = t.why.value_counts().to_dict()
out["real_curve"] = [round(float(x)) for x in 50000 + np.cumsum(pnl)]
json.dump(out, open(f"{S}/mc.json", "w"))
print({k: v for k, v in out.items() if "curve" not in k})
