/* A bare-metal mbed TLS configuration: exactly what app.c calls, and nothing else.
 *
 * DELIBERATELY MINIMAL, because the case is about what the LINKER discards from a vendor archive.
 * A trimmed config means the archive still carries hundreds of members -- the build compiles every
 * enabled module -- while the image needs a handful. That gap is the measurement.
 *
 * The platform layer is left at its defaults: newlib supplies calloc, free and snprintf, and
 * overriding them with MBEDTLS_PLATFORM_NO_STD_FUNCTIONS tripped check_config.h's prerequisites. */
#define MBEDTLS_PLATFORM_C
#define MBEDTLS_NO_PLATFORM_ENTROPY

#define MBEDTLS_AES_C
#define MBEDTLS_SHA256_C
#define MBEDTLS_SHA224_C
#define MBEDTLS_MD_C
#define MBEDTLS_CIPHER_C
#define MBEDTLS_ERROR_C
