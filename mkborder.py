#!/usr/bin/env python3
"""Make a Super Game Boy border PNG that png2asset turns straight into a working
border.

Two ways in:

    mkborder.py out.png --title "MY GAME" [--subtitle "2026"] [colours...]
        draws a simple border: a banded gradient, a frame round the screen,
        and the title/subtitle in a bundled 5x7 pixel font.

    mkborder.py out.png --art my_border.png
        takes your own 256x224 art instead (needs Pillow).

Either way the output is an indexed PNG laid out for

    png2asset out.png -map -bpp 4 -max_palettes 4 -keep_palette_order \\
              -pack_mode sgb -use_map_attributes -c border_data.c

What this does that png2asset will not:

  * keeps the 160x144 Game Boy screen at (48, 40) fully transparent, so the
    game shows through;
  * reserves slot 0 of every palette. The SGB draws colour 0 of each border
    palette as the backdrop, so anything in it vanishes. png2asset reserves it
    only for palettes whose tiles contain a transparent pixel, and since the
    screen hole is tile-aligned, a second palette usually never sees one --
    its brightest colour then renders as backdrop. -keep_palette_order makes
    png2asset use this script's packing instead of its own;
  * snaps colours to the SGB's 15-bit RGB, so near-duplicates share a slot;
  * fails early if the art needs more than 3 palettes of 15 colours, or more
    than 255 unique tiles (the transfer's ceiling, see sgb_border.c).

Standard library only, except --art, which reads the PNG with Pillow.
"""
import argparse
import os
import struct
import sys
import zlib

W, H = 256, 224
GB_X, GB_Y, GB_W, GB_H = 48, 40, 160, 144

TILE = 8                      # the SGB border is laid out in 8x8 tiles
PAL_COLORS = 16               # entries in one SGB border palette
PAL_CAP = PAL_COLORS - 1      # ...of which slot 0 is reserved, so 15 to draw with
PAL_LIMIT = 3                 # the border is drawn with SNES palettes 4, 5 and 6 only
TILE_LIMIT = 255              # see the block split in sgb_border.c
RESERVED = (0, 0, 0)          # what sits in slot 0; never drawn, so the value is arbitrary
CLEAR = (0, 0, 0, 0)

# 5x7 glyphs, one string of rows per character, '#' is ink.
FONT = {
    '0': ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.",
    '1': "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    '2': ".###.|#...#|....#|...#.|..#..|.#...|#####",
    '3': ".###.|#...#|....#|..##.|....#|#...#|.###.",
    '4': "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.",
    '5': "#####|#....|####.|....#|....#|#...#|.###.",
    '6': ".###.|#....|#....|####.|#...#|#...#|.###.",
    '7': "#####|....#|...#.|..#..|.#...|.#...|.#...",
    '8': ".###.|#...#|#...#|.###.|#...#|#...#|.###.",
    '9': ".###.|#...#|#...#|.####|....#|...#.|.##..",
    'A': ".###.|#...#|#...#|#####|#...#|#...#|#...#",
    'B': "####.|#...#|#...#|####.|#...#|#...#|####.",
    'C': ".###.|#...#|#....|#....|#....|#...#|.###.",
    'D': "####.|#...#|#...#|#...#|#...#|#...#|####.",
    'E': "#####|#....|#....|####.|#....|#....|#####",
    'F': "#####|#....|#....|####.|#....|#....|#....",
    'G': ".###.|#...#|#....|#.###|#...#|#...#|.###.",
    'H': "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    'I': ".###.|..#..|..#..|..#..|..#..|..#..|.###.",
    'J': "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
    'K': "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#",
    'L': "#....|#....|#....|#....|#....|#....|#####",
    'M': "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#",
    'N': "#...#|##..#|#.#.#|#..##|#...#|#...#|#...#",
    'O': ".###.|#...#|#...#|#...#|#...#|#...#|.###.",
    'P': "####.|#...#|#...#|####.|#....|#....|#....",
    'Q': ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#",
    'R': "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    'S': ".####|#....|#....|.###.|....#|....#|####.",
    'T': "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    'U': "#...#|#...#|#...#|#...#|#...#|#...#|.###.",
    'V': "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    'W': "#...#|#...#|#...#|#.#.#|#.#.#|##.##|#...#",
    'X': "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    'Y': "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..",
    'Z': "#####|....#|...#.|..#..|.#...|#....|#####",
    '-': ".....|.....|.....|#####|.....|.....|.....",
    '.': ".....|.....|.....|.....|.....|.##..|.##..",
    ':': ".....|.##..|.##..|.....|.##..|.##..|.....",
    '!': "..#..|..#..|..#..|..#..|..#..|.....|..#..",
    "'": "..#..|..#..|.#...|.....|.....|.....|.....",
    '&': ".##..|#..#.|#.#..|.#...|#.#.#|#..#.|.##.#",
    '(': "...#.|..#..|.#...|.#...|.#...|..#..|...#.",
    ')': ".#...|..#..|...#.|...#.|...#.|..#..|.#...",
}


