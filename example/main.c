/* The smallest ROM that shows a Super Game Boy border. Build with `make`. */
#include <gb/gb.h>
#include <stdint.h>
#include <stdio.h>

#include "sgb_border.h"
#include "border_data.h"

void main(void) {
    DISPLAY_ON;
    /* A PAL SNES needs a few frames before sgb_check() answers reliably. */
    for (uint8_t i = 4; i != 0; i--) vsync();

    /* Does nothing on a plain Game Boy. */
    set_sgb_border(border_data_tiles, sizeof(border_data_tiles),
                   border_data_map, sizeof(border_data_map),
                   (const unsigned char *)border_data_palettes, sizeof(border_data_palettes));

    /* The transfer leaves VRAM full of border tiles: load your own graphics
     * after it, not before. printf loads its font on first use. */
    printf("\n\n\n\n\n\n\n\n    HELLO, SGB!");
    while (1) vsync();
}
