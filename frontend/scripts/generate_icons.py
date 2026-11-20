"""Generate the JARVIS PWA icons as PNG files with no extra dependencies.

Usage (from C:\\JARVIS\\frontend):
    python scripts/generate_icons.py

Writes to public/:
    icon-192.png, icon-512.png, icon-maskable-512.png, apple-touch-icon.png
"""
import math
import pathlib
import struct
import zlib

OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "public"

BG = (5, 11, 20)
CYAN = (0, 229, 255)
BLUE = (22, 139, 255)
WHITE = (232, 247, 255)


def blend(base, top, alpha):
    return tuple(int(round(b + (t - b) * alpha)) for b, t in zip(base, top))


def pixel(x, y, size, maskable=False):
    """Return an (r, g, b) tuple for one pixel of the JARVIS orb."""
    cx = cy = size / 2.0
    scale = 0.62 if maskable else 0.78
    r_outer = size * scale / 2.0
    dx, dy = x - cx + 0.5, y - cy + 0.5
    dist = math.hypot(dx, dy)

    color = BG
    # soft radial glow
    glow = max(0.0, 1.0 - dist / (size * 0.62)) ** 3
    color = blend(color, (12, 42, 74), glow * 0.85)

    ring_w = size * (0.055 if not maskable else 0.045)
    ring = abs(dist - r_outer * 0.86)
    ring_alpha = max(0.0, 1.0 - ring / ring_w) ** 1.4
    color = blend(color, CYAN, ring_alpha)

    inner = max(0.0, 1.0 - dist / (r_outer * 0.74))
    if inner > 0:
        grad = min(1.0, max(0.0, (y / size)))
        orb = blend(CYAN, BLUE, grad * 0.85)
        color = blend(color, orb, inner * 0.92)

    # voice bars in the middle
    bars = [-0.22, 0.0, 0.22]
    heights = [0.20, 0.32, 0.20]
    bar_w = size * 0.045
    for offset, height in zip(bars, heights):
        bx = cx + offset * size
        half_h = height * size / 2.0
        if abs(x - bx) <= bar_w / 2.0 and abs(dy) <= half_h:
            color = blend(color, WHITE, 0.92)
    return color


def write_png(path, size, maskable=False):
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            row.extend(pixel(x, y, size, maskable))
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", header)
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    path.write_bytes(png)
    return len(png)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("icon-192.png", 192, False),
        ("icon-512.png", 512, False),
        ("icon-maskable-512.png", 512, True),
        ("apple-touch-icon.png", 180, True),
    ]
    for name, size, maskable in jobs:
        written = write_png(OUT_DIR / name, size, maskable)
        print(f"wrote {name} ({size}x{size}, {written} bytes)")


if __name__ == "__main__":
    main()
