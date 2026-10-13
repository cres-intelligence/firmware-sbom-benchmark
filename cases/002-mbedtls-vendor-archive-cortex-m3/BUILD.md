# Reproducing case 002

Everything needed is in this directory. It was built on 2026-10-13 and rebuilt to confirm the
output is identical.

## One command at a time

```bash
cd benchmark/cases/002-mbedtls-vendor-archive-cortex-m3
docker build -t cres-case002 .
mkdir -p out
docker run --rm -v "$PWD:/work" cres-case002 bash /work/clone.sh           # pins v3.6.2
docker run --rm -v "$PWD:/work" cres-case002 bash /work/build-archives.sh  # the three .a files
docker run --rm -v "$PWD:/work" cres-case002 bash /work/link.sh            # the map
```

**Expected, and asserted in the test suite:**

```
3 archives · 7 objects · 58,291 linked bytes
libmbedcrypto.a   86 members in the archive, 3 pulled into the image
app.elf           sha256:0d0703ca9b2e643a7faad68d53e44a8bd872c6bf7b44fc010a939d635a465c2a
                  text 7,080  data 112  bss 9,000
```

## Four things that bit, written down so they do not again

**`libnewlib-arm-none-eabi` is a separate Debian package.** `gcc-arm-none-eabi` alone gives a
compiler with no libc headers at all, and the build dies on `string.h: No such file or directory` —
which reads like a broken toolchain rather than a missing package.

**A git clone of Mbed TLS 3.6 has no generated files, and generating them needs more than Python.**
`make generated_files` wants `jsonschema` and `jinja2`, and the `framework` submodule — so the
clone is `--recurse-submodules --shallow-submodules`. The `tests/generated_files` half still fails
and does not matter: `make -C library static` is what builds the archives.

**An over-specified config fails `check_config.h` rather than the compiler.**
`MBEDTLS_PLATFORM_NO_STD_FUNCTIONS` with the `MBEDTLS_PLATFORM_STD_*` defines produced
`#error "MBEDTLS_PLATFORM_STD_SNPRINTF defined, but not all prerequisites"`. The platform layer is
now left at its defaults; newlib supplies `calloc`, `free` and `snprintf`.

**COMPILE AND LINK AS TWO STEPS, or the case is not reproducible.** One `gcc` invocation doing both
leaves the application's object as a compiler temporary — `/tmp/ccM19uij.o` — whose name is
different on every run. The map therefore differs between two identical builds, and dimension 7
could never pass. Splitting it gives `app.o`, and two runs then produce byte-identical maps and
byte-identical artifacts. The artifact digest was the same either way; it was the *map* that moved.

## What this case establishes that case 001 could not

Case 001 recorded no commit and kept no artifact, so its versions and its binary binding are
`not-established` and the scorer refuses to score them. This case fixes all of it:

| | case 001 | case 002 |
|---|---|---|
| upstream commit | not recorded | `107ea89d` (v3.6.2), framework `94599c0e` |
| artifact digest | not kept | `sha256:0d0703ca…` |
| component version | not-established | **pinned** — `MBEDTLS_VERSION_STRING` in the built header |
| component licence | heuristic | **pinned** — `LICENSE` plus the SPDX headers of the three members that shipped |
| reproducibility | not measured | **measured** — two runs, identical artifact and map |
| vendor archive | none (loose objects only) | `libmbedcrypto.a`, 86 members, 3 pulled in |

## Capturing newlib's version, which is still open

`newlib` is the largest component in the image at 43KB of 58KB and its version is still
`not-established`: the archive paths carry GCC's version, not newlib's. One line in the recipe would
settle it and is not there yet:

```bash
dpkg -s libnewlib-arm-none-eabi | grep ^Version   # and COPYING.NEWLIB for the licence
```
