# GB-SGB-Tooling — Super Game Boy Asset Pipeline

[![test](https://github.com/Zapskii/GB-SGB-Tooling/actions/workflows/test.yml/badge.svg)](https://github.com/Zapskii/GB-SGB-Tooling/actions/workflows/test.yml)

Super Game Boy borders for [GBDK-2020](https://github.com/gbdk-2020/gbdk-2020) games:
make the art, convert it, send it to the SGB, and test that it arrived.

📖 **[Read the full write-up](https://retro.zapski.com/blog/gb-sgb-tooling-super-game-boy-borders)** | 🎮 **[See it in action: FPS Dungeon](https://retro.zapski.com/play/fps-dungeon)**

## Live case study: FPS Dungeon

This kit is used for the stone-brick border in **[FPS Dungeon](https://retro.zapski.com/blog/fps-dungeon-game-boy-review)**,
a real-time raycaster running on the original 1989 Game Boy. [Play it in your browser](https://retro.zapski.com/play/fps-dungeon).

## Resources and homebrew guides

More dev logs, technical breakdowns and emulation history on **[Zapski Retro](https://retro.zapski.com)**:

* **[GB-SGB-Tooling write-up](https://retro.zapski.com/blog/gb-sgb-tooling-super-game-boy-borders):** why we built it, the transfer bugs we fixed, and how the tests work.
* **[Making Game Boy games in 2026](https://retro.zapski.com/blog/making-game-boy-games-2026-tools-missing):** the tools still missing for Game Boy development.
* **[Blog](https://retro.zapski.com/blog):** reviews and deep dives into Game Boy homebrew.
* **[Console timeline](https://retro.zapski.com/consoles):** Nintendo's handhelds and the rest, console by console.

![The demo ROM with a border from `make TITLE="MY GAME"`, as a Super Game Boy shows it](docs/border.png)

| File | What it does |
|---|---|
| `mkborder.py` | Draws a 256×224 border (gradient, frame, title) or prepares your own art, packed so png2asset gets the SGB's palette rules right |
| `sgb_border.c` / `.h` | `set_sgb_border()`, the GBDK example with its transfer bugs fixed |
| `sgb_border_test.py` | Boots your ROM in PyBoy with SGB support and compares the border bytes the SGB received with `border_data.c` |
| `test_mkborder.py` | Fast checks of `mkborder.py`'s limits; standard library only |
| `gearboy_check.py` | Optional second opinion: runs the ROM in [Gearboy](https://github.com/drhelius/Gearboy) headless and compares the border it draws with your art (`make gearboy`) |
| `example/main.c`, `Makefile` | A minimal demo ROM that ties it together |

## Quick start

Needs GBDK-2020 4.4.0+ and Python 3. The test also needs `pip install "pyboy>=2.8.0" pillow`.

```sh
make GBDK_HOME=/path/to/gbdk TITLE="MY GAME" SUBTITLE="(C) 2026 ME"
make GBDK_HOME=/path/to/gbdk test
```

Or with your own art, any 256×224 PNG:

```sh
make GBDK_HOME=/path/to/gbdk ART=my_border.png test
```

If you have [Gearboy](https://github.com/drhelius/Gearboy) installed, check the border in a second emulator too:

```sh
make GBDK_HOME=/path/to/gbdk gearboy    # frame saved to build/gearboy.png
```

## Using it in your game

1. Copy `sgb_border.c` and `sgb_border.h` into your project.
2. Make the border and convert it:
   ```sh
   python3 mkborder.py border.png --title "MY GAME"      # or --art my_art.png
   png2asset border.png -map -bpp 4 -max_palettes 3 -keep_palette_order \
             -pack_mode sgb -use_map_attributes -c border_data.c
   ```
3. Build with `-Wm-ys` so the header marks the cart SGB-enhanced:
   `lcc -Wm-ys ... sgb_border.c border_data.c`
4. Call it once at startup, with the display on, **before** loading your own tiles:
   ```c
   DISPLAY_ON;
   for (uint8_t i = 4; i != 0; i--) vsync();   // PAL SNES needs this
   set_sgb_border(border_data_tiles, sizeof(border_data_tiles),
                  border_data_map, sizeof(border_data_map),
                  (const unsigned char *)border_data_palettes, sizeof(border_data_palettes));
   ```
   On a plain Game Boy it does nothing. Set SGB palette 0 afterwards too (a `PAL01` packet, as `example/main.c` does): a real SGB starts with a default palette, but some emulators start it all black and your game won't show.
5. Optionally, check it arrives:
   ```sh
   python3 sgb_border_test.py game.gb border.png border_data.c   # PyBoy: the bytes
   python3 gearboy_check.py game.gb border.png                  # Gearboy: the picture
   ```

`python3 mkborder.py --help` lists the colour and layout options.

## The rules this handles for you

- **The Game Boy screen must stay transparent**: it's the 160×144 area at (48, 40). `--art` clears anything painted there and says so.
- **Colour 0 of every palette is invisible**: the SGB draws it as the backdrop. png2asset only reserves it in palettes that happen to contain a transparent pixel, so its brightest colour can vanish. `mkborder.py` reserves slot 0 everywhere, and `-keep_palette_order` makes png2asset keep that.
- **3 palettes of 15 colours, and at most 255 unique tiles.** A border may only use SNES palettes 4–6; the SGB's own menus use 7. `mkborder.py` fails with a clear message if the art needs more.
- **The transfer overwrites VRAM**: load your graphics after `set_sgb_border()`, not before.

`make test` checks the bytes PyBoy's SGB receives; `make gearboy` checks the picture Gearboy draws from them, pixel for pixel. Neither is real hardware: whether a real SGB detects the cart and how the border looks on a TV is still worth checking once on the real thing.

## Development

`make test` runs `test_mkborder.py` (no GBDK needed) and then `sgb_border_test.py` on the demo ROM. GitHub Actions runs both on every push, with GBDK-2020 4.5.0: once with a drawn border and once with generated `--art` big enough to need two palettes and both transfer blocks. `make gearboy` is manual only.

## License

GPLv2 ([LICENSE](LICENSE)) with a linking exception ([LINKING-EXCEPTION](LINKING-EXCEPTION)), the same terms as GBDK-2020.
`sgb_border.c` is derived from GBDK-2020's `sgb_border` example.
Games that include it don't have to be GPL, and shipped ROMs need no credit (though it's appreciated).
