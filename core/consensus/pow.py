#!/usr/bin/env python3
"""
Proof of Work Implementation for Qbitcoin

This file implements a quantum-resistant proof-of-work system using SHA3-256 hashing algorithm.
"""

import os
import sys
import time
import threading
import hashlib
import traceback
from typing import Dict, Any, Tuple

# Import configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from core import config 

# Import required utilities
from utils.logger import get_logger

# Initialize logger
logger = get_logger("pow")

class ProofOfWork:
    """Quantum-resistant proof-of-work implementation using SHA3-256"""
    
    def __init__(self, block_header: Dict[str, Any], difficulty: float):
        """
        Initialize the proof-of-work solver
        
        Args:
            block_header: Dictionary containing block header fields
            difficulty: Current difficulty target
        """
        self.block_header = block_header
        self.difficulty = difficulty
        self.stop_mining = False
    
    @staticmethod
    def get_target_from_difficulty(difficulty: float) -> int:
        """
        Convert mining difficulty to a target value
        
        Args:
            difficulty: Mining difficulty
            
        Returns:
            Integer target (lower means more difficult)
        """
        # Maximum target (lowest difficulty)
        max_target = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
        
        # Calculate target based on difficulty
        # Lower target = higher difficulty
        target = int(max_target / difficulty)
        return target
    
    @staticmethod
    def hash_meets_target(block_hash: str, target: int) -> bool:
        """
        Check if a block hash meets the target difficulty
        
        Args:
            block_hash: Block hash in hexadecimal format
            target: Target value to compare against
            
        Returns:
            True if hash meets target, False otherwise
        """
        # Convert hash to integer
        hash_int = int(block_hash, 16)
        
        # Hash must be below target to meet difficulty
        return hash_int < target
    
    @staticmethod
    def compute_block_hash(header: Dict[str, Any]) -> str:
        """
        Compute SHA3-256 hash of a block header
        
        Args:
            header: Block header with version, prev_hash, merkle_root, timestamp, height, difficulty, nonce
            
        Returns:
            Hexadecimal hash string
        """
        # Create a SHA3-256 hash object
        sha3_hash = hashlib.sha3_256()
        
        # Add all header fields to the hash
        sha3_hash.update(str(header['version']).encode('utf-8'))
        sha3_hash.update(header['prev_hash'].encode('utf-8'))
        sha3_hash.update(header['merkle_root'].encode('utf-8'))
        sha3_hash.update(str(header['timestamp']).encode('utf-8'))
        sha3_hash.update(str(header['height']).encode('utf-8'))
        sha3_hash.update(str(header['difficulty']).encode('utf-8'))
        sha3_hash.update(str(header['nonce']).encode('utf-8'))
        
        # Return the hexadecimal digest
        return sha3_hash.hexdigest()
    
    def mine(self, start_nonce: int = 0, max_nonce: int = None, callback=None) -> Tuple[bool, int, str]:
        """
        Perform mining operation to find a valid nonce
        
        Args:
            start_nonce: Starting nonce value
            max_nonce: Maximum nonce to try before giving up
            callback: Optional callback to track progress
            
        Returns:
            Tuple of (success, nonce, hash)
        """
        if max_nonce is None:
            max_nonce = 2**32  # 32-bit nonce space
            
        # Calculate target from difficulty
        target = self.get_target_from_difficulty(self.difficulty)
        
        # Start mining loop
        nonce = start_nonce
        start_time = time.time()
        status_time = start_time
        hashes = 0
        progress_interval = 10000  # Report progress every 10,000 nonces (more frequent updates)
        progress_counter = 0
        
        while nonce < max_nonce and not self.stop_mining:
            # Update nonce in block header
            self.block_header['nonce'] = nonce
            
            # Compute block hash
            block_hash = self.compute_block_hash(self.block_header)
            hashes += 1
            progress_counter += 1
            
            # Check if hash meets target
            if self.hash_meets_target(block_hash, target):
                # Found a valid hash!
                end_time = time.time()
                time_elapsed = end_time - start_time
                hash_rate = hashes / time_elapsed if time_elapsed > 0 else 0
                
                logger.info(f"Found valid hash after {hashes} attempts ({hash_rate:.2f} H/s)")
                logger.info(f"Block hash: {block_hash}, Nonce: {nonce}")
                
                return True, nonce, block_hash
            
            # Print status every 1 second or every progress_interval nonces
            current_time = time.time()
            if current_time - status_time >= 1 or progress_counter >= progress_interval:
                time_elapsed = current_time - start_time
                hash_rate = hashes / time_elapsed if time_elapsed > 0 else 0
                #logger.info(f"Mining progress: {hashes} hashes, {hash_rate:.2f} H/s, nonce: {nonce}")
                status_time = current_time
                progress_counter = 0
            
            # Increment nonce
            nonce += 1
            
            # Call the callback if provided
            if callback and progress_counter % 1000 == 0:  # Call callback more frequently
                callback(1000)  # Report hashes in smaller batches
        
        # If we get here, mining was unsuccessful or stopped
        if self.stop_mining:
            logger.info("Mining stopped by user")
        else:
            logger.info(f"Mining unsuccessful after {hashes} attempts")
        
        return False, nonce, ""
    
    def stop(self):
        """Stop the mining operation"""
        self.stop_mining = True


