# Reproducing case 003

```bash
cd benchmark/cases/003-mbedtls-lld-armv7m
docker build -t cres-case003 .
mkdir -p out
docker run --rm -v "$PWD:/work" cres-case003 bash /work/clone.sh
docker run --rm -v "$PWD:/work" cres-case003 bash /work/build-archives.sh
docker run --rm -v "$PWD:/work" cres-case003 bash /work/link.sh
```

**Expected:**

```
libmbedcrypto.a   94,294 bytes, 86 members      (byte-identical to case 002)
pulled in by LLD   aes.o, platform_util.o, sha256.o   -- the same three GNU ld chose
app.elf            sha256:339ca9dda1b1b7020b92229ea4861bd7fc7161ed4d1d7ee4e28040bc6a121c8c
map                16,410 linked bytes across its sized rows
```

The container carries **both** toolchains deliberately: `arm-none-eabi-gcc` builds the archive so it
is identical to case 002's, and `clang` + `ld.lld` do the link. One variable changes.

## This is not IAR and not armlink

Case 003 was asked for with IAR or armlink. **Both are proprietary and licence-gated** — the
downloads need an entitlement and the tools refuse to run without a licence server or a node-locked
key. Neither is on this machine and neither installs from a public source, so neither could be
built. Writing a plausible map for either would have been exactly the unreproducible evidence this
corpus exists to replace, so none was written.

LLD is the nearest thing that is real, and it turned out to answer the question better than a third
GNU-family toolchain would have.

**To do IAR or armlink properly, one of:**

* an IAR Build Tools or Keil MDK licence, or
* **a single real `.map` file from either**, for any project, with the build recipe beside it.

One real artifact is enough to write *and test* a reader for a format. A specification is not — see
the third finding below, which no specification would have told us.

## What LLD changed, and what it did not

**It did not change the answer.** LLD pulled in the same three of 86 members. "Which members
shipped" has a toolchain-independent answer, which is the premise the collector rests on, and it
had never been checked against a second linker.

**It changed the format completely.** An LLD map opens with a column header and bare hex sizes:

```
     VMA      LMA     Size Align Out     In      Symbol
   100f4    100f4       10     4 .ARM.exidx
   10104    10104      100     4         libmbedcrypto.a(sha256.o):(.rodata.K)
```

A GNU ld map has no header, writes `0x`-prefixed values, and groups under `Archive member included
to satisfy reference by file`, `Discarded input sections` and `Linker script and memory map`.
`cres_t4.service.linker_map.parse` refuses this file with *"That file does not look like a GNU ld
link map"*, which is the correct behaviour and is pinned by a test: a half-read foreign map produces
confident wrong numbers, which is worse than a refusal.

**And it removed the discard evidence entirely.** This is the finding worth the whole case.

An LLD map contains **zero** occurrences of `Discarded`, `Archive member`, or anything equivalent.
`--print-gc-sections` exists but is a separate stderr artifact, and it is **a list of removals, not
an inventory** — which makes it no substitute, in two ways. Nine lines here, from `app.o`, `aes.o`
and `platform_util.o`. The 83 members never pulled in produce **no output at all**, because there
was nothing to collect. And `sha256.o` produces none either, **despite being in the image**, because
every section it contributed was used. So the output reads neither as what shipped nor as what did
not.

So:

| | GNU ld | LLD |
|---|---|---|
| what shipped | the map | the map |
| which archive members were included | the map | **nowhere in the link** |
| what was discarded from included objects | the map | `--print-gc-sections`, separately |
| "in the archive but did not ship" | inferable from the map alone | **requires reading the archive** |

A collector that reads only the map is correct on GNU ld and blind here. That is a requirement on
the collector, discovered by building something rather than by reading a manual.
