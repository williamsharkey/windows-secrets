#!/usr/bin/make -f
# BASILISK 16 (DPF). DPF_PATH must point at a DPF checkout (see ../tools/build.sh).
NAME = SNDWAVE1993

FILES_DSP = Basilisk16Plugin.cpp SharedCore.cpp SharedCore3Dna.cpp SharedCore3Engine.cpp SharedCore3Recipe.cpp SharedCore3Scales.cpp SharedUserstore.cpp SongTab.cpp Engine.c
FILES_UI  = Basilisk16UI.cpp

DPF_PATH ?= ../../../../DPF
include $(DPF_PATH)/Makefile.plugins.mk

BUILD_CXX_FLAGS += -std=gnu++17
# the Song tab: IEEE arithmetic, as render311 and songrender (SongSession.h)
$(BUILD_DIR)/SongTab.cpp.o: BUILD_CXX_FLAGS += -fno-fast-math -ffp-contract=off
BUILD_C_FLAGS += -I../engine
ifeq ($(WINDOWS),true)
LINK_FLAGS += -static -static-libgcc -static-libstdc++ -lwinmm
else ifeq ($(MACOS),true)
else
LINK_FLAGS += -ldl -lpthread
endif

TARGETS = vst3 clap
ifeq ($(MACOS),true)
TARGETS += au
endif

all: $(TARGETS)
