"""
Blockchain implementation for Qbitcoin

This file implements the core Blockchain class which manages the chain of blocks,
validates transactions, and tracks the state of accounts in the network.
"""

import time
import json
import os
import shutil
import traceback
from typing import List, Dict, Any, Optional
from pathlib import Path
import threading

# Import local modules
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from core.block import Block
from core.chain_manager import ChainManager
from core.storage.database import AccountDatabase
from core.consensus.difficulty_adjuster import adjust_difficulty
from utils.logger import get_logger

# Initialize logger
logger = get_logger("blockchain")

class Blockchain:
    """
    Main blockchain implementation for Qbitcoin
    
    This class manages the blockchain data structure and provides methods
    for adding blocks, validating transactions, and querying the chain.
    """
    
    def __init__(self, chain_id: Optional[str] = None):
        """
        Initialize the blockchain
        
        Args:
            chain_id: Optional chain ID (for testnet or regtest)
        """
        self.chain_id = chain_id or config.BLOCKCHAIN_ID
        self.chain_dir = config.get_chain_dir(self.chain_id)
        
        # Initialize the chain manager for block storage
        self.chain_manager = ChainManager(chain_id)
        
        # Initialize the account database
        self.account_db = AccountDatabase(chain_id)
        
        # In-memory cache of recent blocks for faster access
        self.blocks_cache = {}  # hash -> Block
        self.max_cache_size = 1000  # Maximum number of blocks to keep in memory
        
        # Cache to prevent repeated log warnings for the same block
        self.not_found_cache = set()  # Set of block hashes we know don't exist
        self.not_found_cache_max = 100  # Limit size to prevent memory leaks
        
        # Current blockchain state
        self.current_height = -1
        self.best_hash = ""
        self.lock = threading.RLock()  # For thread safety
        
        # Initialize blockchain state
        self._initialize_blockchain()
        
    def _initialize_blockchain(self):
        """Initialize the blockchain state"""
        with self.lock:
            # Check if blockchain exists
            if not self._blockchain_exists():
                logger.info("No existing blockchain found")
                
                # Check if bootstrap nodes are defined
                # If bootstrap nodes exist, we should get the genesis block from peers
                # instead of creating it ourselves
                if config.BOOTSTRAP_NODES and len(config.BOOTSTRAP_NODES) > 0:
                    logger.info("Bootstrap nodes are defined. Genesis block will be obtained from peers.")
                    # Set the initial state to indicate we need to sync
                    self.current_height = -1
                    self.best_hash = ""
                else:
                    logger.info("No bootstrap nodes defined. Creating and mining genesis block locally.")
                    self._create_genesis()
            else:
                logger.info("Loading existing blockchain")
                self._load_blockchain_state()
                
                # Check if database is in sync with blockchain
                self._sync_account_database()
    
    def _blockchain_exists(self) -> bool:
        """Check if blockchain data exists"""
        # Check for state file
        state_file = self.chain_dir / "chainstate.json"
        return state_file.exists()
    
    def _create_genesis(self):
        """Create the genesis block and initial blockchain state"""
        logger.info("Creating genesis block from yaml configuration")
        
        # Create genesis block using the yaml-based implementation
        genesis_block = Block.create_genesis_block()
        
        # Process genesis block transactions to establish initial balances
        self._process_block_transactions(genesis_block)
        
        # Save genesis block using chain manager
        if not self.chain_manager.store_block(genesis_block):
            logger.error("Failed to store genesis block")
            raise Exception("Genesis block creation failed")
        
        # Update blockchain state with the actual mined genesis block values
        self.current_height = 0
        self.best_hash = genesis_block.hash
        
        # Save blockchain state
        self._save_blockchain_state()
        
        logger.info(f"Genesis block created with hash: {genesis_block.hash}")
        logger.info(f"Genesis merkle root: {genesis_block.merkle_root}")
        logger.info(f"Genesis timestamp: {genesis_block.timestamp}")
    
    def _load_blockchain_state(self):
        """Load the current blockchain state from disk"""
        state_file = self.chain_dir / "chainstate.json"
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
                
            self.current_height = state['height']
            self.best_hash = state['best_hash']
            
            # Load best block into cache
            best_block = self._load_block(self.best_hash)
            
            # If we couldn't load the best block but we have a hash,
            # this is likely a corrupted state or the block file is missing
            if not best_block and self.best_hash:
                logger.warning(f"Could not load best block {self.best_hash}. Creating genesis block.")
                self._create_genesis()
                return
            
            logger.info(f"Blockchain loaded at height {self.current_height}, hash: {self.best_hash}")
        
        except Exception as e:
            logger.error(f"Error loading blockchain state: {e}")
            # Fallback to genesis if state loading fails
            self._create_genesis()
    
    def _sync_account_database(self):
        """Ensure account database is in sync with blockchain"""
        # Check latest processed block in the database
        latest_block = self.account_db.get_last_processed_block()
        
        if not latest_block:
            logger.info("Account database is empty, rebuilding from blockchain...")
            self.account_db.rebuild_from_blocks(self)
            return
            
        if latest_block < self.current_height:
            logger.info(f"Account database needs sync from height {latest_block + 1} to {self.current_height}")
            
            # Process missing blocks
            for height in range(latest_block + 1, self.current_height + 1):
                block = self.get_block_by_height(height)
                if block:
                    logger.info(f"Syncing block {height} to account database")
                    if not self.account_db.process_block(block, self):
                        logger.error(f"Failed to process block {height} in account database")
                        break
                else:
                    logger.error(f"Missing block at height {height}")
                    break
        else:
            logger.info("Account database is in sync with blockchain")
    
    def _save_blockchain_state(self):
        """Save the current blockchain state to disk"""
        state_file = self.chain_dir / "chainstate.json"
        state = {
            'height': self.current_height,
            'best_hash': self.best_hash,
            'timestamp': int(time.time()),
            'version': config.VERSION,
            'chain_id': self.chain_id
        }
        
        # Write the state to disk atomically
        temp_file = self.chain_dir / f"chainstate.tmp.{int(time.time())}"
        with open(temp_file, 'w') as f:
            json.dump(state, f, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk
            
        # Rename temp file to actual state file (atomic operation)
        shutil.move(temp_file, state_file)
        
        logger.debug(f"Blockchain state saved: height={self.current_height}, hash={self.best_hash}")
    
    def _load_block(self, block_hash: str) -> Optional[Block]:
        """
        Load a block from disk or cache
        
        Args:
            block_hash: The hash of the block to load
            
        Returns:
            Block object or None if not found
        """
        # Check cache first
        if block_hash in self.blocks_cache:
            return self.blocks_cache[block_hash]
            
        # Check if we already know this block doesn't exist
        if block_hash in self.not_found_cache:
            return None
            
        # Use chain manager to fetch the block
        block = self.chain_manager.get_block(block_hash)
        if block:
            # Add to cache
            self.blocks_cache[block_hash] = block
            return block
        
        # Add to not found cache to avoid repeated warnings
        if len(self.not_found_cache) >= self.not_found_cache_max:
            self.not_found_cache.clear()  # Clear cache if it gets too large
        self.not_found_cache.add(block_hash)
        
        logger.warning(f"Block not found: {block_hash}")
        return None
    
    def _process_block_transactions(self, block: Block) -> bool:
        """
        Process all transactions in a block, updating account states
        
        Args:
            block: The block containing transactions to process
            
        Returns:
            True if all transactions are valid and processed
        """
        # Instead of processing transactions manually, we now use the account database
        return self.account_db.process_block(block, self)
    
    def add_block(self, block: Block) -> bool:
        """
        Add a new block to the blockchain
        
        Args:
            block: The block to add
            
        Returns:
            True if block is valid and added, False otherwise
        """
        with self.lock:
            # Check if block already exists
            if self.chain_manager.has_block(block.hash):
                logger.info(f"Block {block.hash} already exists")
                return True
                
            # Basic validation
            if not block.validate():
                logger.error(f"Block {block.hash} failed validation")
                return False
                
            # Check if block connects to the chain
            if block.height == 0:
                # Genesis block special handling
                if self.current_height >= 0:
                    logger.error("Genesis block rejected - blockchain already initialized")
                    return False
                # For genesis blocks, don't perform additional parent checks
                # But verify that it has a proper proof of work and valid transactions
                logger.info(f"Adding genesis block with hash {block.hash}")
            else:
                # Regular block - must connect to parent
                parent = self._load_block(block.prev_hash)
                if not parent:
                    logger.error(f"Parent block {block.prev_hash} not found")
                    return False
                    
                # Check height continuity
                if block.height != parent.height + 1:
                    logger.error(f"Block height discontinuity: expected {parent.height + 1}, got {block.height}")
                    return False
                    
                # Check if timestamp is valid
                if block.timestamp <= parent.timestamp:
                    logger.error(f"Block timestamp invalid: <= parent timestamp")
                    return False
                
                # Check difficulty adjustments
                if block.height > 0 and block.height % config.DIFFICULTY_ADJUSTMENT_BLOCKS == 0:
                    # For adjustment blocks, calculate expected difficulty based on past blocks
                    expected_difficulty = self.calculate_next_difficulty(log_info=True)
                    if block.difficulty != expected_difficulty:
                        logger.error(f"Invalid difficulty: expected {expected_difficulty}, got {block.difficulty}")
                        return False
                else:
                    # Ensure difficulty matches the minimum required difficulty
                    if block.difficulty < config.MINIMUM_DIFFICULTY:
                        logger.error(f"Block difficulty {block.difficulty} below minimum {config.MINIMUM_DIFFICULTY}")
                        return False
                    
                    # Normal difficulty validation - must match parent outside adjustment periods
                    if block.difficulty != parent.difficulty:
                        logger.error(f"Invalid difficulty: does not match parent block")
                        return False
            
            # Process and validate all transactions
            if not self._process_block_transactions(block):
                logger.error(f"Failed to process transactions in block {block.hash}")
                return False
                
            # Save block using chain manager
            if not self.chain_manager.store_block(block):
                logger.error(f"Failed to store block {block.hash}")
                return False
                
            # Update blockchain state
            self.current_height = block.height
            self.best_hash = block.hash
            self._save_blockchain_state()
            
            # Remove confirmed transactions from mempool if it's available
            try:
                # Directly access mempool if available
                mempool = None
                # First try to find mempool through node reference
                if hasattr(self, 'node') and self.node and hasattr(self.node, 'mempool') and self.node.mempool:
                    mempool = self.node.mempool
                    logger.info(f"Using node.mempool for transaction cleanup, containing {mempool.get_transaction_count()} transactions")
                # Then try direct mempool reference
                elif hasattr(self, 'mempool') and self.mempool:
                    mempool = self.mempool
                    logger.info(f"Using direct mempool reference for transaction cleanup, containing {mempool.get_transaction_count()} transactions")
                
                if mempool:
                    # Get the transaction count before removal for logging
                    before_count = mempool.get_transaction_count()
                    
                    try:
                        # Remove confirmed transactions
                        removed_count = mempool.remove_confirmed_transactions(block)
                        
                        # Log the results
                        after_count = mempool.get_transaction_count()
                        logger.info(f"Removed {removed_count} transactions from mempool after adding block {block.height}")
                        logger.info(f"Mempool count: before={before_count}, after={after_count}, difference={before_count-after_count}")
                    except Exception as tx_e:
                        logger.warning(f"Error in mempool transaction removal: {tx_e}")
                        # Continue processing the block even if mempool cleanup fails
                else:
                    logger.warning(f"No mempool instance available to clean confirmed transactions for block {block.height}")
            except Exception as e:
                logger.warning(f"Error removing confirmed transactions from mempool: {e}")
                logger.warning(f"Traceback: {traceback.format_exc()}")
            
            # Check if we need to update the blockchain reference in node components
            if hasattr(self, 'node') and self.node:
                # Make sure all components have access to the current blockchain
                if hasattr(self.node, 'p2p_network') and self.node.p2p_network:
                    self.node.p2p_network.blockchain = self
                if hasattr(self.node, 'synchronizer') and self.node.synchronizer:
                    self.node.synchronizer.blockchain = self
                if hasattr(self.node, 'miner') and self.node.miner:
                    self.node.miner.blockchain = self
            
            logger.info(f"Added block {block.height} with hash {block.hash}")
            return True
    
    def get_account_info(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Get account information for an address
        
        Args:
            address: The account address to query
            
        Returns:
            Account information or None if not found
        """
        return self.account_db.get_account(address)
    
    def get_balance(self, address: str) -> float:
        """
        Get the balance of an address
        
        Args:
            address: The account address to query
            
        Returns:
            Account balance or 0 if account not found
        """
        return self.account_db.get_balance(address)
    
    def get_transactions(self, address: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get transaction history for an address
        
        Args:
            address: The account address to query
            limit: Maximum number of transactions to return
            offset: Offset for pagination
            
        Returns:
            List of transactions
        """
        return self.account_db.get_transactions(address, limit, offset)
    
    def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """
        Get a block by its hash
        
        Args:
            block_hash: The hash of the block to retrieve
            
        Returns:
            Block object or None if not found
        """
        return self._load_block(block_hash)
    
    def get_block_by_height(self, height: int) -> Optional[Block]:
        """
        Get a block by its height
        
        Args:
            height: The height of the block to retrieve
            
        Returns:
            Block object or None if not found
        """
        # Check if it's the best block
        if height == self.current_height:
            return self._load_block(self.best_hash)
            
        # Use chain manager to get block by height
        block_hash = self.chain_manager.get_block_hash_by_height(height)
        if block_hash:
            return self._load_block(block_hash)
        
        logger.warning(f"Block at height {height} not found")
        return None
    
    def get_blocks_in_range(self, start_height: int, end_height: int) -> List[Block]:
        """
        Get a list of blocks within a height range
        
        Args:
            start_height: Starting height (inclusive)
            end_height: Ending height (inclusive)
            
        Returns:
            List of Block objects
        """
        blocks = []
        # Use chain manager to scan blocks
        block_hashes = self.chain_manager.scan_blocks(start_height)
        
        for height in range(start_height, end_height + 1):
            if height in block_hashes:
                block = self._load_block(block_hashes[height])
                if block:
                    blocks.append(block)
        return blocks
    
    def get_input_amount(self, tx_input: Dict[str, Any]) -> Optional[float]:
        """
        Get the input amount for a transaction input
        This is used for transaction validation in an account-based model
        
        Args:
            tx_input: Transaction input dictionary
            
        Returns:
            Input amount or None if invalid
        """
        address = tx_input.get('address')
        if not address:
            return None
            
        # In an account-based model, we validate that the address has sufficient funds
        balance = self.get_balance(address)
        input_amount = tx_input.get('amount', 0)
        
        if balance < input_amount:
            return None
        
        return input_amount
    
    def calculate_next_difficulty(self, log_info: bool = True) -> float:
        """
        Calculate the next difficulty target for block mining
        
        Args:
            log_info: Whether to log information about the difficulty calculation
            
        Returns:
            The difficulty target for the next block
        """
        # Only adjust difficulty at specified intervals
        if self.current_height % config.DIFFICULTY_ADJUSTMENT_BLOCKS != 0:
            # Get the current difficulty
            current_block = self._load_block(self.best_hash)
            if log_info:
                logger.info(f"Not at adjustment block, using current difficulty: {current_block.difficulty if current_block else config.INITIAL_DIFFICULTY}")
            return current_block.difficulty if current_block else config.INITIAL_DIFFICULTY
        
        # Get adjustment start block and current block
        adjustment_start_height = max(0, self.current_height - config.DIFFICULTY_ADJUSTMENT_BLOCKS)
        start_block = self.get_block_by_height(adjustment_start_height)
        end_block = self._load_block(self.best_hash)
        
        if not start_block or not end_block:
            if log_info:
                logger.warning("Could not load start or end block for difficulty adjustment, using initial difficulty")
            return config.INITIAL_DIFFICULTY
            
        # Calculate the actual time taken for these blocks
        actual_timespan = end_block.timestamp - start_block.timestamp
        expected_timespan = config.DIFFICULTY_ADJUSTMENT_TIMESPAN
        
        if log_info:
            logger.info(f"Difficulty adjustment - Start block: {adjustment_start_height}, End block: {self.current_height}")
            logger.info(f"Actual timespan: {actual_timespan}s, Expected: {expected_timespan}s")
        
        # Calculate new difficulty using difficulty adjuster module
        new_difficulty = adjust_difficulty(
            prev_difficulty=end_block.difficulty,
            actual_timespan=actual_timespan,
            expected_timespan=expected_timespan,
            min_difficulty=config.MINIMUM_DIFFICULTY,
            log_info=log_info
        )
        
        if log_info:
            logger.info(f"Adjusted difficulty from {end_block.difficulty:.8f} to {new_difficulty:.8f}")
        return new_difficulty
    
    def get_best_block(self) -> Optional[Block]:
        """
        Get the current best (tip) block
        
        Returns:
            The best block object
        """
        return self._load_block(self.best_hash)
    
    def validate_chain(self, max_blocks: int = 1000) -> bool:
        """
        Validate the blockchain integrity
        
        Args:
            max_blocks: Maximum number of blocks to check (0 for all)
            
        Returns:
            True if valid, False otherwise
        """
        with self.lock:
            current_hash = self.best_hash
            blocks_checked = 0
            
            while current_hash and current_hash != config.GENESIS_PREVIOUS_HASH:
                block = self._load_block(current_hash)
                if not block:
                    logger.error(f"Block {current_hash} not found during validation")
                    return False
                
                # Validate block
                if not block.validate():
                    logger.error(f"Block {current_hash} failed validation")
                    return False
                
                # Move to previous block
                current_hash = block.prev_hash
                blocks_checked += 1
                
                # Check limit
                if max_blocks > 0 and blocks_checked >= max_blocks:
                    break
            
            return True
    
    def rebuild_account_state(self) -> bool:
        """
        Rebuild the account state from scratch by replaying all transactions
        
        Returns:
            True if successful, False otherwise
        """
        return self.account_db.rebuild_from_blocks(self)
    
    def get_account_count(self) -> int:
        """
        Get the total number of accounts in the blockchain
        
        Returns:
            Number of accounts
        """
        return self.account_db.get_account_count()
    
    def get_total_supply(self) -> float:
        """
        Get the total supply of coins (sum of all balances)
        
        Returns:
            Total supply
        """
        return self.account_db.get_total_supply()
    
    def export_blockchain(self, output_dir: Path) -> bool:
        """
        Export the entire blockchain data to a directory
        
        Args:
            output_dir: Directory to export blockchain data to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Get chain stats
            chain_stats = self.chain_manager.get_chain_stats()
            
            # Export stats to JSON
            with open(output_dir / "chain_stats.json", 'w') as f:
                json.dump(chain_stats, f, indent=2)
                
            # Export state file
            state_file = self.chain_dir / "chainstate.json"
            if state_file.exists():
                shutil.copy2(state_file, output_dir / "chainstate.json")
            
            # Export account database
            self.account_db.export_to_json(output_dir / "accounts.json")
                
            logger.info(f"Blockchain exported to {output_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting blockchain: {e}")
            return False
    
    def import_blockchain(self, input_dir: Path) -> bool:
        """
        Import blockchain data from a directory
        
        Args:
            input_dir: Directory containing exported blockchain data
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                # Check if input directory exists
                if not input_dir.exists() or not input_dir.is_dir():
                    logger.error(f"Import directory {input_dir} does not exist")
                    return False
                
                # Check for required files
                state_file = input_dir / "chainstate.json"
                if not state_file.exists():
                    logger.error(f"Chain state file not found in {input_dir}")
                    return False
                
                # Back up current chain data
                backup_dir = self.chain_dir.with_suffix(f".bak_{int(time.time())}")
                if self.chain_dir.exists():
                    shutil.copytree(self.chain_dir, backup_dir)
                    logger.info(f"Current blockchain data backed up to {backup_dir}")
                
                # Import state file
                if state_file.exists():
                    shutil.copy2(state_file, self.chain_dir / "chainstate.json")
                
                # Import account database
                accounts_file = input_dir / "accounts.json"
                if accounts_file.exists():
                    self.account_db.import_from_json(accounts_file)
                
                # Rebuild chain index
                self.chain_manager.rebuild_index()
                
                # Reload blockchain state
                self.blocks_cache = {}
                self._load_blockchain_state()
                
                logger.info(f"Blockchain imported successfully from {input_dir}")
                return True
                
            except Exception as e:
                logger.error(f"Error importing blockchain: {e}")
                return False
    
    def close(self):
        """Close blockchain resources"""
        self.chain_manager.close()
        self.account_db.close()
    
    def get_chain_work(self) -> float:
        """
        Calculate and return the total chain work (cumulative difficulty of all blocks)
        
        The chain work is a measure of the total computational effort that has gone into 
        the blockchain, calculated as a sum of the work represented by the difficulty of each block.
        
        Returns:
            Total chain work as a float
        """
        with self.lock:
            try:
                total_work = 0.0
                best_block = self.get_best_block()
                
                # If no blocks, return 0
                if not best_block:
                    return total_work
                
                # For efficiency, we'll calculate work for the last 1000 blocks
                # which is a reasonable approximation for display purposes
                max_blocks = 1000
                blocks_calculated = 0
                current_hash = self.best_hash
                
                while current_hash and blocks_calculated < max_blocks:
                    block = self._load_block(current_hash)
                    if not block:
                        break
                        
                    # Work for a block is proportional to 2^difficulty
                    # This is a simplified calculation for display purposes
                    block_work = 2**block.difficulty
                    total_work += block_work
                    
                    # Move to previous block
                    current_hash = block.prev_hash
                    blocks_calculated += 1
                
                # Extrapolate work for remaining blocks
                if blocks_calculated == max_blocks and self.current_height > max_blocks:
                    avg_work_per_block = total_work / blocks_calculated
                    remaining_blocks = self.current_height - blocks_calculated
                    total_work += avg_work_per_block * remaining_blocks
                
                return total_work
                
            except Exception as e:
                logger.error(f"Error calculating chain work: {e}")
                return 0.0
    
    def get_next_block_difficulty(self, log_info: bool = False) -> float:
        """
        Get the difficulty target for the next block
        
        Args:
            log_info: Whether to log information about the difficulty calculation
            
        Returns:
            The difficulty target for the next block
        """
        # Calculate the height of the next block
        next_height = self.current_height + 1
        
        # Check if the next block is a difficulty adjustment block
        if next_height > 0 and next_height % config.DIFFICULTY_ADJUSTMENT_BLOCKS == 0:
            if log_info:
                logger.info(f"Next block {next_height} is a difficulty adjustment block")
            new_difficulty = self.calculate_next_difficulty(log_info=log_info)
            if log_info:
                logger.info(f"Calculated new difficulty: {new_difficulty:.8f}")
            return new_difficulty
        
        # Use current difficulty for non-adjustment blocks
        current_block = self.get_best_block()
        current_difficulty = current_block.difficulty if current_block else config.INITIAL_DIFFICULTY
        if log_info:
            logger.info(f"Using current difficulty: {current_difficulty:.8f} for block {next_height}")
        return current_difficulty
    
    def __str__(self) -> str:
        """String representation of the blockchain"""
        best_block = self.get_best_block()
        accounts_count = self.get_account_count()
        total_supply = self.get_total_supply()
        last_update = "never"
        
        if best_block:
            last_update = time.strftime(
                "%Y-%m-%d %H:%M:%S", 
                time.localtime(best_block.timestamp)
            )
        
        return (f"{config.BLOCKCHAIN_NAME} ({self.chain_id})\n"
                f"Height: {self.current_height}\n"
                f"Best hash: {self.best_hash[:10]}...\n"
                f"Accounts: {accounts_count}\n"
                f"Total Supply: {total_supply} {config.BLOCKCHAIN_TICKER}\n"
                f"Last update: {last_update}")
    
    def get_transaction_history(self, address: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get full transaction history for an address with all details

        Args:
            address: The account address to query
            limit: Maximum number of transactions to return
            offset: Offset for pagination
            
        Returns:
            List of detailed transaction dictionaries
        """
        # First, get the blocks that contain transactions for this address
        block_numbers = self.account_db.get_transaction_blocks(address, limit=limit, offset=offset)
        
        if not block_numbers:
            return []
            
        transactions = []
        
        # For each block, extract transactions involving this address
        for block_number in block_numbers:
            block = self.get_block_by_height(block_number)
            if not block:
                continue
                
            for tx in block.transactions:
                # Convert to dictionary if needed
                tx_dict = tx.to_dict() if hasattr(tx, 'to_dict') else tx
                tx_hash = tx_dict.get('hash', '')
                
                # Check if this transaction involves this address
                is_sender = False
                is_receiver = False
                
                for tx_input in tx_dict.get('inputs', []):
                    if tx_input.get('address') == address:
                        is_sender = True
                        break
                        
                for tx_output in tx_dict.get('outputs', []):
                    if tx_output.get('address') == address:
                        is_receiver = True
                        break
                
                # Skip if not involved
                if not is_sender and not is_receiver:
                    continue
                    
                # Add block info to transaction
                tx_dict['block_height'] = block.height
                tx_dict['block_hash'] = block.hash
                tx_dict['confirmation_time'] = block.timestamp
                
                # Calculate net transaction value for this address
                sent_amount = 0
                received_amount = 0
                
                if is_sender:
                    for tx_input in tx_dict.get('inputs', []):
                        if tx_input.get('address') == address:
                            sent_amount += tx_input.get('amount', 0)
                
                if is_receiver:
                    for tx_output in tx_dict.get('outputs', []):
                        if tx_output.get('address') == address:
                            received_amount += tx_output.get('amount', 0)
                
                # Add transaction direction and net value
                if is_sender and is_receiver:
                    tx_dict['direction'] = 'self'
                elif is_sender:
                    tx_dict['direction'] = 'outgoing'
                else:
                    tx_dict['direction'] = 'incoming'
                    
                tx_dict['net_value'] = received_amount - sent_amount
                tx_dict['sent_amount'] = sent_amount
                tx_dict['received_amount'] = received_amount
                
                # Add to result list
                transactions.append(tx_dict)
                
                # Break if we've reached the limit
                if len(transactions) >= limit:
                    break
                    
            # Break if we've reached the limit
            if len(transactions) >= limit:
                break
                    
        # Sort transactions by block height descending (newest first)
        transactions.sort(key=lambda x: x.get('block_height', 0), reverse=True)
        
        return transactions
    
    def get_account_public_key(self, address: str) -> Optional[str]:
        """
        Get the public key for an account from the database
        
        Args:
            address: Account address
            
        Returns:
            Public key or None if not found
        """
        # Delegate to the account database's get_account_public_key method
        if self.account_db:
            return self.account_db.get_account_public_key(address, self)
        return None