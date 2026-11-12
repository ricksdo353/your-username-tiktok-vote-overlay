"""
"Fruits Confess Their Secrets" - talking cartoon fruits, each with its own Kokoro voice,
lip-synced mouths and a true (surprising) fact.   python3 fruit_secrets.py
"""
import math
import os
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import explainer as E

W, H, FPS, SR = 1080, 1920, 30, 24000
OUT = E.OUT
font = E.font
FB, FM = E.FB, E.FM

# (fruit, voice, pitch, bg colour, narration)
CAST = [
    ("narrator", "am_michael", 1.0, (25, 20, 45),
     "Your fruit has been keeping secrets. And the last one... is kind of terrifying."),
    ("strawberry", "af_bella", 1.12, (255, 120, 150),
     "Okay, confession. I'm not actually a berry. But Banana is."),
    ("banana", "am_puck", 1.12, (255, 210, 70),
     "Yeah, and that's not my only secret. I'm a tiny bit radioactive. Don't worry, you'd need millions of me."),
    ("apple", "bf_emma", 1.1, (120, 200, 110),
     "I float in water, because about a quarter of me is air."),
    ("watermelon", "bm_george", 1.05, (90, 190, 160),
     "Ninety two percent of me is water. I'm basically a drink with a costume."),
    ("pineapple", "am_fenrir", 1.08, (255, 170, 60),
     "And me? While you eat me... I'm eating you back. My enzymes break down your tongue. That's the tingle."),
    ("narrator", "am_michael", 1.0, (25, 20, 45),
     "Which secret shocked you the most? Comment below."),
]
LABELS = {"strawberry": "SECRET #1", "banana": "SECRET #2", "apple": "SECRET #3",
          "watermelon": "SECRET #4", "pineapple": "SECRET #5 😱"}


# ------------------------------------------------------------ fruit drawing
def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def face(d, cx, cy, s, mouth, blink, look=0.0):
    ex = 70 * s
    for sx in (-1, 1):
        x, y = cx + sx * ex, cy - 20 * s
        if blink:
            d.line((x - 32 * s, y, x + 32 * s, y), fill=(30, 20, 20), width=int(8 * s))
            continue
        d.ellipse((x - 38 * s, y - 44 * s, x + 38 * s, y + 44 * s), fill=(255, 255, 255), outline=(30, 20, 20), width=int(5 * s))
        px = x + look * 12 * s
        d.ellipse((px - 18 * s, y - 14 * s, px + 18 * s, y + 22 * s), fill=(30, 20, 20))
        d.ellipse((px - 6 * s, y - 8 * s, px + 4 * s, y + 2 * s), fill=(255, 255, 255))
    # cheeks
    for sx in (-1, 1):
        x = cx + sx * 120 * s
        d.ellipse((x - 26 * s, cy + 30 * s, x + 26 * s, cy + 50 * s), fill=(255, 120, 140))
    # mouth: opens with the voice
    mw, mh = 60 * s, (8 + 70 * mouth) * s
    my = cy + 70 * s
    d.ellipse((cx - mw, my - mh / 2, cx + mw, my + mh / 2), fill=(90, 20, 30), outline=(30, 20, 20), width=int(5 * s))
    if mouth > 0.25:
        d.ellipse((cx - mw * 0.5, my + mh * 0.05, cx + mw * 0.5, my + mh * 0.45), fill=(240, 90, 110))


def strawberry(d, cx, cy, s):
    top = [(cx + 230 * s * math.cos(a), cy - 70 * s + 190 * s * math.sin(a)) for a in np.linspace(math.pi, 2 * math.pi, 30)]
    right = [(cx + 230 * s * (1 - u) ** 0.8, cy - 70 * s + 370 * s * u ** 1.1) for u in np.linspace(0, 1, 20)]
    left = [(cx - 230 * s * (1 - u) ** 0.8, cy - 70 * s + 370 * s * u ** 1.1) for u in np.linspace(1, 0, 20)]
    d.polygon(top + right + left, fill=(230, 40, 60), outline=(150, 20, 40))
    for i in range(34):
        u, v = ((0.5 + i * 0.7548777) % 1), ((0.5 + i * 0.5698403) % 1)
        y = cy - 40 * s + 300 * s * v
        half = 210 * s * max(0.0, 1 - max(0.0, (y - (cy - 70 * s)) / (370 * s))) ** 0.8
        x = cx + (u * 2 - 1) * half * 0.85
        d.ellipse((x - 6 * s, y - 9 * s, x + 6 * s, y + 9 * s), fill=(255, 220, 120))
    for k in range(6):
        a = -math.pi / 2 + (k - 2.5) * 0.45
        d.polygon([(cx, cy - 250 * s), (cx + 170 * s * math.cos(a) - 30 * s, cy - 250 * s + 90 * s * math.sin(a) + 40 * s),
                   (cx + 170 * s * math.cos(a) + 30 * s, cy - 250 * s + 90 * s * math.sin(a) + 40 * s)], fill=(60, 170, 70))


