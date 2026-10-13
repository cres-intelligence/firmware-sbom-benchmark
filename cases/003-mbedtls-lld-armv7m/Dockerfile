FROM debian:bookworm
# BOTH TOOLCHAINS ON PURPOSE. The archive is built with arm-none-eabi-gcc so it is byte-identical
# to case 002's, and the LINK is done with LLD. Case 003 therefore differs from case 002 in exactly
# one variable: the linker, and so the map format.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc-arm-none-eabi binutils-arm-none-eabi libnewlib-arm-none-eabi \
        clang-14 lld-14 llvm-14 \
        make git python3 python3-jsonschema python3-jinja2 perl ca-certificates \
    && ln -sf /usr/bin/ld.lld-14 /usr/bin/ld.lld \
    && ln -sf /usr/bin/clang-14 /usr/bin/clang \
    && ln -sf /usr/bin/llvm-nm-14 /usr/bin/llvm-nm \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /work
