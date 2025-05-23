#!/usr/bin/env python3
"""
Comprehensive Test Suite for SHA3-256 Proof of Work Mining Implementation

This test script thoroughly tests the quantum-resistant proof-of-work
implementation using SHA3-256 in the core/consensus/pow.py file.
"""

import os
import sys
import time
import hashlib
import unittest
from typing import Dict, Any, List, Tuple
import threading

# Add project root to path to fix imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from core.consensus.pow import ProofOfWork, BlockMiner
from core.block import Block
from core.blockchain import Blockchain
from core.mempool import Mempool
from core.transaction import Transaction
import config
from utils.logger import get_logger

# Initialize logger
logger = get_logger("test_pow")

class MockBlockchain:
    """Mock blockchain for testing purposes"""
    
    def __init__(self, height=10, difficulty=1.0):
        """Initialize mock blockchain with specified height and difficulty"""
        self.current_height = height
        self.best_hash = "0" * 64
        self._difficulty = difficulty
        self.blocks = {}
        
    def get_next_block_difficulty(self, log_info=False):
        """Return the difficulty for the next block"""
        return self._difficulty
        
    def add_block(self, block):
        """Add a block to the mock blockchain"""
        self.blocks[block.hash] = block
        self.current_height = block.height
        self.best_hash = block.hash
        return True
        
    def get_block_by_height(self, height):
        """Get a block by height"""
        for block in self.blocks.values():
            if block.height == height:
                return block
        return None
        
    def get_best_block(self):
        """Get the current best block"""
        return self.blocks.get(self.best_hash)

class MockMempool:
    """Mock mempool for testing purposes"""
    
    def __init__(self):
        """Initialize mock mempool"""
        self.transactions = []
        
    def get_transactions_for_block(self, max_size=None):
        """Get transactions for a new block"""
        return self.transactions
        
    def add_transaction(self, transaction):
        """Add a transaction to the mempool"""
        self.transactions.append(transaction)

