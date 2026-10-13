# Case 005 — Mbed TLS as loose object files, read through a compilation database

## What this case is for

Case 002 links Mbed TLS as a static archive. **This case links the identical sources, built with
the identical compiler and flags for the identical target, as 108 loose object files.** Packaging is
the only variable.

It exists because of a number: case 001 scored **0.25 recall**, and the reason was this shape. A
firmware that hands its dependencies to the linker as loose objects gives the link map no archive to
name, so a collector reading the map alone has nothing to report them as. Answering it needs the
**compile** commands, which is what `build-system-providers` is.

## Reproducing it

```bash
cd benchmark/cases/005-mbedtls-loose-objects-cortex-m3
docker build -t cres-bench-005 .
docker run --rm -v "$PWD":/case:ro -v /tmp/bench005out:/work/out \
  -v ../../../collector/build/cres-collect:/usr/local/bin/cres-collect:ro \
  cres-bench-005 bash -c '
    mkdir -p /work/out
    cp /case/app.c /case/baremetal_config.h /work/
    bash /case/clone.sh && bash /case/build.sh && bash /case/link.sh'
```

Then read the build three ways against the same map:

```bash
cres-collect --map output.map --out bom-map-only.json
cres-collect --map output.map --provider compile-commands \
    --compile-commands compile_commands.json --out bom.json --evidence attribution.txt
cres-collect --map output.map --provider make \
    --make-dry-run make-dry-run.txt --make-dir /work/mbedtls/library --out bom-make.json
```

## What each step is doing, and the traps in it

**`clone.sh`** pins `v3.6.2` and **records the commit**. Case 001 did not record its commit, the
tree is gone, and four of its eight dimensions are permanently unscoreable as a result. It also
prints the project markers it expects the collector to read — `.git` and `LICENSE` in
`/work/mbedtls` — *before* the build, so a missing attribution is a defect in the collector rather
than an absent `LICENSE`.

**`build.sh`** does three things in an order that matters:

1. `make -C library generated_files`, and **only** the library's. The top-level `generated_files`
   target also builds the *test* data, whose generator needs Python packages this image does not
   carry. A case that cannot be rebuilt because of a dependency it never needed is a case that rots.
2. `make -n`, captured **from an untouched tree**. A dry run of an already-built tree prints
   nothing, because nothing is out of date — which looks exactly like a provider that failed to read
   the build.
3. The real build under **`bear`**, which records every compiler invocation into
   `compile_commands.json` by interception. *A hand-authored compilation database is one whose
   contents can be made to come out right*, which would make this case measure nothing.

**`link.sh`** compiles the app in its own directory (`/work/app`, unlike case 002 where it sits at
`/work`) and appends that one compile to the same database with `bear --append`. That is what makes
the case discriminate: the build root is `/work`, `mbedtls/` carries project markers and `app/`
carries none, so a correct collector must produce **two** groups and must say which name rests on a
marker and which rests only on a directory layout.

Then it names all 108 objects on the link line rather than `-lmbedcrypto`. `--gc-sections` is the
only thing standing between the image and all of them.

## What it established

| | case 002 (archive) | case 005 (loose objects) |
|---|---|---|
| Mbed TLS objects on the link line | 3 of 86 members pulled in | **108 of 108** |
| Objects contributing bytes | 3 | **3** |
| Which ones | `aes.o`, `sha256.o`, `platform_util.o` | **the same three** |
| Mbed TLS linked bytes | 14,032 | **14,032** |
| Total linked bytes | 16,184 | **16,184** |

**Byte for byte identical.** Two builds packaging the same dependency two different ways put the
same bytes in the device, and the corpus now has four independent confirmations that *which Mbed TLS
translation units ship* depends on neither the linker (GNU ld in 002/004/005, LLD in 003), nor the
architecture (Cortex-M3 in 002/003/005, RISC-V rv64imac in 004), nor the packaging (archive in
002/003/004, loose objects here).

**It also caught a defect in the byte accounting of both map readers**, which is recorded in the
corpus README. The first run of this case reported Mbed TLS as `108 of 108 objects contributed` in
an image whose entire `.text` is 7,080 bytes. That is not a subtle wrong answer, and the only reason
it was visible at all is that this case's arithmetic is checkable against case 002's.
