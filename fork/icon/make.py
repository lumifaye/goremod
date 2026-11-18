#!/usr/bin/env python3
"""Makes every icon file of the fork from the picture `Untitled.png` in the top folder of this repository.

    python3 fork/icon/make.py          (needs Pillow: pip install pillow)

Run it again after the picture has changed, and commit what it writes next to itself; `fork/apply.py`
only copies those files into the game (a build has no Pillow).

The picture need not be square: it is centred on a square of the colour of its top left corner.
"""
import os
import struct
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "..", "..", "Untitled.png")

ANDROID = {"mdpi": 1.0, "hdpi": 1.5, "xhdpi": 2.0, "xxhdpi": 3.0, "xxxhdpi": 4.0}
FOREGROUND_PART = 0.62


def square(path):
    picture = Image.open(path).convert("RGBA")
    colour = picture.getpixel((0, 0))
    side = max(picture.size)
    out = Image.new("RGBA", (side, side), colour)
    out.paste(picture, ((side - picture.width) // 2, (side - picture.height) // 2), picture)
    return out, colour


def sized(picture, size):
    return picture.resize((size, size), Image.LANCZOS)


def cut(picture, size, radius):
    """The picture at `size`, its corners rounded with `radius` (as a part of the side; 0.5 = a circle)."""
    big = 4
    mask = Image.new("L", (size * big, size * big), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size * big - 1, size * big - 1), radius=int(size * big * radius),
                                           fill=255)
    out = sized(picture, size)
    out.putalpha(mask.resize((size, size), Image.LANCZOS))
    return out


def on_canvas(picture, size, part, colour):
    """A square of `size` in `colour` with the picture, `part` of the side, in its middle."""
    out = Image.new("RGBA", (size, size), colour)
    inner = int(round(size * part))
    small = sized(picture, inner)
    out.paste(small, ((size - inner) // 2, (size - inner) // 2), small)
    return out


def ico(picture, path):
    """A Windows icon: PNG entries are understood from Windows Vista on, but the small sizes are kept as
    plain bitmaps, which is what the tools that read the game's icon (windres, the Explorer) expect."""
    sizes = [16, 24, 32, 48, 64, 128, 256]
    entries = []
    for size in sizes:
        image = sized(picture, size)
        if size == 256:
            import io
            data = io.BytesIO()
            image.save(data, "PNG", optimize=True)
            entries.append((size, data.getvalue()))
            continue
        pixels = image.tobytes("raw", "BGRA")
        rows = [pixels[y * size * 4:(y + 1) * size * 4] for y in range(size)]
        colour_part = b"".join(reversed(rows))
        mask_row = b"\0" * (((size + 31) // 32) * 4)
        header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0, len(colour_part) + len(mask_row) * size,
                             0, 0, 0, 0)
        entries.append((size, header + colour_part + mask_row * size))
    out = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    for size, data in entries:
        out += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    for _, data in entries:
        out += data
    with open(path, "wb") as f:
        f.write(out)


def main():
    picture, colour = square(SOURCE)

    def out(name):
        path = os.path.join(HERE, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    ico(picture, out("icon.ico"))

    mac = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    inner = cut(picture, 824, 0.225)
    mac.paste(inner, (100, 100), inner)
    mac.save(out("icon.icns"), "ICNS")
    sized(picture, 256).save(out("icon.png"), optimize=True)

    with open(out("window-64.rgba"), "wb") as f:
        f.write(cut(picture, 64, 0.16).tobytes("raw", "RGBA"))

    for name, scale in ANDROID.items():
        size = int(48 * scale)
        cut(picture, size, 0.16).save(out("android/mipmap-%s/ic_launcher.png" % name), optimize=True)
        cut(on_canvas(picture, size * 4, 0.80, colour), size, 0.5).save(
            out("android/mipmap-%s/ic_launcher_round.png" % name), optimize=True)
        size = int(108 * scale)
        on_canvas(picture, size, FOREGROUND_PART, colour).convert("RGB").save(
            out("android/mipmap-%s/ic_launcher_foreground.png" % name), optimize=True)
    sized(picture, 512).convert("RGB").save(out("android/ic_launcher-playstore.png"), optimize=True)
    with open(out("background.txt"), "w") as f:
        f.write("#%02X%02X%02X\n" % colour[:3])
    return 0


if __name__ == "__main__":
    sys.exit(main())
