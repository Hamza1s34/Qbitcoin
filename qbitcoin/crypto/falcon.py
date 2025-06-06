"""
Falcon post-quantum signature scheme implementation for Qbitcoin.
This module provides secure signing and verification using the Falcon-512 algorithm.
"""

import hashlib
import base64
import logging
from typing import Tuple, Optional, Dict, Any, Union

# Configure logger
logger = logging.getLogger(__name__)

# Import the Falcon 512 module from pqcrypto
from pqcrypto.sign.falcon_512 import (
    generate_keypair,
    sign as pq_sign,
    verify as pq_verify,
    PUBLIC_KEY_SIZE,
    SECRET_KEY_SIZE,
    SIGNATURE_SIZE,
    __ffi as ffi,  # Direct CFFI access
    __lib as lib   # Direct CFFI access
)


class FalconSignature:
    """
    Implementation of the Falcon post-quantum signature scheme.
    Provides methods for key generation, signing messages, and verifying signatures.
    """
    
    ALGORITHM_NAME = "falcon-512"
    
    @classmethod
    def get_algorithm_details(cls) -> Dict[str, int]:
        """
        Get the algorithm details including key and signature sizes
        
        Returns:
            Dict[str, int]: Dictionary with algorithm details
        """
        return {
            "name": cls.ALGORITHM_NAME,
            "public_key_size": PUBLIC_KEY_SIZE,
            "secret_key_size": SECRET_KEY_SIZE,
            "signature_size": SIGNATURE_SIZE
        }
    
    @staticmethod
    def generate_keypair() -> Tuple[bytes, bytes]:
        """
        Generate a new Falcon-512 key pair
        
        Returns:
            Tuple[bytes, bytes]: A tuple containing the private and public keys as bytes
        """
        # Generate the keypair using pqcrypto library
        key1, key2 = generate_keypair()
        
        # Check key sizes to determine which is which
        # In Falcon 512, SECRET_KEY_SIZE is 1281 and PUBLIC_KEY_SIZE is 897
        if len(key1) == SECRET_KEY_SIZE and len(key2) == PUBLIC_KEY_SIZE:
            # Keys are in correct order (secret_key, public_key)
            return key1, key2
        elif len(key1) == PUBLIC_KEY_SIZE and len(key2) == SECRET_KEY_SIZE:
            # Keys are in reverse order (public_key, secret_key)
            return key2, key1
        else:
            # If sizes don't match expected values, raise an error
            raise ValueError(f"Invalid key sizes: {len(key1)}, {len(key2)}. Expected: {SECRET_KEY_SIZE}, {PUBLIC_KEY_SIZE}")
    
    @staticmethod
    def sign_message(message: Union[str, bytes], private_key: bytes) -> bytes:
        """
        Sign a message using the Falcon-512 private key
        
        Args:
            message (Union[str, bytes]): Message to sign, can be string or bytes
            private_key (bytes): Private key for signing
            
        Returns:
            bytes: Signature
        """
        # Convert string message to bytes if necessary
        if isinstance(message, str):
            message = message.encode('utf-8')
        
        # Verify the private key is the correct size
        if len(private_key) != SECRET_KEY_SIZE:
            raise ValueError(f"Private key must be exactly {SECRET_KEY_SIZE} bytes, got {len(private_key)}")
        
        # Use direct CFFI approach for signing
        signature_buf = ffi.new(f"uint8_t [{lib.PQCLEAN_FALCON512_CLEAN_CRYPTO_BYTES}]")
        signature_len_ptr = ffi.new("size_t *", lib.PQCLEAN_FALCON512_CLEAN_CRYPTO_BYTES)
        
        result = lib.PQCLEAN_FALCON512_CLEAN_crypto_sign_signature(
            signature_buf, signature_len_ptr, message, len(message), private_key
        )
        
        if result != 0:
            raise RuntimeError("Signature generation failed")
        
        # Extract signature to bytes
        signature_len = signature_len_ptr[0]
        signature = bytes(ffi.buffer(signature_buf, signature_len))
        
        return signature
    
    @staticmethod
    def sign_message_with_prehash(message: Union[str, bytes], private_key: bytes) -> bytes:
        """
        Sign a message with SHA-256 prehashing for large messages
        
        Args:
            message (Union[str, bytes]): Message to sign, can be string or bytes
            private_key (bytes): Private key for signing
            
        Returns:
            bytes: Signature
        """
        # Convert string message to bytes if necessary
        if isinstance(message, str):
            message = message.encode('utf-8')
        
        # Hash the message first (recommended for large messages)
        message_hash = hashlib.sha256(message).digest()
        
        # Use the regular signing method with the hashed message
        return FalconSignature.sign_message(message_hash, private_key)
    
    @staticmethod
    def verify_signature(message: Union[str, bytes], signature: bytes, public_key: bytes) -> bool:
        """
        Verify a signature using the Falcon-512 public key
        
        Args:
            message (Union[str, bytes]): Original message
            signature (bytes): Signature to verify
            public_key (bytes): Public key for verification
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        # Convert string message to bytes if necessary
        if isinstance(message, str):
            message = message.encode('utf-8')
        
        # Verify the public key is the correct size
        if len(public_key) != PUBLIC_KEY_SIZE:
            raise ValueError(f"Public key must be exactly {PUBLIC_KEY_SIZE} bytes, got {len(public_key)}")
        
        # Use direct CFFI approach for verification
        try:
            result = lib.PQCLEAN_FALCON512_CLEAN_crypto_sign_verify(
                signature, len(signature), message, len(message), public_key
            )
            return result == 0
        except Exception:
            return False
    
    @staticmethod
    def verify_signature_with_prehash(message: Union[str, bytes], signature: bytes, public_key: bytes) -> bool:
        """
        Verify a signature that was created with prehashing
        
        Args:
            message (Union[str, bytes]): Original message
            signature (bytes): Signature to verify
            public_key (bytes): Public key for verification
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        # Convert string message to bytes if necessary
        if isinstance(message, str):
            message = message.encode('utf-8')
        
        # Hash the message first (same as in signing)
        message_hash = hashlib.sha256(message).digest()
        
        # Use the regular verification method with the hashed message
        return FalconSignature.verify_signature(message_hash, signature, public_key)
    
    @staticmethod
    def hex_to_bytes(hex_string: str) -> bytes:
        """
        Convert a hex string to bytes
        
        Args:
            hex_string (str): Hex-encoded string
            
        Returns:
            bytes: Decoded bytes
        """
        return bytes.fromhex(hex_string)
    
    @staticmethod
    def bytes_to_hex(byte_data: bytes) -> str:
        """
        Convert bytes to a hex string
        
        Args:
            byte_data (bytes): Bytes to encode
            
        Returns:
            str: Hex-encoded string
        """
        return byte_data.hex()
    
    @classmethod
    def create_signature_object(cls, message: Union[str, bytes], signature: bytes, 
                              public_key: bytes, use_prehash: bool = False) -> Dict[str, Any]:
        """
        Create a complete signature object with all relevant information
        
        Args:
            message (Union[str, bytes]): The message that was signed
            signature (bytes): The signature
            public_key (bytes): The public key used for verification
            use_prehash (bool): Whether prehashing was used
            
        Returns:
            Dict[str, Any]: Complete signature object
        """
        # Convert message to bytes if it's a string
        if isinstance(message, str):
            message_bytes = message.encode('utf-8')
        else:
            message_bytes = message
            
        # Verify public key size
        if len(public_key) != PUBLIC_KEY_SIZE:
            raise ValueError(f"Public key must be exactly {PUBLIC_KEY_SIZE} bytes, got {len(public_key)}")
        
        # Create signature object
        signature_object = {
            "algorithm": cls.ALGORITHM_NAME,
            "message_hash": hashlib.sha256(message_bytes).hexdigest(),
            "signature": cls.bytes_to_hex(signature),
            "public_key": cls.bytes_to_hex(public_key),
            "signature_size": len(signature),
            "use_prehash": use_prehash,
            "is_valid": cls.verify_signature_with_prehash(message_bytes, signature, public_key) 
                        if use_prehash else cls.verify_signature(message_bytes, signature, public_key)
        }
        
        return signature_object

