#!/usr/bin/make -f
# SNDWAVE1993 Ensemble (DPF). DPF_PATH must point at a DPF checkout with ../../plugin/dpf.patch applied.
NAME = SNDWAVE1993-Ensemble

FILES_DSP = EnsemblePlugin.cpp EnsSharedCore.cpp EnsSharedCore3Dna.cpp EnsSharedCore3Engine.cpp EnsSharedCore3Recipe.cpp EnsSharedCore3Scales.cpp EnsEngine.c
FILES_UI  = EnsembleUI.cpp

DPF_PATH ?= ../../../../DPF
include $(DPF_PATH)/Makefile.plugins.mk

BUILD_CXX_FLAGS += -std=gnu++17 -fno-fast-math -ffp-contract=off
BUILD_C_FLAGS += -I../../engine
ifeq ($(WINDOWS),true)
LINK_FLAGS += -static -static-libgcc -static-libstdc++ -lwinmm
else ifeq ($(MACOS),true)
else
LINK_FLAGS += -ldl -lpthread
endif

TARGETS = vst3 clap
all: $(TARGETS)
