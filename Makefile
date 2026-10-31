# Builds the demo ROM in example/ and checks its border reaches the SGB.
#
#   make                         build/demo.gb
#   make TITLE="MY GAME"         ...with your own title
#   make ART=my_border.png       ...or your own 256x224 art
#   make test                    boot it in PyBoy and compare the border bytes
#
# GBDK_HOME is your GBDK-2020 install (4.4.0 or later).

GBDK_HOME ?= /opt/gbdk
PYTHON    ?= python3
TITLE     ?= SGB BORDER
SUBTITLE  ?= GB-SGB-TOOLING
ART       ?=

LCC := $(GBDK_HOME)/bin/lcc
P2A := $(GBDK_HOME)/bin/png2asset
ROM := build/demo.gb

.PHONY: all test clean
all: $(ROM)

build/border.png: mkborder.py
	$(PYTHON) mkborder.py $@ $(if $(ART),--art "$(ART)",--title "$(TITLE)" --subtitle "$(SUBTITLE)")

# -keep_palette_order: use mkborder.py's palettes, which keep slot 0 free.
build/border_data.c build/border_data.h: build/border.png
	$(P2A) $< -map -bpp 4 -max_palettes 4 -keep_palette_order \
	       -pack_mode sgb -use_map_attributes -c build/border_data.c

# -Wm-ys sets the SGB flag in the header; without it an SGB shows no border.
$(ROM): example/main.c sgb_border.c sgb_border.h build/border_data.c
	$(LCC) -I. -Ibuild -Wm-ys -Wm-yn"SGBDEMO" -o $@ \
	       example/main.c sgb_border.c build/border_data.c

test: $(ROM)
	$(PYTHON) sgb_border_test.py $(ROM) build/border.png build/border_data.c

clean:
	rm -rf build
