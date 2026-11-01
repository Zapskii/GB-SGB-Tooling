/* The smallest ROM that shows a Super Game Boy border. Build with `make`. */
#include <gb/gb.h>
#include <gb/sgb.h>
#include <stdint.h>
#include <stdio.h>

#include "sgb_border.h"
#include "border_data.h"

/* PAL01 packet: SGB palettes 0 and 1, colour 0 shared. Palette 0 colours the
 * game screen. A real SGB starts with a default one, but not every emulator
 * does (Gearboy without the SGB boot ROM starts all black), so set it. */
static uint8_t pal01[16] = {
    (SGB_PAL_01 << 3) | 1,
    0xFF, 0x7F,     /* white       RGB555 little-endian */
    0x94, 0x52,     /* light grey */
    0x4A, 0x29,     /* dark grey  */
    0x00, 0x00,     /* black      */
};

void main(void) {
    DISPLAY_ON;
    /* A PAL SNES needs a few frames before sgb_check() answers reliably. */
    for (uint8_t i = 4; i != 0; i--) vsync();

    /* Does nothing on a plain Game Boy. */
    set_sgb_border(border_data_tiles, sizeof(border_data_tiles),
                   border_data_map, sizeof(border_data_map),
                   (const unsigned char *)border_data_palettes, sizeof(border_data_palettes));
    if (sgb_check())
        sgb_transfer(pal01);

    /* The transfer leaves VRAM full of border tiles: load your own graphics
     * after it, not before. printf loads its font on first use. */
    printf("\n\n\n\n\n\n\n\n    HELLO, SGB!");
    while (1) vsync();
}
