"""Two-market port of the TJR bot: NQ (16:30-17:30 IL) + GBPJPY (10:00-12:00 IL). Results in R and $ (risk $200/trade)."""
import sys, glob, numpy as np, pandas as pd
RISK = 200.0

def load_nq(d):
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{d}/NQ_*.parquet"))])
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    ts = pd.DatetimeIndex(df.timestamp).tz_localize("UTC")
    return df[["open", "high", "low", "close"]].to_numpy().T, ts

def load_gj(f):
    df = pd.read_parquet(f); df = df[df.ts >= "2015-01-01"]
    wall = pd.DatetimeIndex(df.ts.dt.tz_localize(None)) - pd.Timedelta(hours=5)   # file clock = NY wall time + 5h
    ts = wall.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")
    ok = ~ts.isna()
    return df[["open", "high", "low", "close"]].to_numpy()[ok].T, ts[ok]

CFG = {
 "NQ": dict(win=(16*60+30, 17*60+30), sweep=(16*60, 17*60+30), tick=0.25, minFvg=2.0, stopBuf=1.0, maxStop=40.0,
            cost_pts=0.62*2/2.0, slip=0.5, sessions=["asia", "london"], int_size=True, pv=2.0),
 "GJ": dict(win=(10*60, 12*60), sweep=(9*60+30, 12*60), tick=0.001, minFvg=0.01, stopBuf=0.005, maxStop=0.25,
            cost_pts=0.015, slip=0.005, sessions=["asia"], int_size=False, pv=None),
}
P = dict(disp=1.2, maxSetupB=30, pivLen=2, minRR=2.0, maxRR=6.0, fillBars=10)

