#!/bin/bash
set -euo pipefail
cd /work
git clone --depth 1 --branch v3.6.2 --recurse-submodules --shallow-submodules \
    https://github.com/Mbed-TLS/mbedtls.git 2>&1 | tail -2
cd mbedtls
# THE COMMIT IS RECORDED THIS TIME. Case 001's was not, and that single omission makes four of its
# eight dimensions unscoreable for good -- the tree is gone and there is no way back to it.
{
  echo "commit:   $(git rev-parse HEAD)"
  echo "describe: $(git describe --tags --always)"
  git submodule status
} | tee /work/out/provenance.txt
# The markers the collector will read to name this project. Confirming they are there BEFORE the
# build means a missing attribution is a defect in the collector, not an absent LICENSE.
echo "project markers in /work/mbedtls:"
ls -la /work/mbedtls/.git /work/mbedtls/LICENSE 2>&1 | sed 's/^/    /'
echo "build files inside library/, which must NOT be mistaken for project markers:"
ls /work/mbedtls/library/Makefile /work/mbedtls/library/CMakeLists.txt 2>&1 | sed 's/^/    /'
