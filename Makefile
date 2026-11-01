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

BORDER_ARGS := $(if $(ART),--art "$(ART)",--title "$(TITLE)" --subtitle "$(SUBTITLE)")

.PHONY: all test gearboy clean
all: $(ROM)

# The border arguments are kept in build/border.args, rewritten only when they
# change, so a new TITLE or ART rebuilds the border and an unchanged one does
# not. This runs while the Makefile is read, before make looks at timestamps,
# and deletes the old outputs outright: make 3.81 (macOS) compares mtimes to
# the second, so a stamp from the same second as the last build would not
# look newer.
QUOTED_ARGS := '$(subst ','\'',$(BORDER_ARGS))'
$(shell mkdir -p build; printf '%s\n' $(QUOTED_ARGS) | cmp -s - build/border.args \
  || { printf '%s\n' $(QUOTED_ARGS) > build/border.args; \
       rm -f build/border.png build/border_data.c build/border_data.h $(ROM); })

build/border.png: mkborder.py build/border.args $(ART)
	$(PYTHON) mkborder.py $@ $(BORDER_ARGS)

# -keep_palette_order: use mkborder.py's palettes, which keep slot 0 free.
build/border_data.c build/border_data.h: build/border.png
	$(P2A) $< -map -bpp 4 -max_palettes 3 -keep_palette_order \
	       -pack_mode sgb -use_map_attributes -c build/border_data.c

# -Wm-ys sets the SGB flag in the header; without it an SGB shows no border.
$(ROM): example/main.c sgb_border.c sgb_border.h build/border_data.c
	$(LCC) -I. -Ibuild -Wm-ys -Wm-yn"SGBDEMO" -o $@ \
	       example/main.c sgb_border.c build/border_data.c

test: $(ROM)
	$(PYTHON) test_mkborder.py
	$(PYTHON) sgb_border_test.py $(ROM) build/border.png build/border_data.c

# Manual second-emulator check: Gearboy draws the border, compared with the art.
gearboy: $(ROM)
	$(PYTHON) gearboy_check.py $(ROM) build/border.png --shot build/gearboy.png

clean:
	rm -rf build
