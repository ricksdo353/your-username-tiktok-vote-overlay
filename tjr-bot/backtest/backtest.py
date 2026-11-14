"""Python port of tjr_ny_open_bot.pine, run on 1-minute NQ (UTC) data, priced as MNQ."""
import sys, glob, json
import numpy as np, pandas as pd

DATA = sys.argv[1]; OUT = sys.argv[2]
GRADE = sys.argv[3] if len(sys.argv) > 3 else "A"
HOLD = len(sys.argv) > 4 and sys.argv[4] == "hold"

P = dict(disp=1.2, minFvgTk=8, maxSetupB=30, pivLen=2, minRR=2.0, maxRR=6.0, stopBufTk=4,
         maxStopPts=40.0, risk=200.0, maxQty=5, maxTrades=1, fillBars=10)
TICK, PV = 0.25, 2.0          # MNQ: $2/pt
COMM_RT = 1.24                # per contract round turn
SLIP_TK = 2                   # on stop / market exits

df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{DATA}/NQ_*.parquet"))])
df = df.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
ts = pd.DatetimeIndex(df.timestamp).tz_localize("UTC")
il = ts.tz_convert("Asia/Jerusalem"); ny = ts.tz_convert("America/New_York")
o, h, l, c = (df[k].to_numpy() for k in ["open", "high", "low", "close"])
n = len(df)
il_min = il.hour * 60 + il.minute; ny_min = ny.hour * 60 + ny.minute
inWin = (il_min >= 16*60+30) & (il_min < 17*60+30)
inSweep = (il_min >= 16*60) & (il_min < 17*60+30)

# trading-session date (CME day starts 18:00 ET)
sess = (ny + pd.Timedelta(hours=6)).normalize().tz_localize(None)
sess_s = pd.Series(sess)
dh = pd.Series(h).groupby(sess_s.values).max(); dl = pd.Series(l).groupby(sess_s.values).min()
pdh = sess_s.map(dh.shift(1)).to_numpy(); pdl = sess_s.map(dl.shift(1)).to_numpy()

def session_levels(mask):
    hi = np.full(n, np.nan); lo = np.full(n, np.nan)
    start = mask & ~np.r_[False, mask[:-1]]
    grp = np.cumsum(start); g = pd.Series(np.where(mask, grp, 0))
    hh = pd.Series(h).groupby(g).max(); ll = pd.Series(l).groupby(g).min()
    end = ~mask & np.r_[False, mask[:-1]]
    idx = np.where(end)[0]
    hi[idx] = hh.loc[grp[idx]].to_numpy(); lo[idx] = ll.loc[grp[idx]].to_numpy()
    return pd.Series(hi).ffill().to_numpy(), pd.Series(lo).ffill().to_numpy()
asiaH, asiaL = session_levels((ny_min >= 20*60) & (ny_min <= 23*60+59))
lonH, lonL = session_levels((ny_min >= 2*60) & (ny_min < 5*60))

# HTF (60m) structure bias, previous completed hour
hr = pd.DataFrame({"h": h, "l": l, "c": c}, index=ny.floor("h")).groupby(level=0).agg({"h": "max", "l": "min", "c": "last"})
H, L, C = hr.h.to_numpy(), hr.l.to_numpy(), hr.c.to_numpy(); m = len(hr)
bias = np.zeros(m, int); b = 0; sh = sl = np.nan
for i in range(m):
    j = i - 3
    if j >= 3:
        if H[j] == H[j-3:j+4].max() and (H[j] > H[j-3:j]).all() and (H[j] >= H[j+1:j+4]).all(): sh = H[j]
        if L[j] == L[j-3:j+4].min() and (L[j] < L[j-3:j]).all() and (L[j] <= L[j+1:j+4]).all(): sl = L[j]
    if not np.isnan(sh) and C[i] > sh: b = 1
    if not np.isnan(sl) and C[i] < sl: b = -1
    bias[i] = b
hbias = pd.Series(bias, index=hr.index).shift(1)
htf = pd.Series(ny.floor("h")).map(hbias).fillna(0).to_numpy()

