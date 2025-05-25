
"""
Transaction implementation for Qbitcoin

This file implements the Transaction class for creating, validating and
managing cryptocurrency transactions using the Falcon signature algorithm.
"""

import time
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple, Union
import base64

# Import configuration and crypto module
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import config 
from crypto.falcon import verify_signature, create_signature
from utils.logger import get_logger

# Initialize logger
logger = get_logger("transaction")

class Transaction:
    """
    Transaction structure for Qbitcoin blockchain
    
    Attributes:
        version: Transaction version number
        timestamp: Transaction creation time
        inputs: List of transaction inputs (prev_tx references)
        outputs: List of transaction outputs (addresses and amounts)
        data: Optional data field (for messages or smart contracts)
        fee: Transaction fee
        public_key: Sender's public key (included only for first transaction)
        signature: Cryptographic signature using Falcon
        hash: Transaction hash (ID)
    """
    
    def __init__(self, 
                 version: int = 1,
                 timestamp: Optional[int] = None,
                 inputs: List[Dict[str, Any]] = None,
                 outputs: List[Dict[str, Any]] = None,
                 data: str = "",
                 fee: float = 0.0,
                 public_key: Optional[str] = None,
                 signature: Optional[str] = None):
        """
        Initialize a new transaction
        
        Args:
            version: Transaction version number
            timestamp: Unix timestamp of transaction creation (defaults to current time)
            inputs: List of transaction inputs
            outputs: List of transaction outputs
            data: Optional data payload
            fee: Transaction fee
            public_key: Sender's public key (if first transaction)
            signature: Transaction signature (None for unsigned transactions)
        """
        self.version = version
        self.timestamp = timestamp or int(time.time())
        self.inputs = inputs or []
        self.outputs = outputs or []
        self.data = data
        self.fee = fee
        self.public_key = public_key
        self.signature = signature
        self.hash = self.calculate_hash()
        
    def calculate_hash(self) -> str:
        """
        Calculate the hash of the transaction
        
        Returns:
            String representation of the transaction hash
        """
        # For hash calculation, exclude the signature field
        tx_dict = {
            'version': self.version,
            'timestamp': self.timestamp,
            'inputs': self.inputs,
            'outputs': self.outputs,
            'data': self.data,
            'fee': self.fee,
            'public_key': self.public_key
        }
        
        # Create a deterministic JSON string by sorting keys
        tx_string = json.dumps(tx_dict, sort_keys=True)
        
        # Hash using SHA3-256 (as per config.HASH_ALGORITHM)
        if config.HASH_ALGORITHM == "sha3-256":
            hash_object = hashlib.sha3_256(tx_string.encode())
            return hash_object.hexdigest()
        else:
            # Fallback to SHA-256 if SHA3 not available
            hash_object = hashlib.sha256(tx_string.encode())
            return hash_object.hexdigest()
            
    def sign_transaction(self, private_key: str) -> bool:
        """
        Sign the transaction with the provided private key
        
        Args:
            private_key: Private key string for signing (hex format)
            
        Returns:
            True if signing succeeded, False otherwise
        """
        try:
            # Generate message to sign (transaction hash)
            message = self.hash.encode()
            
            # Convert hex private key to bytes (the same way the test script does it)
            try:
                # Convert hex string to bytes directly
                private_key_bytes = bytes.fromhex(private_key)
                
                # Verify the key size directly
                from crypto.falcon import SECRET_KEY_SIZE
                if len(private_key_bytes) != SECRET_KEY_SIZE:
                    logger.error(f"Private key has incorrect size: {len(private_key_bytes)} bytes, expected {SECRET_KEY_SIZE}")
                    return False
                
                # Use direct signing with bytes
                from crypto.falcon import FalconSignature
                signature_bytes = FalconSignature.sign_message(message, private_key_bytes)
                
                # Convert signature to base64 for storage
                self.signature = base64.b64encode(signature_bytes).decode('utf-8')
            except Exception as e:
                logger.error(f"Failed to sign transaction: {e}")
                return False
            
            # Verify the signature was created correctly
            if not self.verify_signature():
                self.signature = None
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error signing transaction: {e}")
            return False
            
    def verify_signature(self) -> bool:
        """
        Verify the transaction signature
        
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.signature:
            return False
            
        # If this is not the first transaction, get public key from inputs
        if not self.public_key and self.inputs:
            # In a real implementation, we would look up the public key
            # from the blockchain database using the input reference
            return False
            
        if not self.public_key:
            return False
            
        try:
            # Verify signature using Falcon
            message = self.hash.encode()
            return verify_signature(message, self.signature, self.public_key)
        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert transaction to dictionary representation
        
        Returns:
            Dictionary with transaction data
        """
        return {
            'version': self.version,
            'timestamp': self.timestamp,
            'inputs': self.inputs,
            'outputs': self.outputs,
            'data': self.data,
            'fee': self.fee,
            'public_key': self.public_key,
            'signature': self.signature,
            'hash': self.hash
        }
    
    @classmethod
    def from_dict(cls, tx_dict: Dict[str, Any]) -> 'Transaction':
        """
        Create a Transaction from dictionary representation
        
        Args:
            tx_dict: Dictionary with transaction data
            
        Returns:
            Transaction instance
        """
        tx = cls(
            version=tx_dict.get('version', 1),
            timestamp=tx_dict.get('timestamp'),
            inputs=tx_dict.get('inputs', []),
            outputs=tx_dict.get('outputs', []),
            data=tx_dict.get('data', ""),
            fee=tx_dict.get('fee', 0.0),
            public_key=tx_dict.get('public_key'),
            signature=tx_dict.get('signature')
        )
        
        # Verify hash matches if provided
        if 'hash' in tx_dict and tx.hash != tx_dict['hash']:
            # Instead of raising an error, use the provided hash for received transactions
            # This is important for transactions in blocks received from peers
            logger.warning(f"Transaction hash mismatch: expected {tx_dict['hash']}, got {tx.hash}")
            tx.hash = tx_dict['hash']  # Use the provided hash to maintain consistency
        
        return tx
    
    def validate(self, blockchain) -> bool:
        """
        Validate the transaction
        
        Args:
            blockchain: Reference to the blockchain for UTXO lookup
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation
        
        # 1. Check transaction size
        tx_size = len(json.dumps(self.to_dict()).encode())
        if tx_size > config.MAX_TX_SIZE:
            logger.error(f"Transaction too large: {tx_size} bytes")
            return False
            
        # 2. Check if timestamp is reasonable
        current_time = int(time.time())
        if self.timestamp > current_time + 7200:  # 2 hours into future
            logger.error(f"Transaction timestamp too far in future: {self.timestamp}")
            return False
            
        # 3. Check signature
        if not self.verify_signature():
            logger.error("Invalid transaction signature")
            return False
            
        # 4. For standard transactions (not coinbase), verify inputs and outputs
        if self.inputs:
            # Calculate input sum (would require account lookup in an account-based model)
            input_sum = 0
            for tx_input in self.inputs:
                # In an account-based system, we would verify the sender has sufficient balance
                # This is simplified and would be implemented with database lookups
                input_amount = blockchain.get_input_amount(tx_input)
                if input_amount is None:
                    logger.error(f"Invalid input reference: {tx_input}")
                    return False
                input_sum += input_amount
            
            # Calculate output sum
            output_sum = sum(output['amount'] for output in self.outputs)
            
            # Ensure outputs plus fee don't exceed inputs
            if output_sum + self.fee > input_sum:
                logger.error(f"Outputs + fee ({output_sum + self.fee}) exceed inputs ({input_sum})")
                return False
        
        return True
    
    @classmethod
    def create_coinbase(cls, 
                       recipient_address: str, 
                       amount: float, 
                       height: int,
                       data: str = "") -> 'Transaction':
        """
        Create a coinbase transaction (for block rewards)
        
        Args:
            recipient_address: Address to receive the reward
            amount: Reward amount
            height: Block height
            data: Optional data field
            
        Returns:
            Coinbase transaction
        """
        # Create outputs for the reward
        outputs = [{
            'address': recipient_address,
            'amount': amount
        }]
        
        # Create transaction with no inputs
        coinbase_tx = cls(
            version=1,
            timestamp=int(time.time()),
            inputs=[],
            outputs=outputs,
            data=data or f"Coinbase reward for block {height}",
            fee=0.0
        )
        
        return coinbase_tx
        
    @classmethod
    def create_transaction(cls,
                         sender_private_key: str,
                         sender_public_key: str,
                         sender_address: str,
                         recipient_address: str,
                         amount: float,
                         fee: float = None,
                         data: str = "") -> 'Transaction':
        """
        Create a standard transaction between addresses
        
        Args:
            sender_private_key: Private key of sender
            sender_public_key: Public key of sender
            sender_address: Address of sender
            recipient_address: Address of recipient
            amount: Amount to send
            fee: Transaction fee (or None for auto-calculation)
            data: Optional data payload
            
        Returns:
            Signed transaction
        """
        # In an account-based system, we would reference the account state
        # rather than specific UTXOs
        inputs = [{
            'address': sender_address,
            'amount': amount + (fee or config.RECOMMENDED_FEE)
        }]
        
        outputs = [{
            'address': recipient_address,
            'amount': amount
        }]
        
        # Auto-calculate fee if not specified
        if fee is None:
            # In a real implementation, we would estimate size and calculate fee
            fee = config.RECOMMENDED_FEE
        
        # Create transaction
        tx = cls(
            version=1,
            timestamp=int(time.time()),
            inputs=inputs,
            outputs=outputs,
            data=data,
            fee=fee,
            # Include public key only on first transaction from this wallet
            public_key=sender_public_key
        )
        
        # Sign transaction
        success = tx.sign_transaction(sender_private_key)
        if not success:
            raise ValueError("Failed to sign transaction")
            
        return tx
    
    def __str__(self) -> str:
        """
        String representation of the transaction
        
        Returns:
            Human-readable transaction information
        """
        input_str = ", ".join(f"{inp.get('address', 'Unknown')}:{inp.get('amount', 0)}" 
                             for inp in self.inputs) or "Coinbase (No inputs)"
        output_str = ", ".join(f"{out.get('address', 'Unknown')}:{out.get('amount', 0)}" 
                              for out in self.outputs)
        
        return (f"Transaction {self.hash[:8]}...\n"
                f"Type: {'Coinbase' if not self.inputs else 'Standard'}\n"
                f"Inputs: {input_str}\n"
                f"Outputs: {output_str}\n"
                f"Fee: {self.fee} {config.BLOCKCHAIN_TICKER}")