class BlockMiner:
    """Block miner implementation for Qbitcoin"""
    
    def __init__(self, blockchain, mempool):
        """
        Initialize the block miner
        
        Args:
            blockchain: Reference to the blockchain
            mempool: Reference to the transaction memory pool
        """
        self.blockchain = blockchain
        self.mempool = mempool
        self.mining = False
        self.mining_thread = None
        self.reward_address = None
        self.last_mined_block = None
        self.blocks_mined = 0
        self.last_hash_rate = 0.0
        self.total_hashes = 0
        self.mining_start_time = 0
        self.last_status_update = 0
        
    def start_mining(self, reward_address: str) -> bool:
        """
        Start mining blocks in a background thread
        
        Args:
            reward_address: Address to receive mining rewards
            
        Returns:
            True if mining started, False otherwise
        """
        if self.mining:
            logger.warning("Mining already running")
            return True
            
        # Set reward address
        self.reward_address = reward_address
        
        # Set mining flag and start thread
        self.mining = True
        self.mining_thread = threading.Thread(target=self._mining_loop)
        self.mining_thread.daemon = True
        self.mining_thread.start()
        
        logger.info(f"Started mining to address {reward_address}")
        return True
        
    def stop_mining(self) -> bool:
        """
        Stop mining blocks
        
        Returns:
            True if mining was stopped, False if it wasn't running
        """
        if not self.mining:
            return False
            
        # Clear mining flag
        self.mining = False
        
        # Join thread
        if self.mining_thread:
            self.mining_thread.join(timeout=2.0)
            self.mining_thread = None
        
        logger.info("Mining stopped")
        return True
        
    def is_mining(self) -> bool:
        """
        Check if mining is currently running
        
        Returns:
            True if mining, False otherwise
        """
        return self.mining
        
    def _mining_loop(self):
        """Main mining loop that runs in a background thread"""
        logger.info("Mining thread started")
        self.mining_start_time = time.time()
        self.last_status_update = self.mining_start_time
        self.total_hashes = 0
        
        while self.mining:
            try:
                # Create and mine a new block
                logger.debug("Creating a new block for mining...")
                mined_block = self._mine_next_block()
                

                # If mining was successful, add the block to the blockchain
                if mined_block:
                    logger.debug(f"Mined block candidate: {mined_block}")
                    
                    # Store the transactions for later verification
                    block_tx_hashes = set()
                    for tx in mined_block.transactions:
                        if hasattr(tx, 'hash'):
                            block_tx_hashes.add(tx.hash)
                        elif isinstance(tx, dict) and 'hash' in tx:
                            block_tx_hashes.add(tx['hash'])
                    
                    # Add the block to the blockchain
                    result = self.blockchain.add_block(mined_block)
                    
                    if result:
                        self.blocks_mined += 1
                        self.last_mined_block = mined_block
                        logger.info(f"Successfully mined and added block {mined_block.height}")
                        
                        # Double-check that transactions were removed from mempool
                        if self.mempool:
                            remaining_tx_count = 0
                            for tx_hash in block_tx_hashes:
                                if self.mempool.has_transaction(tx_hash):
                                    remaining_tx_count += 1
                                    logger.warning(f"Transaction {tx_hash} was not removed from mempool after mining")
                            
                            if remaining_tx_count > 0:
                                logger.warning(f"Found {remaining_tx_count} transactions still in mempool after mining")
                                # Force removal of transactions if they're still in mempool
                                try:
                                    self.mempool.remove_confirmed_transactions(mined_block)
                                    logger.info(f"Forced removal of transactions from mempool for block {mined_block.height}")
                                except Exception as e:
                                    logger.error(f"Error forcing transaction removal: {str(e)}")
                        
                        # Broadcast block to network if blockchain has p2p network access
                        try:
                            # First check direct access to p2p network via blockchain
                            if hasattr(self.blockchain, 'node') and self.blockchain.node and hasattr(self.blockchain.node, 'p2p_network') and self.blockchain.node.p2p_network:
                                # Get peer count for logging
                                if hasattr(self.blockchain.node.p2p_network, 'active_connections'):
                                    peer_count = len(self.blockchain.node.p2p_network.active_connections)
                                    logger.info(f"Attempting to broadcast block to {peer_count} connected peers")
                                
                                # Try to broadcast the block
                                broadcast_result = self.blockchain.node.p2p_network.broadcast_block(mined_block)
                                
                                if broadcast_result:
                                    logger.info(f"Block {mined_block.height} successfully broadcast to network")
                                else:
                                    logger.warning(f"Failed to broadcast block {mined_block.height} - no connected peers or connection issues")
                                    
                                    # Try to connect to bootstrap nodes if we have no peers
                                    if hasattr(self.blockchain.node.p2p_network, '_bootstrap'):
                                        logger.info("Attempting to connect to bootstrap nodes...")
                                        self.blockchain.node.p2p_network._bootstrap()
                                        
                                        # Try broadcasting again after bootstrap
                                        time.sleep(2)  # Wait for connections to establish
                                        logger.info("Retrying block broadcast after bootstrap...")
                                        retry_result = self.blockchain.node.p2p_network.broadcast_block(mined_block)
                                        if retry_result:
                                            logger.info(f"Block {mined_block.height} successfully broadcast after retry")
                            else:
                                # Log detailed information about what's missing
                                if not hasattr(self.blockchain, 'node'):
                                    logger.warning("No P2P network available for block broadcasting - blockchain has no node attribute")
                                elif not self.blockchain.node:
                                    logger.warning("No P2P network available for block broadcasting - blockchain.node is None")
                                elif not hasattr(self.blockchain.node, 'p2p_network'):
                                    logger.warning("No P2P network available for block broadcasting - node has no p2p_network attribute")
                                elif not self.blockchain.node.p2p_network:
                                    logger.warning("No P2P network available for block broadcasting - node.p2p_network is None")
                                else:
                                    logger.warning("No P2P network available for block broadcasting - unknown reason")
                        except Exception as e:
                            import traceback
                            logger.error(f"Error broadcasting mined block: {e}")
                            logger.error(f"Exception details: {traceback.format_exc()}")
                    else:
                        logger.warning(f"Failed to add mined block to blockchain. Possible validation failure.")
                else:
                    logger.debug("Mining did not produce a valid block.")
                
                # Update mining statistics regularly even if no block is found
                current_time = time.time()
                if current_time - self.last_status_update >= 10:  # Update every 10 seconds
                    elapsed = current_time - self.mining_start_time
                    if elapsed > 0:
                        self.last_hash_rate = self.total_hashes / elapsed
                        logger.info(f"Mining statistics: {self.total_hashes} total hashes, {self.last_hash_rate:.2f} H/s")
                    self.last_status_update = current_time
            
            except Exception as e:
                logger.error(f"Error in mining loop: {e}")
                time.sleep(5)  # Wait before retrying after error
    
    def _mine_next_block(self):
        """
        Mine the next block
        
        Returns:
            Block object if mining successful, None otherwise
        """
        if not self.mining:
            return None
            
        # Get current blockchain state
        prev_hash = self.blockchain.best_hash
        height = self.blockchain.current_height + 1
        
        # Use the next block difficulty based on blockchain state
        # Only log the difficulty periodically, not on every attempt
        current_time = time.time()
        should_log = (current_time - self.last_status_update) >= 60  # Only log once per minute
        
        difficulty = self.blockchain.get_next_block_difficulty(log_info=should_log)
        timestamp = int(current_time)
        
        if should_log:
            logger.info(f"Preparing to mine block {height} with difficulty {difficulty}")
            self.last_status_update = current_time
        
        # Create coinbase transaction
        reward = config.calculate_block_reward(height)
        coinbase_tx = self._create_coinbase_transaction(reward, height)
        
        # Get transactions from mempool
        transactions = self.mempool.get_transactions_for_block(max_size=config.MAX_BLOCK_SIZE)
        logger.info(f"Selected {len(transactions)} transactions for block, total size: {sum(tx.size for tx in transactions if hasattr(tx, 'size'))}")
        
        # Add coinbase transaction
        all_transactions = [coinbase_tx] + transactions
        
        # Calculate merkle root
        merkle_root = self._calculate_merkle_root(all_transactions)
        
        # Create block header
        block_header = {
            'version': config.GENESIS_VERSION,
            'prev_hash': prev_hash,
            'merkle_root': merkle_root,
            'timestamp': timestamp,
            'height': height,
            'difficulty': difficulty,
            'nonce': 0  # Will be filled during mining
        }
        
        # Initialize proof of work solver
        pow_solver = ProofOfWork(block_header, difficulty)
        
        # Start mining
        logger.info(f"Mining block {height} with {len(all_transactions)} transactions")
        logger.info(f"Started mining to address {self.reward_address}")
        
        # Define a callback to track hashing progress
        def hash_callback(hashes_performed):
            self.total_hashes += hashes_performed
        
        # Mine with the callback
        success, nonce, block_hash = pow_solver.mine(callback=hash_callback)
        
        # Check if mining was successful
        if not success or not self.mining:
            logger.debug("Mining was unsuccessful or stopped.")
            return None
            
        # Create block with transactions
        from core.block import Block
        block = Block(
            version=block_header['version'],
            prev_hash=block_header['prev_hash'],
            merkle_root=block_header['merkle_root'],
            timestamp=block_header['timestamp'],
            height=block_header['height'],
            difficulty=block_header['difficulty'],
            nonce=nonce,
            transactions=all_transactions
        )
        
        # Set the hash manually after creation
        block.hash = block_hash
        
        logger.info(f"Successfully mined block #{height} with hash {block_hash[:10]}...")
        return block
    
    def _create_coinbase_transaction(self, reward: float, height: int):
        """
        Create a coinbase transaction for a new block
        
        Args:
            reward: Block mining reward
            height: Block height
            
        Returns:
            Coinbase transaction object
        """
        from core.transaction import Transaction
        
        # Create coinbase input data (includes block height)
        coinbase_data = f"Qbitcoin mined block {height}".encode('utf-8').hex()
        
        # Create transaction with coinbase input and reward output
        tx = Transaction.create_coinbase(
            recipient_address=self.reward_address,
            amount=reward,
            height=height,
            data=coinbase_data
        )
        
        # If we're returning a Transaction object, ensure it's properly initialized
        # so it can be serialized properly
        if not hasattr(tx, 'to_dict') or not callable(getattr(tx, 'to_dict')):
            # Convert to dictionary if it's not a proper Transaction object
            return tx.to_dict() if hasattr(tx, 'to_dict') else tx
            
        return tx
    
    def _calculate_merkle_root(self, transactions):
        """
        Calculate the merkle root of a list of transactions
        
        Args:
            transactions: List of transaction objects
            
        Returns:
            Merkle root hash string
        """
        # Get transaction hashes
        hashes = [tx.hash for tx in transactions]
        
        # Calculate merkle root using SHA3-256
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])  # Duplicate last hash if odd number
                
            new_hashes = []
            for i in range(0, len(hashes), 2):
                # Concatenate adjacent hashes and rehash
                concat = hashes[i] + hashes[i + 1]
                hash_obj = hashlib.sha3_256(concat.encode('utf-8'))
                new_hashes.append(hash_obj.hexdigest())
                
            hashes = new_hashes
            
        # Return single remaining hash (merkle root)
        return hashes[0] if hashes else hashlib.sha3_256(b"").hexdigest()
    
    def get_mining_stats(self) -> Dict[str, Any]:
        """
        Get mining statistics
        
        Returns:
            Dictionary with mining statistics
        """
        elapsed = 0
        if self.mining_start_time > 0:
            elapsed = time.time() - self.mining_start_time
        
        # Calculate current hashrate
        current_hashrate = 0
        if elapsed > 0:
            current_hashrate = self.total_hashes / elapsed
        
        return {
            "mining": self.mining,
            "blocks_mined": self.blocks_mined,
            "reward_address": self.reward_address,
            "last_block_height": self.last_mined_block.height if self.last_mined_block else None,
            "last_block_hash": self.last_mined_block.hash if self.last_mined_block else None,
            "algorithm": config.MINING_ALGORITHM,
            "current_difficulty": self.blockchain.get_next_block_difficulty(log_info=False) if self.blockchain else 0,
            "last_hash_rate": self.last_hash_rate or current_hashrate,
            "total_hashes": self.total_hashes
        }