# ATR (Wilder 14), displacement
tr = np.maximum(h - l, np.maximum(abs(h - np.r_[c[0], c[:-1]]), abs(l - np.r_[c[0], c[:-1]])))
atr = pd.Series(tr).ewm(alpha=1/14, adjust=False).mean().to_numpy()
body = abs(c - o); disp = pd.Series(body).rolling(3).max().to_numpy() >= P["disp"] * atr

# pivots (confirmed pivLen bars later), last swing high/low and its bar
k = P["pivLen"]; w = 2*k+1
rh = pd.Series(h).rolling(w).max().to_numpy(); rl = pd.Series(l).rolling(w).min().to_numpy()
hc = np.r_[np.full(k, np.nan), h[:-k]]; lc = np.r_[np.full(k, np.nan), l[:-k]]
isPH = (hc == rh); isPL = (lc == rl)
lastPH = pd.Series(np.where(isPH, hc, np.nan)).ffill().to_numpy()
lastPL = pd.Series(np.where(isPL, lc, np.nan)).ffill().to_numpy()
lastPHbar = pd.Series(np.where(isPH, np.arange(n) - k, np.nan)).ffill().to_numpy()
lastPLbar = pd.Series(np.where(isPL, np.arange(n) - k, np.nan)).ffill().to_numpy()

h2 = np.r_[np.nan, np.nan, h[:-2]]; l2 = np.r_[np.nan, np.nan, l[:-2]]
bullFvg = (l > h2) & ((l - h2) >= P["minFvgTk"]*TICK)
bearFvg = (h < l2) & ((l2 - h) >= P["minFvgTk"]*TICK)

def swept_low(i):  return any(not np.isnan(v) and l[i] < v and c[i] > v for v in (pdl[i], asiaL[i], lonL[i]))
def swept_high(i): return any(not np.isnan(v) and h[i] > v and c[i] < v for v in (pdh[i], asiaH[i], lonH[i]))

def target(i, e, r, side):
    lv = [v for v in ((pdh[i], asiaH[i], lonH[i]) if side > 0 else (pdl[i], asiaL[i], lonL[i])) if not np.isnan(v)]
    need = e + side*P["minRR"]*r
    cand = [v for v in lv if (v >= need if side > 0 else v <= need)]
    if not cand: return None
    t = min(cand) if side > 0 else max(cand)
    return t if abs(t - e)/r <= P["maxRR"] else None

def grade_ok(biasOk): return True if GRADE == "B" else biasOk