def run(name, ohlc, ts, max_trades, opt=None):
    opt = opt or {}; P = {**globals()["P"], **opt}; FIXED = opt.get("fixed", False); BIAS = opt.get("bias", True)
    cfg = CFG[name]; o, h, l, c = ohlc; n = len(o)
    il = ts.tz_convert("Asia/Jerusalem"); ny = ts.tz_convert("America/New_York")
    ilm = np.asarray(il.hour * 60 + il.minute); nym = np.asarray(ny.hour * 60 + ny.minute)
    inWin = (ilm >= cfg["win"][0]) & (ilm < cfg["win"][1]); inSweep = (ilm >= cfg["sweep"][0]) & (ilm < cfg["sweep"][1])
    sess = pd.Series((ny + pd.Timedelta(hours=7 if name == "GJ" else 6)).normalize().tz_localize(None))
    dh = pd.Series(h).groupby(sess.values).max(); dl = pd.Series(l).groupby(sess.values).min()
    pdh = sess.map(dh.shift(1)).to_numpy(); pdl = sess.map(dl.shift(1)).to_numpy()
    def levels(mask):
        hi = np.full(n, np.nan); lo = np.full(n, np.nan)
        start = mask & ~np.r_[False, mask[:-1]]; grp = np.cumsum(start); g = pd.Series(np.where(mask, grp, 0))
        hh = pd.Series(h).groupby(g).max(); ll = pd.Series(l).groupby(g).min()
        idx = np.where(~mask & np.r_[False, mask[:-1]])[0]
        hi[idx] = hh.loc[grp[idx]].to_numpy(); lo[idx] = ll.loc[grp[idx]].to_numpy()
        return pd.Series(hi).ffill().to_numpy(), pd.Series(lo).ffill().to_numpy()
    LH = [pdh]; LL = [pdl]
    if "asia" in cfg["sessions"]:
        a, b = levels((nym >= 20*60) & (nym <= 23*60+59)); LH.append(a); LL.append(b)
    if "london" in cfg["sessions"]:
        a, b = levels((nym >= 2*60) & (nym < 5*60)); LH.append(a); LL.append(b)
    LH = np.vstack(LH); LL = np.vstack(LL)
    # HTF bias
    hr = pd.DataFrame({"h": h, "l": l, "c": c}, index=ny.floor("h")).groupby(level=0).agg({"h": "max", "l": "min", "c": "last"})
    H, L, C = hr.h.to_numpy(), hr.l.to_numpy(), hr.c.to_numpy(); bias = np.zeros(len(hr), int); b = 0; sh = sl = np.nan
    for i in range(len(hr)):
        j = i - 3
        if j >= 3:
            if (H[j] > H[j-3:j]).all() and (H[j] >= H[j+1:j+4]).all(): sh = H[j]
            if (L[j] < L[j-3:j]).all() and (L[j] <= L[j+1:j+4]).all(): sl = L[j]
        if not np.isnan(sh) and C[i] > sh: b = 1
        if not np.isnan(sl) and C[i] < sl: b = -1
        bias[i] = b
    htf = pd.Series(ny.floor("h")).map(pd.Series(bias, index=hr.index).shift(1)).fillna(0).to_numpy()
    pc = np.r_[c[0], c[:-1]]
    atr = pd.Series(np.maximum(h-l, np.maximum(abs(h-pc), abs(l-pc)))).ewm(alpha=1/14, adjust=False).mean().to_numpy()
    disp = pd.Series(abs(c-o)).rolling(3).max().to_numpy() >= P["disp"]*atr
    k = P["pivLen"]; w = 2*k+1
    hc = np.r_[np.full(k, np.nan), h[:-k]]; lc = np.r_[np.full(k, np.nan), l[:-k]]
    isPH = hc == pd.Series(h).rolling(w).max().to_numpy(); isPL = lc == pd.Series(l).rolling(w).min().to_numpy()
    lastPH = pd.Series(np.where(isPH, hc, np.nan)).ffill().to_numpy(); lastPL = pd.Series(np.where(isPL, lc, np.nan)).ffill().to_numpy()
    PHb = pd.Series(np.where(isPH, np.arange(n)-k, np.nan)).ffill().to_numpy(); PLb = pd.Series(np.where(isPL, np.arange(n)-k, np.nan)).ffill().to_numpy()
    h2 = np.r_[np.nan, np.nan, h[:-2]]; l2 = np.r_[np.nan, np.nan, l[:-2]]
    mf = c*opt["minFvgPct"]/100 if "minFvgPct" in opt else cfg["minFvg"]
    bullF = (l > h2) & ((l-h2) >= mf); bearF = (h < l2) & ((l2-h) >= mf)
    sslS = ((l[None] < LL) & (c[None] > LL)).any(0); bslS = ((h[None] > LH) & (c[None] < LH)).any(0)

    def target(i, e, r, side):
        lv = LH[:, i] if side > 0 else LL[:, i]; lv = lv[~np.isnan(lv)]
        if FIXED: return e + side*P["minRR"]*r
        need = e + side*P["minRR"]*r; cand = lv[lv >= need] if side > 0 else lv[lv <= need]
        if not len(cand): return None
        t = cand.min() if side > 0 else cand.max()
        return t if abs(t-e)/r <= P["maxRR"] else None

    trades = []; idx = np.where(inSweep)[0]
    for block in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1):
        if not len(block): continue
        S = {1: dict(st=0), -1: dict(st=0)}; traded = 0; pos = None; endbar = block[-1] + 1
        for i in range(block[0], min(endbar+1, n)):
            if pos is None and i < endbar and traded < max_trades:
                for side in (1, -1):
                    s = S[side]; ext = l[i] if side > 0 else h[i]
                    if s["st"] == 0 and (sslS[i] if side > 0 else bslS[i]):
                        s.update(st=1, ext=ext, bar=i, ref=lastPH[i] if side > 0 else lastPL[i], shift=False, fvg=None)
                    elif s["st"] == 1:
                        if (ext < s["ext"]) if side > 0 else (ext > s["ext"]): s.update(ext=ext, bar=i, shift=False, fvg=None)
                        if side > 0 and isPH[i] and PHb[i] < s["bar"]: s["ref"] = lastPH[i]
                        if side < 0 and isPL[i] and PLb[i] < s["bar"]: s["ref"] = lastPL[i]
                        if side > 0 and bullF[i] and i-2 >= s["bar"]: s["fvg"] = (l[i], h2[i])
                        if side < 0 and bearF[i] and i-2 >= s["bar"]: s["fvg"] = (l2[i], h[i])
                        if not s["shift"] and not np.isnan(s["ref"]) and disp[i] and (c[i] > s["ref"] if side > 0 else c[i] < s["ref"]): s["shift"] = True
                        if i - s["bar"] > P["maxSetupB"] or not inSweep[i]: s["st"] = 0
                        elif s["shift"] and s["fvg"] and inWin[i] and S[-side]["st"] != 2:
                            top, bot = s["fvg"]; e = top if side > 0 else bot
                            stop = s["ext"] - side*cfg["stopBuf"]; r = (e-stop)*side
                            mx = c[i]*opt["maxStopPct"]/100 if "maxStopPct" in opt else cfg["maxStop"]
                            if 0 < r <= mx and ((c[i] > e) if side > 0 else (c[i] < e)) and (htf[i] == side or not BIAS):
                                tp = target(i, e, r, side)
                                q = min(int(RISK // (r*cfg["pv"])), 5) if cfg["int_size"] else 1
                                if tp is not None and q >= 1: s.update(st=2, e=e, stop=stop, tp=tp, q=q, arm=i)
                    elif s["st"] == 2 and i > s["arm"]:
                        e, stop, tp = s["e"], s["stop"], s["tp"]
                        if (l[i] <= e) if side > 0 else (h[i] >= e):
                            pos = dict(side=side, e=e, stop=stop, tp=tp, q=s["q"], ent=i); traded += 1; s["st"] = 0
                            if (l[i] <= stop) if side > 0 else (h[i] >= stop): pos.update(x=stop - side*cfg["slip"], why="stop")
                            break
                        elif i - s["arm"] >= P["fillBars"] or not inWin[i] or ((l[i] <= stop or h[i] >= tp) if side > 0 else (h[i] >= stop or l[i] <= tp)):
                            s["st"] = 0
            elif pos is not None and "x" not in pos:
                side = pos["side"]
                if i >= endbar or not inWin[i]: pos.update(x=o[i] - side*cfg["slip"], why="window end")
                elif (l[i] <= pos["stop"]) if side > 0 else (h[i] >= pos["stop"]):
                    px = min(o[i], pos["stop"]) if side > 0 else max(o[i], pos["stop"]); pos.update(x=px - side*cfg["slip"], why="stop")
                elif (h[i] >= pos["tp"]) if side > 0 else (l[i] <= pos["tp"]): pos.update(x=pos["tp"], why="target")
            if pos is not None and "x" in pos:
                r_pts = abs(pos["e"] - pos["stop"])
                R = ((pos["x"] - pos["e"])*pos["side"] - cfg["cost_pts"]) / r_pts
                pnl = R * r_pts * pos["q"] * cfg["pv"] if cfg["int_size"] else R * RISK
                trades.append(dict(mkt=name, time=il[pos["ent"]], day=str(il[pos["ent"]].date()), side=pos["side"],
                                   why=pos["why"], R=R, pnl=pnl))
                pos = None
                S = {1: dict(st=0), -1: dict(st=0)}
    return pd.DataFrame(trades)

if __name__ == "__main__":
    S_ = sys.argv[1]
    nq = load_nq(f"{S_}/data"); gj = load_gj(f"{S_}/fx/gj.parquet")
    for mt in (1, 2, 3):
        for name, d in (("NQ", nq), ("GJ", gj)):
            t = run(name, *d, mt); t.to_pickle(f"{S_}/t_{name}_{mt}.pkl")
            print(name, "max/day", mt, "trades", len(t), "win %.1f%%" % ((t.pnl > 0).mean()*100), "avgR %.3f" % t.R.mean(),
                  "total $%.0f" % t.pnl.sum(), t.why.value_counts().to_dict())
