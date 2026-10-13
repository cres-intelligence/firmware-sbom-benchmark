# Reproducing case 004

```bash
cd benchmark/cases/004-mbedtls-riscv-rv64imac
docker build -t cres-case004 .
mkdir -p out
docker run --rm -v "$PWD:/work" cres-case004 bash /work/clone.sh
docker run --rm -v "$PWD:/work" cres-case004 bash /work/build-archives.sh
docker run --rm -v "$PWD:/work" cres-case004 bash /work/link.sh
```

**Expected:**

```
libmbedcrypto.a   156,234 bytes, 86 members   (94,294 on Cortex-M -- same source, larger encoding)
pulled in          aes.o, platform_util.o, sha256.o   -- the SAME THREE as cases 002 and 003
libgcc.a           1 member: _bswapsi2.o
app.elf            sha256:6490e81dbf15d0c1fbae3da8aa8fcfb9a216c327e6791d3a10ea02248d9bd096
                   text 9,384  data 8  bss 10,864
2 archives · 1 object · 19,848 linked bytes
```

## Three things that bit, in the order they bit

**1. `gcc-riscv64-unknown-elf` has no libc headers.** `stdint.h: No such file or directory` — the
RISC-V twin of case 002's `string.h`. Debian splits the libc out of every cross toolchain:
`libnewlib` for arm-none-eabi, **`picolibc` for riscv64**. I had written that lesson down on case
002 and still made it again here.

**2. Installing picolibc is not enough; it needs a flag.** The package puts its headers somewhere
the compiler does not look by default. Checked by seeing which invocations actually produce an
object file, rather than trusting an exit code:

```
plain                                      -> FAILED
--specs=picolibc.specs                     -> PRODUCED
-isystem /usr/lib/picolibc/.../include     -> PRODUCED
```

**3. `-march=rv64imac_zicsr` is valid ISA syntax and is not a shipped multilib**, so gcc fell back
to the default — `rv64imafdc/lp64d`, double-float — and the link died on *"can't link double-float
modules with soft-float modules"*. The error names the symptom; the cause is a march string nothing
was built for. `riscv64-unknown-elf-gcc -print-multi-lib` lists what exists; `rv64imac/lp64` does.

## And one thing that is a finding rather than a bother

**`-lgcc` is required here and was not on Cortex-M.** The link fails with `undefined reference to
__bswapsi2`: base RISC-V has no byte-swap instruction, so mbed TLS's SHA-256 calls libgcc's helper
where ARM got a single `rev`.

So **libgcc is a real component of this image**, 1,298 bytes and exactly one member — a component
of case 002's too (division helpers) and of **neither** case 003's. Even the compiler runtime's
presence is a property of the architecture and the configuration rather than of the project, and it
appears in no source file and no manifest.

## What this case settles

| | 002 Cortex-M, GNU ld | 003 Cortex-M, LLD | 004 RISC-V, GNU ld |
|---|---|---|---|
| members pulled in | **aes, platform_util, sha256** | **the same three** | **the same three** |

**"Which archive members ship" is independent of the linker and of the architecture.** That is the
premise the collector rests on, and it now has three independent confirmations instead of an
assumption.