trades = []
idx = np.where(inSweep)[0]
# group consecutive sweep-window bars per day
breaks = np.where(np.diff(idx) > 1)[0] + 1
for block in np.split(idx, breaks):
    if len(block) == 0: continue
    S = {1: dict(st=0), -1: dict(st=0)}
    traded = 0; pos = None
    endbar = block[-1] + 1
    last = endbar + (330 if HOLD else 0)
    for i in range(block[0], min(last + 1, n)):
        if pos is None and i < endbar:
            for side in (1, -1):
                s = S[side]; ext = l[i] if side > 0 else h[i]
                if s["st"] == 0 and (swept_low(i) if side > 0 else swept_high(i)):
                    s.update(st=1, ext=ext, bar=i, ref=lastPH[i] if side > 0 else lastPL[i], shift=False, fvg=None)
                elif s["st"] == 1:
                    if (ext < s["ext"]) if side > 0 else (ext > s["ext"]):
                        s.update(ext=ext, bar=i, shift=False, fvg=None)
                    if side > 0 and isPH[i] and lastPHbar[i] < s["bar"]: s["ref"] = lastPH[i]
                    if side < 0 and isPL[i] and lastPLbar[i] < s["bar"]: s["ref"] = lastPL[i]
                    if side > 0 and bullFvg[i] and i-2 >= s["bar"]: s["fvg"] = (l[i], h2[i])
                    if side < 0 and bearFvg[i] and i-2 >= s["bar"]: s["fvg"] = (l2[i], h[i])
                    if not s["shift"] and not np.isnan(s["ref"]) and disp[i] and (c[i] > s["ref"] if side > 0 else c[i] < s["ref"]):
                        s["shift"] = True
                    other = S[-side]["st"] == 2
                    if i - s["bar"] > P["maxSetupB"] or not inSweep[i]:
                        s["st"] = 0
                    elif s["shift"] and s["fvg"] and inWin[i] and traded < P["maxTrades"] and not other:
                        top, bot = s["fvg"]; e = top if side > 0 else bot
                        stop = s["ext"] - side*P["stopBufTk"]*TICK; r = (e - stop)*side
                        if r > 0 and r <= P["maxStopPts"] and ((c[i] > e) if side > 0 else (c[i] < e)):
                            tp = target(i, e, r, side); q = min(int(P["risk"] // (r*PV)), P["maxQty"])
                            biasOk = htf[i] == side
                            if tp is not None and q >= 1 and grade_ok(biasOk):
                                s.update(st=2, e=e, stop=stop, tp=tp, q=q, arm=i, biasOk=biasOk)
                elif s["st"] == 2 and i > s["arm"]:
                    e, stop, tp = s["e"], s["stop"], s["tp"]
                    filled = (l[i] <= e) if side > 0 else (h[i] >= e)
                    if filled:
                        pos = dict(side=side, e=e, stop=stop, tp=tp, q=s["q"], ent=i, biasOk=s["biasOk"])
                        traded += 1; s["st"] = 0
                        if (l[i] <= stop) if side > 0 else (h[i] >= stop):   # stopped on the fill bar
                            pos.update(x=stop - side*SLIP_TK*TICK, xi=i, why="stop")
                    elif i - s["arm"] >= P["fillBars"] or not inWin[i] or \
                         ((l[i] <= stop or h[i] >= tp) if side > 0 else (h[i] >= stop or l[i] <= tp)):
                        s["st"] = 0
        elif pos is not None and "x" not in pos:
            side = pos["side"]
            if (i >= last) if HOLD else (i >= endbar or not inWin[i]):   # flatten at open
                pos.update(x=o[i] - side*SLIP_TK*TICK, xi=i, why="window end")
            elif (l[i] <= pos["stop"]) if side > 0 else (h[i] >= pos["stop"]):
                px = min(o[i], pos["stop"]) if side > 0 else max(o[i], pos["stop"])
                pos.update(x=px - side*SLIP_TK*TICK, xi=i, why="stop")
            elif (h[i] >= pos["tp"]) if side > 0 else (l[i] <= pos["tp"]):
                pos.update(x=pos["tp"], xi=i, why="target")
        if pos is not None and "x" in pos:
            r_pts = abs(pos["e"] - pos["stop"])
            pnl = (pos["x"] - pos["e"]) * pos["side"] * pos["q"] * PV - COMM_RT * pos["q"]
            trades.append(dict(time=str(il[pos["ent"]]), side="long" if pos["side"] > 0 else "short",
                               entry=pos["e"], stop=pos["stop"], target=pos["tp"], exit=pos["x"], qty=pos["q"],
                               why=pos["why"], pnl=round(pnl, 2), R=round(pnl / (r_pts*pos["q"]*PV), 3),
                               bias=bool(pos["biasOk"])))
            pos = None
            break_after = traded >= P["maxTrades"]
            if break_after: break

t = pd.DataFrame(trades); t.to_csv(OUT, index=False)
print(f"grade {GRADE}: {len(t)} trades, {df.timestamp.iloc[0]} -> {df.timestamp.iloc[-1]}")
if len(t):
    print("win rate %.1f%%  avg R %.3f  total $%.0f  PF %.2f" % ((t.pnl > 0).mean()*100, t.R.mean(), t.pnl.sum(),
          t.pnl[t.pnl > 0].sum() / -t.pnl[t.pnl < 0].sum()))
    print(t.why.value_counts().to_dict())
