import sys, numpy as np, pandas as pd
sys.path.insert(0, sys.argv[2]); import bt2
S = sys.argv[1]
def resample(ohlc, ts, tf):
    df = pd.DataFrame(np.array(ohlc).T, columns=list("ohlc"), index=ts)
    r = df.resample(tf, label="left", closed="left").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    return r.to_numpy().T, r.index
nq = bt2.load_nq(f"{S}/data"); gj = bt2.load_gj(f"{S}/fx/gj.parquet")
for tf in ("1min", "5min", "15min"):
    rows = []
    for name, d in (("NQ", nq), ("GJ", gj)):
        dd = d if tf == "1min" else resample(*d, tf)
        t = bt2.run(name, *dd, 3); t["mkt"] = name; rows.append(t)
    t = pd.concat(rows).sort_values("time"); t = t[t.groupby("day").cumcount() < 3]
    for name, g in list(t.groupby("mkt")) + [("BOTH", t)]:
        print(f"{tf:6} {name:4} trades {len(g):4}  win {100*(g.pnl>0).mean():4.1f}%  avgR {g.R.mean():+.3f}  total ${g.pnl.sum():8.0f}  ", g.why.value_counts().to_dict())
