"""
Memory Pool (Mempool) for Qbitcoin

This file implements the Mempool class which manages unconfirmed transactions
that are waiting to be included in blocks.
"""

import time
import json
import threading
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
import os
import heapq

# Import local modules
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import config 
from core.transaction import Transaction
from utils.logger import get_logger
from utils.serializer import serialize_transaction, deserialize_transaction

# Initialize logger
logger = get_logger("mempool")

class Mempool:
    """
    Memory Pool for unconfirmed transactions
    
    This class manages pending transactions that haven't yet been included in blocks.
    It provides methods for adding, removing, and querying transactions, as well as
    sorting them by fee to prioritize inclusion in new blocks.
    """
    
    def __init__(self, chain_id: Optional[str] = None):
        """
        Initialize the mempool
        
        Args:
            chain_id: Optional chain ID (for testnet or regtest)
        """
        self.chain_id = chain_id or config.BLOCKCHAIN_ID
        self.chain_dir = config.get_chain_dir(self.chain_id)
        self.mempool_dir = self.chain_dir / "mempool"
        self.mempool_dir.mkdir(exist_ok=True)
        
        # Main mempool storage: tx_hash -> transaction
        self.transactions = {}
        
        # Track transaction metadata
        self.tx_metadata = {}  # tx_hash -> {received_time, fee_per_kb, etc.}
        
        # Track transactions by address for quick lookups
        self.address_tx_index = {}  # address -> set(tx_hash)
        
        # Cache for ancestor/descendant relationships
        self.depends_on = {}  # tx_hash -> set(ancestor_tx_hashes)
        self.dependents = {}  # tx_hash -> set(descendant_tx_hashes)
        
        # Track orphan transactions (those with missing inputs)
        self.orphan_tx = {}  # tx_hash -> transaction
        
        # Track current mempool size in bytes
        self.total_size = 0
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Load persisted mempool
        self._load_mempool()
    
    def _load_mempool(self):
        """Load persisted mempool transactions from disk"""
        try:
            mempool_file = self.mempool_dir / "mempool.dat"
            if not mempool_file.exists():
                return
                
            with self.lock, open(mempool_file, "rb") as f:
                # Read number of transactions
                tx_count_bytes = f.read(4)
                if not tx_count_bytes or len(tx_count_bytes) < 4:
                    return
                    
                tx_count = int.from_bytes(tx_count_bytes, byteorder='little')
                logger.info(f"Loading {tx_count} transactions from mempool.dat")
                
                # Read each transaction
                loaded = 0
                for _ in range(tx_count):
                    try:
                        # Get transaction size
                        tx_size_bytes = f.read(4)
                        if not tx_size_bytes or len(tx_size_bytes) < 4:
                            break
                            
                        tx_size = int.from_bytes(tx_size_bytes, byteorder='little')
                        
                        # Get transaction data
                        tx_data = f.read(tx_size)
                        if not tx_data or len(tx_data) < tx_size:
                            break
                            
                        # Deserialize transaction
                        try:
                            tx_dict = json.loads(tx_data.decode('utf-8'))
                            tx = Transaction.from_dict(tx_dict)
                            
                            # Add to mempool (don't verify again since it was already verified)
                            self._add_transaction_internal(tx)
                            loaded += 1
                        except Exception as e:
                            logger.error(f"Error deserializing transaction: {e}")
                    except Exception as e:
                        logger.error(f"Error loading transaction: {e}")
                
                logger.info(f"Loaded {loaded} transactions into mempool")
        
        except Exception as e:
            logger.error(f"Error loading mempool: {e}")
            # If loading fails, start with an empty mempool
            self.transactions = {}
            self.tx_metadata = {}
            self.address_tx_index = {}
            self.orphan_tx = {}
            self.total_size = 0
    
    def _save_mempool(self):
        """Save mempool transactions to disk"""
        try:
            mempool_file = self.mempool_dir / "mempool.dat"
            
            with self.lock, open(mempool_file, "wb") as f:
                # Write number of transactions
                f.write(len(self.transactions).to_bytes(4, byteorder='little'))
                
                # Write each transaction
                for tx_hash, tx in self.transactions.items():
                    tx_data = json.dumps(tx.to_dict()).encode('utf-8')
                    
                    # Write transaction size
                    f.write(len(tx_data).to_bytes(4, byteorder='little'))
                    
                    # Write transaction data
                    f.write(tx_data)
            
            logger.info(f"Saved {len(self.transactions)} transactions to mempool.dat")
            
        except Exception as e:
            logger.error(f"Error saving mempool: {e}")
    
    def _add_transaction_internal(self, tx: Transaction):
        """
        Add transaction to mempool structures without validation
        
        Args:
            tx: Transaction to add
        """
        tx_hash = tx.hash
        
        # Calculate transaction size
        tx_size = len(json.dumps(tx.to_dict()).encode())
        
        # Add to main transaction storage
        self.transactions[tx_hash] = tx
        
        # Update total size
        self.total_size += tx_size
        
        # Add metadata
        self.tx_metadata[tx_hash] = {
            'received_time': int(time.time()),
            'size': tx_size,
            'fee_per_kb': (tx.fee * 1000) / tx_size if tx_size > 0 else 0,
            'height': -1  # Not in a block yet
        }
        
        # Update address index
        # Add sender addresses from inputs
        for tx_input in tx.inputs:
            address = tx_input.get('address')
            if address:
                if address not in self.address_tx_index:
                    self.address_tx_index[address] = set()
                self.address_tx_index[address].add(tx_hash)
        
        # Add recipient addresses from outputs
        for tx_output in tx.outputs:
            address = tx_output.get('address')
            if address:
                if address not in self.address_tx_index:
                    self.address_tx_index[address] = set()
                self.address_tx_index[address].add(tx_hash)
    
    def add_transaction(self, tx: Transaction, blockchain=None) -> bool:
        """
        Add a transaction to the mempool
        
        Args:
            tx: Transaction to add
            blockchain: Optional reference to blockchain for validation
            
        Returns:
            True if added successfully, False otherwise
        """
        with self.lock:
            tx_hash = tx.hash
            
            # Check if already in mempool
            if tx_hash in self.transactions:
                logger.info(f"Transaction {tx_hash} already in mempool")
                return True
            
            # STRICT VALIDATION CHECKS
            
            # 1. Basic signature verification with public key recovery if needed
            if not tx.public_key and tx.inputs and blockchain:
                # Transaction doesn't have public key. Try to retrieve it from blockchain
                sender_address = None
                for tx_input in tx.inputs:
                    if 'address' in tx_input:
                        sender_address = tx_input['address']
                        break
                
                if sender_address:
                    logger.info(f"Transaction doesn't include public key. Retrieving from blockchain for address: {sender_address}")
                    # Get public key from blockchain
                    public_key = blockchain.get_account_public_key(sender_address)
                    
                    if public_key:
                        logger.info(f"Found public key in blockchain for {sender_address}")
                        # Temporarily set the public key for verification
                        tx.public_key = public_key
                    else:
                        logger.warning(f"No public key found for address: {sender_address}")
                        return False
            
            # 2. Verify signature (with retrieved public key if needed)
            if not tx.verify_signature():
                logger.warning(f"Transaction {tx_hash} failed signature verification")
                return False
            
            # 3. Check for double-spending with transactions already in mempool
            if blockchain:
                for tx_input in tx.inputs:
                    if 'prev_tx' in tx_input and 'output_index' in tx_input:
                        spent_output = f"{tx_input['prev_tx']}:{tx_input['output_index']}"
                        
                        # Check if any existing mempool transaction already spends this output
                        for existing_tx_hash, existing_tx in self.transactions.items():
                            for existing_input in existing_tx.inputs:
                                if ('prev_tx' in existing_input and 'output_index' in existing_input and
                                    f"{existing_input['prev_tx']}:{existing_input['output_index']}" == spent_output):
                                    logger.warning(f"Transaction {tx_hash} attempts to double-spend output {spent_output}")
                                    return False
            
            # 4. Check sender balance to make sure they have enough funds
            if blockchain:
                sender_addresses = set()
                total_spending = {}  # Track spending by address
                
                # Get sender addresses from inputs
                for tx_input in tx.inputs:
                    if 'address' in tx_input:
                        address = tx_input['address']
                        sender_addresses.add(address)
                        if address not in total_spending:
                            total_spending[address] = 0
                
                # For each address, calculate its spending in this transaction
                for address in sender_addresses:
                    # Calculate this transaction amount for this address
                    for tx_input in tx.inputs:
                        if 'address' in tx_input and tx_input['address'] == address:
                            if 'amount' in tx_input:
                                total_spending[address] += tx_input['amount']
                    
                    # Add a proportional share of the fee
                    if len(sender_addresses) > 0:
                        total_spending[address] += tx.fee / len(sender_addresses)
                
                # Now check each address has sufficient balance
                for address, spending in total_spending.items():
                    # Calculate how much this address is spending in mempool already
                    spending_in_mempool = 0
                    for existing_tx_hash, existing_tx in self.transactions.items():
                        for existing_input in existing_tx.inputs:
                            if 'address' in existing_input and existing_input['address'] == address:
                                if 'amount' in existing_input:
                                    spending_in_mempool += existing_input['amount']
                                else:
                                    # If amount not in input, use output total + fee as an estimate
                                    spending_in_mempool += sum(output['amount'] for output in existing_tx.outputs)
                                    spending_in_mempool += existing_tx.fee
                    
                    # Get current balance
                    balance = blockchain.get_balance(address)
                    
                    # Check if balance is sufficient for this tx + existing mempool txs
                    if balance < (spending_in_mempool + spending):
                        logger.warning(f"Insufficient balance for {address}: balance={balance}, "
                                      f"mempool_spending={spending_in_mempool}, tx_spending={spending}")
                        return False
            
            # 5. Full transaction validation (includes more checks)
            if blockchain:
                if not tx.validate(blockchain):
                    logger.warning(f"Transaction {tx_hash} failed validation")
                    return False
            
            # 6. Check mempool size limit
            tx_size = len(json.dumps(tx.to_dict()).encode())
            if self.total_size + tx_size > config.MEMPOOL_MAX_SIZE:
                # If we're at the size limit, remove lowest fee transactions
                if not self._make_room_for_transaction(tx_size, tx.fee):
                    logger.warning(f"Failed to make room for transaction {tx_hash}")
                    return False
            
            # 7. Check minimum transaction fee (if configured)
            if hasattr(config, 'MIN_TRANSACTION_FEE') and tx.fee < config.MIN_TRANSACTION_FEE:
                logger.warning(f"Transaction fee {tx.fee} is below minimum required fee {config.MIN_TRANSACTION_FEE}")
                return False
            
            # If public key was retrieved from blockchain and not needed for future
            # (already exists in blockchain), we can remove it to save space
            if blockchain and tx.public_key:
                sender_address = None
                for tx_input in tx.inputs:
                    if 'address' in tx_input:
                        sender_address = tx_input['address']
                        break
                
                if sender_address:
                    # Keep the public key if this is the first transaction from this address
                    existing_pubkey = blockchain.get_account_public_key(sender_address)
                    if existing_pubkey:
                        logger.info(f"Public key already exists for {sender_address}, removing from transaction to save space")
                        tx.public_key = None
            
            # Add to mempool
            self._add_transaction_internal(tx)
            
            # Log successful addition
            logger.info(f"Added transaction {tx_hash} to mempool (fee: {tx.fee}, size: {tx_size} bytes)")
            
            # Periodically save mempool to disk (could optimize to not save after every tx)
            if len(self.transactions) % 10 == 0:
                self._save_mempool()
                
            return True
    
    def _make_room_for_transaction(self, required_size: int, new_fee: float) -> bool:
        """
        Make room in the mempool by removing lower fee transactions
        
        Args:
            required_size: Required space in bytes
            new_fee: Fee of the new transaction
            
        Returns:
            True if room was made, False otherwise
        """
        # First check if we even need to make room
        if self.total_size + required_size <= config.MEMPOOL_MAX_SIZE:
            return True
        
        # Calculate fee density (satoshis per byte) for the new transaction
        new_fee_per_byte = new_fee / required_size if required_size > 0 else 0
        
        # Get all transactions sorted by fee per byte (lowest first)
        sorted_transactions = sorted(
            self.transactions.items(),
            key=lambda x: self.tx_metadata[x[0]]['fee_per_kb'] / 1000
        )
        
        freed_space = 0
        removed_txs = []
        
        # Remove transactions starting with lowest fee per byte
        for tx_hash, tx in sorted_transactions:
            # Don't remove transactions with higher fees than the new one
            if self.tx_metadata[tx_hash]['fee_per_kb'] / 1000 >= new_fee_per_byte:
                break
                
            freed_space += self.tx_metadata[tx_hash]['size']
            removed_txs.append(tx_hash)
            
            # Stop once we've freed enough space
            if freed_space >= required_size:
                break
        
        # Remove the selected transactions
        for tx_hash in removed_txs:
            self._remove_transaction_internal(tx_hash)
            logger.info(f"Removed low-fee transaction {tx_hash} to make room")
        
        # Check if we freed enough space
        return self.total_size + required_size <= config.MEMPOOL_MAX_SIZE
    
    def _remove_transaction_internal(self, tx_hash: str):
        """
        Remove a transaction from all mempool data structures
        
        Args:
            tx_hash: Hash of transaction to remove
        """
        if tx_hash not in self.transactions:
            return
            
        tx = self.transactions[tx_hash]
        
        # Update total size
        self.total_size -= self.tx_metadata[tx_hash]['size']
        
        # Update address index
        # Remove sender addresses from inputs
        for tx_input in tx.inputs:
            address = tx_input.get('address')
            if address and address in self.address_tx_index:
                self.address_tx_index[address].discard(tx_hash)
                if not self.address_tx_index[address]:
                    del self.address_tx_index[address]
        
        # Remove recipient addresses from outputs
        for tx_output in tx.outputs:
            address = tx_output.get('address')
            if address and address in self.address_tx_index:
                self.address_tx_index[address].discard(tx_hash)
                if not self.address_tx_index[address]:
                    del self.address_tx_index[address]
        
        # Remove from dependency tracking
        if tx_hash in self.depends_on:
            del self.depends_on[tx_hash]
        if tx_hash in self.dependents:
            del self.dependents[tx_hash]
        
        # Remove from main transaction storage
        del self.transactions[tx_hash]
        del self.tx_metadata[tx_hash]
    
    def remove_transaction(self, tx_hash: str) -> bool:
        """
        Remove a transaction from the mempool
        
        Args:
            tx_hash: Hash of transaction to remove
            
        Returns:
            True if removed, False if not found
        """
        with self.lock:
            if tx_hash not in self.transactions:
                return False
                
            self._remove_transaction_internal(tx_hash)
            return True
    
    def get_transaction(self, tx_hash: str) -> Optional[Transaction]:
        """
        Get a transaction from the mempool by hash
        
        Args:
            tx_hash: Hash of transaction to retrieve
            
        Returns:
            Transaction or None if not found
        """
        with self.lock:
            return self.transactions.get(tx_hash)
    
    def get_transactions_by_address(self, address: str) -> List[Transaction]:
        """
        Get all transactions related to an address
        
        Args:
            address: Address to look for
            
        Returns:
            List of transactions involving the address
        """
        with self.lock:
            result = []
            if address in self.address_tx_index:
                for tx_hash in self.address_tx_index[address]:
                    if tx_hash in self.transactions:
                        result.append(self.transactions[tx_hash])
            return result
    
    def get_transactions_for_block(self, max_size: int = None) -> List[Transaction]:
        """
        Get transactions for inclusion in a new block, sorted by fee
        
        Args:
            max_size: Maximum total size in bytes
            
        Returns:
            List of transactions to include in block
        """
        with self.lock:
            # Default max_size to config value if not specified
            if max_size is None:
                max_size = config.MAX_BLOCK_SIZE
                
            # Use a priority queue to sort transactions by fee per KB
            tx_queue = []
            
            # Add all transactions to priority queue (negative fee for max-heap)
            for tx_hash, tx in self.transactions.items():
                fee_per_kb = self.tx_metadata[tx_hash]['fee_per_kb']
                heapq.heappush(tx_queue, (-fee_per_kb, tx_hash))
            
            # Select transactions greedily by fee
            selected = []
            total_selected_size = 0
            
            while tx_queue:
                # Get highest fee transaction
                fee_priority, tx_hash = heapq.heappop(tx_queue)
                
                # Check size
                tx_size = self.tx_metadata[tx_hash]['size']
                
                # Skip if it would exceed block size
                if total_selected_size + tx_size > max_size:
                    continue
                    
                # Add transaction to selected list
                tx = self.transactions[tx_hash]
                selected.append(tx)
                total_selected_size += tx_size
                
                # Stop if we've filled the block
                if total_selected_size >= max_size:
                    break
            
            logger.info(f"Selected {len(selected)} transactions for block, total size: {total_selected_size}")
            return selected
    
    def remove_transactions(self, tx_hashes: List[str]):
        """
        Remove multiple transactions from the mempool
        
        Args:
            tx_hashes: List of transaction hashes to remove
        """
        with self.lock:
            for tx_hash in tx_hashes:
                self._remove_transaction_internal(tx_hash)
            
            # Save mempool after batch removal
            self._save_mempool()
    
    def expire_old_transactions(self):
        """
        Remove transactions that have been in the mempool for too long
        """
        with self.lock:
            current_time = int(time.time())
            expiry_time = current_time - (config.MEMPOOL_EXPIRY * 3600)  # Convert hours to seconds
            
            # Find transactions older than expiry time
            expired = []
            
            for tx_hash, metadata in self.tx_metadata.items():
                if metadata['received_time'] < expiry_time:
                    expired.append(tx_hash)
            
            # Remove expired transactions
            for tx_hash in expired:
                self._remove_transaction_internal(tx_hash)
                logger.info(f"Expired transaction {tx_hash} from mempool")
            
            if expired:
                self._save_mempool()
                logger.info(f"Expired {len(expired)} transactions from mempool")
    
    def remove_expired(self):
        """
        Alias for expire_old_transactions to maintain API compatibility
        
        This method is called by the node's maintenance loop
        """
        return self.expire_old_transactions()
    
    def clear(self):
        """Clear the entire mempool"""
        with self.lock:
            self.transactions = {}
            self.tx_metadata = {}
            self.address_tx_index = {}
            self.depends_on = {}
            self.dependents = {}
            self.orphan_tx = {}
            self.total_size = 0
            
            # Save empty mempool
            self._save_mempool()
            logger.info("Mempool cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current state of the mempool
        
        Returns:
            Dictionary with mempool statistics
        """
        with self.lock:
            # Calculate total fees
            total_fees = sum(tx.fee for tx in self.transactions.values())
            
            # Get average fee per KB
            avg_fee_per_kb = 0
            if self.transactions:
                avg_fee_per_kb = sum(metadata['fee_per_kb'] for metadata in self.tx_metadata.values()) / len(self.tx_metadata)
            
            return {
                'tx_count': len(self.transactions),
                'size_bytes': self.total_size,
                'size_mb': self.total_size / (1024 * 1024),
                'total_fees': total_fees,
                'orphan_tx_count': len(self.orphan_tx),
                'avg_fee_per_kb': avg_fee_per_kb
            }
    
    def get_transaction_count(self) -> int:
        """
        Get the number of transactions in the mempool
        
        Returns:
            Number of transactions in the mempool
        """
        with self.lock:
            return len(self.transactions)
    
    def get_size_bytes(self) -> int:
        """
        Get the total size of all transactions in the mempool in bytes
        
        Returns:
            Total size in bytes
        """
        with self.lock:
            return self.total_size
            
    def get_transactions(self, limit: int = 100) -> list:
        """
        Get transactions from the mempool
        
        Args:
            limit: Maximum number of transactions to return
            
        Returns:
            List of transaction dictionaries
        """
        with self.lock:
            result = []
            count = 0
            
            # Sort transactions by fee (highest first)
            sorted_txs = sorted(
                self.transactions.items(),
                key=lambda x: self.tx_metadata[x[0]]['fee_per_kb'],
                reverse=True
            )
            
            for tx_hash, tx in sorted_txs:
                if count >= limit:
                    break
                    
                result.append(tx.to_dict())
                count += 1
                
            return result
    
    def __str__(self) -> str:
        """String representation of mempool"""
        stats = self.get_stats()
        return (f"Mempool Statistics:\n"
                f"Transactions: {stats['tx_count']}\n"
                f"Size: {stats['size_mb']:.2f} MB\n"
                f"Total Fees: {stats['total_fees']} {config.BLOCKCHAIN_TICKER}\n"
                f"Avg Fee/KB: {stats['avg_fee_per_kb']:.8f} {config.BLOCKCHAIN_TICKER}")
    
    def close(self):
        """Save mempool and release resources"""
        with self.lock:
            self._save_mempool()
            logger.info("Mempool closed")
    
    def remove_confirmed_transactions(self, block) -> int:
        """
        Remove transactions that have been confirmed in a block from the mempool
        
        Args:
            block: Block object containing confirmed transactions
            
        Returns:
            Number of transactions removed
        """
        with self.lock:
            removed_count = 0
            tx_hashes_to_remove = set()  # Using a set to avoid duplicates
            spent_outputs = set()  # Track outputs spent in this block
            affected_addresses = set()  # Track addresses to check for conflicts
            
            # Extract transaction hashes and metadata from the block
            for tx in block.transactions:
                # Extract transaction hash correctly based on type
                if hasattr(tx, 'hash'):
                    tx_hash = tx.hash
                    tx_obj = tx
                elif isinstance(tx, dict) and 'hash' in tx:
                    tx_hash = tx['hash']
                    try:
                        # For received blocks, don't validate the hash to avoid mismatches
                        tx_obj = Transaction.from_dict(tx) if 'inputs' in tx else None
                    except Exception as e:
                        logger.warning(f"Error processing transaction from block: {e}")
                        tx_obj = None
                else:
                    # Try to convert to dict if it has to_dict method
                    if hasattr(tx, 'to_dict'):
                        tx_dict = tx.to_dict()
                        tx_hash = tx_dict.get('hash', '')
                        tx_obj = tx
                    else:
                        continue
                
                # Skip coinbase transactions (they're not in the mempool)
                if not getattr(tx_obj, 'inputs', None) and not (isinstance(tx, dict) and tx.get('inputs')):
                    continue
                    
                # Add this transaction to removal list if in mempool
                if tx_hash in self.transactions:
                    tx_hashes_to_remove.add(tx_hash)
                
                # Track all inputs (spent outputs) to detect conflicts
                if hasattr(tx_obj, 'inputs'):
                    for tx_input in tx_obj.inputs:
                        if isinstance(tx_input, dict) and 'prev_tx' in tx_input and 'output_index' in tx_input:
                            # Format: prev_tx:output_index
                            spent_output = f"{tx_input['prev_tx']}:{tx_input['output_index']}"
                            spent_outputs.add(spent_output)
                        
                        # Track affected addresses
                        if isinstance(tx_input, dict) and 'address' in tx_input:
                            affected_addresses.add(tx_input['address'])
            
            # Now remove the confirmed transactions
            for tx_hash in tx_hashes_to_remove:
                self._remove_transaction_internal(tx_hash)
                removed_count += 1
            
            # Find and remove any conflicting transactions (double-spends)
            conflicting_txs = set()
            
            # Method 1: Check for transactions that spend the same outputs
            for tx_hash, tx in list(self.transactions.items()):
                if tx_hash in tx_hashes_to_remove:
                    continue  # Already removed
                
                # Check if this transaction spends any output that was spent in the block
                for tx_input in tx.inputs:
                    if isinstance(tx_input, dict) and 'prev_tx' in tx_input and 'output_index' in tx_input:
                        spend_check = f"{tx_input['prev_tx']}:{tx_input['output_index']}"
                        if spend_check in spent_outputs:
                            conflicting_txs.add(tx_hash)
                            break
            
            # Method 2: Check for transactions from the same addresses
            # (they might have different balances now after the block is processed)
            for address in affected_addresses:
                if address in self.address_tx_index:
                    for tx_hash in self.address_tx_index[address]:
                        if tx_hash not in tx_hashes_to_remove and tx_hash in self.transactions:
                            conflicting_txs.add(tx_hash)
            
            # Remove all conflicting transactions
            conflict_count = 0
            for tx_hash in conflicting_txs:
                if tx_hash in self.transactions:  # Double-check it's still there
                    self._remove_transaction_internal(tx_hash)
                    conflict_count += 1
            
            total_removed = removed_count + conflict_count
            if total_removed > 0:
                logger.info(f"Removed {removed_count} confirmed and {conflict_count} conflicting transactions from mempool (block {block.height})")
                # Save mempool state after removing transactions
                self._save_mempool()
                
            return total_removed

    def has_transaction(self, tx_hash: str) -> bool:
        """
        Check if a transaction exists in the mempool
        
        Args:
            tx_hash: Transaction hash to check
            
        Returns:
            True if transaction exists in mempool, False otherwise
        """
        with self.lock:
            return tx_hash in self.transactions