# Top-level wrapper functions for easier use in transaction module

def generate_keys() -> Tuple[str, str]:
    """
    Generate a new keypair for signing
    
    Returns:
        Tuple[str, str]: (private_key, public_key) as base64 strings
    """
    # Generate keys using the FalconSignature class
    private_key_bytes, public_key_bytes = FalconSignature.generate_keypair()
    
    # Convert to base64 for string representation
    private_key = base64.b64encode(private_key_bytes).decode('utf-8')
    public_key = base64.b64encode(public_key_bytes).decode('utf-8')
    
    return private_key, public_key

def create_signature(message: Union[str, bytes], private_key: str) -> str:
    """
    Create a signature for a message
    
    Args:
        message: Message to sign (string or bytes)
        private_key: Private key as base64 string
        
    Returns:
        Signature as base64 string
    """
    # Decode private key from base64
    try:
        # Remove any whitespace and normalize padding
        private_key = private_key.strip()
        # Remove existing padding if any
        private_key = private_key.rstrip('=')
        # Add correct padding
        padding_needed = len(private_key) % 4
        if padding_needed:
            private_key += '=' * (4 - padding_needed)
            
        private_key_bytes = base64.b64decode(private_key)
        
        # Verify the private key is the correct size after decoding
        if len(private_key_bytes) != SECRET_KEY_SIZE:
            raise ValueError(f"Private key must be exactly {SECRET_KEY_SIZE} bytes, got {len(private_key_bytes)}")
        
        # Sign the message
        signature_bytes = FalconSignature.sign_message(message, private_key_bytes)
        
        # Return base64 encoded signature
        return base64.b64encode(signature_bytes).decode('utf-8')
        
    except Exception as e:
        # Log the error but don't expose key details
        logger.error(f"Error in create_signature: {str(e)}")
        raise

