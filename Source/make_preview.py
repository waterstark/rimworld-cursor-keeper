"""Draws About/Preview.png (640x360) for Cursor Keeper.

Run from the repository root:  python3 Source/make_preview.py [path/to/cursor.png]
Needs Pillow and the Avenir Next font that ships with macOS.

The game cursor in the picture is the HSK theme cursor from RimThemesLite
(Themes/-HSK/Textures/CustomCursor.CursorTex.png). It is read from the local
RimWorld install and is not stored in this repository.
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 640, 360
S = 2  # draw at 2x, then downscale for smooth edges
OUT = Path(__file__).resolve().parent.parent / "About" / "Preview.png"
FONT = "/System/Library/Fonts/Avenir Next.ttc"
HSK_CURSOR = (Path.home() / "Desktop/RimWorldMac.app/Mods/RimThemesLite/Themes/-HSK"
              / "Textures/CustomCursor.CursorTex.png")
ORANGE = (236, 140, 40)

BG_TOP = (44, 40, 35)
BG_BOTTOM = (24, 22, 20)
GOLD = (214, 172, 92)
TEXT = (236, 228, 214)
MUTED = (165, 156, 142)
SYSTEM_GREY = (120, 120, 124)


def font(size, index):
    return ImageFont.truetype(FONT, size * S, index=index)


def face_index(wanted):
    """Index of a face in the .ttc by its style name, e.g. "Regular"."""
    for i in range(32):
        try:
            f = ImageFont.truetype(FONT, 10, index=i)
        except OSError:
            break
        if f.getname()[1] == wanted:
            return i
    raise SystemExit(f"font face {wanted!r} not found in {FONT}")


def background():
    img = Image.new("RGB", (W * S, H * S))
    d = ImageDraw.Draw(img)
    for y in range(H * S):
        t = y / (H * S - 1)
        c = tuple(round(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM))
        d.line([(0, y), (W * S, y)], fill=c)
    # faint noise, like the game's panel texture
    rnd = random.Random(7)
    noise = Image.new("L", (W * S, H * S), 0)
    nd = ImageDraw.Draw(noise)
    for _ in range(9000):
        x, y = rnd.randrange(W * S), rnd.randrange(H * S)
        nd.point((x, y), fill=rnd.randrange(10, 26))
    img = Image.composite(Image.new("RGB", img.size, (255, 240, 220)), img, noise)
    # vignette
    vig = Image.new("L", img.size, 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-W * S * 0.25, -H * S * 0.35, W * S * 1.25, H * S * 1.35], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(90 * S))
    img = Image.composite(img, Image.new("RGB", img.size, (12, 11, 10)), vig)
    return img


def arrow_points(x, y, k):
    """Classic pointer shape, tip at (x, y), scaled by k."""
    pts = [(0, 0), (0, 17), (4, 13), (7, 20), (10, 19), (7, 12), (12, 12)]
    return [(x + px * k, y + py * k) for px, py in pts]


def draw_cursor(img, x, y, k, fill, outline, glow=None, alpha=255):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = arrow_points(x, y, k)
    if glow:
        g = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).polygon(pts, fill=glow + (150,))
        g = g.filter(ImageFilter.GaussianBlur(14 * S))
        layer = Image.alpha_composite(layer, g)
        d = ImageDraw.Draw(layer)
    d.polygon(pts, fill=fill + (alpha,), outline=outline + (alpha,))
    d.line(pts + [pts[0]], fill=outline + (alpha,), width=round(1.6 * k), joint="curve")
    return Image.alpha_composite(img.convert("RGBA"), layer)


def draw_texture_cursor(img, path, x, y, size):
    """Pastes the game cursor texture with its tip at (x, y), `size` px tall, with a glow."""
    tex = Image.open(path).convert("RGBA")
    scale = size / tex.height
    # the texture is 33x32 pixel art: enlarge it with hard pixels first, then
    # smooth down to the target size, so it stays crisp instead of blurry
    k = math.ceil(scale)
    crisp = tex.resize((tex.width * k, tex.height * k), Image.NEAREST)
    big = crisp.resize((round(tex.width * scale), round(size)), Image.LANCZOS)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    alpha = big.getchannel("A").point(lambda a: 255 if a > 40 else 0)
    shape = Image.new("RGBA", big.size, ORANGE + (0,))
    shape.putalpha(alpha.point(lambda a: a * 0.55))
    glow.alpha_composite(shape, (round(x), round(y)))
    glow = glow.filter(ImageFilter.GaussianBlur(16 * S))
    img = Image.alpha_composite(img, glow)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dark = Image.new("RGBA", big.size, (0, 0, 0, 0))
    dark.putalpha(alpha.point(lambda a: a * 0.6))
    shadow.alpha_composite(dark, (round(x + 6 * S), round(y + 8 * S)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(5 * S))
    img = Image.alpha_composite(img, shadow)
    img.alpha_composite(big, (round(x), round(y)))
    return img


def draw_return_arc(img, cx, cy, r):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w = 5 * S
    d.arc([cx - r, cy - r, cx + r, cy + r], start=200, end=330, fill=GOLD + (230,), width=w)
    # arrow head at the end of the arc (330 degrees), pointing clockwise
    a = math.radians(330)
    ex, ey = cx + r * math.cos(a), cy + r * math.sin(a)
    tx, ty = -math.sin(a), math.cos(a)  # clockwise tangent
    nx, ny = math.cos(a), math.sin(a)
    h = 15 * S
    head = [
        (ex + tx * h, ey + ty * h),
        (ex + nx * h * 0.7, ey + ny * h * 0.7),
        (ex - nx * h * 0.7, ey - ny * h * 0.7),
    ]
    d.polygon(head, fill=GOLD + (230,))
    return Image.alpha_composite(img, layer)


def main():
    regular, demi, bold = face_index("Medium"), face_index("Demi Bold"), face_index("Bold")
    img = background().convert("RGBA")

    # left: the macOS arrow (faded) and the game cursor coming back
    img = draw_cursor(img, 70 * S, 120 * S, 4.2 * S, SYSTEM_GREY, (40, 40, 42), alpha=120)
    img = draw_return_arc(img, 150 * S, 170 * S, 78 * S)
    cursor = Path(sys.argv[1]) if len(sys.argv) > 1 else HSK_CURSOR
    if cursor.exists():
        img = draw_texture_cursor(img, cursor, 140 * S, 146 * S, 112 * S)
    else:
        print(f"{cursor} not found, drawing a plain arrow instead")
        img = draw_cursor(img, 150 * S, 150 * S, 6.2 * S, (250, 246, 236), (28, 24, 20), glow=GOLD)

    d = ImageDraw.Draw(img)
    x = 288 * S
    d.text((x, 104 * S), "Cursor Keeper", font=font(46, bold), fill=TEXT)
    d.text((x + 2 * S, 166 * S), "macOS only", font=font(26, demi), fill=GOLD)
    d.line([(x + 2 * S, 212 * S), (x + 300 * S, 212 * S)], fill=(90, 80, 66), width=2 * S)
    d.text((x + 2 * S, 226 * S), "Keeps the game cursor in fullscreen.", font=font(17, regular), fill=MUTED)
    d.text((x + 2 * S, 252 * S), "Возвращает игровой курсор на Mac.", font=font(17, regular), fill=MUTED)

    # version pill
    pill = font(13, demi)
    label = "RimWorld 1.6"
    tw = d.textlength(label, font=pill)
    px, py = x + 2 * S, 298 * S
    d.rounded_rectangle([px, py, px + tw + 22 * S, py + 26 * S], radius=13 * S,
                        outline=GOLD + (200,), width=2 * S)
    d.text((px + 11 * S, py + 4 * S), label, font=pill, fill=GOLD)

    # thin frame
    d.rectangle([1 * S, 1 * S, W * S - 2 * S, H * S - 2 * S], outline=(70, 62, 52), width=2 * S)

    img = img.convert("RGB").resize((W, H), Image.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
