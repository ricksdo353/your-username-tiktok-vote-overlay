"""TJR stream copier for DEMO testing.

  python copier.py replay <kick VOD url>        transcribe a past stream -> signals CSV (the backtest input)
  python copier.py review signals/<file>.csv     confirm/reject each detected signal by hand
  python copier.py evaluate signals/*.csv --data <1-min NQ data>   simulate the copied trades
  python copier.py live                         watch the channel live and send DEMO orders by webhook

Needs: ffmpeg, yt-dlp, faster-whisper (see README.md).
"""
import argparse, csv, datetime as dt, glob, json, os, subprocess, sys, time, urllib.request
from collections import deque

from signals import detect

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 16000
FIELDS = ["time_utc", "offset_s", "kind", "side", "phrase", "context", "keep"]


def load_cfg(path):
    with open(path) as f:
        return json.load(f)


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


def log(msg):
    print(f"[{utcnow():%H:%M:%S}] {msg}", flush=True)


def whisper(cfg):
    from faster_whisper import WhisperModel
    return WhisperModel(cfg["whisper_model"], device=cfg.get("whisper_device", "auto"), compute_type="int8")


# ───────────────────────────── replay (backtest input) ─────────────────────────────
def vod_info(url):
    out = subprocess.run(["yt-dlp", "-J", "--no-warnings", url], capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    ts = info.get("release_timestamp") or info.get("timestamp")
    return info, (dt.datetime.fromtimestamp(ts, dt.timezone.utc) if ts else None)


def cmd_replay(a, cfg):
    info, start = vod_info(a.url)
    if a.start:
        start = dt.datetime.fromisoformat(a.start.replace("Z", "+00:00"))
    if start is None:
        sys.exit("Could not read the stream start time. Pass --start 2025-06-03T13:00:00Z (UTC).")
    vid = info.get("id", "vod")
    os.makedirs(f"{HERE}/audio", exist_ok=True); os.makedirs(f"{HERE}/signals", exist_ok=True)
    wav = f"{HERE}/audio/{vid}.wav"
    if not os.path.exists(wav):
        log(f"downloading audio of '{info.get('title', vid)}' ...")
        src = f"{HERE}/audio/{vid}.src"
        subprocess.run(["yt-dlp", "-f", "ba/b", "-o", src, "--no-part", "--no-warnings", a.url], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vn", "-ac", "1", "-ar", str(SR), wav], check=True)
        os.remove(src)
    log(f"stream started {start:%Y-%m-%d %H:%M} UTC; transcribing (this takes a while on CPU) ...")
    segs = list(whisper(cfg).transcribe(wav, language="en", vad_filter=True, word_timestamps=False)[0])
    rows, last = [], {}
    for i, sg in enumerate(segs):
        for kind, side, phrase in detect(sg.text):
            key = (kind, side)
            if sg.start - last.get(key, -1e9) < cfg["cooldown_s"]:
                continue
            last[key] = sg.start
            ctx = " ".join(s.text.strip() for s in segs[max(0, i - 2): i + 3])
            rows.append(dict(time_utc=(start + dt.timedelta(seconds=sg.start)).isoformat(), offset_s=round(sg.start),
                             kind=kind, side=side or "", phrase=phrase, context=ctx, keep=""))
    out = f"{HERE}/signals/{start:%Y%m%d_%H%M}_{vid}.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS); w.writeheader(); w.writerows(rows)
    with open(out.replace(".csv", "_transcript.txt"), "w") as f:
        for sg in segs:
            f.write(f"{int(sg.start)//3600:02d}:{int(sg.start)%3600//60:02d}:{int(sg.start)%60:02d}  {sg.text.strip()}\n")
    log(f"{len(rows)} signals -> {out}")


# ───────────────────────────── review ─────────────────────────────
def cmd_review(a, cfg):
    for path in a.files:
        with open(path) as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if r["keep"] and not a.redo:
                continue
            o = int(float(r["offset_s"]))
            print(f"\n{path}  @ {o//3600}:{o%3600//60:02d}:{o%60:02d} in the VOD  ({r['time_utc']})")
            print(f"  {r['kind'].upper()} {r['side']}   matched: \"{r['phrase']}\"\n  …{r['context']}…")
            ans = input("  real trade signal? [y]es / [n]o / [s]kip / [q]uit: ").strip().lower()
            if ans == "q":
                break
            if ans in ("y", "n"):
                r["keep"] = ans
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, FIELDS); w.writeheader(); w.writerows(rows)
        print(f"saved {path}")


# ───────────────────────────── evaluate (backtest) ─────────────────────────────
def load_prices(src):
    import pandas as pd
    if os.path.isdir(src):
        df = pd.concat([pd.read_parquet(p) for p in sorted(glob.glob(f"{src}/*.parquet"))])
    elif src.endswith(".parquet"):
        df = pd.read_parquet(src)
    else:
        df = pd.read_csv(src)
    df.columns = [c.lower() for c in df.columns]
    tcol = next(c for c in ("timestamp", "time", "datetime", "date") if c in df.columns)
    t = df[tcol]
    t = pd.to_datetime(t, unit="s", utc=True) if pd.api.types.is_numeric_dtype(t) else pd.to_datetime(t, utc=True)
    df = df.assign(t=t).set_index("t").sort_index()[["open", "high", "low", "close"]]
    return df[~df.index.duplicated()]


def cmd_evaluate(a, cfg):
    import numpy as np, pandas as pd
    sig = []
    for p in sorted(sum((glob.glob(x) for x in a.files), [])):
        with open(p) as f:
            for r in csv.DictReader(f):
                if a.all or r["keep"] == "y":
                    sig.append(r)
    if not sig:
        sys.exit("No signals to test. Run `review` first (or pass --all to use every detected signal).")
    sig.sort(key=lambda r: r["time_utc"])
    px = load_prices(a.data)
    E = cfg["eval"]; pv, stop_pts, tgt_pts = E["point_value"], E["stop_points"], E["target_points"]
    delay = pd.Timedelta(seconds=E["delay_seconds"]); max_hold = pd.Timedelta(minutes=cfg["max_hold_minutes"])
    idx = px.index; O, H, L = px.open.to_numpy(), px.high.to_numpy(), px.low.to_numpy()

    def bar_at(t):  # first bar that opens at/after t
        i = idx.searchsorted(t)
        return i if i < len(idx) and idx[i] - t < pd.Timedelta(minutes=5) else None

    trades, pos = [], None
    exits = [pd.Timestamp(r["time_utc"]) + delay for r in sig if r["kind"] == "exit"]
    for r in sig:
        if r["kind"] != "entry":
            continue
        t0 = pd.Timestamp(r["time_utc"]) + delay
        if trades and t0 < trades[-1]["exit_time"]:
            continue                                          # still in the previous copied trade
        i = bar_at(t0)
        if i is None:
            print(f"  no price data at {t0} – skipped"); continue
        side = 1 if r["side"] == "long" else -1
        e = O[i]; stop = e - side*stop_pts; tgt = e + side*tgt_pts
        nxt_exit = next((x for x in exits if x > t0), None)
        x = why = None
        for j in range(i, len(idx)):
            if idx[j] - idx[i] > max_hold:
                x, why = O[j], "max hold"; break
            if nxt_exit is not None and idx[j] >= nxt_exit and j > i:
                x, why = O[j], "his exit"; break
            if (L[j] <= stop) if side > 0 else (H[j] >= stop):
                x, why = stop, "stop"; break
            if (H[j] >= tgt) if side > 0 else (L[j] <= tgt):
                x, why = tgt, "target"; break
        if x is None:
            continue
        pts = (x - e)*side
        trades.append(dict(entry_time=idx[i], exit_time=idx[j], side=r["side"], entry=e, exit=x, why=why, points=pts,
                           usd=pts*pv*E["contracts"] - E["commission_rt"]*E["contracts"], said=r["phrase"]))
    t = pd.DataFrame(trades)
    if t.empty:
        sys.exit("No trades could be simulated (check the price data covers the stream dates).")
    os.makedirs(f"{HERE}/results", exist_ok=True)
    t.to_csv(f"{HERE}/results/copied_trades.csv", index=False)
    eq = t.usd.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max()
    print(t[["entry_time", "side", "entry", "exit", "why", "points", "usd"]].to_string(index=False))
    print(f"\n{len(t)} trades | win rate {100*(t.usd > 0).mean():.0f}% | avg {t.points.mean():+.1f} pts | "
          f"total ${t.usd.sum():,.0f} | max drawdown ${dd:,.0f} | exits {t.why.value_counts().to_dict()}")
    print(f"assumes {E['delay_seconds']}s copy delay, {E['contracts']} contract(s) at ${pv}/pt, "
          f"stop {stop_pts} / target {tgt_pts} pts unless his exit comes first")


# ───────────────────────────── live (demo orders) ─────────────────────────────
def send(cfg, action, qty=None):
    body = {"ticker": cfg["ticker"], "action": action}
    if qty:
        body["quantity"] = qty
    body.update(cfg.get("extra_fields", {}))
    if not cfg.get("webhook_url"):
        log(f"(no webhook set) would send {body}"); return "dry-run"
    req = urllib.request.Request(cfg["webhook_url"], data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return str(r.status)
    except Exception as ex:  # keep running; it's logged
        return f"error: {ex}"


def in_hours(cfg):
    from zoneinfo import ZoneInfo
    now = dt.datetime.now(ZoneInfo(cfg["timezone"])).strftime("%H:%M")
    a, b = cfg["active_hours"]
    return a <= now < b


def cmd_live(a, cfg):
    import numpy as np
    if "demo" not in cfg.get("account_label", "").lower() and not a.i_understand:
        sys.exit("Set \"account_label\" to something containing 'demo' in config.json. This copier is for demo accounts.")
    os.makedirs(f"{HERE}/logs", exist_ok=True)
    logf = f"{HERE}/logs/live_{utcnow():%Y%m%d}.csv"
    new = not os.path.exists(logf)
    lf = open(logf, "a", newline=""); w = csv.writer(lf)
    if new:
        w.writerow(["time_utc", "kind", "side", "phrase", "action", "result", "text"])
    model = whisper(cfg)
    url_page = f"https://kick.com/{cfg['channel']}"
    pos, entered, trades_today, day, last = 0, None, 0, None, {}
    while True:
        try:
            hls = subprocess.run(["yt-dlp", "-g", "--no-warnings", url_page], capture_output=True, text=True, timeout=60).stdout.split()
        except subprocess.TimeoutExpired:
            hls = []
        if not hls:
            log(f"{cfg['channel']} is not live; checking again in 60 s"); time.sleep(60); continue
        log("live – listening")
        ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", hls[0], "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                              stdout=subprocess.PIPE)
        chunk = int(cfg["chunk_seconds"]*SR)*2; tail = deque(maxlen=3)
        prev = np.zeros(0, np.float32)
        while True:
            raw = ff.stdout.read(chunk)
            if not raw:
                log("stream ended"); break
            audio = np.frombuffer(raw, np.int16).astype(np.float32)/32768
            buf = np.concatenate([prev, audio]); prev = audio[-SR*2:]     # 2 s overlap so words aren't cut
            text = " ".join(s.text for s in model.transcribe(buf, language="en", vad_filter=True)[0]).strip()
            if not text:
                continue
            tail.append(text); now = utcnow()
            if a.verbose:
                log(f"“{text}”")
            today = now.date()
            if today != day:
                day, trades_today = today, 0
            if pos and entered and now - entered > dt.timedelta(minutes=cfg["max_hold_minutes"]):
                res = send(cfg, "exit"); w.writerow([now.isoformat(), "exit", "", "max hold", "exit", res, ""]); lf.flush()
                log(f"max hold reached -> exit ({res})"); pos = 0
            for kind, side, phrase in detect(text):
                key = (kind, side)
                if (now - last.get(key, now - dt.timedelta(days=1))).total_seconds() < cfg["cooldown_s"]:
                    continue
                last[key] = now
                action, res = "", ""
                if kind == "exit" and pos:
                    action = "exit"; res = send(cfg, "exit"); pos = 0
                elif kind == "entry":
                    want = 1 if side == "long" else -1
                    if not in_hours(cfg):
                        action = "ignored (outside active hours)"
                    elif pos == want:
                        action = "ignored (already in)"
                    elif trades_today >= cfg["max_trades_per_day"]:
                        action = "ignored (daily limit)"
                    else:
                        if pos:
                            send(cfg, "exit")
                        action = "buy" if want > 0 else "sell"
                        res = send(cfg, action, cfg["quantity"]); pos, entered = want, now; trades_today += 1
                else:
                    action = "ignored (flat)"
                log(f"{kind.upper()} {side or ''} “{phrase}” -> {action} {res}")
                w.writerow([now.isoformat(), kind, side or "", phrase, action, res, " | ".join(tail)]); lf.flush()
        ff.kill()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=f"{HERE}/config.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("replay"); p.add_argument("url"); p.add_argument("--start", help="stream start, UTC ISO time")
    p = sub.add_parser("review"); p.add_argument("files", nargs="+"); p.add_argument("--redo", action="store_true")
    p = sub.add_parser("evaluate"); p.add_argument("files", nargs="+"); p.add_argument("--data", required=True)
    p.add_argument("--all", action="store_true", help="use every detected signal, not only reviewed ones")
    p = sub.add_parser("live"); p.add_argument("--verbose", action="store_true"); p.add_argument("--i-understand", action="store_true")
    a = ap.parse_args()
    cfg_path = a.config if os.path.exists(a.config) else f"{HERE}/config.example.json"
    cfg = load_cfg(cfg_path)
    {"replay": cmd_replay, "review": cmd_review, "evaluate": cmd_evaluate, "live": cmd_live}[a.cmd](a, cfg)


if __name__ == "__main__":
    main()