def verify_signature(message: Union[str, bytes], signature: str, public_key: str) -> bool:
    """
    Verify a message signature
    
    Args:
        message: Original message (string or bytes)
        signature: Signature as base64 or hex string
        public_key: Public key as base64 or hex string
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # First try to decode public key as hex (as used in wallet files)
        try:
            # Try with hex-encoded public key first (the format used in wallets)
            public_key_bytes = bytes.fromhex(public_key)
        except ValueError:
            # If hex decoding fails, try base64 with proper padding handling
            # Handle public key padding for base64 format
            public_key = public_key.strip()
            public_key = public_key.rstrip('=')
            padding_needed = len(public_key) % 4
            if padding_needed:
                public_key += '=' * (4 - padding_needed)
            public_key_bytes = base64.b64decode(public_key)
        
        # Similarly handle signature - first try hex, then base64
        try:
            # Try with hex-encoded signature
            signature_bytes = bytes.fromhex(signature)
        except ValueError:
            # If hex decoding fails, try base64 with proper padding handling
            signature = signature.strip()
            signature = signature.rstrip('=')
            padding_needed = len(signature) % 4
            if padding_needed:
                signature += '=' * (4 - padding_needed)
            signature_bytes = base64.b64decode(signature)
        
        # Verify the public key size
        if len(public_key_bytes) != PUBLIC_KEY_SIZE:
            raise ValueError(f"Public key must be exactly {PUBLIC_KEY_SIZE} bytes, got {len(public_key_bytes)}")
        
        # Verify the signature
        return FalconSignature.verify_signature(message, signature_bytes, public_key_bytes)
    except Exception as e:
        logger.error(f"Error verifying signature: {e}")
        return False