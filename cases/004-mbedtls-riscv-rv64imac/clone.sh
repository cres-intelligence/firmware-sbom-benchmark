#!/bin/bash
set -euo pipefail
cd /work
git clone --depth 1 --branch v3.6.2 --recurse-submodules --shallow-submodules \
    https://github.com/Mbed-TLS/mbedtls.git 2>&1 | tail -2
cd mbedtls
echo "commit:   $(git rev-parse HEAD)"      | tee /work/out/provenance.txt
echo "describe: $(git describe --tags --always)" | tee -a /work/out/provenance.txt
git submodule status | tee -a /work/out/provenance.txt
