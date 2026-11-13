# DOSBox Pure (with the BSYN card, patched as for the plugin) compiled to WebAssembly objects.
#   make -f core.mk DBP=~/b16web/dbp OUT=~/b16web/obj -j16
DBP ?= $(HOME)/b16web/dbp
OUT ?= $(HOME)/b16web/obj
CXX := em++
FLAGS := -O3 -fwasm-exceptions -pthread -DSTATIC_LINKING -D__LIBRETRO__ -I$(DBP)/include -DDISABLE_DYNAREC=1 -std=gnu++11 \
  -DNDEBUG -fomit-frame-pointer -Wno-address-of-packed-member -Wno-format -Wno-switch -Wno-psabi -D_FILE_OFFSET_BITS=64 \
  -Wno-deprecated-declarations -Wno-unused-value -Wno-invalid-offsetof $(EXTRA)
SRC := $(wildcard $(DBP)/*.cpp $(DBP)/src/*.cpp $(DBP)/src/*/*.cpp $(DBP)/src/*/*/*.cpp)
OBJ := $(patsubst $(DBP)/%.cpp,$(OUT)/%.o,$(SRC))
$(OUT)/libdbp.a: $(OBJ)
	rm -f $@; emar rcs $@ $^
$(OUT)/%.o: $(DBP)/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) -c $(FLAGS) $< -o $@
