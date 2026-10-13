#!/bin/bash
set -euo pipefail
cd /work/mbedtls
# rv64imac / lp64, soft float: the ordinary embedded RISC-V profile.
CFL="--specs=picolibc.specs -march=rv64imac -mabi=lp64 -Os -ffunction-sections -fdata-sections"
CFL="$CFL -I/work -DMBEDTLS_CONFIG_FILE='<baremetal_config.h>'"
echo "=== generated files ==="
make generated_files 2>&1 | tail -3 || echo "!! generated_files partially failed (tests half does not matter)"
echo "=== the three vendor archives, for RISC-V this time ==="
make -C library CC=riscv64-unknown-elf-gcc AR=riscv64-unknown-elf-ar CFLAGS="$CFL" static 2>&1 | tail -4
ls -la library/*.a
for a in library/*.a; do echo "$a members=$(riscv64-unknown-elf-ar t "$a" | wc -l)"; done