class TestProofOfWork(unittest.TestCase):
    """Test cases for the ProofOfWork class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a sample block header for testing
        self.test_header = {
            'version': 1,
            'prev_hash': "0" * 64,
            'merkle_root': "abcdef" + "0" * 58,
            'timestamp': int(time.time()),
            'height': 1,
            'difficulty': 1,  # Low difficulty for fast tests
            'nonce': 0
        }
        
    def test_initialization(self):
        """Test initialization of ProofOfWork class"""
        pow_solver = ProofOfWork(self.test_header, self.test_header['difficulty'])
        self.assertEqual(pow_solver.block_header, self.test_header)
        self.assertEqual(pow_solver.difficulty, self.test_header['difficulty'])
        self.assertFalse(pow_solver.stop_mining)
    
    def test_target_calculation(self):
        """Test difficulty to target conversion"""
        difficulty = 1.0
        target = ProofOfWork.get_target_from_difficulty(difficulty)
        self.assertEqual(target, 0x00000000FFFF0000000000000000000000000000000000000000000000000000)
        
        # Test higher difficulty (lower target)
        difficulty = 10.0
        target = ProofOfWork.get_target_from_difficulty(difficulty)
        self.assertEqual(target, 0x000000000FFFF000000000000000000000000000000000000000000000000)
        
        # Test lower difficulty (higher target)
        difficulty = 0.5
        target = ProofOfWork.get_target_from_difficulty(difficulty)
        self.assertEqual(target, 0x000000001FFFE000000000000000000000000000000000000000000000000)
    
    def test_hash_computation(self):
        """Test block hash computation"""
        computed_hash = ProofOfWork.compute_block_hash(self.test_header)
        self.assertEqual(len(computed_hash), 64)  # SHA3-256 produces 64 hex chars
        
        # Verify hash is deterministic
        computed_hash2 = ProofOfWork.compute_block_hash(self.test_header)
        self.assertEqual(computed_hash, computed_hash2)
        
        # Verify hash changes when header changes
        modified_header = dict(self.test_header)
        modified_header['nonce'] = 1
        different_hash = ProofOfWork.compute_block_hash(modified_header)
        self.assertNotEqual(computed_hash, different_hash)
    
    def test_hash_target_verification(self):
        """Test verification of hash against target"""
        # Hash that meets a really easy target
        easy_target = 0x00FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        hash_value = "00ABCDEF" + "F" * 56
        self.assertTrue(ProofOfWork.hash_meets_target(hash_value, easy_target))
        
        # Hash that doesn't meet the target
        hard_target = 0x0000FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        self.assertFalse(ProofOfWork.hash_meets_target(hash_value, hard_target))
    
    def test_mining_success(self):
        """Test successful block mining"""
        # Use very low difficulty for quick test
        header = dict(self.test_header)
        header['difficulty'] = 0.00001
        pow_solver = ProofOfWork(header, header['difficulty'])
        
        # Mine the block
        success, nonce, block_hash = pow_solver.mine()
        
        # Verify mining was successful
        self.assertTrue(success)
        self.assertIsInstance(nonce, int)
        self.assertEqual(len(block_hash), 64)
        
        # Verify the found hash actually meets the target
        target = ProofOfWork.get_target_from_difficulty(header['difficulty'])
        self.assertTrue(ProofOfWork.hash_meets_target(block_hash, target))
    
    def test_mining_stop(self):
        """Test stopping the mining process"""
        # Use higher difficulty to ensure it would take time
        header = dict(self.test_header)
        header['difficulty'] = 1.0
        pow_solver = ProofOfWork(header, header['difficulty'])
        
        # Start mining in a thread
        mining_thread = threading.Thread(target=lambda: setattr(self, 'mining_result', pow_solver.mine()))
        mining_thread.daemon = True
        mining_thread.start()
        
        # Let it run briefly
        time.sleep(0.5)
        
        # Stop mining
        pow_solver.stop()
        
        # Wait for thread to complete
        mining_thread.join(timeout=1.0)
        
        # Verify mining was stopped
        success, _, _ = self.mining_result
        self.assertFalse(success)
        self.assertTrue(pow_solver.stop_mining)
    
    def test_mining_max_nonce(self):
        """Test mining with a maximum nonce limit"""
        header = dict(self.test_header)
        header['difficulty'] = 100.0  # Very high difficulty
        pow_solver = ProofOfWork(header, header['difficulty'])
        
        # Mine with a small max_nonce
        success, nonce, _ = pow_solver.mine(start_nonce=0, max_nonce=1000)
        
        # Verify mining failed due to reaching max_nonce
        self.assertFalse(success)
        self.assertLessEqual(nonce, 1000)
    
    def test_different_start_nonce(self):
        """Test mining with a different starting nonce"""
        # Use very low difficulty for quick test
        header = dict(self.test_header)
        header['difficulty'] = 0.00001
        pow_solver = ProofOfWork(header, header['difficulty'])
        
        # Mine the block with a high start_nonce
        start_nonce = 1000000
        success, nonce, _ = pow_solver.mine(start_nonce=start_nonce)
        
        # Verify mining started from the specified nonce
        self.assertTrue(success)
        self.assertGreaterEqual(nonce, start_nonce)


class TestBlockMiner(unittest.TestCase):
    """Test cases for the BlockMiner class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create mock blockchain and mempool for testing
        self.mock_blockchain = MockBlockchain()
        self.mock_mempool = MockMempool()
        
        # Create a test BlockMiner instance
        self.miner = BlockMiner(self.mock_blockchain, self.mock_mempool)
        
        # Sample mining address
        self.test_address = "QkF2AoXUxsbUuTeexmjGM6rSVVtaui85cq"
        
        # Mock transaction
        self.mock_transaction = Transaction(
            version=1,
            inputs=[],
            outputs=[{"address": self.test_address, "amount": 10.0}],
            timestamp=int(time.time()),
            data="test",
            fee=0.001
        )
    
    def test_initialization(self):
        """Test initialization of BlockMiner class"""
        self.assertEqual(self.miner.blockchain, self.mock_blockchain)
        self.assertEqual(self.miner.mempool, self.mock_mempool)
        self.assertFalse(self.miner.mining)
        self.assertIsNone(self.miner.mining_thread)
        self.assertIsNone(self.miner.reward_address)
        self.assertIsNone(self.miner.last_mined_block)
        self.assertEqual(self.miner.blocks_mined, 0)
    
    def test_start_stop_mining(self):
        """Test starting and stopping mining operations"""
        # Start mining
        result = self.miner.start_mining(self.test_address)
        self.assertTrue(result)
        self.assertTrue(self.miner.mining)
        self.assertEqual(self.miner.reward_address, self.test_address)
        self.assertIsNotNone(self.miner.mining_thread)
        
        # Let mining run briefly
        time.sleep(1.0)
        
        # Stop mining
        result = self.miner.stop_mining()
        self.assertTrue(result)
        self.assertFalse(self.miner.mining)
        self.assertIsNone(self.miner.mining_thread)
    
    def test_mining_stats(self):
        """Test getting mining statistics"""
        # Start mining
        self.miner.start_mining(self.test_address)
        
        # Get mining stats
        stats = self.miner.get_mining_stats()
        
        # Verify stats contain expected fields
        self.assertTrue(stats["mining"])
        self.assertEqual(stats["reward_address"], self.test_address)
        self.assertEqual(stats["algorithm"], config.MINING_ALGORITHM)
        self.assertEqual(stats["blocks_mined"], 0)
        
        # Stop mining
        self.miner.stop_mining()
    
    def test_coinbase_creation(self):
        """Test creation of coinbase transaction"""
        # Create a coinbase transaction
        height = 10
        reward = 2.5
        coinbase_tx = self.miner._create_coinbase_transaction(reward, height)
        
        # Verify coinbase transaction
        self.assertEqual(len(coinbase_tx.inputs), 1)
        self.assertEqual(len(coinbase_tx.outputs), 1)
        self.assertEqual(coinbase_tx.outputs[0]["address"], self.test_address)
        self.assertEqual(coinbase_tx.outputs[0]["amount"], reward)
    
    def test_merkle_root_calculation(self):
        """Test calculation of merkle root"""
        # Add transaction to mempool
        self.mock_mempool.add_transaction(self.mock_transaction)
        
        # Set miner reward address
        self.miner.reward_address = self.test_address
        
        # Create a test coinbase transaction
        coinbase_tx = self.miner._create_coinbase_transaction(2.5, 1)
        
        # Calculate merkle root with transactions including coinbase
        transactions = [coinbase_tx, self.mock_transaction]
        merkle_root = self.miner._calculate_merkle_root(transactions)
        
        # Verify merkle root
        self.assertEqual(len(merkle_root), 64)  # SHA3-256 hash length
    
    def test_is_mining(self):
        """Test is_mining function"""
        self.assertFalse(self.miner.is_mining())
        
        # Start mining
        self.miner.start_mining(self.test_address)
        self.assertTrue(self.miner.is_mining())
        
        # Stop mining
        self.miner.stop_mining()
        self.assertFalse(self.miner.is_mining())


