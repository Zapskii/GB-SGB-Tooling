#!/usr/bin/env python3
"""Second-emulator check: run a ROM in Gearboy and compare the border it draws
with the art.

sgb_border_test.py checks the bytes PyBoy's SGB receives. This checks the
picture an independent emulator draws from them: palettes, slot 0, tile
attributes and all. Gearboy (https://github.com/drhelius/Gearboy, 3.8+) is
driven headless over its MCP stdio interface, so no window or screen capture
is needed. A manual check -- it does not run in CI.

    python3 gearboy_check.py game.gb border.png [--shot out.png]

Gearboy is found at $GEARBOY, else the macOS app, else `gearboy` on PATH.
Needs Pillow.
"""
import argparse
import base64
import io
import json
import os
import shutil
import subprocess
import sys
import time

from PIL import Image

GB_X, GB_Y, GB_W, GB_H = 48, 40, 160, 144
MAC_APP = "/Applications/Gearboy.app/Contents/MacOS/gearboy"


def find_gearboy():
    for path in (os.environ.get("GEARBOY"), MAC_APP, shutil.which("gearboy")):
        if path and os.path.exists(path):
            return path
    sys.exit("gearboy_check.py: Gearboy not found; set GEARBOY=/path/to/gearboy")


class Gearboy:
    """Just enough of an MCP client: one request at a time over stdio."""

    def __init__(self, exe):
        self.p = subprocess.Popen([exe, "--mcp-stdio", "--headless", "--mcp-router"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True)
        self.n = 0
        self.rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                "clientInfo": {"name": "gearboy_check", "version": "1"}})
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def send(self, msg):
        self.p.stdin.write(json.dumps(msg) + "\n")
        self.p.stdin.flush()

    def rpc(self, method, params):
        self.n += 1
        self.send({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params})
        while True:
            line = self.p.stdout.readline()
            if not line:
                sys.exit("gearboy_check.py: Gearboy exited during %s" % method)
            r = json.loads(line)
            if r.get("id") == self.n:
                if "error" in r:
                    sys.exit("gearboy_check.py: %s failed: %s" % (method, r["error"]))
                return r["result"]

    def call(self, tool, args=None):
        return self.rpc("tools/call", {"name": tool, "arguments": args or {}})["content"]

    def screenshot(self):
        for c in self.call("get_screenshot"):
            if c.get("type") == "image":
                return Image.open(io.BytesIO(base64.b64decode(c["data"]))).convert("RGB")
        sys.exit("gearboy_check.py: Gearboy returned no screenshot")

    def close(self):
        self.p.kill()


def border_diff(shot, art):
    """Border pixels (outside the screen hole) that differ beyond 5-bit rounding."""
    n = 0
    for y in range(224):
        for x in range(256):
            if GB_X <= x < GB_X + GB_W and GB_Y <= y < GB_Y + GB_H:
                continue
            a, b = art.getpixel((x, y))[:3], shot.getpixel((x, y))
            n += any(abs((i & 0xF8) - (j & 0xF8)) > 8 for i, j in zip(a, b))
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("rom")
    ap.add_argument("art", help="the border PNG mkborder.py wrote")
    ap.add_argument("--shot", help="save Gearboy's 256x224 frame here")
    ap.add_argument("--timeout", type=float, default=15, help="seconds to wait (default 15)")
    a = ap.parse_args()

    art = Image.open(a.art).convert("RGBA")
    gb = Gearboy(find_gearboy())
    try:
        gb.call("load_media", {"file_path": os.path.abspath(a.rom)})
        gb.call("debug_continue")
        # The border arrives a second or two in; poll until it matches or time is up.
        deadline, diff = time.time() + a.timeout, None
        while time.time() < deadline:
            time.sleep(1)
            shot = gb.screenshot()
            if shot.size != (256, 224):
                continue                         # not in SGB mode (yet)
            diff = border_diff(shot, art)
            if diff == 0:
                break
    finally:
        gb.close()

    if a.shot:
        shot.save(a.shot)
    if diff is None:
        sys.exit("FAIL  Gearboy never showed a 256x224 SGB frame -- is the SGB "
                 "flag set (lcc -Wm-ys)?")
    centre = shot.crop((GB_X, GB_Y, GB_X + GB_W, GB_Y + GB_H)).getcolors(1 << 16)
    print(("ok    " if diff == 0 else "FAIL  ")
          + "Gearboy's border matches the art (%d of %d border pixels differ)"
          % (diff, 256 * 224 - GB_W * GB_H))
    if len(centre) == 1:
        print("note  the game screen is one flat colour %s -- if it should show "
              "something, set SGB palette 0 (PAL01); see example/main.c"
              % (centre[0][1],))
    sys.exit(0 if diff == 0 else 1)


if __name__ == "__main__":
    main()
