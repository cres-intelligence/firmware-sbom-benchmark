# Reproducing case 001

The point of a corpus is that somebody else gets the same bytes. This is how.

## What was done on 2026-10-12

```bash
git clone --recurse-submodules https://github.com/FreeRTOS/FreeRTOS.git   # ~1.6GB
cd FreeRTOS/FreeRTOS-Plus/Demo/FreeRTOS_Plus_TCP_Echo_Qemu_mps2
make                                   # emits build/output.map unchanged by us
```

In a container, because **this Mac cannot do it natively**: Apple clang and `ld64` emit a Mach-O
map in a completely different format, and there is no `arm-none-eabi-gcc` here.

```dockerfile
FROM debian:bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc-arm-none-eabi make ca-certificates git && rm -rf /var/lib/apt/lists/*
```

`arm-none-eabi-gcc` 12.2.1 is what bookworm ships. The demo's own Makefile already passes
`-ffunction-sections -fdata-sections` and `-Xlinker --gc-sections -Xlinker -Map=build/output.map`
— **we changed no flags.** That matters more than it looks: the discarded sections this case turns
on are a consequence of the project's configuration, not of one we imposed to make the result come
out the way we wanted.

Result: `freertos_tcp_mps2_demo.axf`, 80,540 bytes of text, and a 309KB map.

## What is wrong with the above, and must be fixed first

**No commit was recorded, and the clone is gone.** So:

* **No component version is established.** The map never carries versions; the source tree would
  have, and we cannot get back to it.
* **No artifact digest was recorded**, so nothing binds this map to a specific binary.

Both are marked `not-established` in `ground-truth.json` and `score.py` refuses to score the
dimensions that depend on them. That is the honest outcome, and it is also a smaller corpus than it
needed to be.

**So the next run records all of it**, which is the only change to the recipe:

```bash
git clone --recurse-submodules https://github.com/FreeRTOS/FreeRTOS.git
cd FreeRTOS
git rev-parse HEAD                     > ../case-commit.txt
git submodule status                   > ../case-submodules.txt
cd FreeRTOS-Plus/Demo/FreeRTOS_Plus_TCP_Echo_Qemu_mps2
make
sha256sum build/freertos_tcp_mps2_demo.axf > ../../../../case-artifact.sha256
```

The submodule statuses matter as much as the top-level commit: FreeRTOS-Plus-TCP and the kernel are
submodules, and they are the two components whose versions this case cannot currently state.

## Checking the map parses to the same thing

```bash
cd cres-aws-t4
PYTHONPATH=/path/to/cres-aws:$PWD python3 - <<'PY'
import gzip
from cres_t4.service import linker_map
text = gzip.open('benchmark/cases/001-freertos-plus-tcp-mps2/evidence/output.map.gz',
                 'rt', errors='replace').read()
out = linker_map.parse(text)
print(out['ArchiveCount'], out['ObjectCount'], out['LinkedBytes'])   # 3 56 297027
PY
```

`3 56 297027` is the fingerprint of this case. The same three numbers are asserted in
`tests/unit/suites/sbom/test_linker_map.py`, which reads this same file — there is one copy of the
map in the repository and both the corpus and the test suite use it.
