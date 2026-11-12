"""Thumbnails for 'How GPS Works': vertical 1080x1920 (Shorts/TikTok cover) and 1280x720."""
import math
import os

from PIL import Image, ImageDraw, ImageFilter

import explainer as E

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def glow_text(img, xy, text, f, fill, glow=(255, 214, 10), stroke=10):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(xy, text, font=f, fill=glow + (200,))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(22)))
    d = ImageDraw.Draw(img)
    d.text(xy, text, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def scene(w, h, cx, cy, s, sats):
    img = Image.new("RGBA", (w, h), E.BG + (255,))
    d = ImageDraw.Draw(img)
    for x, y, z in E.STARS:
        r = 1 + z * 3
        d.ellipse((x * w - r, y * h - r, x * w + r, y * h + r), fill=(150, 160, 200))
    # Earth peeking from the bottom
    E.earth(d, w / 2, h + 120 * s, 470 * s)
    # satellites beaming down
    for k, (px, py) in enumerate(sats):
        E.satellite(d, px, py, 1.3 * s)
        for j in range(3):
            r = (60 + j * 55) * s
            d.arc((px - r, py - r, px + r, py + r), 40 if k == 0 else 100, 80 if k == 0 else 140, fill=(255, 214, 10), width=int(8 * s))
    E.phone(d, cx, cy, 3.0 * s)
    # big red X over the phone
    r = 230 * s
    for dx, dy in [(1, 1), (1, -1)]:
        d.line((cx - r, cy - r * dy, cx + r, cy + r * dy), fill=(0, 0, 0), width=int(62 * s))
        d.line((cx - r, cy - r * dy, cx + r, cy + r * dy), fill=E.RED, width=int(44 * s))
    return img


def centered(img, y, text, size, fill):
    f = E.font(E.FB, size)
    tw = ImageDraw.Draw(img).textlength(text, font=f)
    glow_text(img, ((img.width - tw) / 2, y), text, f, fill)


# vertical (Shorts / TikTok cover)
v = scene(1080, 1920, 540, 1090, 1.0, [(170, 760), (910, 760)])
centered(v, 150, "YOUR PHONE", 128, E.WHITE)
centered(v, 300, "NEVER TALKS", 128, E.WHITE)
centered(v, 450, "TO GPS", 180, E.YELLOW)
centered(v, 1520, "SO HOW DOES IT", 84, E.WHITE)
centered(v, 1620, "FIND YOU?", 110, E.CYAN)
v.convert("RGB").save(os.path.join(OUT, "thumbnail_vertical.png"))

# horizontal (YouTube 16:9)
hz = scene(1280, 720, 1040, 420, 0.6, [(860, 110), (1200, 90)])
d = ImageDraw.Draw(hz)
for i, (txt, size, col) in enumerate([("YOUR PHONE", 110, E.WHITE), ("NEVER TALKS", 110, E.WHITE), ("TO GPS", 150, E.YELLOW)]):
    glow_text(hz, (60, 90 + i * 135), txt, E.font(E.FB, size), col, stroke=8)
hz.convert("RGB").save(os.path.join(OUT, "thumbnail_horizontal.png"))
print("ok")
