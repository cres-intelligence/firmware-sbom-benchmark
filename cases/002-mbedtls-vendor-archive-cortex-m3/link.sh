#!/bin/bash
set -euo pipefail
cd /work
mkdir -p out
FLAGS=(-mcpu=cortex-m3 -mthumb -Os -ffunction-sections -fdata-sections
       -I/work -I/work/mbedtls/include
       '-DMBEDTLS_CONFIG_FILE="baremetal_config.h"')

# COMPILE AND LINK AS TWO STEPS, deliberately. Doing both in one gcc invocation leaves the app's
# object as a compiler temporary -- /tmp/ccM19uij.o -- whose name differs on every run, so two
# equivalent builds produce different maps and the reproducibility dimension can never pass. A
# corpus case has to be reproducible before it can measure anything.
echo "=== compile ==="
arm-none-eabi-gcc "${FLAGS[@]}" -c /work/app.c -o /work/out/app.o

echo "=== link against the vendor archive, --gc-sections, with a map ==="
cd /work/out
arm-none-eabi-gcc -mcpu=cortex-m3 -mthumb \
  --specs=nosys.specs --specs=nano.specs \
  -Wl,--gc-sections -Wl,-Map=output.map \
  app.o -L/work/mbedtls/library -lmbedcrypto \
  -o app.elf

echo "=== the artifact, hashed ==="
sha256sum app.elf app.o | tee app.sha256
arm-none-eabi-size app.elf | tee size.txt
echo "map bytes: $(wc -c < output.map)"

echo "=== archive members: in the archive vs pulled into the image ==="
arm-none-eabi-ar t /work/mbedtls/library/libmbedcrypto.a | sort > members-in-archive.txt
grep -oE 'libmbedcrypto\.a\(([a-z0-9_]+\.o)\)' output.map \
  | sed -E 's/.*\((.*)\)/\1/' | sort -u > members-pulled-in.txt
echo "in archive:  $(wc -l < members-in-archive.txt)"
echo "pulled in:   $(wc -l < members-pulled-in.txt)"
comm -23 members-in-archive.txt members-pulled-in.txt > members-never-pulled.txt
echo "never pulled: $(wc -l < members-never-pulled.txt)"
gzip -9 -k -f output.map
