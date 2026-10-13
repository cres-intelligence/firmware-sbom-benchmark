/* A deliberately small consumer of a vendor static library.
 *
 * It calls SHA-256 and AES, and NOTHING else. That is the whole point of the case: mbed TLS
 * builds to an archive carrying hundreds of object files, the linker pulls in only the members
 * needed to satisfy these calls, and --gc-sections then discards sections within them. What
 * reached the image is a question only the map can answer. */
#include <stddef.h>
#include "mbedtls/sha256.h"
#include "mbedtls/aes.h"

static unsigned char key[16];
static unsigned char block[16];
static unsigned char digest[32];

int main(void)
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
