"""
Builds a 1080x1920 "Would You Rather" Short with narration and retention effects.

  python3 make_short.py                 -> out/would_you_rather.mp4
  python3 make_short.py --no-voice      -> same, without narration

Narration uses OpenAI text-to-speech (model gpt-4o-mini-tts). The key comes from
OPENAI_API_KEY (in this cloud environment the network proxy injects it).
Narration clips are cached in out/vo/, so re-renders are free.
Edit QUESTIONS / SCRIPT to make a new video.
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import urllib.request
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FRAMES = os.path.join(OUT, "frames")
VO_DIR = os.path.join(OUT, "vo")
FONT_B = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_M = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"

BG = (12, 12, 20)
RED = (255, 59, 92)
BLUE = (47, 123, 255)
GOLD = (255, 190, 30)
WHITE = (255, 255, 255)
YELLOW = (255, 214, 10)
GREY = (170, 170, 190)

QUESTIONS = [
    ("$1,000,000 right now", "$1 that doubles every day for 30 days"),
    ("Never use your phone again", "Never eat your favorite food again"),
    ("Know WHEN you'll die", "Know HOW you'll die"),
    ("Be able to fly", "Be invisible"),
    ("An AI that does all your work forever", "$50,000 cash today"),
    ("Go viral once", "Be rich but nobody knows you"),
    ("Live without music", "Live without the internet"),
]

INTRO_VO = "You have three seconds to choose. And the first one... is a trap."
ROUND_VO = "Would you rather {a}... or {b}?"
FINAL_VO = "Final one. The hardest. {a}... or {b}?"
OUTRO_VO = ("If you took the million, you lost. One dollar doubled for thirty days "
            "is over five hundred thirty six million dollars. Comment your answers!")
VOICE = "ash"
VOICE_STYLE = ("Energetic, punchy YouTube Shorts narrator. Fast pace, excited, "
               "dramatic pause before 'is a trap' and before 'or'.")

SLIDE, TIMER, GAP = 0.35, 3.0, 0.35
SR = 44100
SR_HALF_BG = None


# ---------------------------------------------------------------- narration
def say(text):
    """Return mono float32 @SR for text (cached), or None if TTS is unavailable."""
    os.makedirs(VO_DIR, exist_ok=True)
    key = hashlib.sha1(f"{VOICE}|{VOICE_STYLE}|{text}".encode()).hexdigest()[:16]
    path = os.path.join(VO_DIR, key + ".wav")
    if not os.path.exists(path):
        body = json.dumps({
            "model": "gpt-4o-mini-tts", "voice": VOICE, "input": text,
            "instructions": VOICE_STYLE, "response_format": "wav",
        }).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/audio/speech", data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + os.environ.get("OPENAI_API_KEY", "sk-proxy-injected")})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
        except Exception as e:  # no key / no network -> silent video
            print("narration unavailable:", e)
            return None
        with open(path, "wb") as f:
            f.write(data)
    return read_wav(path)


def read_wav(path):
    with wave.open(path, "rb") as w:
        sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    if n <= 0 or n > 10**8:  # streamed wav with unknown length
        raw = open(path, "rb").read()[44:]
    a = np.frombuffer(raw[: len(raw) // (sw * ch) * sw * ch], dtype=np.int16).astype(np.float32) / 32768
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    if sr != SR:
        a = np.interp(np.arange(0, len(a), sr / SR), np.arange(len(a)), a)
    # trim silence
    nz = np.where(np.abs(a) > 0.01)[0]
    return a[nz[0]: nz[-1] + 1] if len(nz) else a


# ---------------------------------------------------------------- drawing
_fonts = {}


def font(path, size):
    k = (path, int(size))
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, int(size))
    return _fonts[k]


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def back(t):  # overshoot ease
    t = max(0.0, min(1.0, t))
    c = 1.9
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def background(t, tint):
    """Slowly moving glow blobs, computed small and upscaled."""
    w, h = 54, 96
    y, x = np.mgrid[0:h, 0:w]
    img = np.zeros((h, w, 3), np.float32) + np.array(BG, np.float32)
    for k, col in enumerate([tint, (120, 60, 255)]):
        cx = w * (0.5 + 0.35 * math.sin(t * 0.6 + k * 2.1))
        cy = h * (0.5 + 0.30 * math.cos(t * 0.45 + k * 1.3))
        d = ((x - cx) ** 2 + (y - cy) ** 2) / (w * 0.45) ** 2
        img += np.exp(-d)[..., None] * np.array(col, np.float32) * 0.22
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    return im.convert("RGBA")


def wrap(draw, text, f, max_w):
    lines, cur = [], ""
    for w in text.split():
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=f) <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def text_block(d, cx, cy, text, max_w, start=92, fill=WHITE):
    size = start
    while True:
        f = font(FONT_B, size)
        lines = wrap(d, text, f, max_w)
        lh = int(size * 1.12)
        if len(lines) * lh <= 430 or size < 50:
            break
        size -= 6
    y = cy - len(lines) * lh // 2
    for ln in lines:
        tw = d.textlength(ln, font=f)
        d.text((cx - tw / 2 + 4, y + 5), ln, font=f, fill=(0, 0, 0, 140))
        d.text((cx - tw / 2, y), ln, font=f, fill=fill)
        y += lh


def centered(img, y, text, f, color, a=255, scale=1.0, dx=0):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tw = d.textlength(text, font=f)
    d.text(((W - tw) / 2 + 5 + dx, y + 6), text, font=f, fill=(0, 0, 0, int(a * 0.5)))
    d.text(((W - tw) / 2 + dx, y), text, font=f, fill=color[:3] + (a,))
    if scale != 1.0:
        layer = zoom(layer, scale, (W / 2, y + f.size / 2))
    img.alpha_composite(layer)


def zoom(layer, s, center):
    cx, cy = center
    k = 1 / s
    return layer.transform((W, H), Image.AFFINE, (k, 0, cx - cx * k, 0, k, cy - cy * k), Image.BILINEAR)


def card(img, box, color, label, text, scale=1.0, dim=0.0, dy=0):
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((x0, y0 + dy, x1, y1 + dy), radius=48, fill=color + (255,))
    bx, by = x0 + 70, y0 + 70 + dy
    d.ellipse((bx - 48, by - 48, bx + 48, by + 48), fill=WHITE)
    f = font(FONT_B, 64)
    tw = d.textlength(label, font=f)
    d.text((bx - tw / 2, by - 40), label, font=f, fill=color)
    text_block(d, (x0 + x1) / 2, (y0 + y1) / 2 + 20 + dy, text, (x1 - x0) - 120)
    if dim > 0:
        shade = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(shade).rounded_rectangle((x0, y0 + dy, x1, y1 + dy), radius=48, fill=(0, 0, 0, int(150 * dim)))
        layer.alpha_composite(shade)
    if scale != 1.0:
        layer = zoom(layer, scale, ((x0 + x1) / 2, (y0 + y1) / 2 + dy))
    if scale > 1.0:  # glow behind the active card
        glow = layer.filter(ImageFilter.GaussianBlur(28))
        img.alpha_composite(glow)
    img.alpha_composite(layer)


def progress(d, i, n, final):
    gap, r = 54, 11
    x0 = W / 2 - gap * (n - 1) / 2
    for k in range(n):
        col = (GOLD if final else WHITE) if k <= i else (70, 70, 90)
        rr = r + (5 if k == i else 0)
        d.ellipse((x0 + k * gap - rr, 270 - rr, x0 + k * gap + rr, 270 + rr), fill=col)


# ---------------------------------------------------------------- scenes
def scene_intro(t, dur):
    img = background(t, RED)
    shake = int(10 * math.sin(t * 45) * max(0, 1 - t / 0.5))
    pop = back(t / 0.35)
    centered(img, 560, "YOU HAVE", font(FONT_B, 120), WHITE, scale=max(0.01, pop), dx=shake)
    centered(img, 700, "3 SECONDS", font(FONT_B, 150), YELLOW, scale=max(0.01, pop) * (1 + 0.04 * math.sin(t * 8)), dx=shake)
    ts = 1.1
    if t > ts:
        k = ease((t - ts) / 0.3)
        centered(img, 960, "The first one is a", font(FONT_M, 64), WHITE, a=int(255 * k))
    tt = ts + 0.9
    if t > tt:
        s = 2.2 - 1.2 * ease((t - tt) / 0.22)
        centered(img, 1050, "TRAP", font(FONT_B, 190), RED, scale=s, a=int(255 * ease((t - tt) / 0.15)))
    return img


def scene_round(i, t, dur, read_split, read_end):
    final = i == len(QUESTIONS) - 1
    img = background(t + i * 3, GOLD if final else (BLUE if i % 2 else RED))
    d = ImageDraw.Draw(img)
    title = "FINAL QUESTION" if final else "WOULD YOU RATHER"
    f = font(FONT_B, 80)
    pulse = 1 + (0.05 * math.sin(t * 9) if final else 0)
    centered(img, 120, title, f, GOLD if final else WHITE, scale=pulse)
    progress(d, i, len(QUESTIONS), final)
    a, b = QUESTIONS[i]
    k = back(t / SLIDE)
    off = int((1 - k) * W)
    # highlight the card being read
    act1 = 1.0 if t < read_split else 0.0
    act2 = 1.0 if read_split <= t < read_end else 0.0
    timer_on = t >= read_end
    s1 = 1 + 0.04 * act1
    s2 = 1 + 0.04 * act2
    dim1 = 0.6 * act2
    dim2 = 0.6 * act1 if t > SLIDE else 0
    bob = math.sin(t * 6) * 6 if timer_on else 0
    card(img, (60 - off, 330, W - 60 - off, 1000), RED, "1", a, s1, dim1, int(bob))
    card(img, (60 + off, 1060, W - 60 + off, 1730), BLUE, "2", b, s2, dim2, int(-bob))
    d = ImageDraw.Draw(img)
    # countdown (inside the OR badge) + bar
    p = 1.0 if not timer_on else max(0.0, 1 - (t - read_end) / TIMER)
    col = YELLOW if p > 0.34 else RED
    frac = (p * TIMER) % 1 if timer_on else 0
    p_or = 1 + (0.25 * frac if timer_on else 0.1 * math.sin(t * 10))
    r = int(80 * p_or * ease(t / SLIDE))
    if r > 4:
        ring = col if timer_on else (GOLD if final else WHITE)
        d.ellipse((W / 2 - r, 1030 - r, W / 2 + r, 1030 + r), fill=BG, outline=ring, width=9)
        label = str(max(1, math.ceil(p * TIMER))) if timer_on and p > 0 else "OR"
        fo = font(FONT_B, (80 if timer_on else 54) * p_or)
        tw = d.textlength(label, font=fo)
        d.text((W / 2 - tw / 2, 1030 - fo.size * 0.62), label, font=fo, fill=col if timer_on else WHITE)
    d.rounded_rectangle((80, 1790, W - 80, 1830), radius=20, fill=(40, 40, 55))
    if p > 0:
        d.rounded_rectangle((80, 1790, 80 + int((W - 160) * p), 1830), radius=20, fill=col)
    if t > dur - 0.15:
        img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (t - (dur - 0.15)) / 0.15))))
    return img


def scene_outro(t, dur):
    img = background(t, GOLD)
    centered(img, 430, "Remember #1?", font(FONT_M, 60), GREY)
    centered(img, 520, "$1 doubled for 30 days =", font(FONT_M, 60), GREY)
    target = 536_870_912
    k = ease(t / 2.2)
    shown = int(target * k)
    pop = 1 + (0.12 * math.sin(min(1, (t - 2.2) / 0.3) * math.pi) if t > 2.2 else 0)
    centered(img, 690, f"${shown:,}", font(FONT_B, 118), YELLOW, scale=pop)
    if t > 2.6:
        a = int(255 * ease((t - 2.6) / 0.4))
        centered(img, 960, "vs  $1,000,000", font(FONT_B, 70), RED, a=a)
    if t > dur - 3.2:
        a = int(255 * ease((t - (dur - 3.2)) / 0.4))
        centered(img, 1180, "Comment your answers", font(FONT_B, 72), WHITE, a=a)
        centered(img, 1280, "like  1 2 2 1 1 2 1", font(FONT_B, 72), WHITE, a=a)
        centered(img, 1430, "Who picked the same as you?", font(FONT_M, 50), GREY, a=a)
    return img


# ---------------------------------------------------------------- sfx
def tone(freq, dur, decay=30.0, vol=0.5):
    t = np.arange(int(SR * dur)) / SR
    return vol * np.sin(2 * np.pi * freq * t) * np.exp(-decay * t)


def kick():
    t = np.arange(int(SR * 0.35)) / SR
    f = 50 + 90 * np.exp(-25 * t)
    return 0.9 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-9 * t)


def hat():
    n = int(SR * 0.04)
    return 0.15 * np.random.default_rng(2).standard_normal(n) * np.exp(-np.arange(n) / (SR * 0.008))


def whoosh(dur=0.35):
    n = int(SR * dur)
    noise = np.random.default_rng(1).standard_normal(n)
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    return 0.5 * np.convolve(noise, np.ones(30) / 30, mode="same") * env


def impact():
    t = np.arange(int(SR * 0.6)) / SR
    return 0.9 * np.sin(2 * np.pi * (40 + 60 * np.exp(-12 * t)) * t) * np.exp(-6 * t) + whoosh(0.6) * 0.4


# ---------------------------------------------------------------- build
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-voice", action="store_true")
    ap.add_argument("--name", default="would_you_rather")
    args = ap.parse_args()
    voice = not args.no_voice

    # 1) narration + timeline
    def vo(text):
        return say(text) if voice else None

    segs = []  # (kind, idx, dur, vo, read_split, read_end)
    v = vo(INTRO_VO)
    segs.append(("intro", 0, max(3.0, (len(v) / SR + 0.4) if v is not None else 3.0), v, 0, 0))
    for i, (a, b) in enumerate(QUESTIONS):
        tmpl = FINAL_VO if i == len(QUESTIONS) - 1 else ROUND_VO
        v = vo(tmpl.format(a=a, b=b))
        if v is not None:
            read = len(v) / SR
            split = SLIDE + read * (len(tmpl.split("{b}")[0].format(a=a)) / len(tmpl.format(a=a, b=b)))
            end = SLIDE + read + 0.1
        else:
            split, end = SLIDE + 1.0, SLIDE + 1.6
        segs.append(("round", i, end + TIMER + GAP, v, split, end))
    v = vo(OUTRO_VO)
    segs.append(("outro", 0, max(6.5, (len(v) / SR + 1.2) if v is not None else 6.5), v, 0, 0))
    total = sum(s[2] for s in segs)
    print(f"length {total:.1f}s, narration {'on' if any(s[3] is not None for s in segs) else 'off'}")

    # 2) frames
    os.makedirs(FRAMES, exist_ok=True)
    fi, t0 = 0, 0.0
    starts = []
    for kind, idx, dur, _, split, end in segs:
        starts.append(t0)
        while fi / FPS < t0 + dur and fi / FPS < total:
            t = fi / FPS - t0
            if kind == "intro":
                img = scene_intro(t, dur)
            elif kind == "round":
                img = scene_round(idx, t, dur, split, end)
            else:
                img = scene_outro(t, dur)
            img.convert("RGB").save(os.path.join(FRAMES, f"{fi:05d}.png"), compress_level=1)
            fi += 1
        t0 += dur

    # 3) audio: beat bed (ducked under voice) + sfx + narration
    n = int(SR * (total + 1))
    bed, sfx, voc = np.zeros(n), np.zeros(n), np.zeros(n)

    def add(buf, sig, at):
        i = int(at * SR)
        if i < n:
            buf[i:i + len(sig)] += sig[: n - i]

    for k in np.arange(0, total - 0.4, 0.5):
        add(bed, kick() * 0.6, k)
        add(bed, hat(), k + 0.25)
    for (kind, idx, dur, v, split, end), st in zip(segs, starts):
        if v is not None:
            add(voc, v * 1.0, st + (0.15 if kind != "round" else SLIDE))
        if kind == "intro":
            add(sfx, impact() * 0.7, st)
            add(sfx, impact(), st + 2.0)
        elif kind == "round":
            add(sfx, whoosh(), st)
            for s in range(int(TIMER)):
                add(sfx, tone(1500, 0.05, 60, 0.35), st + end + s)
            add(sfx, tone(600, 0.25, 12, 0.5), st + end + TIMER - 0.05)
        else:
            add(sfx, whoosh(0.5), st)
            for j in range(10):
                add(sfx, tone(1700 + j * 110, 0.06, 40, 0.22), st + j * 0.22)
            add(sfx, tone(1046, 0.9, 4, 0.45) + tone(1568, 0.9, 4, 0.3), st + 2.2)
    env = np.convolve(np.abs(voc), np.ones(4410) / 4410, mode="same")
    duck = 1 - 0.7 * np.clip(env * 12, 0, 1)
    mix = bed * 0.35 * duck + sfx * 0.6 + voc * 1.1
    mix = mix[: int(SR * total)]
    mix = mix / max(1e-9, np.abs(mix).max()) * 0.9
    wav = os.path.join(OUT, "audio.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())

    mp4 = os.path.join(OUT, args.name + ".mp4")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
        "-i", os.path.join(FRAMES, "%05d.png"), "-i", wav,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4,
    ], check=True)
    for f in os.listdir(FRAMES):
        os.remove(os.path.join(FRAMES, f))
    os.rmdir(FRAMES)
    os.remove(wav)
    print(mp4)


if __name__ == "__main__":
    main()
