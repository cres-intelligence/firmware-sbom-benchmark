#!/bin/bash
set -euo pipefail
cd /work/mbedtls

CFL="-mcpu=cortex-m3 -mthumb -Os -ffunction-sections -fdata-sections"
CFL="$CFL -I/work -DMBEDTLS_CONFIG_FILE='<baremetal_config.h>'"

echo "=== generated files (a git clone has none; a release tarball does) ==="
make generated_files 2>&1 | tail -4 || echo "!! generated_files failed"

echo "=== build the three vendor archives for Cortex-M3 ==="
make -C library CC=arm-none-eabi-gcc AR=arm-none-eabi-ar CFLAGS="$CFL" static 2>&1 | tail -6

echo "=== the archives ==="
ls -la library/*.a
for a in library/*.a; do
  echo "$a members=$(arm-none-eabi-ar t "$a" | wc -l)"
done
