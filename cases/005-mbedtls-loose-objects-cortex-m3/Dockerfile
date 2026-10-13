FROM debian:bookworm
# libnewlib-arm-none-eabi IS A SEPARATE PACKAGE, as case 002 discovered the hard way: the cross
# gcc alone has no libc headers at all.
#
# bear IS THE POINT OF THIS CASE. It wraps a build and records every compiler invocation into a
# compile_commands.json, which is the input the collector's compile-commands provider reads. Using
# a real interception tool rather than writing the database by hand is deliberate -- a database we
# authored would be a database we could make come out right.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc-arm-none-eabi binutils-arm-none-eabi libnewlib-arm-none-eabi \
        bear make git python3 python3-jsonschema python3-jinja2 perl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /work
