"""
Wallet creator module for Qbitcoin using Falcon 512 post-quantum signature algorithm.
This module provides functionality for generating wallets with key pairs and addresses.
"""


import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import os
import hashlib
import json
import time
import base64
from pathlib import Path
from typing import Dict, Tuple, Any, Optional, Union



# Import the Falcon 512 module from pqcrypto
from pqcrypto.sign.falcon_512 import (
    generate_keypair,
    sign,
    verify,
    PUBLIC_KEY_SIZE,
    SECRET_KEY_SIZE,
    SIGNATURE_SIZE
)


class WalletCreator:
    """
    Wallet creation and management class using Falcon 512 post-quantum signatures.
    Provides methods for generating key pairs, creating addresses, and managing wallets.
    """
    
    
    @staticmethod
    def generate_seed() -> bytes:
        """Generate a random seed for key generation"""
        return os.urandom(32)  # 256-bit seed
    
    @staticmethod
    def create_keypair() -> Tuple[bytes, bytes]:
        """
        Generate a new Falcon 512 key pair for a wallet
        
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
    def generate_address(public_key: bytes) -> str:
        """
        Generate a wallet address from a public key using a hash function
        
        Args:
            public_key (bytes): The public key to generate an address from
            
        Returns:
            str: Human-readable Q-prefixed address for qbitcoin blockchain
        """
        # Perform SHA-256 hash
        sha256_hash = hashlib.sha256(public_key).digest()
        
        # Perform RIPEMD-160 hash on the SHA-256 hash
        ripemd160_hash = hashlib.new('ripemd160')
        ripemd160_hash.update(sha256_hash)
        hash160 = ripemd160_hash.digest()
        
        # Create binary address with proper format:
        # [0] - Address type (0x01 for standard Qbitcoin address)
        # [1:21] - RIPEMD160 hash of the public key (20 bytes)
        address_bytes = b'\x01' + hash160
        
        # For blockchain internal use - create uniform binary format
        # Add a 4-byte checksum (double SHA-256 of the first 21 bytes)
        checksum = hashlib.sha256(hashlib.sha256(address_bytes).digest()).digest()[:4]
        binary_address = address_bytes + checksum
        
        # Create a human-readable address with Q prefix
        q_address = "Q" + binary_address.hex()
        
        # Return the Q-prefixed address for qbitcoin blockchain
        return q_address
    
    @classmethod
    def create_wallet(cls, wallet_name: str = None) -> Dict[str, Any]:
        """
        Create a new wallet with a Falcon 512 key pair and address
        
        Args:
            wallet_name (str, optional): Name of the wallet. If None, uses a timestamp.
            
        Returns:
            Dict[str, Any]: Wallet information including keys and address
        """
        # Generate key pair
        # secret_key should be 1281 bytes, public_key should be 897 bytes
        secret_key, public_key = cls.create_keypair()
        
        # Validate key sizes
        if len(secret_key) != SECRET_KEY_SIZE:
            raise ValueError(f"Secret key size mismatch: {len(secret_key)} != {SECRET_KEY_SIZE}")
        if len(public_key) != PUBLIC_KEY_SIZE:
            raise ValueError(f"Public key size mismatch: {len(public_key)} != {PUBLIC_KEY_SIZE}")
        
        # Generate address from public key
        address = cls.generate_address(public_key)
        
        # Create wallet name if not provided
        if wallet_name is None:
            wallet_name = f"wallet_{int(time.time())}"
        
        # Create wallet data structure
        wallet_data = {
            "name": wallet_name,
            "creation_time": time.time(),
            "address": address,
            "public_key": public_key.hex(),
            "public_key_size": len(public_key),
            "private_key": secret_key.hex(),
            "private_key_size": len(secret_key),
            "algorithm": "falcon-512"
        }
        
        return wallet_data
    
    @classmethod
    def save_wallet(cls, wallet_data: Dict[str, Any], password: str, 
                    directory: Optional[Path] = None) -> Path:
        """
        Encrypt and save a wallet to disk
        
        Args:
            wallet_data (Dict[str, Any]): Wallet data to save
            password (str): Password to encrypt the wallet
            directory (Path, optional): Directory to save wallet. Defaults to DEFAULT_WALLET_DIR.
            
        Returns:
            Path: Path to the saved wallet file
        """
        # Create wallet directory if it doesn't exist
        if directory is None:
            directory = cls.DEFAULT_WALLET_DIR
        
        directory.mkdir(parents=True, exist_ok=True)
        
        # Encrypt sensitive wallet data
        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        
        # TODO: Implement proper encryption with the derived key
        # For now, we'll just store the salt with the wallet data
        encrypted_wallet = wallet_data.copy()
        encrypted_wallet["salt"] = salt.hex()
        
        # Create wallet file
        wallet_file = directory / f"{wallet_data['name']}.wallet"
        with open(wallet_file, 'w') as f:
            json.dump(encrypted_wallet, f, indent=2)
        
        return wallet_file
    
    @classmethod
    def load_wallet(cls, wallet_path: Path, password: str) -> Dict[str, Any]:
        """
        Load and decrypt a wallet from disk
        
        Args:
            wallet_path (Path): Path to the wallet file
            password (str): Password to decrypt the wallet
            
        Returns:
            Dict[str, Any]: Loaded wallet data
        """
        # Load encrypted wallet data
        with open(wallet_path, 'r') as f:
            encrypted_wallet = json.load(f)
        
        # TODO: Implement proper decryption using the password and salt
        # For now, just return the wallet without decryption
        
        return encrypted_wallet
    
    @staticmethod
    def sign_message(message: bytes, secret_key: bytes) -> bytes:
        """
        Sign a message using the wallet's private key
        
        Args:
            message (bytes): Message to sign
            secret_key (bytes): Private key for signing
            
        Returns:
            bytes: Signature
        """
        # Ensure the secret key is the correct length
        if len(secret_key) != SECRET_KEY_SIZE:
            raise ValueError(f"Private key must be exactly {SECRET_KEY_SIZE} bytes, got {len(secret_key)}")
            
        return sign(message, secret_key)
    
    @staticmethod
    def verify_signature(message: bytes, signature: bytes, 
                         public_key: bytes) -> bool:
        """
        Verify a signature using the wallet's public key
        
        Args:
            message (bytes): Original message
            signature (bytes): Signature to verify
            public_key (bytes): Public key for verification
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        # Ensure the public key is the correct length
        if len(public_key) != PUBLIC_KEY_SIZE:
            raise ValueError(f"Public key must be exactly {PUBLIC_KEY_SIZE} bytes, got {len(public_key)}")
            
        try:
            verify(message, signature, public_key)
            return True
        except Exception:
            return False


