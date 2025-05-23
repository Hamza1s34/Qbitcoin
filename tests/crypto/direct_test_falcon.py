#!/usr/bin/env python3
"""
Direct test of the pqcrypto library with Falcon-512
"""

from pqcrypto.sign.falcon_512 import (
    generate_keypair,
    sign,
    verify,
    PUBLIC_KEY_SIZE,
    SECRET_KEY_SIZE,
    SIGNATURE_SIZE,
    __ffi as ffi,  # Direct CFFI access
    __lib as lib   # Direct CFFI access
)

print("==== Testing with direct pqcrypto library usage ====")
print(f"Library reported constants:")
print(f"PUBLIC_KEY_SIZE = {PUBLIC_KEY_SIZE}")
print(f"SECRET_KEY_SIZE = {SECRET_KEY_SIZE}")
print(f"SIGNATURE_SIZE = {SIGNATURE_SIZE}")

# Get the actual expected sizes from the library C API
print("\n==== Raw library constants ====")
print(f"PQCLEAN_FALCON512_CLEAN_CRYPTO_PUBLICKEYBYTES = {lib.PQCLEAN_FALCON512_CLEAN_CRYPTO_PUBLICKEYBYTES}")
print(f"PQCLEAN_FALCON512_CLEAN_CRYPTO_SECRETKEYBYTES = {lib.PQCLEAN_FALCON512_CLEAN_CRYPTO_SECRETKEYBYTES}")
print(f"PQCLEAN_FALCON512_CLEAN_CRYPTO_BYTES = {lib.PQCLEAN_FALCON512_CLEAN_CRYPTO_BYTES}")

# Generate a new key pair directly using pqcrypto's lower-level CFFI interface
print("\n==== Generating keys with direct CFFI ====")
public_key_buf = ffi.new(f"uint8_t [{lib.PQCLEAN_FALCON512_CLEAN_CRYPTO_PUBLICKEYBYTES}]")
secret_key_buf = ffi.new(f"uint8_t [{lib.PQCLEAN_FALCON512_CLEAN_CRYPTO_SECRETKEYBYTES}]")

if 0 != lib.PQCLEAN_FALCON512_CLEAN_crypto_sign_keypair(public_key_buf, secret_key_buf):
    print("Key generation failed!")
else:
    print("Key generation succeeded")

# Extract the keys to Python bytes objects
public_key = bytes(ffi.buffer(public_key_buf, lib.PQCLEAN_FALCON512_CLEAN_CRYPTO_PUBLICKEYBYTES))
secret_key = bytes(ffi.buffer(secret_key_buf, lib.PQCLEAN_FALCON512_CLEAN_CRYPTO_SECRETKEYBYTES))

# Print sizes to verify
print(f"Generated public key size: {len(public_key)}")
print(f"Generated secret key size: {len(secret_key)}")

# Test message
message = b"This is a direct test message for Falcon-512 signature"
message_len = len(message)
print(f"\nMessage: {message.decode()}")

# Sign the message using direct CFFI
print("\n==== Signing message with direct CFFI ====")
signature_buf = ffi.new(f"uint8_t [{lib.PQCLEAN_FALCON512_CLEAN_CRYPTO_BYTES}]")
signature_len_ptr = ffi.new("size_t *", lib.PQCLEAN_FALCON512_CLEAN_CRYPTO_BYTES)

result = lib.PQCLEAN_FALCON512_CLEAN_crypto_sign_signature(
    signature_buf, signature_len_ptr, message, message_len, secret_key
)

if result != 0:
    print("Signing failed!")
else:
    signature_len = signature_len_ptr[0]
    print(f"Signing succeeded, signature length: {signature_len}")
    
    # Extract signature to bytes
    signature = bytes(ffi.buffer(signature_buf, signature_len))
    print(f"Extracted signature size: {len(signature)}")
    
    # Verify the signature
    print("\n==== Verifying signature with direct CFFI ====")
    result = lib.PQCLEAN_FALCON512_CLEAN_crypto_sign_verify(
        signature_buf, signature_len, message, message_len, public_key
    )
    
    if result != 0:
        print("Signature verification failed!")
    else:
        print("Signature verification succeeded!")