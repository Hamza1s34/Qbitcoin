"""
Account Database implementation for Qbitcoin - Ultra-Compact Version

This module provides SQLite3-based storage for account data with minimal storage:
- Account balances only
- Block references for public keys and transactions
"""

import os
import sqlite3
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import threading

# Import configuration
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from core import config 
from utils.logger import get_logger

# Initialize logger
logger = get_logger("account_db")

class AccountDatabase:
    """
    SQLite3 database for storing minimal account information
    
    This class manages ultra-compact storage of account data:
    - Balances
    - Block number references only
    """
    
    def __init__(self, chain_id: Optional[str] = None):
        """
        Initialize the account database
        
        Args:
            chain_id: Optional chain ID for different networks
        """
        self.chain_id = chain_id or config.BLOCKCHAIN_ID
        self.db_dir = config.DATA_DIR / "database"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.db_dir / f"{self.chain_id}_accounts.db"
        self.lock = threading.RLock()
        self.connection = None
        self._initialize_database()
        
    def _initialize_database(self):
        """Initialize the database and create necessary tables if they don't exist"""
        with self.lock:
            try:
                logger.info(f"Initializing minimal account database at {self.db_path}")
                self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
                
                # Enable foreign keys
                self.connection.execute("PRAGMA foreign_keys = ON")
                # Create tables if they don't exist
                self._create_tables()
                logger.info("Account database initialized successfully")
            except sqlite3.Error as e:
                logger.error(f"Database initialization error: {e}")
                raise
                
    def _create_tables(self):
        """Create minimal tables for the database"""
        with self.lock:
            cursor = self.connection.cursor()
            
            # Create accounts table with only essential fields
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                address TEXT PRIMARY KEY,
                balance REAL NOT NULL DEFAULT 0,
                pubkey_block INTEGER,
                tx_count INTEGER NOT NULL DEFAULT 0
            )
            ''')
            
            # Create transaction block reference table (just block numbers)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tx_blocks (
                address TEXT NOT NULL,
                block_num INTEGER NOT NULL,
                PRIMARY KEY (address, block_num)
            )
            ''')
            
            # Create index on tx_blocks
            cursor.execute('CREATE INDEX IF NOT EXISTS tx_block_idx ON tx_blocks(block_num)')
            
            # Create last processed block tracking - only height needed
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS last_block (
                height INTEGER PRIMARY KEY
            )
            ''')
            
            # Commit changes
            self.connection.commit()
    
    def account_exists(self, address: str) -> bool:
        """
        Check if an account exists in the database
        
        Args:
            address: Account address to check
            
        Returns:
            True if account exists, False otherwise
        """
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1 FROM accounts WHERE address = ?", (address,))
            return cursor.fetchone() is not None
    
    def get_account(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Get account information
        
        Args:
            address: Account address to retrieve
            
        Returns:
            Account information or None if not found
        """
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT address, balance, pubkey_block, tx_count 
                FROM accounts 
                WHERE address = ?
            """, (address,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            # Basic account info    
            account = {
                'address': result[0],
                'balance': result[1],
                'pubkey_block': result[2],
                'tx_count': result[3]
            }
                
            return account
    
    def get_balance(self, address: str) -> float:
        """
        Get account balance
        
        Args:
            address: Account address
            
        Returns:
            Account balance or 0 if account doesn't exist
        """
        account = self.get_account(address)
        return account['balance'] if account else 0
    
    def get_account_public_key(self, address: str, blockchain=None) -> Optional[str]:
        """
        Get the public key for an account, fetching from blockchain if necessary
        
        Args:
            address: Account address
            blockchain: Blockchain instance to fetch block data if needed
            
        Returns:
            Public key or None if not found
        """
        with self.lock:
            account = self.get_account(address)
            if not account or not account.get('pubkey_block'):
                return None
                
            # We need to fetch the public key from the blockchain
            if blockchain:
                block_height = account['pubkey_block']
                block = blockchain.get_block_by_height(block_height)
                
                if block:
                    # Find transaction with this address as sender
                    for tx in block.transactions:
                        # Handle both Transaction objects and dictionaries
                        tx_dict = tx.to_dict() if hasattr(tx, 'to_dict') else tx
                        
                        # Check if any inputs have this address
                        for input_data in tx_dict.get('inputs', []):
                            if input_data.get('address') == address:
                                # Return public key from this transaction
                                return tx_dict.get('public_key')
                                
            return None
    
    def create_account(self, 
                     address: str, 
                     balance: float = 0, 
                     public_key: Optional[str] = None,
                     block_height: int = 0) -> bool:
        """
        Create a new account in the database
        
        Args:
            address: Account address
            balance: Initial account balance
            public_key: Account public key (optional)
            block_height: Block height when account was first seen
            
        Returns:
            True if created successfully, False otherwise
        """
        with self.lock:
            try:
                if self.account_exists(address):
                    logger.debug(f"Account {address} already exists")
                    return False
                    
                cursor = self.connection.cursor()
                
                # Store pubkey_block if we have a public key
                pubkey_block = block_height if public_key else None
                
                cursor.execute("""
                    INSERT INTO accounts 
                    (address, balance, pubkey_block, tx_count)
                    VALUES (?, ?, ?, ?)
                """, (address, balance, pubkey_block, 1))
                
                self.connection.commit()
                logger.debug(f"Created account {address} with balance {balance}")
                return True
            except sqlite3.Error as e:
                logger.error(f"Error creating account {address}: {e}")
                self.connection.rollback()
                return False
    
    def update_balance(self, address: str, new_balance: float) -> bool:
        """
        Update account balance
        
        Args:
            address: Account address
            new_balance: New account balance
            
        Returns:
            True if updated successfully, False otherwise
        """
        with self.lock:
            try:
                if not self.account_exists(address):
                    logger.warning(f"Cannot update non-existent account {address}")
                    return False
                    
                cursor = self.connection.cursor()
                cursor.execute("""
                    UPDATE accounts
                    SET balance = ?
                    WHERE address = ?
                """, (new_balance, address))
                
                self.connection.commit()
                logger.debug(f"Updated account {address} balance to {new_balance}")
                return True
            except sqlite3.Error as e:
                logger.error(f"Error updating account {address} balance: {e}")
                self.connection.rollback()
                return False
    
    def update_account(self, 
                      address: str, 
                      balance: Optional[float] = None, 
                      pubkey_block: Optional[int] = None,
                      increment_tx_count: bool = False) -> bool:
        """
        Update account information
        
        Args:
            address: Account address
            balance: New balance (if None, doesn't update)
            pubkey_block: Block containing public key (if None, doesn't update)
            increment_tx_count: Whether to increment transaction count
            
        Returns:
            True if updated successfully, False otherwise
        """
        with self.lock:
            try:
                if not self.account_exists(address):
                    logger.warning(f"Cannot update non-existent account {address}")
                    return False
                    
                cursor = self.connection.cursor()
                
                # Build the update query based on provided parameters
                update_parts = []
                params = []
                
                if balance is not None:
                    update_parts.append("balance = ?")
                    params.append(balance)
                    
                if pubkey_block is not None:
                    update_parts.append("pubkey_block = ?")
                    params.append(pubkey_block)
                    
                if increment_tx_count:
                    update_parts.append("tx_count = tx_count + 1")
                
                if not update_parts:
                    return True  # Nothing to update
                
                # Complete the query and parameters
                query = f"UPDATE accounts SET {', '.join(update_parts)} WHERE address = ?"
                params.append(address)
                
                cursor.execute(query, tuple(params))
                self.connection.commit()
                
                logger.debug(f"Updated account {address}")
                return True
            except sqlite3.Error as e:
                logger.error(f"Error updating account {address}: {e}")
                self.connection.rollback()
                return False
    
    def add_transaction_block(self, address: str, block_height: int) -> bool:
        """
        Add a transaction block reference for an address
        
        Args:
            address: Account address
            block_height: Block height containing the transaction
            
        Returns:
            True if added successfully, False otherwise
        """
        with self.lock:
            try:
                if not self.account_exists(address):
                    logger.warning(f"Cannot add transaction block for non-existent account {address}")
                    return False
                
                cursor = self.connection.cursor()
                
                # Check if we already have this block reference
                cursor.execute("""
                    SELECT 1 FROM tx_blocks
                    WHERE address = ? AND block_num = ?
                """, (address, block_height))
                
                if not cursor.fetchone():
                    # Insert new reference only if it doesn't exist
                    cursor.execute("""
                        INSERT INTO tx_blocks
                        (address, block_num)
                        VALUES (?, ?)
                    """, (address, block_height))
                
                # Increment transaction count for the account
                self.update_account(address, increment_tx_count=True)
                
                self.connection.commit()
                logger.debug(f"Added transaction block reference for {address} in block {block_height}")
                return True
            except sqlite3.Error as e:
                logger.error(f"Error adding transaction block for {address}: {e}")
                self.connection.rollback()
                return False
    
    def get_transaction_blocks(self, address: str, limit: int = 100, offset: int = 0) -> List[int]:
        """
        Get blocks containing transactions for an account
        
        Args:
            address: Account address
            limit: Maximum number of blocks to return
            offset: Offset for pagination
            
        Returns:
            List of block numbers
        """
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT block_num
                FROM tx_blocks
                WHERE address = ?
                ORDER BY block_num DESC
                LIMIT ? OFFSET ?
            """, (address, limit, offset))
            
            # Return just a list of block numbers
            return [row[0] for row in cursor.fetchall()]
    
    def get_transactions(self, address: str, limit: int = 100, offset: int = 0, blockchain=None) -> List[Dict[str, Any]]:
        """
        Get transaction history for an account by fetching from blockchain using references
        
        Args:
            address: Account address
            limit: Maximum number of transactions to return
            offset: Offset for pagination
            blockchain: Reference to blockchain instance to fetch blocks
            
        Returns:
            List of transactions
        """
        if not blockchain:
            logger.error("Blockchain reference required to fetch transactions")
            return []
            
        # Get block references containing transactions for this address
        block_nums = self.get_transaction_blocks(address, limit=limit, offset=offset)
        
        transactions = []
        for block_num in block_nums:
            # Fetch the block from blockchain
            block = blockchain.get_block_by_height(block_num)
            if not block:
                continue
                
            # Extract transactions involving this address
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
                    
                # Calculate amounts
                debit_amount = 0
                credit_amount = 0
                
                if is_sender:
                    # Sum outputs to other addresses
                    for output in tx_dict.get('outputs', []):
                        if output.get('address') != address:
                            debit_amount += output.get('amount', 0)
                
                if is_receiver:
                    # Sum outputs to this address
                    for output in tx_dict.get('outputs', []):
                        if output.get('address') == address:
                            credit_amount += output.get('amount', 0)
                
                # Determine transaction type
                if is_sender and is_receiver:
                    tx_type = 'transfer'  # Sending to self
                elif is_sender:
                    tx_type = 'debit'  # Sending to others
                else:
                    tx_type = 'credit'  # Receiving
                
                # Create transaction record
                transactions.append({
                    'tx_hash': tx_hash,
                    'block_height': block.height,
                    'timestamp': tx_dict.get('timestamp', block.timestamp),
                    'type': tx_type,
                    'debit': debit_amount,
                    'credit': credit_amount,
                    'net': credit_amount - debit_amount,
                    'data': tx_dict.get('data', '')
                })
                
                # Limit the number of transactions
                if len(transactions) >= limit:
                    return transactions
                    
        return transactions
    
    def set_last_processed_block(self, height: int) -> bool:
        """
        Record last processed block height
        
        Args:
            height: Block height
            
        Returns:
            True if recorded successfully, False otherwise
        """
        with self.lock:
            try:
                cursor = self.connection.cursor()
                cursor.execute("DELETE FROM last_block")  # Clear previous entry
                cursor.execute("INSERT INTO last_block (height) VALUES (?)", (height,))
                
                self.connection.commit()
                logger.debug(f"Recorded last processed block {height}")
                return True
            except sqlite3.Error as e:
                logger.error(f"Error recording last processed block {height}: {e}")
                self.connection.rollback()
                return False
    
    def get_last_processed_block(self) -> Optional[int]:
        """
        Get the last processed block height
        
        Returns:
            Block height or None if no blocks processed
        """
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("SELECT height FROM last_block LIMIT 1")
            
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_account_count(self) -> int:
        """
        Get total number of accounts
        
        Returns:
            Number of accounts in database
        """
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM accounts")
            return cursor.fetchone()[0]
    
    def get_total_supply(self) -> float:
        """
        Get total supply (sum of all account balances)
        
        Returns:
            Total supply
        """
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("SELECT SUM(balance) FROM accounts")
            result = cursor.fetchone()[0]
            return float(result) if result is not None else 0
    
    def process_block(self, block, blockchain) -> bool:
        """
        Process a block and update account database
        
        Args:
            block: Block to process
            blockchain: Blockchain reference
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                # Special handling for genesis block - check if this block has already been processed
                # to prevent double-counting the genesis allocations
                if block.height == 0:
                    last_block = self.get_last_processed_block()
                    if last_block is not None and last_block >= 0:
                        logger.warning(f"Skipping duplicate processing of genesis block")
                        return True
                
                # Start a transaction
                self.connection.execute("BEGIN TRANSACTION")
                
                # Process each transaction in the block
                for tx_data in block.transactions:
                    # Convert dict to Transaction object if needed
                    if isinstance(tx_data, dict):
                        tx_hash = tx_data.get('hash')
                    else:
                        tx_hash = tx_data.hash
                        tx_data = tx_data.to_dict()
                    
                    # Process coinbase transactions (no inputs, just outputs)
                    if not tx_data.get('inputs'):
                        for output in tx_data.get('outputs', []):
                            address = output.get('address')
                            amount = output.get('amount', 0)
                            
                            # Create or update account
                            if not self.account_exists(address):
                                self.create_account(
                                    address=address,
                                    balance=amount,
                                    block_height=block.height
                                )
                            else:
                                # Update balance
                                current = self.get_account(address)
                                new_balance = current['balance'] + amount
                                self.update_balance(address, new_balance)
                            
                            # Add transaction block reference
                            self.add_transaction_block(address, block.height)
                    
                    # Process regular transactions
                    else:
                        # Process inputs (debit from sender)
                        for tx_input in tx_data.get('inputs', []):
                            address = tx_input.get('address')
                            amount = tx_input.get('amount', 0)
                            
                            # Ensure account exists
                            if not self.account_exists(address):
                                logger.warning(f"Input references non-existent account {address}")
                                self.connection.rollback()
                                return False
                            
                            # Update sender balance
                            current = self.get_account(address)
                            if current['balance'] < amount:
                                logger.warning(f"Insufficient balance for {address}: {current['balance']} < {amount}")
                                self.connection.rollback()
                                return False
                                
                            new_balance = current['balance'] - amount
                            self.update_balance(address, new_balance)
                            
                            # Update public key block reference if this transaction has the public key
                            if tx_data.get('public_key') and not current.get('pubkey_block'):
                                self.update_account(address, pubkey_block=block.height)
                            
                            # Add transaction block reference
                            self.add_transaction_block(address, block.height)
                        
                        # Process outputs (credit to recipient)
                        for output in tx_data.get('outputs', []):
                            address = output.get('address')
                            amount = output.get('amount', 0)
                            
                            # Create or update account
                            if not self.account_exists(address):
                                self.create_account(
                                    address=address,
                                    balance=amount,
                                    block_height=block.height
                                )
                            else:
                                # Update balance
                                current = self.get_account(address)
                                new_balance = current['balance'] + amount
                                self.update_balance(address, new_balance)
                            
                            # Add transaction block reference
                            self.add_transaction_block(address, block.height)
                
                # Record last processed block
                self.set_last_processed_block(block.height)
                
                # Commit transaction
                self.connection.commit()
                
                # Verify total supply after processing genesis block
                if block.height == 0:
                    total_supply = self.get_total_supply()
                    if total_supply != config.INITIAL_SUPPLY:
                        logger.warning(f"Total supply after genesis block is {total_supply}, expected {config.INITIAL_SUPPLY}")
                
                return True
                
            except Exception as e:
                logger.error(f"Error processing block {block.height}: {e}")
                self.connection.rollback()
                return False
    
    def rebuild_from_blocks(self, blockchain) -> bool:
        """
        Rebuild database from blockchain blocks
        
        Args:
            blockchain: Blockchain instance to rebuild from
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                logger.info("Rebuilding account database from blockchain...")
                
                # Clear existing tables
                cursor = self.connection.cursor()
                cursor.execute("DELETE FROM tx_blocks")
                cursor.execute("DELETE FROM accounts")
                cursor.execute("DELETE FROM last_block")
                self.connection.commit()
                
                # Process blocks from genesis
                height = 0
                while True:
                    block = blockchain.get_block_by_height(height)
                    if not block:
                        break
                        
                    # Process block transactions
                    self.process_block(block, blockchain)
                    height += 1
                
                logger.info(f"Rebuilt account database successfully with {self.get_account_count()} accounts")
                return True
                
            except Exception as e:
                logger.error(f"Error rebuilding account database: {e}")
                self.connection.rollback()
                return False
    
    def export_to_json(self, output_path: Path) -> bool:
        """
        Export database to JSON format
        
        Args:
            output_path: Path to write JSON file
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                # Get all accounts
                cursor = self.connection.cursor()
                cursor.execute("SELECT address FROM accounts")
                addresses = [row[0] for row in cursor.fetchall()]
                
                data = {
                    'metadata': {
                        'chain_id': self.chain_id,
                        'exported_at': int(time.time()),
                        'account_count': self.get_account_count(),
                        'total_supply': self.get_total_supply(),
                        'last_block': self.get_last_processed_block()
                    },
                    'accounts': {}
                }
                
                for address in addresses:
                    account = self.get_account(address)
                    
                    # Get transaction block references
                    cursor.execute("""
                        SELECT block_num
                        FROM tx_blocks
                        WHERE address = ?
                        ORDER BY block_num DESC
                    """, (address,))
                    
                    tx_blocks = [row[0] for row in cursor.fetchall()]
                    
                    data['accounts'][address] = {
                        'balance': account['balance'],
                        'pubkey_block': account['pubkey_block'],
                        'tx_count': account['tx_count'],
                        'tx_blocks': tx_blocks
                    }
                
                # Write to file
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
                    
                logger.info(f"Exported account database to {output_path}")
                return True
                
            except Exception as e:
                logger.error(f"Error exporting database: {e}")
                return False
    
    def import_from_json(self, input_path: Path) -> bool:
        """
        Import database from JSON format
        
        Args:
            input_path: Path to read JSON file
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                if not input_path.exists():
                    logger.error(f"Import file {input_path} does not exist")
                    return False
                
                # Load JSON data
                with open(input_path, 'r') as f:
                    data = json.load(f)
                
                # Begin transaction
                self.connection.execute("BEGIN TRANSACTION")
                
                # Clear existing data
                cursor = self.connection.cursor()
                cursor.execute("DELETE FROM tx_blocks")
                cursor.execute("DELETE FROM accounts")
                cursor.execute("DELETE FROM last_block")
                
                # Import accounts and transaction references
                for address, account_data in data['accounts'].items():
                    # Create account
                    cursor.execute("""
                        INSERT INTO accounts 
                        (address, balance, pubkey_block, tx_count)
                        VALUES (?, ?, ?, ?)
                    """, (
                        address, 
                        account_data['balance'],
                        account_data.get('pubkey_block'),
                        account_data['tx_count']
                    ))
                    
                    # Import transaction block references
                    for block_num in account_data.get('tx_blocks', []):
                        cursor.execute("""
                            INSERT INTO tx_blocks
                            (address, block_num)
                            VALUES (?, ?)
                        """, (address, block_num))
                
                # Import last processed block
                if data['metadata'].get('last_block') is not None:
                    self.set_last_processed_block(data['metadata']['last_block'])
                
                # Commit transaction
                self.connection.commit()
                logger.info(f"Imported account database from {input_path}")
                return True
                
            except Exception as e:
                logger.error(f"Error importing database: {e}")
                self.connection.rollback()
                return False
    
    def vacuum_database(self):
        """Optimize database with VACUUM command"""
        with self.lock:
            self.connection.execute("VACUUM")
            logger.info("Database vacuumed")
    
    def close(self):
        """Close database connection"""
        with self.lock:
            if self.connection:
                self.connection.close()
                self.connection = None
                logger.info("Database connection closed")
    
    def __del__(self):
        """Ensure database is closed on deletion"""
        self.close()