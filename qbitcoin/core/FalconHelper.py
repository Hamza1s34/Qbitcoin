"""
Falcon Helper functions for working with addresses and public keys
"""
import hashlib


def falcon_pk_to_address(public_key: bytes) -> bytes:
    """
    Convert a Falcon public key to a QRL address in bytes format
    
    Args:
        public_key (bytes): Falcon public key
        
    Returns:
        bytes: QRL address in bytes format (25 bytes total)
    """
    # Perform SHA-256 hash
    sha256_hash = hashlib.sha256(public_key).digest()
    
    # Perform RIPEMD-160 hash on the SHA-256 hash
    ripemd160_hash = hashlib.new('ripemd160')
    ripemd160_hash.update(sha256_hash)
    hash160 = ripemd160_hash.digest()
    
    # Create binary address with proper format:
    # [0] - Address type (0x01 for standard Qbitcoin address with Falcon)
    # [1:21] - RIPEMD160 hash of the public key (20 bytes)
    address_bytes = b'\x01' + hash160
    
    # Add a 4-byte checksum (double SHA-256 of the first 21 bytes)
    checksum = hashlib.sha256(hashlib.sha256(address_bytes).digest()).digest()[:4]
    binary_address = address_bytes + checksum
    
    return binary_address


def is_falcon_public_key(pk: bytes) -> bool:
    """
    Checks if the provided public key is a valid Falcon public key
    
    Args:
        pk (bytes): Public key to check
        
    Returns:
        bool: True if the public key is likely a Falcon public key
    """
    from pqcrypto.sign.falcon_512 import PUBLIC_KEY_SIZE
    
    # Falcon-512 has a specific public key size
    return len(pk) == PUBLIC_KEY_SIZE
