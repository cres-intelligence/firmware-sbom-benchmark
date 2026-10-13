FROM debian:bookworm
# THE LIBC IS A SEPARATE PACKAGE, AND I MADE THIS EXACT MISTAKE ON CASE 002 AND WROTE IT DOWN.
# gcc-riscv64-unknown-elf alone is a compiler with no libc headers: the build dies on
# `stdint.h: No such file or directory`, the RISC-V twin of case 002's `string.h`. Debian
# splits the libc out of every cross toolchain -- libnewlib for arm-none-eabi,
# picolibc for riscv64-unknown-elf. Documenting a lesson is not the same as applying it.
#
# A DIFFERENT ARCHITECTURE, THE SAME LINKER FAMILY. Case 004 changes rv64 for Cortex-M and holds
# everything else still -- same project, same commit, same minimal config, same GNU ld -- so a
# difference in the result is attributable to the architecture and nothing else.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc-riscv64-unknown-elf binutils-riscv64-unknown-elf \
        picolibc-riscv64-unknown-elf \
        make git python3 python3-jsonschema python3-jinja2 perl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /work
