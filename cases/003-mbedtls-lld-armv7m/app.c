/* The same consumer as case 002, made FREESTANDING so no libc is needed.
 *
 * WHY FREESTANDING. Case 003 exists to compare LINKERS, so everything else has to be held still.
 * Pulling newlib in would mean linking a GCC-built libc with LLD and comparing two maps that
 * differ in their libc as well as their linker. With -nostdlib the image is the application, the
 * vendor archive, and nothing else -- and the three mbed TLS members it needs supply their own
 * requirements apart from memcpy and memset, which are provided here. */
#include <stddef.h>
#include "mbedtls/sha256.h"
#include "mbedtls/aes.h"

void *memcpy(void *to, const void *from, size_t n)
{
    unsigned char *d = to; const unsigned char *s = from;
    while (n--) { *d++ = *s++; }
    return to;
}

void *memset(void *to, int value, size_t n)
{
    unsigned char *d = to;
    while (n--) { *d++ = (unsigned char) value; }
    return to;
}

static unsigned char key[16];
static unsigned char block[16];
static unsigned char digest[32];

int work(void)
{
    mbedtls_sha256_context sha;
    mbedtls_aes_context aes;

    mbedtls_sha256_init(&sha);
    mbedtls_sha256_starts(&sha, 0);
    mbedtls_sha256_update(&sha, block, sizeof(block));
    mbedtls_sha256_finish(&sha, digest);
    mbedtls_sha256_free(&sha);

    mbedtls_aes_init(&aes);
    mbedtls_aes_setkey_enc(&aes, key, 128);
    mbedtls_aes_crypt_ecb(&aes, MBEDTLS_AES_ENCRYPT, block, block);
    mbedtls_aes_free(&aes);

    return (int) digest[0] ^ (int) block[0];
}

/* The entry point, so -nostdlib has something to start from. */
void _start(void) { for (;;) { (void) work(); } }
