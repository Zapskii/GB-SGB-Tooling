#!/usr/bin/env python3
"""Fast checks for mkborder.py's limits. Standard library only: no GBDK,
PyBoy or Pillow. The end-to-end check is sgb_border_test.py.

    python3 test_mkborder.py
"""
import contextlib
import io
import os
import tempfile

import mkborder as mb


def blank():
    return [[mb.CLEAR] * mb.W for _ in range(mb.H)]


def fill_tile(px, tx, ty, colours):
    """Paint tile (tx, ty) cycling through colours, one per pixel."""
    for i in range(mb.TILE * mb.TILE):
        px[ty * mb.TILE + i // mb.TILE][tx * mb.TILE + i % mb.TILE] = colours[i % len(colours)]


def rgb(n):
    """The nth of many distinct colours, already on the SGB's 5-bit grid."""
    return ((n * 8) % 256, (n // 32) * 8, 128, 255)


def exits(fn, *args):
    """fn's sys.exit/argparse message, or None if it returned normally."""
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            fn(*args)
    except SystemExit as e:
        return str(e.code) if isinstance(e.code, str) else err.getvalue()
    return None


def test_tile_colour_limit():
    px = blank()
    fill_tile(px, 0, 0, [rgb(n) for n in range(15)])
    assert exits(mb.pack_palettes, px) is None
    fill_tile(px, 0, 0, [rgb(n) for n in range(16)])
    assert "at most 15" in exits(mb.pack_palettes, px)


def test_palette_limit():
    px = blank()
    for t in range(3):                       # three tiles, 15 colours each, no overlap
        fill_tile(px, t, 0, [rgb(15 * t + n) for n in range(15)])
    colors, _ = mb.pack_palettes(px)
    assert len(colors) == 3 and all(c[0] == mb.RESERVED for c in colors)
    fill_tile(px, 3, 0, [rgb(45 + n) for n in range(15)])
    assert "only 3" in exits(mb.pack_palettes, px)


def test_tile_count():
    rows = [[0] * mb.W for _ in range(mb.H)]
    # Tile k carries k in binary down its first column, plus a marker in the
    # top row that no flip can line up with another tile's: 256 distinct tiles.
    for k in range(256):
        tx, ty = k % 32, k // 32
        for bit in range(8):
            rows[ty * 8 + bit][tx * 8] = 1 + (k >> bit & 1)
        rows[ty * 8][tx * 8 + 1] = 3
    assert mb.count_tiles(rows) == 257      # ...and the blank rest; main() caps at 255
    # A horizontally mirrored copy is the same tile to png2asset.
    rows = [[0] * mb.W for _ in range(mb.H)]
    rows[0][0] = rows[0][15] = 1             # tile 0 left column, tile 1 right column
    assert mb.count_tiles(rows) == 2         # that tile, and blank


def test_drawn_border():
    """The drawn border keeps the screen transparent and slot 0 free."""
    with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
        out = os.path.join(d, "b.png")
        mb.main([out, "--title", "TEST", "--subtitle", "(C) 2026"])
        data = open(out, "rb").read()
    assert data.startswith(b"\x89PNG")
    at = data.index(b"tRNS")
    trns = data[at + 4:at + 4 + int.from_bytes(data[at - 4:at], "big")]
    assert len(trns) % 16 == 0
    for p in range(0, len(trns), 16):                 # every palette:
        assert trns[p] == 0 and trns[p + 1] == 255    # slot 0 clear, slot 1 drawn


def test_bad_arguments():
    out = os.path.join(tempfile.gettempdir(), "test_mkborder.png")  # if a check fails
    for args in (["--art", "a.png", "--title", "T"], ["--bands", "0"],
                 ["--frame-width", "-1"]):
        assert exits(mb.main, [out] + args), args
    assert "font has no" in exits(mb.main, [out, "--title", "A~B"])


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok   ", t.__name__)
    print("\n%d passed" % len(tests))
