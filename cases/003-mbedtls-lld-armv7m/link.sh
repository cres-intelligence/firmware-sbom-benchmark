#!/bin/bash
set -euo pipefail
cd /work
mkdir -p out

echo "=== versions ==="
clang --version | head -1
ld.lld --version

echo "=== compile the app with clang for armv7m ==="
clang --target=armv7m-none-eabi -Os -ffunction-sections -fdata-sections \
      -I/work -I/work/mbedtls/include \
      '-DMBEDTLS_CONFIG_FILE="baremetal_config.h"' \
      -c /work/app.c -o /work/out/app.o

echo "=== link with LLD -- the same archive case 002 linked with GNU ld ==="
cd /work/out
ld.lld -o app.elf app.o \
  --gc-sections --entry _start --Map=output.map \
  -L/work/mbedtls/library -lmbedcrypto

echo "=== the artifact ==="
sha256sum app.elf app.o | tee app.sha256
llvm-size app.elf 2>/dev/null || true
echo "map bytes: $(wc -c < output.map)"

echo "=== which archive members did LLD pull in? ==="
grep -oE 'libmbedcrypto\.a\(([a-z0-9_]+\.o)\)' output.map | sed -E 's/.*\((.*)\)/\1/' \
  | sort -u > members-pulled-in.txt || true
cat members-pulled-in.txt
echo "pulled in: $(wc -l < members-pulled-in.txt)"

echo "=== THE FIRST 25 LINES OF AN LLD MAP, which is the point of this case ==="
head -25 output.map

echo "=== LLD's discard evidence is NOT in the map; it is a separate artifact ==="
cd /work/out
ld.lld -o /dev/null app.o \
  --gc-sections --entry _start --print-gc-sections \
  -L/work/mbedtls/library -lmbedcrypto 2>&1 | tee gc-sections.txt | head -8
echo "removed sections reported: $(grep -c 'removing unused section' gc-sections.txt || true)"
grep -oE 'libmbedcrypto\.a\(([a-z0-9_]+\.o)\)' gc-sections.txt | sed -E 's/.*\((.*)\)/\1/' \
  | sort -u > gc-members.txt || true
echo "members with at least one removed section: $(wc -l < gc-members.txt)"
gzip -9 -k -f output.map
