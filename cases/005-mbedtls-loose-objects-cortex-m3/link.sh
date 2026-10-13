#!/bin/bash
set -euo pipefail
cd /work
mkdir -p out

# THE APP IS IN ITS OWN DIRECTORY, unlike case 002 where it sits at /work. That is what makes this
# case discriminate: the build root is /work, mbedtls/ carries project markers and app/ carries
# none, so the collector must produce TWO groups and must say which name rests on a marker and
# which rests only on the directory layout.
mkdir -p /work/app
cp /work/app.c /work/app/main.c

FLAGS=(-mcpu=cortex-m3 -mthumb -Os -ffunction-sections -fdata-sections
       -I/work -I/work/mbedtls/include
       '-DMBEDTLS_CONFIG_FILE="baremetal_config.h"')

# THE APP'S COMPILE GOES INTO THE SAME DATABASE, with bear --append. Without it the collector
# attributed 108 Mbed TLS objects and left main.o accounted for by nothing -- correct behaviour for
# a provider that was never shown the app, but it meant the case demonstrated only one group and so
# could not show that the attribution DISCRIMINATES between two trees.
echo "=== compile the app, appended to the same compilation database ==="
bear --append --output /work/out/compile_commands.json -- \
  arm-none-eabi-gcc "${FLAGS[@]}" -c /work/app/main.c -o /work/out/main.o

# LINK THE LOOSE OBJECTS, NOT THE ARCHIVE. This is the whole variable this case isolates. Case 002
# links -lmbedcrypto and the linker picks the members it needs; here every object is on the command
# line, so --gc-sections is the only thing standing between the image and all 86 of them. The link
# map then reports 80-odd LOOSE OBJECTS and not one archive from Mbed TLS -- the shape case 001
# has, and the shape the collector scored 0.25 recall on.
echo "=== link every library object directly, --gc-sections, with a map ==="
cd /work/out
arm-none-eabi-gcc -mcpu=cortex-m3 -mthumb \
  --specs=nosys.specs --specs=nano.specs \
  -Wl,--gc-sections -Wl,-Map=output.map \
  main.o /work/mbedtls/library/*.o \
  -o app.elf

echo "=== the artifact, hashed ==="
sha256sum app.elf main.o | tee app.sha256
arm-none-eabi-size app.elf | tee size.txt
echo "map bytes: $(wc -c < output.map)"
gzip -9 -k -f output.map
