#!/bin/bash
set -euo pipefail
cd /work/mbedtls
mkdir -p /work/out

CFL="-mcpu=cortex-m3 -mthumb -Os -ffunction-sections -fdata-sections"
CFL="$CFL -I/work -DMBEDTLS_CONFIG_FILE='<baremetal_config.h>'"

# ONLY THE LIBRARY'S GENERATED FILES. The top-level `generated_files` target also builds the TEST
# data, whose generator needs python packages this image does not carry -- and a case that cannot
# be rebuilt because of a dependency it never needed is a case that rots. The library is what gets
# linked here.
echo "=== the library's generated files (a git clone has none; a release tarball does) ==="
make -C library generated_files 2>&1 | tail -3 || echo "!! library/generated_files failed"

# THE DRY RUN, CAPTURED FIRST AND FROM AN UNTOUCHED TREE. `make -n` on an already-built tree prints
# nothing, because nothing is out of date -- which would look exactly like a provider that failed
# to read the build.
echo "=== make -n, for the make provider ==="
make -C library --no-print-directory -n CC=arm-none-eabi-gcc AR=arm-none-eabi-ar \
    CFLAGS="$CFL" static > /work/out/make-dry-run.txt 2>/dev/null || true
echo "dry run lines: $(wc -l < /work/out/make-dry-run.txt)"

# THE REAL BUILD, UNDER bear, for the compile-commands provider. `static` builds the archives, and
# the loose .o files it compiles on the way are what this case links -- so the SAME build produces
# both providers' input and the objects in the image.
echo "=== make under bear, for the compile-commands provider ==="
bear --output /work/out/compile_commands.json -- \
    make -C library CC=arm-none-eabi-gcc AR=arm-none-eabi-ar CFLAGS="$CFL" static 2>&1 | tail -4
echo "compile commands recorded: $(python3 -c 'import json,sys; print(len(json.load(open("/work/out/compile_commands.json"))))')"
echo "loose objects compiled:    $(ls library/*.o | wc -l)"