def in_gb(x, y):
    return GB_X <= x < GB_X + GB_W and GB_Y <= y < GB_Y + GB_H


def snap(c):
    """Drop the bits the SGB's 5-bit channels cannot hold."""
    return (c[0] & 0xF8, c[1] & 0xF8, c[2] & 0xF8, c[3])


def colour(s):
    s = s.lstrip("#")
    if len(s) != 6:
        raise argparse.ArgumentTypeError("colours are #rrggbb, got %r" % s)
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)


# ---------------------------------------------------------------- drawing

def rect(px, x, y, w, h, c):
    for yy in range(max(y, 0), min(y + h, H)):
        for xx in range(max(x, 0), min(x + w, W)):
            if not in_gb(xx, yy):
                px[yy][xx] = c


def text(px, s, y, scale, c):
    """Draw s centred on the border at row y."""
    s = s.upper()
    bad = sorted(set(ch for ch in s if ch != " " and ch not in FONT))
    if bad:
        sys.exit("mkborder: the font has no %s" % " ".join(bad))
    pitch = 6 * scale                         # 5px glyph + 1px gap
    width = len(s) * pitch - scale
    if width > W:
        sys.exit("mkborder: %r is %dpx wide at scale %d; the border is %d"
                 % (s, width, scale, W))
    x0 = (W - width) // 2
    for i, ch in enumerate(s):
        if ch == " ":
            continue
        for gy, row in enumerate(FONT[ch].split("|")):
            for gx, bit in enumerate(row):
                if bit == "#":
                    rect(px, x0 + i * pitch + gx * scale, y + gy * scale, scale, scale, c)


def draw(a):
    """The built-in border: gradient bands, a frame, a title and a subtitle."""
    px = [[CLEAR] * W for _ in range(H)]
    bands = a.bands
    for b in range(bands):
        t = b / max(bands - 1, 1)
        c = tuple(int(round(a.top[i] + (a.bottom[i] - a.top[i]) * t)) for i in range(3)) + (255,)
        y0, y1 = b * H // bands, (b + 1) * H // bands
        rect(px, 0, y0, W, y1 - y0, c)
    f = a.frame_width
    if f:
        rect(px, GB_X - f, GB_Y - f, GB_W + 2 * f, GB_H + 2 * f, a.frame)
    if a.title:
        # 14px tall at scale 2, centred in the 40px above the screen.
        if a.shadow:
            text(px, a.title, 13 + 1, 2, a.shadow)
        text(px, a.title, 13 - 1, 2, a.ink)
    if a.subtitle:
        text(px, a.subtitle, GB_Y + GB_H + 16, 1, a.ink)
    return px


def load_art(path):
    try:
        from PIL import Image
    except ImportError:
        sys.exit("mkborder: --art needs Pillow (pip install pillow)")
    im = Image.open(path).convert("RGBA")
    if im.size != (W, H):
        sys.exit("mkborder: %s is %dx%d; a border is %dx%d" % (path, *im.size, W, H))
    px = [[im.getpixel((x, y)) for x in range(W)] for y in range(H)]
    painted = sum(1 for y in range(GB_Y, GB_Y + GB_H)
                  for x in range(GB_X, GB_X + GB_W) if px[y][x][3])
    if painted:
        print("mkborder: cleared %d painted pixels inside the Game Boy screen "
              "(%d,%d %dx%d)" % (painted, GB_X, GB_Y, GB_W, GB_H), file=sys.stderr)
    # Anything not fully opaque counts as transparent: the SGB has no blending.
    return [[CLEAR if in_gb(x, y) or px[y][x][3] < 255 else px[y][x]
             for x in range(W)] for y in range(H)]


# ---------------------------------------------------------------- packing

def luminance(c):
    return c[0] * 299 + c[1] * 587 + c[2] * 114


