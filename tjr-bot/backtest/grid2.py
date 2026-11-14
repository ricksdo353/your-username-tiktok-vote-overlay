import sys, itertools, pandas as pd
sys.path.insert(0, sys.argv[2]); import bt2
from tf import resample
S = sys.argv[1]; nq = bt2.load_nq(f"{S}/data"); d5 = resample(*nq, "5min"); rows = []
for tf, minRR, fixed, bias in itertools.product(("1min", "5min"), (1.0, 1.5, 2.0), (False, True), (True, False)):
    t = bt2.run("NQ", *(nq if tf == "1min" else d5), 3, dict(minRR=minRR, fixed=fixed, bias=bias, maxStopPct=0.3, minFvgPct=0.01))
    t["cfg"] = f"{tf}|RR{minRR}|{'fixedR' if fixed else 'liquidity'}|{'bias' if bias else 'nobias'}"; rows.append(t)
    tr, te = t[t.day < "2022"], t[t.day >= "2022"]
    print(f"{t.cfg.iloc[0]:32} n={len(t):4} win={100*(t.pnl>0).mean():4.1f}%  R train {tr.R.mean():+.3f} (n{len(tr)})  test {te.R.mean():+.3f} (n{len(te)}, win {100*(te.pnl>0).mean():.0f}%)", flush=True)
pd.concat(rows).to_pickle(f"{S}/grid2.pkl")