def banana(d, cx, cy, s):
    outer = [(cx + 320 * s * math.cos(a), cy - 120 * s + 380 * s * math.sin(a)) for a in np.linspace(0.35, 2.8, 40)]
    inner = [(cx + 230 * s * math.cos(a), cy - 200 * s + 300 * s * math.sin(a)) for a in np.linspace(2.8, 0.35, 40)]
    d.polygon(outer + inner, fill=(255, 225, 60), outline=(170, 130, 20))
    d.line(outer, fill=(220, 180, 30), width=int(10 * s))
    tip = outer[0]
    d.ellipse((tip[0] - 18 * s, tip[1] - 18 * s, tip[0] + 18 * s, tip[1] + 18 * s), fill=(90, 60, 30))


def apple(d, cx, cy, s):
    for sx in (-1, 1):
        d.ellipse((cx + sx * 90 * s - 190 * s, cy - 200 * s, cx + sx * 90 * s + 190 * s, cy + 220 * s), fill=(220, 30, 40))
    d.ellipse((cx - 150 * s, cy - 170 * s, cx - 60 * s, cy - 60 * s), fill=(255, 120, 120))
    d.line((cx, cy - 190 * s, cx + 20 * s, cy - 290 * s), fill=(100, 60, 30), width=int(18 * s))
    d.ellipse((cx + 20 * s, cy - 300 * s, cx + 140 * s, cy - 240 * s), fill=(70, 170, 70))


def watermelon(d, cx, cy, s):
    box = (cx - 330 * s, cy - 300 * s, cx + 330 * s, cy + 360 * s)
    d.pieslice(box, 0, 180, fill=(40, 140, 60))
    inset = (box[0] + 30 * s, box[1] + 30 * s, box[2] - 30 * s, box[3] - 30 * s)
    d.pieslice(inset, 0, 180, fill=(240, 240, 200))
    inset2 = (box[0] + 50 * s, box[1] + 50 * s, box[2] - 50 * s, box[3] - 50 * s)
    d.pieslice(inset2, 0, 180, fill=(240, 60, 80))
    for i in range(12):
        a = 0.3 + i * 0.22
        r = 200 + (i % 3) * 50
        x, y = cx + r * s * math.cos(a), cy + 30 * s + r * 0.9 * s * math.sin(a)
        if y > cy + 130 * s:
            d.ellipse((x - 9 * s, y - 14 * s, x + 9 * s, y + 14 * s), fill=(30, 20, 20))


def pineapple(d, cx, cy, s):
    for k in range(7):
        a = -math.pi / 2 + (k - 3) * 0.28
        L = (260 - abs(k - 3) * 40) * s
        d.polygon([(cx - 30 * s, cy - 230 * s), (cx + 30 * s, cy - 230 * s),
                   (cx + L * math.cos(a), cy - 230 * s + L * math.sin(a))], fill=(60, 160, 70), outline=(30, 110, 40))
    d.ellipse((cx - 210 * s, cy - 260 * s, cx + 210 * s, cy + 300 * s), fill=(240, 170, 40), outline=(170, 110, 20), width=int(8 * s))
    for r in range(-4, 5):
        for c in range(-3, 4):
            x, y = cx + c * 60 * s + (r % 2) * 30 * s, cy + 20 * s + r * 55 * s
            if ((x - cx) / (190 * s)) ** 2 + ((y - cy - 20 * s) / (260 * s)) ** 2 < 1:
                d.line((x - 18 * s, y - 10 * s, x, y + 8 * s, x + 18 * s, y - 10 * s), fill=(190, 120, 25), width=int(6 * s))


DRAW = {"strawberry": strawberry, "banana": banana, "apple": apple, "watermelon": watermelon, "pineapple": pineapple}
FACE_Y = {"strawberry": 30, "banana": 40, "apple": 20, "watermelon": 90, "pineapple": 40}


def character(img, kind, t, mouth, s=1.0, cx=W / 2, cy=930):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    bounce = 18 * mouth + 8 * math.sin(t * 3)
    cy = cy - bounce
    # shadow
    d.ellipse((cx - 220 * s, 1330, cx + 220 * s, 1380), fill=(0, 0, 0, 70))
    DRAW[kind](d, cx, cy, s)
    blink = (t % 3.1) < 0.12
    face(d, cx, cy + FACE_Y[kind] * s, s * 0.9, mouth, blink, math.sin(t * 0.8))
    tilt = 4 * math.sin(t * 2.2) + 6 * mouth
    layer = layer.rotate(tilt, center=(cx, cy + 300), resample=Image.BICUBIC)
    img.alpha_composite(layer)


# ------------------------------------------------------------ scenes
CONFETTI = np.random.default_rng(9).random((60, 4))


