#!/usr/bin/make -f
# BASILISK SYNTH - VST3 (Windows, macOS), AU and CLAP (macOS).
#   Windows, from Linux/WSL:  make WINDOWS=true CC=x86_64-w64-mingw32-gcc CXX=x86_64-w64-mingw32-g++
#   macOS:                    make
# DPF (https://github.com/DISTRHO/DPF, ISC) is expected at $(DPF_PATH), checked out at 4238e1c with submodules.

DPF_PATH ?= $(HOME)/synth-build/dpf
NAME = BasiliskSynth
DPF_BUILD_DIR ?= $(CURDIR)/build
DPF_TARGET_DIR ?= $(CURDIR)/bin

FILES_DSP = \
	BasiliskSynthPlugin.cpp \
	Machine.cpp \
	DBusIn.cpp \
	../core/dna.cpp \
	../core/voices.cpp \
	../core/dna3.cpp \
	../core/engine3.cpp \
	../core/scales.cpp

FILES_UI = \
	BasiliskSynthUI.cpp

include $(DPF_PATH)/Makefile.plugins.mk

BUILD_CXX_FLAGS += -std=gnu++17 -I.
ifeq ($(WINDOWS),true)
LINK_FLAGS += -lws2_32 -lshell32 -lwinmm -static -static-libgcc -static-libstdc++
endif

TARGETS += vst3
ifeq ($(MACOS),true)
TARGETS += au clap
endif

all: $(TARGETS)
