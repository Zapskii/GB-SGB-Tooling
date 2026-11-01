# GB-SGB-Tooling

[![test](https://github.com/Zapskii/GB-SGB-Tooling/actions/workflows/test.yml/badge.svg)](https://github.com/Zapskii/GB-SGB-Tooling/actions/workflows/test.yml)

Super Game Boy borders for [GBDK-2020](https://github.com/gbdk-2020/gbdk-2020) games:
make the art, convert it, send it to the SGB, and test that it arrived.

![The demo ROM with a border from `make TITLE="MY GAME"`, as a Super Game Boy shows it](docs/border.png)

| File | What it does |
|---|---|
| `mkborder.py` | Draws a 256×224 border (gradient, frame, title) or prepares your own art, packed so png2asset gets the SGB's palette rules right |
| `sgb_border.c` / `.h` | `set_sgb_border()`, the GBDK example with its transfer bugs fixed |
| `sgb_border_test.py` | Boots your ROM in PyBoy with SGB support and compares the border bytes the SGB received with `border_data.c` |
| `test_mkborder.py` | Fast checks of `mkborder.py`'s limits; standard library only |
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
   On a plain Game Boy it does nothing.
5. Optionally: `python3 sgb_border_test.py game.gb border.png border_data.c`

`python3 mkborder.py --help` lists the colour and layout options.

## The rules this handles for you

- **The Game Boy screen must stay transparent**: it's the 160×144 area at (48, 40). `--art` clears anything painted there and says so.
- **Colour 0 of every palette is invisible**: the SGB draws it as the backdrop. png2asset only reserves it in palettes that happen to contain a transparent pixel, so its brightest colour can vanish. `mkborder.py` reserves slot 0 everywhere, and `-keep_palette_order` makes png2asset keep that.
- **3 palettes of 15 colours, and at most 255 unique tiles.** `mkborder.py` fails with a clear message if the art needs more.
- **The transfer overwrites VRAM**: load your graphics after `set_sgb_border()`, not before.

What the test can't tell you is how the border looks on a real SGB or whether real hardware detects it. Check that on hardware or in an accurate emulator.

## License

GPLv2 ([LICENSE](LICENSE)) with a linking exception ([LINKING-EXCEPTION](LINKING-EXCEPTION)), the same terms as GBDK-2020.
`sgb_border.c` is derived from GBDK-2020's `sgb_border` example.
Games that include it don't have to be GPL, and shipped ROMs need no credit (though it's appreciated).