def background(col, t):
    top, bot = shade(col, 1.0), shade(col, 0.55)
    g = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(top) * (1 - g) + np.array(bot) * g) * np.ones((1, W, 1))
    img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img)
    for x, y, sp, c in CONFETTI:
        yy = (y * H + t * 120 * (0.5 + sp)) % H
        r = 6 + 8 * c
        d.ellipse((x * W - r, yy - r, x * W + r, yy + r), fill=(255, 255, 255, 60))
    return img


def label(img, y, text, size, fill, bg=(0, 0, 0)):
    d = ImageDraw.Draw(img)
    f = font(FB, size)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle((W / 2 - tw / 2 - 28, y - 14, W / 2 + tw / 2 + 28, y + size + 18), radius=24, fill=bg)
    d.text((W / 2 - tw / 2, y), text, font=f, fill=fill)


def narrator_scene(img, t, first):
    # all fruits peeking, line-up
    for i, k in enumerate(["strawberry", "banana", "apple", "watermelon", "pineapple"]):
        x = 140 + i * 200
        y = 1050 + 30 * math.sin(t * 4 + i)
        character(img, k, t + i, 0.0, s=0.36, cx=x, cy=y)
    if first:
        label(img, 300, "YOUR FRUIT HAS", 84, (255, 255, 255))
        label(img, 420, "SECRETS", 130, (255, 214, 10))
        if t > 2.6:
            label(img, 1420, "#5 IS TERRIFYING", 70, (255, 80, 90))
    else:
        label(img, 360, "WHICH ONE", 90, (255, 255, 255))
        label(img, 490, "SHOCKED YOU?", 100, (255, 214, 10))
        label(img, 1420, "COMMENT BELOW", 70, (255, 255, 255))


# ------------------------------------------------------------ audio
def voice(text, v, pitch):
    E.VOICE = v
    a = E.tts(text)
    if pitch != 1.0:  # cartoon pitch-up by resampling
        a = np.interp(np.arange(0, len(a), pitch), np.arange(len(a)), a)
    return a


def envelope(a):
    hop = SR // FPS
    env = np.array([np.sqrt((a[i:i + hop] ** 2).mean()) if i < len(a) else 0 for i in range(0, len(a) + hop, hop)])
    env = env / max(1e-6, np.percentile(env, 95))
    return np.clip(env, 0, 1)


def pop_sfx():
    t = np.arange(int(SR * 0.15)) / SR
    return 0.5 * np.sin(2 * np.pi * (300 + 900 * t / 0.15) * t) * np.exp(-18 * t)


def main():
    frames = os.path.join(OUT, "frames_fruit")
    os.makedirs(frames, exist_ok=True)
    clips = [voice(text, v, p) for _, v, p, _, text in CAST]
    GAP = 0.25
    durs = [len(c) / SR + GAP for c in clips]
    total = sum(durs)
    print(f"length {total:.1f}s")
    fi, t0 = 0, 0.0
    for idx, ((kind, _, _, col, text), clip, dur) in enumerate(zip(CAST, clips, durs)):
        env = envelope(clip)
        words = E.word_times(text, dur - GAP)
        while fi / FPS < t0 + dur:
            t = fi / FPS - t0
            img = background(col, fi / FPS)
            m = env[min(len(env) - 1, int(t * FPS))] if t < len(clip) / SR else 0.0
            if kind == "narrator":
                narrator_scene(img, t, idx == 0)
            else:
                k = E.ease(t / 0.3)
                s = 0.3 + 1.0 * k + 0.08 * math.sin(min(1, t / 0.3) * math.pi)
                character(img, kind, t, m, s=s)
                label(img, 230, LABELS[kind].replace(" 😱", "!"), 80, (255, 255, 255))
                label(img, 350, kind.upper(), 64, shade(col, 1.0), bg=(255, 255, 255))
            rgb = img.convert("RGB")
            E.captions(rgb, words, t)
            if t < 0.1:
                rgb = Image.blend(rgb, Image.new("RGB", (W, H), (255, 255, 255)), 0.4 * (1 - t / 0.1))
            rgb.save(os.path.join(frames, f"{fi:05d}.png"), compress_level=1)
            fi += 1
        t0 += dur
    audio = np.zeros(int(SR * (total + 0.5)))
    t0 = 0.0
    for clip, dur in zip(clips, durs):
        i = int(t0 * SR)
        audio[i:i + len(clip)] += clip
        p = pop_sfx()
        audio[i:i + len(p)] += p * 0.6
        t0 += dur
    audio = audio[: int(SR * total)]
    audio = audio / max(1e-9, np.abs(audio).max()) * 0.9
    wav = os.path.join(OUT, "fruit.wav")
    with wave.open(wav, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((audio * 32767).astype(np.int16).tobytes())
    mp4 = os.path.join(OUT, "fruit_secrets.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(frames, "%05d.png"),
                    "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", "-movflags", "+faststart", mp4], check=True)
    for f in os.listdir(frames):
        os.remove(os.path.join(frames, f))
    os.rmdir(frames)
    os.remove(wav)
    print(mp4)


if __name__ == "__main__":
    main()