# Helper function to create a new wallet
def create_new_wallet(wallet_name: str = None, save: bool = False, 
                     password: str = None) -> Dict[str, Any]:
    """
    Create a new wallet with optional saving to disk
    
    Args:
        wallet_name (str, optional): Name for the wallet
        save (bool, optional): Whether to save the wallet to disk
        password (str, optional): Password for wallet encryption if saving
        
    Returns:
        Dict[str, Any]: Wallet information
    """
    wallet = WalletCreator.create_wallet(wallet_name)
    
    if save and password:
        wallet_file = WalletCreator.save_wallet(wallet, password)
        print(f"Wallet saved to: {wallet_file}")
    
    return wallet


# Helper function to convert keys between formats
def hex_to_keys(public_key_hex: str, private_key_hex: str = None) -> Tuple[bytes, Optional[bytes]]:
    """
    Convert hex-encoded keys back to bytes format
    
    Args:
        public_key_hex (str): Hex-encoded public key
        private_key_hex (str, optional): Hex-encoded private key
        
    Returns:
        Tuple[bytes, Optional[bytes]]: Tuple of key byte objects (private key may be None)
    """
    public_key = bytes.fromhex(public_key_hex)
    
    # Verify the public key length matches the expected value
    if len(public_key) != PUBLIC_KEY_SIZE:
        raise ValueError(f"Public key must be exactly {PUBLIC_KEY_SIZE} bytes, got {len(public_key)}")
    
    private_key = None
    if private_key_hex:
        private_key = bytes.fromhex(private_key_hex)
        
        # Verify the private key length matches the expected value
        if len(private_key) != SECRET_KEY_SIZE:
            raise ValueError(f"Private key must be exactly {SECRET_KEY_SIZE} bytes, got {len(private_key)}")
    
    return public_key, private_key


# Helper function to get address from public key (for use in test.py)
def address_from_public_key(public_key: str) -> str:
    """
    Generate address from public key (for convenience in tests)
    
    Args:
        public_key: Base64-encoded public key or bytes
        
    Returns:
        Q-prefixed address for qbitcoin blockchain
    """
    try:
        if isinstance(public_key, str):
            # If it's a base64 string
            public_key_bytes = base64.b64decode(public_key)
        else:
            # If it's already bytes
            public_key_bytes = public_key
            
        # Generate address using WalletCreator method
        return WalletCreator.generate_address(public_key_bytes)
    except Exception as e:
        print(f"Error generating address from public key: {e}")
        return "ERROR_ADDRESS"


# Additional helper methods for address format conversion

def q_address_to_base64(q_address: str) -> str:
    """
    Convert a human-readable 'Q' prefixed address to base64 format required by QRL core
    
    Args:
        q_address: Q-prefixed address string
    
    Returns:
        Base64 encoded address for use with QRL blockchain core
    """
    try:
        # Q addresses should start with "Q" prefix
        if not q_address.startswith("Q"):
            raise ValueError(f"Invalid Q address format, must start with 'Q': {q_address}")
            
        # Strip the Q prefix and convert hex to bytes
        address_hex = q_address[1:]
        binary_address = bytes.fromhex(address_hex)
        
        # Return base64 encoded version without padding
        b64_address = base64.b64encode(binary_address).decode('utf-8')
        # Remove padding characters if any
        return b64_address.rstrip('=')
    except Exception as e:
        print(f"Error converting Q address to base64: {e}")
        return None

