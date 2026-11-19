"""Generate crisp monochrome Swiss-instrument PNG icons for iPhone PWA home screen (180, 192, 512px)."""
import os
import struct
import zlib

def make_png(width: int, height: int, rgba_func) -> bytes:
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0
        for x in range(width):
            r, g, b, a = rgba_func(x, y, width, height)
            raw.extend((r, g, b, a))

    def chunk(ctype: bytes, data: bytes) -> bytes:
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw), level=9)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")

def manifold_icon_pixel(x: int, y: int, w: int, h: int):
    nx = x / w
    ny = y / h
    # Deep obsidian-slate background (#0e1116)
    bg = (14, 17, 22, 255)
    # Minimal logarithmic ruler + amber-vermilion marker (#e8a247) + crisp white ticks
    # Horizontal baseline at ny = 0.56
    if 0.14 <= nx <= 0.86 and abs(ny - 0.56) <= 0.014:
        return (232, 236, 242, 255)
    # Logarithmic-spaced ticks along the ruler
    ticks = [0.16, 0.28, 0.37, 0.45, 0.52, 0.62, 0.74, 0.84]
    for i, tx in enumerate(ticks):
        tall = 0.095 if i in (0, 3, 7) else 0.055
        if abs(nx - tx) <= 0.010 and (0.56 - tall) <= ny <= (0.56 + 0.03):
            return (150, 162, 180, 255) if i not in (0, 3, 7) else (232, 236, 242, 255)
    # Warm amber tolerance band around nx = 0.62
    if 0.56 <= nx <= 0.68 and 0.48 <= ny <= 0.64:
        # subtle blend
        return (62, 48, 28, 255)
    # Diamond / circle placement marker at (0.62, 0.40)
    dx = nx - 0.62
    dy = ny - 0.40
    if dx * dx + dy * dy <= 0.055 * 0.055:
        return (236, 162, 72, 255)
    # Vertical needle from marker to ruler
    if abs(nx - 0.62) <= 0.008 and 0.40 <= ny <= 0.56:
        return (236, 162, 72, 255)
    return bg

def main():
    out_dir = os.path.join("public", "icons")
    os.makedirs(out_dir, exist_ok=True)
    for name, size in [("apple-touch-icon.png", 180), ("icon-192.png", 192), ("icon-512.png", 512)]:
        data = make_png(size, size, manifold_icon_pixel)
        with open(os.path.join(out_dir, name), "wb") as f:
            f.write(data)
        print(f"Wrote {name} ({size}x{size}, {len(data)} bytes)")

if __name__ == "__main__":
    main()
