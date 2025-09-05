# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import os
import json
import time
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from pyqrllib.pyqrllib import  hstr2bin

from qbitcoin.core.config import UserConfig
from qbitcoin.core.misc import logger
from qbitcoin.core.Singleton import Singleton


class DonorWalletManager(object, metaclass=Singleton):
    """
    Secure donor wallet management for staking rewards
    Handles encrypted storage of donor wallet private keys
    """
    
    def __init__(self):
        user_config = UserConfig.getInstance()
        self.donor_wallet_dir = os.path.join(user_config.qrl_dir, 'donor_wallets')
        self.donor_wallet_file = os.path.join(self.donor_wallet_dir, 'donor_wallet.json')
        self.loaded_wallet = None
        self.decrypted_private_key = None
        
        # Ensure donor wallet directory exists
        os.makedirs(self.donor_wallet_dir, exist_ok=True)
        
    def _derive_key_from_password(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
        
    def _encrypt_data(self, data: str, password: str) -> dict:
        """Encrypt data with password"""
        salt = os.urandom(16)
        key = self._derive_key_from_password(password, salt)
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(data.encode())
        
        return {
            'encrypted_data': base64.b64encode(encrypted_data).decode(),
            'salt': base64.b64encode(salt).decode(),
            'type': 'encrypted_donor_wallet'
        }
        
    def _decrypt_data(self, encrypted_data: str, salt: str, password: str) -> str:
        """Decrypt data with password"""
        salt_bytes = base64.b64decode(salt.encode())
        key = self._derive_key_from_password(password, salt_bytes)
        fernet = Fernet(key)
        
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted_data = fernet.decrypt(encrypted_bytes)
        return decrypted_data.decode()
        
    def import_donor_wallet(self, wallet_file_path: str, password: str = None) -> bool:
        """
        Import an existing wallet file as donor wallet
        
        Args:
            wallet_file_path: Path to the wallet file (JSON format)
            password: Password if wallet is encrypted (None if not encrypted)
            
        Returns:
            bool: True if wallet was imported successfully
        """
        try:
            if not os.path.exists(wallet_file_path):
                logger.error("Wallet file not found: %s", wallet_file_path)
                return False
                
            # Read the wallet file
            with open(wallet_file_path, 'r') as f:
                if wallet_file_path.endswith('.json'):
                    # Unencrypted JSON wallet (like genesis_keys.json)
                    wallet_data = json.load(f)
                    
                    # Extract required fields
                    if 'address' not in wallet_data or 'private_key_hex' not in wallet_data:
                        logger.error("Invalid wallet format - missing required fields")
                        return False
                        
                    # Convert hex keys to bytes
                    private_key = bytes.fromhex(wallet_data['private_key_hex'])
                    public_key = bytes.fromhex(wallet_data.get('public_key_hex', ''))
                    
                    # Prepare standardized wallet data
                    standardized_data = {
                        'address': wallet_data['address'],
                        'private_key': private_key.hex(),
                        'public_key': public_key.hex(),
                        'imported_at': time.time(),
                        'algorithm': wallet_data.get('algorithm', 'falcon-512'),
                        'original_file': wallet_file_path
                    }
                    
                elif wallet_file_path.endswith('.enc'):
                    # Encrypted wallet file
                    if not password:
                        logger.error("Password required for encrypted wallet")
                        return False
                        
                    encrypted_data = f.read().encode() if isinstance(f.read(), str) else f.read()
                    decrypted_json = self._decrypt_data(encrypted_data, password)
                    standardized_data = json.loads(decrypted_json)
                    
                else:
                    logger.error("Unsupported wallet file format")
                    return False
            
            # Save as encrypted donor wallet
            donor_name = os.path.splitext(os.path.basename(wallet_file_path))[0]
            donor_password = password or "imported_wallet_default"
            
            encrypted_wallet_dict = self._encrypt_data(json.dumps(standardized_data), donor_password)
            
            # Save to donor wallet directory
            donor_wallet_path = os.path.join(self.donor_wallet_dir, f"{donor_name}_donor.json")
            with open(donor_wallet_path, 'w') as f:
                json.dump(encrypted_wallet_dict, f, indent=2)
                
            logger.info("Donor wallet imported successfully: %s", donor_wallet_path)
            
            # Store the password for this session
            self._current_password = donor_password
            
            return True
            
        except Exception as e:
            logger.error("Failed to import donor wallet: %s", str(e))
            return False
            
    def load_donor_wallet(self, password: str) -> Optional[dict]:
        """
        Load and decrypt donor wallet
        
        Args:
            password: Password for decryption
            
        Returns:
            dict: Wallet data if successful, None otherwise
        """
        try:
            # Look for any donor wallet files
            donor_wallet_files = []
            if os.path.exists(self.donor_wallet_file):
                donor_wallet_files.append(self.donor_wallet_file)
            
            # Also look for imported donor wallets
            if os.path.exists(self.donor_wallet_dir):
                for filename in os.listdir(self.donor_wallet_dir):
                    if filename.endswith('_donor.json'):
                        donor_wallet_files.append(os.path.join(self.donor_wallet_dir, filename))
            
            if not donor_wallet_files:
                logger.warning("No donor wallet files found")
                return None
            
            # Try to load the first available wallet
            for wallet_file in donor_wallet_files:
                try:
                    # Load encrypted data
                    with open(wallet_file, 'r') as f:
                        encrypted_wallet = json.load(f)
                        
                    # Verify it's encrypted wallet
                    if encrypted_wallet.get('type') != 'encrypted_donor_wallet':
                        logger.warning("Invalid wallet file format: %s", wallet_file)
                        continue
                        
                    # Decrypt wallet data
                    decrypted_data = self._decrypt_data(
                        encrypted_wallet['encrypted_data'],
                        encrypted_wallet['salt'],
                        password
                    )
                    
                    wallet_data = json.loads(decrypted_data)
                    
                    # Cache loaded wallet
                    self.loaded_wallet = wallet_data
                    self.decrypted_private_key = wallet_data['private_key']
                    
                    logger.info("Donor wallet loaded successfully: %s", wallet_data['address'])
                    return wallet_data
                    
                except Exception as e:
                    logger.warning("Failed to load wallet %s: %s", wallet_file, str(e))
                    continue
            
            logger.error("Could not load any donor wallet with provided password")
            return None
            
        except Exception as e:
            logger.error("Failed to load donor wallet: %s", str(e))
            return None
            
    def get_wallet_info(self) -> Optional[dict]:
        """Get current loaded wallet info (including public key but not private key)"""
        if not self.loaded_wallet:
            return None
            
        return {
            'address': self.loaded_wallet['address'],
            'public_key': self.loaded_wallet.get('public_key_hex') or self.loaded_wallet.get('public_key', ''),
            'algorithm': self.loaded_wallet.get('algorithm', 'falcon-512'),
            'imported_at': self.loaded_wallet.get('imported_at'),
            'created_at': self.loaded_wallet.get('created_at')
        }
        
    def get_address_bytes(self) -> Optional[bytes]:
        """Get donor wallet address as bytes"""
        if not self.loaded_wallet:
            return None
            
        try:
            address_hex = self.loaded_wallet['address'][1:]  # Remove Q prefix
            address_bytes = hstr2bin(address_hex)
            
            # Ensure it's bytes, not tuple
            if isinstance(address_bytes, tuple):
                return bytes(address_bytes)
            elif isinstance(address_bytes, bytes):
                return address_bytes
            else:
                return bytes(address_bytes)
        except Exception as e:
            logger.error("Failed to convert address to bytes: %s", str(e))
            return None
            
    def get_private_key_bytes(self) -> Optional[bytes]:
        """Get donor wallet private key as bytes"""
        if not self.decrypted_private_key:
            return None
            
        try:
            private_key_bytes = hstr2bin(self.decrypted_private_key)
            
            # Ensure it's bytes, not tuple
            if isinstance(private_key_bytes, tuple):
                return bytes(private_key_bytes)
            elif isinstance(private_key_bytes, bytes):
                return private_key_bytes
            else:
                return bytes(private_key_bytes)
        except Exception as e:
            logger.error("Failed to convert private key to bytes (security: details omitted)")
            return None
            
    def is_wallet_loaded(self) -> bool:
        """Check if a donor wallet is currently loaded"""
        return self.loaded_wallet is not None
        
    def unload_wallet(self):
        """Unload current wallet and clear sensitive data"""
        self.loaded_wallet = None
        self.decrypted_private_key = None
        logger.info("Donor wallet unloaded")
        
    def wallet_exists(self) -> bool:
        """Check if donor wallet file exists"""
        return os.path.exists(self.donor_wallet_file)
        
    def get_wallet_path(self) -> str:
        """Get the path to the donor wallet file"""
        return self.donor_wallet_file
        
    def verify_password(self, password: str) -> bool:
        """Verify if password is correct for the stored wallet"""
        try:
            if not self.wallet_exists():
                return False
                
            # Try to load wallet with password
            wallet_data = self.load_donor_wallet(password)
            return wallet_data is not None
            
        except Exception:
            return False
            
    def import_encrypted_wallet_as_unencrypted(self, wallet_path: str, password: str) -> bool:
        """Import encrypted wallet, decrypt it, and save as unencrypted for automatic loading"""
        try:
            # Load and decrypt the wallet
            with open(wallet_path, 'r') as f:
                encrypted_data = json.load(f)
                
            if not encrypted_data.get('encrypted'):
                logger.error('Wallet is not encrypted')
                return False
                
            # Decrypt the wallet data
            salt = base64.b64decode(encrypted_data['salt'])
            key = self._derive_key_from_password(password, salt)
            fernet = Fernet(key)
            
            try:
                decrypted_bytes = fernet.decrypt(encrypted_data['encrypted_data'].encode())
                wallet_data = json.loads(decrypted_bytes.decode())
            except Exception as e:
                logger.error('Failed to decrypt wallet (wrong password?): %s', str(e))
                return False
                
            # Save as unencrypted for automatic loading
            wallet_filename = os.path.basename(wallet_path)
            name_part = os.path.splitext(wallet_filename)[0]
            donor_wallet_path = os.path.join(self.donor_wallet_dir, f"{name_part}_donor.json")
            
            # Prepare unencrypted wallet data
            unencrypted_wallet = {
                'address': wallet_data['address'],
                'private_key_hex': wallet_data.get('private_key_hex') or wallet_data.get('pk'),
                'algorithm': wallet_data.get('algorithm', 'falcon-512'),
                'imported_from': wallet_path,
                'imported_at': time.time(),
                'encrypted': False  # Mark as unencrypted
            }
            
            # Save unencrypted
            with open(donor_wallet_path, 'w') as f:
                json.dump(unencrypted_wallet, f, indent=2)
                
            logger.info('Encrypted wallet decrypted and saved to: %s', donor_wallet_path)
            return True
            
        except Exception as e:
            logger.error('Error importing encrypted wallet: %s', str(e))
            return False
            
    def import_unencrypted_wallet_direct(self, wallet_path: str) -> bool:
        """Import unencrypted wallet directly without encryption for automatic loading"""
        try:
            # Load wallet data
            with open(wallet_path, 'r') as f:
                wallet_data = json.load(f)
                
            # Validate structure - support multiple wallet formats
            has_address = 'address' in wallet_data
            has_private_key = any(key in wallet_data for key in ['pk', 'private_key_hex', 'private_key'])
            
            if not (has_address and has_private_key):
                logger.error('Invalid wallet structure: missing address or private key')
                logger.error('Expected: address + (pk/private_key_hex/private_key)')
                logger.error('Found keys: %s', list(wallet_data.keys()))
                return False
                
            # Save as unencrypted for automatic loading
            wallet_filename = os.path.basename(wallet_path)
            name_part = os.path.splitext(wallet_filename)[0]
            donor_wallet_path = os.path.join(self.donor_wallet_dir, f"{name_part}_donor.json")
            
            # Extract private key from various possible field names
            private_key_hex = None
            if 'private_key_hex' in wallet_data:
                private_key_hex = wallet_data['private_key_hex']
            elif 'pk' in wallet_data:
                private_key_hex = wallet_data['pk']
            elif 'private_key' in wallet_data:
                private_key_hex = wallet_data['private_key']
            
            # Prepare unencrypted wallet data
            unencrypted_wallet = {
                'address': wallet_data['address'],
                'private_key_hex': private_key_hex,
                'algorithm': wallet_data.get('algorithm', 'falcon-512'),
                'imported_from': wallet_path,
                'imported_at': time.time(),
                'encrypted': False  # Mark as unencrypted
            }
            
            # Copy public key if available (important for transaction signing)
            if 'public_key_hex' in wallet_data:
                unencrypted_wallet['public_key_hex'] = wallet_data['public_key_hex']
            elif 'public_key' in wallet_data:
                unencrypted_wallet['public_key_hex'] = wallet_data['public_key']
            
            # Copy additional fields if present
            optional_fields = ['genesis_balance', 'genesis_balance_qrl', 'balance']
            for field in optional_fields:
                if field in wallet_data:
                    unencrypted_wallet[field] = wallet_data[field]
            
            # Save unencrypted
            with open(donor_wallet_path, 'w') as f:
                json.dump(unencrypted_wallet, f, indent=2)
                
            logger.info('Unencrypted wallet saved to: %s', donor_wallet_path)
            return True
            
        except Exception as e:
            logger.error('Error importing unencrypted wallet: %s', str(e))
            return False
            
    def load_unencrypted_donor_wallet(self, wallet_data: dict) -> bool:
        """Load donor wallet from unencrypted data"""
        try:
            # Validate wallet data
            if not isinstance(wallet_data, dict):
                logger.error('Invalid wallet data format')
                return False
                
            required_fields = ['address', 'private_key_hex']
            if not all(field in wallet_data for field in required_fields):
                logger.error('Missing required fields in wallet data')
                return False
                
            # Store wallet data
            self.loaded_wallet = {
                'address': wallet_data['address'],
                'algorithm': wallet_data.get('algorithm', 'falcon-512'),
                'public_key_hex': wallet_data.get('public_key_hex', ''),
                'imported_at': wallet_data.get('imported_at'),
                'created_at': wallet_data.get('created_at')
            }
            
            # Store decrypted private key
            self.decrypted_private_key = wallet_data['private_key_hex']
            
            logger.info('Unencrypted donor wallet loaded successfully')
            return True
            
        except Exception as e:
            logger.error('Error loading unencrypted donor wallet: %s', str(e))
            return False


# Import time for timestamp
import time
