FROM debian:bookworm
# libnewlib-arm-none-eabi IS A SEPARATE PACKAGE ON DEBIAN. gcc-arm-none-eabi alone gives a
# compiler with no libc headers at all -- the first build failed on `string.h: No such file`.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc-arm-none-eabi binutils-arm-none-eabi libnewlib-arm-none-eabi \
        make git python3 python3-jsonschema python3-jinja2 perl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /work
