"""
Builds a 1080x1920 "Would You Rather" YouTube Short / TikTok with sound effects.
  python3 make_short.py            -> out/would_you_rather.mp4
Edit QUESTIONS to make a new video.
"""
import math
import os
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FRAMES = os.path.join(OUT, "frames")
FONT_B = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
if not os.path.exists(FONT_B):
    FONT_B = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_M = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"

BG = (12, 12, 20)
RED = (255, 59, 92)
BLUE = (47, 123, 255)
WHITE = (255, 255, 255)
YELLOW = (255, 214, 10)

QUESTIONS = [
    ("$1,000,000 right now", "$1 that doubles every day for 30 days"),
    ("Never use your phone again", "Never eat your favorite food again"),
    ("Know WHEN you'll die", "Know HOW you'll die"),
    ("Be able to fly", "Be invisible"),
    ("An AI that does all your work forever", "$50,000 cash today"),
    ("Go viral once", "Be rich but nobody knows you"),
    ("Live without music", "Live without the internet"),
]

INTRO, ROUND, OUTRO = 2.0, 4.6, 5.0
SLIDE, TIMER = 0.35, 3.6  # card slide-in, countdown length


def font(path, size):
    return ImageFont.truetype(path, size)


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def wrap(draw, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=f) <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def text_block(draw, cx, cy, text, max_w, start=92, fill=WHITE, path=FONT_B):
    size = start
    while True:
        f = font(path, size)
        lines = wrap(draw, text, f, max_w)
        lh = int(size * 1.12)
        if len(lines) * lh <= 430 or size < 50:
            break
        size -= 6
    y = cy - len(lines) * lh // 2
    for ln in lines:
        tw = draw.textlength(ln, font=f)
        # shadow for readability
        draw.text((cx - tw / 2 + 4, y + 5), ln, font=f, fill=(0, 0, 0, 140))
        draw.text((cx - tw / 2, y), ln, font=f, fill=fill)
        y += lh


def card(img, box, color, label, text, shake=0):
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((x0, y0 + shake, x1, y1 + shake), radius=48, fill=color + (255,))
    # number badge
    bx, by = x0 + 70, y0 + 70 + shake
    d.ellipse((bx - 48, by - 48, bx + 48, by + 48), fill=WHITE)
    f = font(FONT_B, 64)
    tw = d.textlength(label, font=f)
    d.text((bx - tw / 2, by - 40), label, font=f, fill=color)
    text_block(d, (x0 + x1) / 2, (y0 + y1) / 2 + 20 + shake, text, (x1 - x0) - 120)
    img.alpha_composite(layer)


def faded(img, xy, text, f, color, a):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(xy, text, font=f, fill=color[:3] + (a,))
    img.alpha_composite(layer)


def header(d, title, sub=None):
    f = font(FONT_B, 78)
    tw = d.textlength(title, font=f)
    d.text(((W - tw) / 2, 120), title, font=f, fill=WHITE)
    if sub:
        fs = font(FONT_M, 44)
        sw = d.textlength(sub, font=fs)
        d.text(((W - sw) / 2, 222), sub, font=fs, fill=(170, 170, 190))


def frame_intro(t):
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    s = 1 + 0.06 * math.sin(t * 9)
    f = font(FONT_B, int(150 * s))
    for i, (txt, col) in enumerate([("CHOOSE", WHITE), ("FAST.", YELLOW)]):
        tw = d.textlength(txt, font=f)
        d.text(((W - tw) / 2, 640 + i * 180), txt, font=f, fill=col)
    if t > 0.7:
        a = int(255 * ease((t - 0.7) / 0.3))
        fm = font(FONT_M, 64)
        txt = "The first one is a trap."
        tw = d.textlength(txt, font=fm)
        faded(img, ((W - tw) / 2, 1080), txt, fm, WHITE, a)
    return img


def frame_round(i, t):
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    header(d, "WOULD YOU RATHER", f"{i + 1} / {len(QUESTIONS)}")
    a, b = QUESTIONS[i]
    k = ease(t / SLIDE)
    off = int((1 - k) * W)
    card(img, (60 - off, 330, W - 60 - off, 1000), RED, "1", a)
    card(img, (60 + off, 1060, W - 60 + off, 1730), BLUE, "2", b)
    d = ImageDraw.Draw(img)
    # OR badge
    pulse = 1 + 0.08 * math.sin(t * 10)
    r = int(78 * pulse * k)
    if r > 4:
        d.ellipse((W / 2 - r, 1030 - r, W / 2 + r, 1030 + r), fill=BG, outline=WHITE, width=8)
        f = font(FONT_B, int(54 * pulse))
        tw = d.textlength("OR", font=f)
        d.text((W / 2 - tw / 2, 1030 - 34 * pulse), "OR", font=f, fill=WHITE)
    # countdown bar
    p = max(0.0, 1 - (t - SLIDE) / TIMER)
    col = YELLOW if p > 0.3 else RED
    d.rounded_rectangle((80, 1790, W - 80, 1830), radius=20, fill=(40, 40, 55))
    if p > 0:
        d.rounded_rectangle((80, 1790, 80 + int((W - 160) * p), 1830), radius=20, fill=col)
    secs = math.ceil(p * TIMER) if t > SLIDE else int(TIMER)
    f = font(FONT_B, 48)
    d.text((W - 150, 1712), f"{secs}s", font=f, fill=col)
    # flash at end
    if t > ROUND - 0.15:
        img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (t - (ROUND - 0.15)) / 0.15))))
    return img


