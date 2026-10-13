#!/bin/bash
set -euo pipefail
cd /work; mkdir -p out
FLAGS=(--specs=picolibc.specs -march=rv64imac -mabi=lp64 -Os -ffunction-sections -fdata-sections
       -I/work -I/work/mbedtls/include
       '-DMBEDTLS_CONFIG_FILE="baremetal_config.h"')
echo "=== versions ==="; riscv64-unknown-elf-gcc --version | head -1; riscv64-unknown-elf-ld --version | head -1
# -march=rv64imac, NOT rv64imac_zicsr. The _zicsr suffix is a valid ISA string and is NOT a
# shipped multilib, so gcc silently fell back to the default (rv64imafdc/lp64d, double-float)
# and the link died on "can't link double-float modules with soft-float modules". The error
# names the symptom; the cause is a march string with no matching multilib.
# `riscv64-unknown-elf-gcc -print-multi-lib` lists what actually exists.
#
# -lgcc IS REQUIRED HERE AND WAS NOT ON CORTEX-M, which is a finding rather than a nuisance:
# base RISC-V has no byte-swap instruction, so mbed TLS's SHA-256 calls libgcc's __bswapsi2
# where ARM got a single `rev`. libgcc is therefore a real component of this image and not of
# case 003's.
echo "=== compile then link, two steps (see case 002: one step makes the map non-reproducible) ==="
riscv64-unknown-elf-gcc "${FLAGS[@]}" -c /work/app.c -o /work/out/app.o
cd /work/out
riscv64-unknown-elf-gcc --specs=picolibc.specs -march=rv64imac -mabi=lp64 -nostdlib \
  -Wl,--gc-sections -Wl,-Map=output.map -Wl,--entry=_start \
  app.o -L/work/mbedtls/library -lmbedcrypto -lgcc -o app.elf
sha256sum app.elf app.o | tee app.sha256
riscv64-unknown-elf-size app.elf | tee size.txt
echo "map bytes: $(wc -c < output.map)"
echo "=== members pulled in ==="
riscv64-unknown-elf-ar t /work/mbedtls/library/libmbedcrypto.a | sort > members-in-archive.txt
grep -oE 'libmbedcrypto\.a\(([a-z0-9_]+\.o)\)' output.map | sed -E 's/.*\((.*)\)/\1/' | sort -u > members-pulled-in.txt
echo "in archive: $(wc -l < members-in-archive.txt)  pulled: $(wc -l < members-pulled-in.txt)"
cat members-pulled-in.txt
comm -23 members-in-archive.txt members-pulled-in.txt > members-never-pulled.txt
echo "never pulled: $(wc -l < members-never-pulled.txt)"
gzip -9 -k -f output.map