def pack_palettes(px):
    """Choose the border's palettes and say which tile uses which.

    Tiles go first-fit in raster order, each taking the first palette with room
    for its colours -- the same greedy png2asset applies. Fully transparent
    pixels take the reserved slot 0 and are not counted against a palette.
    """
    palettes = []
    slots = [[0] * (W // TILE) for _ in range(H // TILE)]
    for ty in range(H // TILE):
        for tx in range(W // TILE):
            drawn = {px[y][x][:3]
                     for y in range(ty * TILE, (ty + 1) * TILE)
                     for x in range(tx * TILE, (tx + 1) * TILE)
                     if px[y][x][3] != 0}
            if len(drawn) > PAL_CAP:
                sys.exit("mkborder: the tile at (%d, %d) uses %d colours; an SGB "
                         "tile can use at most %d" % (tx * TILE, ty * TILE, len(drawn), PAL_CAP))
            for i, pal in enumerate(palettes):
                if len(pal | drawn) <= PAL_CAP:
                    pal |= drawn
                    break
            else:
                palettes.append(set(drawn))
                i = len(palettes) - 1
            slots[ty][tx] = i
    if len(palettes) > PAL_LIMIT:
        sys.exit("mkborder: the art needs %d palettes of %d colours, but the SGB's "
                 "border can use only %d" % (len(palettes), PAL_CAP, PAL_LIMIT))
    return [[RESERVED] + sorted(pal, key=luminance, reverse=True)
            for pal in palettes], slots


def index_pixels(px, colors, slots):
    """Index every pixel as 16 * palette + slot, which -keep_palette_order reads."""
    rows = [[0] * W for _ in range(H)]
    for ty in range(H // TILE):
        for tx in range(W // TILE):
            slot_of = {c: i for i, c in enumerate(colors[slots[ty][tx]])}
            base = PAL_COLORS * slots[ty][tx]
            for y in range(ty * TILE, (ty + 1) * TILE):
                for x in range(tx * TILE, (tx + 1) * TILE):
                    rows[y][x] = base + (0 if px[y][x][3] == 0 else slot_of[px[y][x][:3]])
    return rows


def count_tiles(rows):
    """Unique tiles as png2asset dedupes them: by pixels within the palette,
    a flipped copy counting as the same tile."""
    seen = set()
    for ty in range(H // TILE):
        for tx in range(W // TILE):
            t = tuple(tuple(rows[y][x] % PAL_COLORS for x in range(tx * TILE, (tx + 1) * TILE))
                      for y in range(ty * TILE, (ty + 1) * TILE))
            h = tuple(r[::-1] for r in t)
            seen.add(min(t, h, t[::-1], h[::-1]))
    return len(seen)


def write_png(path, rows, colors):
    """Minimal indexed PNG writer: 8 bits a pixel, 16 entries a palette, slot 0
    of each palette fully transparent."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    raw = b"".join(b"\x00" + bytes(row) for row in rows)

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    plte, trns = bytearray(), bytearray()
    for pal in colors:
        for i, c in enumerate(pal):
            plte += bytes(c)
            trns.append(0 if i == 0 else 255)
        for _ in range(PAL_COLORS - len(pal)):
            plte += bytes(RESERVED)
            trns.append(0)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 3, 0, 0, 0)))
        f.write(chunk(b"PLTE", bytes(plte)))
        f.write(chunk(b"tRNS", bytes(trns)))
        f.write(chunk(b"IDAT", zlib.compress(raw, 9)))
        f.write(chunk(b"IEND", b""))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("out", help="indexed PNG to write, ready for png2asset")
    p.add_argument("--art", help="your own 256x224 border art (needs Pillow)")
    p.add_argument("--title", help="drawn at 2x above the screen")
    p.add_argument("--subtitle", help="drawn at 1x below the screen")
    p.add_argument("--top", type=colour, default=colour("#1f1a40"), help="gradient top")
    p.add_argument("--bottom", type=colour, default=colour("#a5416f"), help="gradient bottom")
    p.add_argument("--bands", type=int, default=8, help="gradient steps (default 8)")
    p.add_argument("--frame", type=colour, default=colour("#ffffff"), help="frame colour")
    p.add_argument("--frame-width", type=int, default=2, help="0 for no frame")
    p.add_argument("--ink", type=colour, default=colour("#fff1c9"), help="text colour")
    p.add_argument("--shadow", type=colour, default=colour("#000000"), help="title shadow")
    p.add_argument("--no-shadow", dest="shadow", action="store_const", const=None)
    a = p.parse_args(argv)

    px = load_art(a.art) if a.art else draw(a)
    px = [[snap(c) for c in row] for row in px]
    colors, slots = pack_palettes(px)
    rows = index_pixels(px, colors, slots)
    n = count_tiles(rows)
    if n > TILE_LIMIT:
        sys.exit("mkborder: the art needs %d unique tiles; set_sgb_border() can "
                 "send at most %d" % (n, TILE_LIMIT))
    write_png(a.out, rows, colors)
    print("%s  %d tiles, %d palettes (%s colours)"
          % (a.out, n, len(colors), " + ".join(str(len(c) - 1) for c in colors)))


if __name__ == "__main__":
    main()