class TestBlockMining(unittest.TestCase):
    """Integration tests for block mining"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a new block for mining tests
        self.block = Block(
            version=1, 
            prev_hash="0" * 64,
            height=1,
            difficulty=0.00001  # Very low difficulty for testing
        )
        
        # Sample transaction
        self.test_tx = Transaction(
            version=1,
            inputs=[],
            outputs=[{"address": "QTest", "amount": 10.0}],
            timestamp=int(time.time()),
            data="test transaction",
            fee=0.001
        )
        self.block.transactions = [self.test_tx]
        
        # Calculate merkle root
        self.block.calculate_merkle_root()
    
    def test_block_mining(self):
        """Test mining a block using the Block.mine method"""
        # Mine the block
        start_time = time.time()
        success = self.block.mine()
        end_time = time.time()
        
        # Verify mining was successful
        self.assertTrue(success)
        logger.info(f"Block mined in {end_time - start_time:.2f} seconds")
        logger.info(f"Block hash: {self.block.hash}, nonce: {self.block.nonce}")
        
        # Verify block hash meets difficulty target
        from core.consensus.pow import ProofOfWork
        target = ProofOfWork.get_target_from_difficulty(self.block.difficulty)
        self.assertTrue(ProofOfWork.hash_meets_target(self.block.hash, target))
    
    def test_block_validation(self):
        """Test block validation after mining"""
        # Mine the block
        success = self.block.mine()
        self.assertTrue(success)
        
        # Validate the block
        valid = self.block.validate()
        self.assertTrue(valid)
        
        # Tamper with the block and revalidate
        original_nonce = self.block.nonce
        self.block.nonce += 1
        valid = self.block.validate()
        self.assertFalse(valid)
        
        # Reset nonce and tamper with merkle root
        self.block.nonce = original_nonce
        original_merkle = self.block.merkle_root
        self.block.merkle_root = "a" * 64
        valid = self.block.validate()
        self.assertFalse(valid)


class TestBlockchainMining(unittest.TestCase):
    """End-to-end test for mining on a blockchain"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test blockchain once for all tests"""
        # Use a test-specific chain ID
        cls.chain_id = "test-pow-mining-" + str(int(time.time()))
        
        # Initialize a real blockchain with a low difficulty genesis block
        config.INITIAL_DIFFICULTY = 0.00001  # Very low for testing
        cls.blockchain = Blockchain(chain_id=cls.chain_id)
    
    def test_mine_multiple_blocks(self):
        """Test mining multiple blocks on the blockchain"""
        # Create mempool
        mempool = Mempool()
        
        # Create mining address
        mining_address = "QTestMiningAddress12345"
        
        # Create and start miner
        miner = BlockMiner(self.blockchain, mempool)
        
        # Create a few test transactions
        for i in range(5):
            tx = Transaction(
                version=1,
                inputs=[],
                outputs=[{"address": f"QTest{i}", "amount": 1.0}],
                timestamp=int(time.time()),
                data=f"test transaction {i}",
                fee=0.001
            )
            mempool.add_transaction(tx)
        
        # Define a callback for mining progress
        class MiningProgress:
            def __init__(self):
                self.updates = []
                
            def update(self, status):
                self.updates.append(status)
                logger.info(f"Mining progress: {status}")
        
        progress = MiningProgress()
        
        # Mine a block manually
        logger.info(f"Starting to mine block at height {self.blockchain.current_height + 1}")
        
        # Prepare block header for next block
        prev_hash = self.blockchain.best_hash
        height = self.blockchain.current_height + 1
        timestamp = int(time.time())
        difficulty = self.blockchain.get_next_block_difficulty()
        
        # Create transactions including coinbase
        reward = config.calculate_block_reward(height)
        coinbase_tx = Transaction.create_coinbase(
            reward_address=mining_address,
            reward_amount=reward,
            height=height,
            coinbase_data=f"TestMining-{height}"
        )
        
        transactions = mempool.get_transactions_for_block()
        all_transactions = [coinbase_tx] + transactions
        
        # Create block
        block = Block(
            version=1,
            prev_hash=prev_hash,
            merkle_root="",  # Will be calculated
            timestamp=timestamp,
            height=height,
            difficulty=difficulty,
            transactions=all_transactions
        )
        
        # Mine the block
        start_time = time.time()
        success = block.mine()
        end_time = time.time()
        
        mining_time = end_time - start_time
        logger.info(f"Block {height} mined in {mining_time:.2f} seconds with {len(all_transactions)} transactions")
        logger.info(f"Block hash: {block.hash}, nonce: {block.nonce}")
        
        # Add block to blockchain
        result = self.blockchain.add_block(block)
        self.assertTrue(result)
        
        # Verify blockchain state
        self.assertEqual(self.blockchain.current_height, height)
        self.assertEqual(self.blockchain.best_hash, block.hash)
        
        # Use the miner to mine another block automatically
        miner.start_mining(mining_address)
        
        # Let mining run for a short time
        time.sleep(5.0)
        
        # Stop mining
        miner.stop_mining()
        
        # Verify mining stats
        stats = miner.get_mining_stats()
        logger.info(f"Mining stats: {stats}")
        
        # If a block was mined, verify it's in the blockchain
        if miner.blocks_mined > 0 and miner.last_mined_block:
            self.assertEqual(self.blockchain.best_hash, miner.last_mined_block.hash)
            logger.info(f"Miner successfully added {miner.blocks_mined} blocks to the blockchain")
            logger.info(f"Last block hash: {miner.last_mined_block.hash}")
            logger.info(f"Current blockchain height: {self.blockchain.current_height}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        # Close blockchain
        if cls.blockchain:
            cls.blockchain.close()
        
        # Remove blockchain files (optional)
        try:
            import shutil
            chain_dir = config.get_chain_dir(cls.chain_id)
            if chain_dir.exists():
                shutil.rmtree(chain_dir)
        except Exception as e:
            logger.error(f"Error cleaning up test blockchain: {e}")


if __name__ == "__main__":
    # Run with higher verbosity 
    unittest.main(verbosity=2)