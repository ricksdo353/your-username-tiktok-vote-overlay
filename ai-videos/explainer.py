"""
"How Things Work" explainer Shorts - original animation + Kokoro narration + word captions.

  python3 explainer.py gps            -> out/how_gps_works.mp4

Each episode is a list of scenes: (narration text, draw function). The scene lasts as
long as its narration. Kokoro (Apache-2.0) runs locally from /home/user/models/kokoro.
No licensed music is used (keeps 100% of revenue, no Content ID claims).
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, SR = 1080, 1920, 30, 24000
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
MODEL_DIR = "/home/user/models/kokoro"
VOICE, SPEED = "am_michael", 1.12

FB = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FM = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
BG = (8, 12, 28)
CYAN = (60, 200, 255)
YELLOW = (255, 214, 10)
WHITE = (255, 255, 255)
GREY = (150, 160, 190)
RED = (255, 70, 90)
GREEN = (60, 220, 130)
SERIES = "HOW THINGS WORK"

_f = {}


def font(p, s):
    k = (p, int(s))
    if k not in _f:
        _f[k] = ImageFont.truetype(p, max(8, int(s)))
    return _f[k]


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ctext(d, y, text, f, fill, x=None):
    tw = d.textlength(text, font=f)
    x = W / 2 if x is None else x
    d.text((x - tw / 2 + 4, y + 5), text, font=f, fill=(0, 0, 0))
    d.text((x - tw / 2, y), text, font=f, fill=fill)


# ------------------------------------------------------------- shared props
STARS = np.random.default_rng(5).random((140, 3))


def base(t):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for x, y, s in STARS:
        a = int(90 + 80 * math.sin(t * 2 + s * 20))
        r = 1 + s * 2
        d.ellipse((x * W - r, y * H - r, x * W + r, y * H + r), fill=(a, a, a + 20))
    return img, d


def earth(d, cx, cy, r):
    for k in range(12, 0, -1):  # glow
        rr = r + k * 6
        c = int(10 + (12 - k) * 3)
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(c, c + 10, c + 40))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(30, 90, 200))
    for ox, oy, rx, ry in [(-0.35, -0.2, 0.3, 0.22), (0.25, 0.1, 0.28, 0.35), (-0.1, 0.45, 0.2, 0.12)]:
        d.ellipse((cx + (ox - rx) * r, cy + (oy - ry) * r, cx + (ox + rx) * r, cy + (oy + ry) * r), fill=(50, 170, 100))


def satellite(d, x, y, s=1.0, col=WHITE):
    d.rectangle((x - 16 * s, y - 16 * s, x + 16 * s, y + 16 * s), fill=col)
    for sgn in (-1, 1):
        x0 = x + sgn * 22 * s
        x1 = x + sgn * 70 * s
        d.rectangle((min(x0, x1), y - 11 * s, max(x0, x1), y + 11 * s), fill=CYAN)
        d.line((x + sgn * 16 * s, y, x0, y), fill=GREY, width=max(1, int(3 * s)))


def phone(d, x, y, s=1.0):
    d.rounded_rectangle((x - 60 * s, y - 110 * s, x + 60 * s, y + 110 * s), radius=int(18 * s), fill=(30, 30, 40), outline=WHITE, width=max(2, int(5 * s)))
    d.rounded_rectangle((x - 48 * s, y - 92 * s, x + 48 * s, y + 92 * s), radius=int(8 * s), fill=(20, 60, 110))
    # map pin
    d.ellipse((x - 16 * s, y - 30 * s, x + 16 * s, y + 2 * s), fill=RED)
    d.polygon([(x - 13 * s, y - 6 * s), (x + 13 * s, y - 6 * s), (x, y + 22 * s)], fill=RED)
    d.ellipse((x - 6 * s, y - 20 * s, x + 6 * s, y - 8 * s), fill=WHITE)


def pin(d, x, y, s=1.0, col=RED):
    d.ellipse((x - 26 * s, y - 70 * s, x + 26 * s, y - 18 * s), fill=col)
    d.polygon([(x - 22 * s, y - 34 * s), (x + 22 * s, y - 34 * s), (x, y)], fill=col)
    d.ellipse((x - 10 * s, y - 54 * s, x + 10 * s, y - 34 * s), fill=WHITE)


def label(d, x, y, text, size=48, fill=WHITE, bg=(0, 0, 0)):
    f = font(FB, size)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle((x - tw / 2 - 22, y - 12, x + tw / 2 + 22, y + size + 14), radius=18, fill=bg)
    d.text((x - tw / 2, y), text, font=f, fill=fill)


# ------------------------------------------------------------- GPS episode
def s_hook(t, dur):
    img, d = base(t)
    cx, cy = W / 2, 820
    for k in range(4):  # incoming waves: arcs shrinking toward the phone
        ph = ((t * 0.9 + k / 4) % 1)
        r = 420 * (1 - ph)
        a = int(255 * ph)
        d.arc((cx - r, cy - 120 - r, cx + r, cy - 120 + r), 200, 340, fill=(a // 4, int(a / 1.4), a), width=10)
    phone(d, cx, cy + 40, 2.1 * (0.9 + 0.1 * ease(t / 0.4)))
    if t > 0.9:
        label(d, W / 2, 1220, "SENDS: NOTHING", 64, RED)
    if t > 1.9:
        label(d, W / 2, 1330, "ONLY LISTENS", 64, GREEN)
    return img


def s_constellation(t, dur):
    img, d = base(t)
    cx, cy, r = W / 2, 860, 230
    orbits = [(470, 170, 0.0), (470, 170, 1.05), (470, 170, 2.1)]
    sats = []
    for ox, oy, rot in orbits:
        pts = []
        for k in range(73):
            a = k / 72 * 2 * math.pi
            x, y = ox * math.cos(a), oy * math.sin(a)
            pts.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
        d.line(pts, fill=(50, 70, 120), width=3)
        for j in range(3):
            a = t * 0.5 + j * 2.09 + rot
            x, y = ox * math.cos(a), oy * math.sin(a)
            sats.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot), math.sin(a)))
    for sx, sy, z in sats:
        if z < 0:
            satellite(d, sx, sy, 0.6)
    earth(d, cx, cy, r)
    for sx, sy, z in sats:
        if z >= 0:
            satellite(d, sx, sy, 0.6)
            ph = (t * 1.5 + sx / 300) % 1
            rr = 20 + 60 * ph
            d.ellipse((sx - rr, sy - rr, sx + rr, sy + rr), outline=(int(255 * (1 - ph)), int(214 * (1 - ph)), 10), width=4)
    if t > 0.4:
        label(d, W / 2, 360, "~30 SATELLITES", 70, YELLOW)
    if t > 1.6:
        label(d, W / 2, 470, "20,000 km UP", 56, WHITE)
    if t > 3.0:
        tm = 12 * 3600 + t * 1.0
        s = f"POSITION + TIME  {int(tm // 3600):02d}:{int(tm % 3600 // 60):02d}:{tm % 60:09.6f}"
        label(d, W / 2, 1210, s, 40, CYAN)
    return img


def s_delay(t, dur):
    img, d = base(t)
    sx, sy, px, py = W / 2, 420, W / 2, 1180
    satellite(d, sx, sy, 1.4)
    phone(d, px, py, 1.3)
    d.line((sx, sy + 40, px, py - 150), fill=(40, 60, 100), width=6)
    ph = min(1.0, (t % 2.0) / 1.4)
    yy = sy + 40 + (py - 150 - sy - 40) * ph
    d.ellipse((sx - 22, yy - 22, sx + 22, yy + 22), fill=YELLOW)
    elapsed = 0.067 * ph
    label(d, W / 2 + 250, 760, f"{elapsed:.3f} s", 64, YELLOW)
    if t > 2.0:
        label(d, W / 2 - 230, 760, "x LIGHT SPEED", 46, WHITE)
    if t > 3.2:
        label(d, W / 2, 900, "= 20,000 km", 72, GREEN)
    return img


def s_trilateration(t, dur):
    img, d = base(t)
    target = (W / 2 + 40, 980)
    sats = [(230, 420), (880, 470), (560, 1420)]
    step = dur / 4
    for i, (sx, sy) in enumerate(sats):
        st = i * step
        if t < st:
            continue
        r = math.dist((sx, sy), target)
        k = ease((t - st) / 0.8)
        rr = r * k
        col = [CYAN, YELLOW, GREEN][i]
        d.ellipse((sx - rr, sy - rr, sx + rr, sy + rr), outline=col, width=6)
        satellite(d, sx, sy, 0.8, col)
    if t > 3 * step:
        pin(d, target[0], target[1], 1.6 + 0.2 * math.sin(t * 6))
        label(d, W / 2, 450, "+ 4th = FIXES THE CLOCK", 48, WHITE)
    names = ["1 = A SPHERE", "2 = A CIRCLE", "3 = A POINT"]
    idx = min(2, int(t / step))
    label(d, W / 2, 330, names[idx], 72, [CYAN, YELLOW, GREEN][idx])
    return img


def s_precision(t, dur):
    img, d = base(t)
    label(d, W / 2, 420, "1 MILLIONTH OF A SECOND", 56, YELLOW)
    if t > 1.2:
        label(d, W / 2, 540, "=", 70, WHITE)
        label(d, W / 2, 660, "300 METERS OFF", 84, RED)
    # street grid with a pin jumping
    gx, gy = 140, 900
    for k in range(9):
        d.line((gx, gy + k * 70, W - gx, gy + k * 70), fill=(40, 50, 80), width=3)
        d.line((gx + k * 100, gy, gx + k * 100, gy + 560), fill=(40, 50, 80), width=3)
    pin(d, 360, 1240, 1.3, GREEN)
    if t > 1.2:
        k = ease((t - 1.2) / 0.5)
        pin(d, 360 + 400 * k, 1240 - 120 * k, 1.3, RED)
        d.line((360, 1250, 360 + 400 * k, 1250 - 120 * k), fill=RED, width=5)
    return img


def s_relativity(t, dur):
    img, d = base(t)
    earth(d, W / 2, 1330, 220)
    satellite(d, W / 2, 520, 1.2)

    def clock(x, y, speed, col):
        d.ellipse((x - 90, y - 90, x + 90, y + 90), fill=(20, 25, 45), outline=col, width=8)
        a = t * speed * 2
        d.line((x, y, x + 70 * math.sin(a), y - 70 * math.cos(a)), fill=col, width=8)
    clock(W / 2 + 260, 520, 3.4, YELLOW)
    clock(W / 2 + 280, 1330, 3.0, CYAN)
    label(d, W / 2, 330, "TIME RUNS FASTER UP HERE", 50, YELLOW)
    if t > 1.5:
        label(d, W / 2, 760, "+38 MICROSECONDS / DAY", 54, WHITE)
    if t > 3.2:
        label(d, W / 2, 900, "UNCORRECTED: ~10 km / DAY", 54, RED)
    if t > 4.6:
        label(d, W / 2, 1040, "EINSTEIN WAS RIGHT", 60, GREEN)
    return img


def s_cta(t, dur):
    img, d = base(t)
    phone(d, W / 2, 800, 2.0)
    for k in range(3):
        ph = (t * 0.8 + k / 3) % 1
        r = 200 + 300 * ph
        d.ellipse((W / 2 - r, 800 - r, W / 2 + r, 800 + r), outline=(int(60 * (1 - ph)), int(200 * (1 - ph)), int(255 * (1 - ph))), width=6)
    label(d, W / 2, 1180, "FOLLOW FOR PART 2:", 54, WHITE)
    label(d, W / 2, 1290, "HOW YOUR PHONE KNOWS", 54, YELLOW)
    label(d, W / 2, 1380, "WHICH WAY YOU FACE", 54, YELLOW)
    return img


EPISODES = {
    "gps": ("How GPS Works", [
        ("Your phone has never sent a single message to a GPS satellite. It only listens. So how does it know exactly where you are?", s_hook),
        ("About thirty GPS satellites circle the Earth, twenty thousand kilometers up. Each one keeps broadcasting two things: where it is, and the exact time, from an atomic clock.", s_constellation),
        ("The signal travels at the speed of light. Your phone checks how late it arrived, and turns that tiny delay into a distance.", s_delay),
        ("One satellite puts you somewhere on a giant sphere. Two, on a circle. Three, on a single point. A fourth fixes your phone's cheap clock.", s_trilateration),
        ("The timing is insane. Off by one millionth of a second, and you're three hundred meters off.", s_precision),
        ("And here's the wild part. Up there, time runs faster. The satellite clocks gain thirty eight microseconds a day. Without correcting for Einstein, GPS would drift about ten kilometers every day.", s_relativity),
        ("Follow for part two: how your phone knows which way you're facing.", s_cta),
    ]),
}


# ------------------------------------------------------------- narration
_tts = None


def tts(text):
    global _tts
    if _tts is None:
        from kokoro_onnx import Kokoro
        vpath = os.path.join(MODEL_DIR, "voices.npz")
        if not os.path.exists(vpath):
            vs = {}
            for f in os.listdir(MODEL_DIR):
                if f.endswith(".bin"):
                    vs[f[:-4]] = np.fromfile(os.path.join(MODEL_DIR, f), dtype=np.float32).reshape(-1, 1, 256)
            np.savez(vpath, **vs)
        _tts = Kokoro(os.path.join(MODEL_DIR, "model.onnx"), vpath)
    samples, sr = _tts.create(text, voice=VOICE, speed=SPEED, lang="en-us")
    a = np.asarray(samples, dtype=np.float32)
    if sr != SR:
        a = np.interp(np.arange(0, len(a), sr / SR), np.arange(len(a)), a)
    nz = np.where(np.abs(a) > 0.01)[0]
    return a[nz[0]: nz[-1] + 1] if len(nz) else a


def word_times(text, dur):
    """Approximate per-word timing, weighted by length and punctuation pauses."""
    words = text.split()
    wts = [len(w) + 2 + (5 if w[-1] in ".?!" else 2 if w[-1] in ",:" else 0) for w in words]
    tot = sum(wts)
    out, acc = [], 0.0
    for w, x in zip(words, wts):
        out.append((w, acc / tot * dur, (acc + x) / tot * dur))
        acc += x
    return out


def captions(img, words, t):
    d = ImageDraw.Draw(img)
    idx = next((i for i, (_, a, b) in enumerate(words) if a <= t < b), len(words) - 1)
    g0 = idx - idx % 3
    group = words[g0:g0 + 3]
    f = font(FB, 78)
    parts = [w.upper().strip() for w, _, _ in group]
    tw = sum(d.textlength(p + " ", font=f) for p in parts)
    x = W / 2 - tw / 2
    y = 1560
    for j, p in enumerate(parts):
        active = g0 + j == idx
        col = YELLOW if active else WHITE
        for dx, dy in [(-4, 0), (4, 0), (0, -4), (0, 4), (4, 6)]:
            d.text((x + dx, y + dy), p, font=f, fill=(0, 0, 0))
        d.text((x, y), p, font=f, fill=col)
        x += d.textlength(p + " ", font=f)


def header(img, title):
    d = ImageDraw.Draw(img)
    ctext(d, 110, SERIES, font(FM, 40), GREY)
    ctext(d, 165, title.upper(), font(FB, 64), WHITE)


# ------------------------------------------------------------- sfx
def whoosh(dur=0.3):
    n = int(SR * dur)
    noise = np.random.default_rng(1).standard_normal(n)
    return 0.25 * np.convolve(noise, np.ones(25) / 25, mode="same") * np.sin(np.linspace(0, np.pi, n)) ** 2


def build(ep):
    title, scenes = EPISODES[ep]
    os.makedirs(OUT, exist_ok=True)
    frames = os.path.join(OUT, "frames_" + ep)
    os.makedirs(frames, exist_ok=True)
    clips = []
    for text, _ in scenes:
        try:
            v = tts(text)
        except Exception as e:
            print("TTS unavailable, silent draft:", e)
            v = np.zeros(int(SR * len(text.split()) / 2.9))
        clips.append(v)
    GAP = 0.18
    durs = [len(v) / SR + GAP for v in clips]
    total = sum(durs)
    print(f"{title}: {total:.1f}s")
    fi, t0 = 0, 0.0
    for (text, fn), dur in zip(scenes, durs):
        words = word_times(text, dur - GAP)
        while fi / FPS < t0 + dur:
            t = fi / FPS - t0
            img = fn(t, dur)
            header(img, title)
            captions(img, words, t)
            if t < 0.12:  # quick cut flash
                img = Image.blend(img, Image.new("RGB", (W, H), WHITE), 0.35 * (1 - t / 0.12))
            img.save(os.path.join(frames, f"{fi:05d}.png"), compress_level=1)
            fi += 1
        t0 += dur
    audio = np.zeros(int(SR * (total + 0.5)))
    t0 = 0.0
    for v, dur in zip(clips, durs):
        i = int(t0 * SR)
        audio[i:i + len(v)] += v
        w = whoosh()
        audio[i:i + len(w)] += w
        t0 += dur
    audio = audio[: int(SR * total)]
    audio = audio / max(1e-9, np.abs(audio).max()) * 0.9
    wav = os.path.join(OUT, ep + ".wav")
    with wave.open(wav, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((audio * 32767).astype(np.int16).tobytes())
    mp4 = os.path.join(OUT, f"how_{ep}_works.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(frames, "%05d.png"),
                    "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", "-movflags", "+faststart", mp4], check=True)
    for f in os.listdir(frames):
        os.remove(os.path.join(frames, f))
    os.rmdir(frames)
    os.remove(wav)
    print(mp4)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "gps")
