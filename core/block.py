"""
Block implementation for Qbitcoin

This file implements the Block class which forms the basic unit of the blockchain.
It includes block header information and transaction data.
"""

import time
import hashlib
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import struct
import os
import sys
import yaml

# Import configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from utils.logger import get_logger

# Avoid circular imports by doing the import inside methods that need it
# from core.transaction import Transaction

# Initialize logger
logger = get_logger("block")

class Block:
    """
    Block structure for Qbitcoin blockchain
    
    Attributes:
        version: Block version number
        prev_hash: Hash of the previous block
        merkle_root: Merkle root hash of transactions
        timestamp: Block creation time
        difficulty: Mining difficulty target
        nonce: Value modified during mining
        height: Block height in blockchain
        transactions: List of transactions in the block
        hash: Hash of the block header (computed)
    """
    
    def __init__(self, version: int = 1, 
                prev_hash: Optional[str] = None, 
                merkle_root: str = "", 
                timestamp: int = None, 
                height: int = 0,
                nonce: int = 0,
                difficulty: float = config.INITIAL_DIFFICULTY,
                transactions: List[Dict[str, Any]] = None,
                extra_data: Dict[str, Any] = None):
        """
        Initialize a new block
        
        Args:
            version: Block version number
            prev_hash: Hash of the previous block (None for genesis block)
            merkle_root: Merkle root hash of transactions (calculated if not provided)
            timestamp: Block creation time (defaults to current time)
            height: Block height in blockchain
            nonce: Starting nonce value for mining
            difficulty: Mining difficulty target
            transactions: List of transaction objects or dicts
            extra_data: Optional extra data to include in the block
        """
        self.version = version
        self.prev_hash = prev_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp or int(time.time())
        self.height = height
        self.nonce = nonce
        self.difficulty = difficulty
        self.transactions = transactions or []
        self.extra_data = extra_data or {}
        
        # Calculate merkle root if not provided and transactions exist
        if not merkle_root and self.transactions:
            self.calculate_merkle_root()
            
        # Calculate block hash
        self.hash = self.calculate_hash()
        
    def calculate_hash(self) -> str:
        """
        Calculate the hash of the block header
        
        Returns:
            String representation of the block hash
        """
        # Combine block header fields
        header = {
            'version': self.version,
            'prev_hash': self.prev_hash,
            'merkle_root': self.merkle_root,
            'timestamp': self.timestamp,
            'height': self.height,
            'difficulty': self.difficulty,
            'nonce': self.nonce
        }
        
        # Create deterministic string representation
        header_str = json.dumps(header, sort_keys=True)
        
        # Hash using SHA3-256
        if config.HASH_ALGORITHM == "sha3-256":
            hash_object = hashlib.sha3_256(header_str.encode())
        else:
            # Fallback to SHA-256
            hash_object = hashlib.sha256(header_str.encode())
            
        return hash_object.hexdigest()
    
    def calculate_merkle_root(self) -> str:
        """
        Calculate the Merkle root of the transactions
        
        Returns:
            Merkle root hash string
        """
        if not self.transactions:
            self.merkle_root = "0" * 64  # Empty merkle root
            return self.merkle_root
            
        # Get transaction hashes
        tx_hashes = []
        for tx in self.transactions:
            # Handle both Transaction objects and dictionaries
            if isinstance(tx, dict):
                if 'hash' in tx:
                    tx_hash = tx['hash']
                else:
                    # If no hash, calculate from the transaction data
                    tx_str = json.dumps(tx, sort_keys=True)
                    tx_hash = hashlib.sha3_256(tx_str.encode()).hexdigest()
            else:
                tx_hash = tx.hash
                
            tx_hashes.append(tx_hash)
            
        # Build merkle tree
        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 == 1:
                tx_hashes.append(tx_hashes[-1])  # Duplicate last hash if odd
                
            new_tx_hashes = []
            for i in range(0, len(tx_hashes), 2):
                concat_hash = tx_hashes[i] + tx_hashes[i+1]
                new_hash = hashlib.sha3_256(concat_hash.encode()).hexdigest()
                new_tx_hashes.append(new_hash)
                
            tx_hashes = new_tx_hashes
            
        self.merkle_root = tx_hashes[0]
        return self.merkle_root
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert block to dictionary
        
        Returns:
            Dictionary representation of the block
        """
        # Convert transactions to dictionaries if they are objects
        tx_list = []
        for tx in self.transactions:
            if hasattr(tx, 'to_dict'):
                # If transaction is an object with to_dict method, use it
                tx_list.append(tx.to_dict())
            else:
                # If it's already a dictionary, use it as is
                tx_list.append(tx)
        
        return {
            'version': self.version,
            'prev_hash': self.prev_hash,
            'merkle_root': self.merkle_root,
            'timestamp': self.timestamp,
            'height': self.height,
            'difficulty': self.difficulty,
            'nonce': self.nonce,
            'transactions': tx_list,
            'extra_data': self.extra_data,
            'hash': self.hash
        }
    
    @classmethod
    def from_dict(cls, block_dict: Dict[str, Any]) -> 'Block':
        """
        Create a Block from dictionary
        
        Args:
            block_dict: Dictionary with block data
            
        Returns:
            Block instance
        """
        # Create the block with all parameters from dict
        block = cls(
            version=block_dict.get('version', 1),
            prev_hash=block_dict.get('prev_hash'),
            merkle_root=block_dict.get('merkle_root', ""),
            timestamp=block_dict.get('timestamp'),
            height=block_dict.get('height', 0),
            nonce=block_dict.get('nonce', 0),
            difficulty=block_dict.get('difficulty', config.INITIAL_DIFFICULTY),
            transactions=block_dict.get('transactions', []),
            extra_data=block_dict.get('extra_data', {})
        )
        
        # Set hash from dict if provided (important for mined blocks)
        if 'hash' in block_dict:
            block.hash = block_dict['hash']
        
        return block
    
    def validate(self) -> bool:
        """
        Validate the block structure with strict requirements
        
        Returns:
            True if valid, False otherwise
        """
        # Check block size
        block_size = len(json.dumps(self.to_dict()).encode())
        if block_size > config.MAX_BLOCK_SIZE:
            logger.error(f"Block too large: {block_size} bytes")
            return False
        
        # Check for valid timestamp (within reasonable range)
        current_time = int(time.time())
        if self.timestamp > current_time + 7200:  # 2 hours into future
            logger.error(f"Block timestamp too far in future: {self.timestamp}, current: {current_time}")
            return False
        
        # Check for reasonable nonce value
        if self.nonce < 0 or self.nonce >= 2**32:
            logger.error(f"Invalid nonce value: {self.nonce}")
            return False
            
        # Verify difficulty is at least the minimum difficulty
        if self.difficulty < config.MINIMUM_DIFFICULTY:
            logger.error(f"Block difficulty {self.difficulty} below minimum {config.MINIMUM_DIFFICULTY}")
            return False
            
        # Verify merkle root is correct
        calculated_root = self.calculate_merkle_root()
        if (calculated_root != self.merkle_root):
            logger.error(f"Invalid merkle root: expected {calculated_root}, got {self.merkle_root}")
            return False
            
        # Import the PoW implementation
        from core.consensus.pow import ProofOfWork
        
        # Verify proof of work using SHA3-256
        header = {
            'version': self.version,
            'prev_hash': self.prev_hash or "0" * 64,
            'merkle_root': self.merkle_root,
            'timestamp': self.timestamp,
            'height': self.height,
            'difficulty': self.difficulty,
            'nonce': self.nonce
        }
        
        # Calculate target from difficulty
        target = ProofOfWork.get_target_from_difficulty(self.difficulty)
        
        # Compute block hash and check against target
        computed_hash = ProofOfWork.compute_block_hash(header)
        if not ProofOfWork.hash_meets_target(computed_hash, target):
            logger.error(f"Invalid proof of work for block {self.hash}")
            return False
        
        # Verify the stored hash matches the computed hash
        if computed_hash != self.hash:
            logger.error(f"Block hash mismatch: stored {self.hash}, computed {computed_hash}")
            return False
        
        # Check if block has transactions
        if not self.transactions:
            logger.error(f"Block has no transactions")
            return False
        
        # First transaction must be coinbase
        if len(self.transactions) > 0:
            coinbase = self.transactions[0]
            # Check if it's a coinbase transaction (no inputs or empty inputs)
            coinbase_has_inputs = False
            if isinstance(coinbase, dict):
                coinbase_has_inputs = coinbase.get('inputs') and len(coinbase.get('inputs', [])) > 0
            else:
                coinbase_has_inputs = hasattr(coinbase, 'inputs') and coinbase.inputs and len(coinbase.inputs) > 0
                
            if coinbase_has_inputs:
                logger.error(f"First transaction is not a valid coinbase transaction")
                return False
            
        return True
        
    def _get_pow_input(self) -> bytes:
        """
        Get the binary input for proof of work
        
        Returns:
            Binary data for PoW calculation
        """
        # Prepare header fields in a binary format for mining
        # Format: version (4) + prev_hash (32) + merkle_root (32) + timestamp (8) + height (4) + difficulty (8)
        header = bytearray()
        
        # Version - 4 bytes, little endian
        header.extend(struct.pack("<I", self.version))
        
        # Previous block hash - 32 bytes
        if self.prev_hash:
            header.extend(bytes.fromhex(self.prev_hash))
        else:
            header.extend(bytes(32))  # 32 zeros for genesis block
            
        # Merkle root - 32 bytes
        header.extend(bytes.fromhex(self.merkle_root if self.merkle_root else "0" * 64))
        
        # Timestamp - 8 bytes, little endian
        header.extend(struct.pack("<Q", self.timestamp))
        
        # Height - 4 bytes, little endian
        header.extend(struct.pack("<I", self.height))
        
        # Difficulty - 8 bytes, double precision float
        header.extend(struct.pack("<d", self.difficulty))
        
        return bytes(header)
    
    def mine(self, callback=None) -> bool:
        """
        Mine the block using SHA3-256 proof-of-work algorithm
        
        Args:
            callback: Optional callback function for progress updates
            
        Returns:
            True if mining succeeded, False otherwise
        """
        logger.info(f"Starting to mine block at height {self.height} using SHA3-256...")
        
        # Make sure merkle root is calculated
        if not self.merkle_root:
            self.calculate_merkle_root()
        
        # Import the PoW implementation
        from core.consensus.pow import ProofOfWork
        
        # Create block header dictionary for mining
        header = {
            'version': self.version,
            'prev_hash': self.prev_hash or "0" * 64,
            'merkle_root': self.merkle_root,
            'timestamp': self.timestamp,
            'height': self.height,
            'difficulty': self.difficulty,
            'nonce': self.nonce
        }
        
        # Initialize proof-of-work solver
        pow_solver = ProofOfWork(header, self.difficulty)
        
        # Start mining
        success, nonce, block_hash = pow_solver.mine(start_nonce=self.nonce)
        
        if success:
            # Mining succeeded
            self.nonce = nonce
            # Use the hash returned by the mining function
            self.hash = block_hash
            logger.info(f"Successfully mined block {self.height} with hash {self.hash}")
            return True
        else:
            # Mining failed or was stopped
            logger.warning("Mining failed or was stopped")
            return False
    
    @classmethod
    def create_genesis_block(cls) -> 'Block':
        """
        Create the genesis block and mine it to find a valid hash
        
        Returns:
            Genesis block instance
        """
        logger.info("Creating and mining genesis block")
        
        # Load genesis information from genesis.yaml
        genesis_path = os.path.join(os.path.dirname(__file__), 'genesis.yaml')
        with open(genesis_path, 'r') as file:
            genesis_info = yaml.safe_load(file)
        
        # Use current time instead of predefined timestamp
        current_timestamp = int(time.time())
        logger.info(f"Using current timestamp for genesis block: {current_timestamp}")
        
        # Create coinbase transactions for genesis block allocations (one per allocation)
        # We use the Transaction class to ensure proper hash calculation
        transactions = []
        for address, amount in genesis_info['allocations'].items():
            # Create a proper Transaction object for genesis allocation
            from core.transaction import Transaction
            
            # Create transaction with correct data
            tx_obj = Transaction(
                version=1,
                timestamp=current_timestamp,
                inputs=[],  # No inputs for genesis allocations
                outputs=[{'address': address, 'amount': amount}],
                data=genesis_info['message'],
                fee=0,
                public_key=None,
                signature=None
            )
            
            # Transaction object will calculate its hash correctly
            # Convert to dict for consistency with existing code
            tx = tx_obj.to_dict()
            transactions.append(tx)
            
        # Generate a deterministic previous hash (all zeros for genesis)
        prev_hash = "0" * 64
            
        # Create genesis block
        genesis = cls(
            version=config.GENESIS_VERSION,
            prev_hash=prev_hash,
            timestamp=current_timestamp,  # Use current timestamp
            height=0,
            difficulty=config.INITIAL_DIFFICULTY,  # Using initial difficulty from config
            transactions=transactions,
            extra_data={"message": genesis_info['message']}
        )
        
        # Calculate merkle root from the transactions
        genesis.calculate_merkle_root()
        logger.info(f"Genesis merkle root calculated: {genesis.merkle_root}")
        
        # Mine the genesis block to find a valid hash
        logger.info(f"Mining genesis block at difficulty {config.INITIAL_DIFFICULTY}...")
        
        # Import the PoW implementation to mine the block
        from core.consensus.pow import ProofOfWork
        
        # Create block header dictionary for mining
        header = {
            'version': genesis.version,
            'prev_hash': genesis.prev_hash,
            'merkle_root': genesis.merkle_root,
            'timestamp': genesis.timestamp,
            'height': genesis.height,
            'difficulty': genesis.difficulty,
            'nonce': 0  # Start with nonce 0
        }
        
        # Initialize proof-of-work solver
        pow_solver = ProofOfWork(header, genesis.difficulty)
        
        # Start mining the genesis block
        success, nonce, block_hash = pow_solver.mine(start_nonce=0)
        
        if success:
            # Mining succeeded, update the block with the found nonce and hash
            genesis.nonce = nonce
            genesis.hash = block_hash
            logger.info(f"Genesis block successfully mined:")
            logger.info(f"Genesis block hash: {genesis.hash}")
            logger.info(f"Genesis merkle root: {genesis.merkle_root}")
            logger.info(f"Genesis timestamp: {genesis.timestamp}")
            logger.info(f"Genesis nonce: {genesis.nonce}")
            logger.info(f"Genesis previous hash: {genesis.prev_hash}")
            logger.info(f"Genesis difficulty: {genesis.difficulty}")
            logger.info(f"Genesis transactions: {len(genesis.transactions)}")
        else:
            # Mining failed - this should not happen in normal conditions
            logger.error("Failed to mine genesis block!")
            raise Exception("Genesis block mining failed")
        
        return genesis
        
    def verify_transactions(self, blockchain) -> bool:
        """
        Verify all transactions in the block
        
        Args:
            blockchain: Reference to blockchain for UTXO validation
            
        Returns:
            True if all transactions are valid, False otherwise
        """
        # In a production implementation, you'd verify each transaction
        # For now, return True for simplicity
        return True
    
    def __str__(self) -> str:
        """String representation of the block"""
        tx_count = len(self.transactions)
        timestamp_str = datetime.fromtimestamp(self.timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        return (f"Block {self.height} ({self.hash[:8]}...)\n"
                f"Time: {timestamp_str}\n"
                f"Transactions: {tx_count}\n"
                f"Difficulty: {self.difficulty}")