def frame_outro(t):
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    f = font(FONT_M, 58)
    lines = ["Remember #1?", "$1 doubled for 30 days ="]
    for j, ln in enumerate(lines):
        tw = d.textlength(ln, font=f)
        d.text(((W - tw) / 2, 470 + j * 90), ln, font=f, fill=(200, 200, 215))
    target = 536_870_912
    shown = int(target * ease(t / 1.6))
    fb = font(FONT_B, 118)
    txt = f"${shown:,}"
    tw = d.textlength(txt, font=fb)
    d.text(((W - tw) / 2, 700), txt, font=fb, fill=YELLOW)
    if t > 1.9:
        a = int(255 * ease((t - 1.9) / 0.4))
        fm = font(FONT_B, 70)
        for j, ln in enumerate(["Comment your answers", "like  1 2 2 1 1 2 1"]):
            tw = d.textlength(ln, font=fm)
            faded(img, ((W - tw) / 2, 1080 + j * 100), ln, fm, WHITE, a)
        fs = font(FONT_M, 50)
        ln = "Who picked the same as you?"
        tw = d.textlength(ln, font=fs)
        faded(img, ((W - tw) / 2, 1330), ln, fs, (170, 170, 190), a)
    return img


# ---------------- audio ----------------
SR = 44100


def tone(freq, dur, decay=30.0, vol=0.5):
    t = np.arange(int(SR * dur)) / SR
    return vol * np.sin(2 * np.pi * freq * t) * np.exp(-decay * t)


def kick():
    t = np.arange(int(SR * 0.35)) / SR
    f = 50 + 90 * np.exp(-25 * t)
    return 0.9 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-9 * t)


def whoosh(dur=0.35):
    n = int(SR * dur)
    noise = np.random.default_rng(1).standard_normal(n)
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    sm = np.convolve(noise, np.ones(30) / 30, mode="same")
    return 0.5 * sm * env


def build_audio(total, path):
    buf = np.zeros(int(SR * (total + 1)))

    def add(sig, at):
        i = int(at * SR)
        buf[i:i + len(sig)] += sig[: len(buf) - i]

    for k in np.arange(0, total - 0.5, 0.5):  # 120 bpm kick bed
        add(kick() * 0.55, k)
    add(tone(880, 0.4, 6, 0.4) + tone(1320, 0.4, 6, 0.25), 0.0)
    t0 = INTRO
    for _ in QUESTIONS:
        add(whoosh(), t0)
        for s in range(int(TIMER)):
            add(tone(1500, 0.05, 60, 0.35), t0 + SLIDE + s)
        add(tone(600, 0.25, 12, 0.5), t0 + SLIDE + TIMER - 0.05)
        t0 += ROUND
    add(whoosh(0.5), t0)
    for j in range(8):  # counter "ka-ching" ticks
        add(tone(1800 + j * 120, 0.06, 40, 0.25), t0 + j * 0.2)
    add(tone(1046, 0.8, 4, 0.45) + tone(1568, 0.8, 4, 0.3), t0 + 1.6)
    buf = buf[: int(SR * total)]
    buf = buf / max(1e-9, np.abs(buf).max()) * 0.85
    pcm = (buf * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    os.makedirs(FRAMES, exist_ok=True)
    total = INTRO + ROUND * len(QUESTIONS) + OUTRO
    n = int(total * FPS)
    for fi in range(n):
        t = fi / FPS
        if t < INTRO:
            img = frame_intro(t)
        elif t < INTRO + ROUND * len(QUESTIONS):
            r = int((t - INTRO) // ROUND)
            img = frame_round(r, t - INTRO - r * ROUND)
        else:
            img = frame_outro(t - INTRO - ROUND * len(QUESTIONS))
        img.convert("RGB").save(os.path.join(FRAMES, f"{fi:05d}.png"), compress_level=1)
    wav = os.path.join(OUT, "audio.wav")
    build_audio(total, wav)
    mp4 = os.path.join(OUT, "would_you_rather.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
        "-i", os.path.join(FRAMES, "%05d.png"), "-i", wav,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", mp4,
    ], check=True)
    for f in os.listdir(FRAMES):
        os.remove(os.path.join(FRAMES, f))
    os.rmdir(FRAMES)
    print(mp4, f"{total:.1f}s")


if __name__ == "__main__":
    main()
