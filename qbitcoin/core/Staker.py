# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import os
import json
import time
import threading
import math
from typing import Dict, List, Optional, Set

from pyqrllib.pyqrllib import bin2hstr, hstr2bin

from qbitcoin.core.config import DevConfig, UserConfig
from qbitcoin.core.misc import logger
from qbitcoin.core.txs.TransferTransaction import TransferTransaction
from qbitcoin.core.Singleton import Singleton
from qbitcoin.core.DonorWalletManager import DonorWalletManager


class StakeInfo:
    """Information about a staker"""
    
    def __init__(self, address: bytes, balance: int, peer_ip: str = None, is_local: bool = False):
        self.address = address
        self.balance = balance
        self.stake_start_time = time.time()
        self.last_seen_time = time.time()
        self.is_online = True
        self.peer_ip = peer_ip  # IP of peer that shared this staker info
        self.is_local = is_local  # True if this is our own node's staker
        self.last_balance_check = time.time()
        self.balance_verified = False
        
    def update_last_seen(self):
        """Update last seen time to current time"""
        self.last_seen_time = time.time()
        self.is_online = True
        
    def check_online_status(self, max_offline_time: int) -> bool:
        """Check if staker is still online based on last seen time"""
        current_time = time.time()
        offline_time = current_time - self.last_seen_time
        self.is_online = offline_time <= max_offline_time
        return self.is_online
        
    def get_stake_share(self, total_stake: int) -> float:
        """Calculate this staker's share of total stake"""
        if total_stake == 0:
            return 0.0
        return self.balance / total_stake
        
    def serialize(self) -> dict:
        """Serialize stake info to dictionary"""
        return {
            'address': bin2hstr(self.address),
            'balance': self.balance,
            'stake_start_time': self.stake_start_time,
            'last_seen_time': self.last_seen_time,
            'is_online': self.is_online,
            'peer_ip': self.peer_ip,
            'is_local': self.is_local,
            'last_balance_check': self.last_balance_check,
            'balance_verified': self.balance_verified
        }
        
    @classmethod
    def deserialize(cls, data: dict) -> 'StakeInfo':
        """Deserialize stake info from dictionary"""
        stake_info = cls(
            address=hstr2bin(data['address']),
            balance=data['balance'],
            peer_ip=data.get('peer_ip'),
            is_local=data.get('is_local', False)
        )
        stake_info.stake_start_time = data.get('stake_start_time', time.time())
        stake_info.last_seen_time = data.get('last_seen_time', time.time())
        stake_info.is_online = data.get('is_online', True)
        stake_info.last_balance_check = data.get('last_balance_check', time.time())
        stake_info.balance_verified = data.get('balance_verified', False)
        return stake_info


class StakingManager(object, metaclass=Singleton):
    """
    Simplified staking mechanism for Qbitcoin
    Only stores staker addresses and verifies balances from blockchain
    """
    
    def __init__(self):
        self.stakers: Set[bytes] = set()  # Only store addresses
        self.last_reward_block = 0
        self.lock = threading.RLock()
        self.chain_manager = None
        self.p2p_factory = None
        self.dev_config = None
        
        # For P2P staker synchronization (like blocks)
        self.pending_broadcasts = []  # Keep for compatibility
        self.is_node_synced = False
        
        # Initialize persistent storage
        user_config = UserConfig.getInstance()
        self.stakers_db_path = os.path.join(user_config.qrl_dir, 'data', 'stakers.json')
        self.ensure_data_directory()
        
        # Initialize donor wallet manager
        self.donor_wallet_manager = DonorWalletManager()
        
        # Load existing stakers from database
        self.load_stakers_from_db()
        
        # Auto-load donor wallet if available
        wallet_loaded = self.auto_load_donor_wallet()
        if wallet_loaded:
            logger.info("✓ DONOR WALLET LOADED SUCCESSFULLY - Rewards will be distributed automatically")
        else:
            logger.debug("No donor wallet found - rewards will not be distributed")
        
        # Start reward monitoring thread
        self._reward_monitoring = True
        self._reward_thread = threading.Thread(target=self._monitor_rewards, daemon=True)
        self._reward_thread.start()
        
    def ensure_data_directory(self):
        """Ensure data directory exists"""
        data_dir = os.path.dirname(self.stakers_db_path)
        os.makedirs(data_dir, exist_ok=True)
        
    def load_stakers_from_db(self):
        """Load stakers from persistent storage - only addresses"""
        try:
            if os.path.exists(self.stakers_db_path):
                with open(self.stakers_db_path, 'r') as f:
                    data = json.load(f)
                
                # Handle both old and new database formats
                stakers_data = data.get('stakers', [])
                loaded_count = 0  # Initialize counter
                
                for item in stakers_data:
                    try:
                        # Handle new format (list of address strings)
                        if isinstance(item, str):
                            # Validate Qbitcoin address format (50 hex chars for 25 bytes)
                            if len(item) == 50:  # Qbitcoin addresses are 50 hex chars (25 bytes)
                                try:
                                    address_data = hstr2bin(item)
                                    # Convert tuple to bytes if needed (hstr2bin returns tuple in this version)
                                    if isinstance(address_data, tuple):
                                        address_bytes = bytes(address_data)
                                    else:
                                        address_bytes = address_data
                                        
                                    self.stakers.add(address_bytes)
                                    loaded_count += 1
                                    logger.debug("Loaded staker address: %s", item)
                                except Exception as e:
                                    logger.warning("Failed to convert address %s: %s", item, str(e))
                            else:
                                logger.warning("Invalid address format: %s (length: %d)", item, len(item))
                        
                        # Handle old format (dict with address field)
                        elif isinstance(item, dict) and 'address' in item:
                            address_hex = item['address']
                            if isinstance(address_hex, str) and len(address_hex) == 50:
                                try:
                                    address_data = hstr2bin(address_hex)
                                    # Convert tuple to bytes if needed (hstr2bin returns tuple in this version)
                                    if isinstance(address_data, tuple):
                                        address_bytes = bytes(address_data)
                                    else:
                                        address_bytes = address_data
                                        
                                    self.stakers.add(address_bytes)
                                    loaded_count += 1
                                    logger.debug("Loaded staker address from dict: %s", address_hex)
                                except Exception as e:
                                    logger.warning("Failed to convert address %s: %s", address_hex, str(e))
                            else:
                                logger.warning("Invalid address in old format: %s", address_hex)
                                
                        # Handle tuple format (raw bytes as tuple) - this is valid for Qbitcoin
                        elif isinstance(item, (list, tuple)) and len(item) == 25:
                            if all(isinstance(x, int) and 0 <= x <= 255 for x in item):
                                address_bytes = bytes(item)
                                from qbitcoin.core.OptimizedAddressState import OptimizedAddressState
                                if OptimizedAddressState.address_is_valid(address_bytes):
                                    self.stakers.add(address_bytes)
                                    loaded_count += 1
                                    logger.debug("Loaded tuple address: %s", bin2hstr(address_bytes)[:10] + "...")
                                else:
                                    logger.warning("Invalid tuple address format: %s", item)
                            else:
                                logger.warning("Invalid tuple data: %s", item)
                        else:
                            logger.warning("Unknown staker data format: %s", type(item))
                            
                    except Exception as e:
                        logger.warning("Failed to load staker address %s: %s", str(item)[:20], str(e))
                        
                self.last_reward_block = data.get('last_reward_block', 0)
                logger.info("Loaded %d staker addresses from database", len(self.stakers))
                    
            else:
                logger.info("No existing stakers database found")
        except Exception as e:
            logger.error("Failed to load stakers database: %s", str(e))
            # Reset stakers to empty set if loading fails
            self.stakers = set()
            
    def save_stakers_to_db(self):
        """Save stakers to persistent storage - only addresses"""
        try:
            data = {
                'stakers': [bin2hstr(address) for address in self.stakers],
                'last_reward_block': self.last_reward_block,
                'last_saved': time.time()
            }
            
            # Write to temporary file first, then rename for atomicity
            temp_path = self.stakers_db_path + '.tmp'
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            os.rename(temp_path, self.stakers_db_path)
            logger.debug("Saved %d staker addresses to database", len(self.stakers))
        except Exception as e:
            logger.error("Failed to save stakers database: %s", str(e))
        
    def set_chain_manager(self, chain_manager):
        """Set the chain manager instance"""
        self.chain_manager = chain_manager
        
    def verify_staker_balance(self, address: bytes) -> Optional[int]:
        """
        Verify staker balance from blockchain
        
        Args:
            address: Staker's address
            
        Returns:
            Balance if valid, None if invalid
        """
        if not self.chain_manager:
            logger.error("Chain manager not available for balance verification")
            return None
            
        try:
            # Ensure address is bytes type
            if isinstance(address, str):
                if address.startswith('Q'):
                    address_data = hstr2bin(address[1:])  # Remove Q prefix
                else:
                    address_data = hstr2bin(address)
                
                # Convert tuple to bytes if needed (hstr2bin returns tuple in this version)
                if isinstance(address_data, tuple):
                    address = bytes(address_data)
                else:
                    address = address_data
                    
            elif isinstance(address, tuple):
                # Convert tuple of integers to bytes (this is valid for Qbitcoin addresses)
                if len(address) == 25 and all(isinstance(x, int) and 0 <= x <= 255 for x in address):
                    address = bytes(address)
                    logger.debug("Converted tuple address to bytes: %s", bin2hstr(address)[:10] + "...")
                else:
                    logger.error("Invalid tuple address format: %s", address)
                    return None
            elif not isinstance(address, bytes):
                logger.error("Invalid address type: %s", type(address))
                return None
                
            # Validate address format using existing validation
            from qbitcoin.core.OptimizedAddressState import OptimizedAddressState
            if not OptimizedAddressState.address_is_valid(address):
                logger.warning("Address format is invalid: %s", bin2hstr(address))
                return None
                
            address_state = self.chain_manager.get_optimized_address_state(address)
            if not address_state:
                logger.warning("Address %s not found in blockchain", bin2hstr(address))
                return None
                
            balance = address_state.balance
            
            # Check positive balance
            if balance <= 0:
                logger.warning("Address %s has zero or negative balance: %d", bin2hstr(address), balance)
                return None
                
            # Check minimum balance requirement
            if self.dev_config and balance < self.dev_config.staking_min_balance:
                logger.warning("Address %s balance below minimum: %d < %d", 
                             bin2hstr(address), balance, self.dev_config.staking_min_balance)
                return None
                
            return balance
            
        except Exception as e:
            logger.error("Error verifying balance for %s: %s", bin2hstr(address), str(e))
            return None
        
    def set_p2p_factory(self, p2p_factory):
        """Set the P2P factory"""
        self.p2p_factory = p2p_factory
        
    def set_grpc_client(self, grpc_client):
        """Set the gRPC client for transaction broadcasting"""
        self.grpc_client = grpc_client
        
    def set_dev_config(self, dev_config: DevConfig):
        """Set the development configuration"""
        self.dev_config = dev_config
        
    def validate_and_cleanup_stakers(self) -> int:
        """
        Validate all current stakers and remove those with insufficient balance
        
        Returns:
            int: Number of stakers removed
        """
        if not self.chain_manager or not self.dev_config:
            logger.warning("Cannot validate stakers: chain_manager or dev_config not available")
            return 0
            
        removed_count = 0
        stakers_to_remove = []
        
        with self.lock:
            logger.info("Validating %d stakers for minimum balance requirement", len(self.stakers))
            
            for address in self.stakers.copy():  # Use copy to avoid modification during iteration
                try:
                    # Verify current balance
                    balance = self.verify_staker_balance(address)
                    
                    if balance is None:
                        # Balance verification failed (address not found, below minimum, etc.)
                        stakers_to_remove.append(address)
                        logger.info("Removing staker %s: balance verification failed", bin2hstr(address))
                    else:
                        logger.debug("Staker %s validated: balance %d QBC", bin2hstr(address), balance // 10**9)
                        
                except Exception as e:
                    logger.error("Error validating staker %s: %s", bin2hstr(address), str(e))
                    stakers_to_remove.append(address)
            
            # Remove invalid stakers
            for address in stakers_to_remove:
                if address in self.stakers:
                    self.stakers.discard(address)
                    removed_count += 1
                    logger.info("Removed staker %s due to insufficient balance", bin2hstr(address))
                    
                    # Broadcast removal to peers
                    self.broadcast_staker_to_peers(address, 'remove')
            
            # Save updated staker list if any were removed
            if removed_count > 0:
                self.save_stakers_to_db()
                logger.info("Staker cleanup completed: removed %d invalid stakers, %d remaining", 
                           removed_count, len(self.stakers))
            else:
                logger.debug("Staker validation completed: all %d stakers are valid", len(self.stakers))
        
        return removed_count
    
    def periodic_staker_validation(self):
        """
        Periodically validate stakers (called from monitoring thread)
        """
        try:
            # Only run validation if node is synced and we have stakers
            if not self.is_node_synced or not self.stakers:
                return
                
            # Run validation every 10 minutes (600 seconds)
            current_time = time.time()
            if not hasattr(self, '_last_validation_time'):
                self._last_validation_time = 0
                
            if current_time - self._last_validation_time >= 600:  # 10 minutes
                logger.debug("Starting periodic staker validation...")
                removed_count = self.validate_and_cleanup_stakers()
                
                if removed_count > 0:
                    logger.info("Periodic staker validation: removed %d invalid stakers", removed_count)
                
                self._last_validation_time = current_time
                
        except Exception as e:
            logger.error("Error in periodic staker validation: %s", str(e))
    
    def validate_staker_after_transaction(self, address: bytes):
        """
        Validate a specific staker after a transaction that might affect their balance
        
        Args:
            address: Address to validate
        """
        try:
            if not self.chain_manager or not self.dev_config:
                return
                
            # Check if this address is a staker
            if address not in self.stakers:
                return
                
            # Verify current balance
            balance = self.verify_staker_balance(address)
            
            if balance is None:
                # Remove staker due to insufficient balance
                with self.lock:
                    if address in self.stakers:
                        self.stakers.discard(address)
                        self.save_stakers_to_db()
                        self.broadcast_staker_to_peers(address, 'remove')
                        
                        balance_qbc = 0
                        try:
                            address_state = self.chain_manager.get_optimized_address_state(address)
                            if address_state:
                                balance_qbc = address_state.balance / 10**9
                        except:
                            pass
                            
                        logger.info("Staker %s removed after transaction: balance %.3f QBC below minimum %.0f QBC", 
                                   bin2hstr(address), balance_qbc, self.dev_config.staking_min_balance / 10**9)
            else:
                logger.debug("Staker %s still valid after transaction: balance %d quarks", 
                           bin2hstr(address), balance)
                
        except Exception as e:
            logger.error("Error validating staker %s after transaction: %s", bin2hstr(address), str(e))
    
    def force_validate_all_stakers(self) -> Dict[str, int]:
        """
        Force immediate validation of all stakers (for testing/debugging)
        
        Returns:
            dict: Statistics about the validation
        """
        try:
            logger.info("Force validating all stakers...")
            
            initial_count = len(self.stakers)
            removed_count = self.validate_and_cleanup_stakers()
            remaining_count = len(self.stakers)
            
            stats = {
                'initial_stakers': initial_count,
                'removed_stakers': removed_count,
                'remaining_stakers': remaining_count
            }
            
            logger.info("Force validation completed: %d initial, %d removed, %d remaining", 
                       initial_count, removed_count, remaining_count)
            
            return stats
            
        except Exception as e:
            logger.error("Error in force validation: %s", str(e))
            return {'error': str(e)}
        
    def load_donor_wallet(self, password: str) -> bool:
        """
        Load donor wallet with password
        
        Args:
            password: Password to decrypt donor wallet
            
        Returns:
            bool: True if wallet was loaded successfully
        """
        return self.donor_wallet_manager.load_donor_wallet(password) is not None
        
    def auto_load_donor_wallet(self) -> bool:
        """
        Automatically load donor wallet if available
        
        Returns:
            bool: True if wallet was loaded successfully
        """
        try:
            
            from qbitcoin.core.config import UserConfig
            user_config = UserConfig.getInstance()
            donor_wallets_dir = os.path.join(user_config.qrl_dir, 'donor_wallets')
            
            # First try to load from donor_wallets directory
            if os.path.exists(donor_wallets_dir):
                logger.info("Checking donor wallets directory: %s", donor_wallets_dir)
                # Find unencrypted donor wallet files
                for filename in os.listdir(donor_wallets_dir):
                    if filename.endswith('_donor.json'):
                        wallet_path = os.path.join(donor_wallets_dir, filename)
                        logger.info("Found donor wallet file: %s", filename)
                        try:
                            with open(wallet_path, 'r') as f:
                                wallet_data = json.load(f)
                                
                            # Check if it's unencrypted
                            if not wallet_data.get('encrypted', True):  # Default to encrypted if not specified
                                logger.info("Loading unencrypted donor wallet: %s", filename)
                                
                                # Load the wallet directly without password
                                if self.donor_wallet_manager.load_unencrypted_donor_wallet(wallet_data):
                                    logger.info("✓ Successfully auto-loaded donor wallet from %s", filename)
                                    logger.info("✓ Donor wallet address: %s", wallet_data.get('address', 'unknown'))
                                    return True
                                else:
                                    logger.warning("✗ Failed to load unencrypted donor wallet: %s", filename)
                            else:
                                logger.info("Skipping encrypted donor wallet: %s", filename)
                        except Exception as e:
                            logger.warning("Error reading donor wallet %s: %s", filename, str(e))
            else:
                logger.info("Donor wallets directory not found: %s", donor_wallets_dir)
            
            # REMOVED: No longer automatically load genesis wallet as donor wallet
            # This was causing confusion - donor wallets should be explicitly created
            logger.debug("No donor wallet found - rewards will not be distributed")
            return False
            
        except Exception as e:
            logger.error("Error in auto_load_donor_wallet: %s", str(e))
            return False
        
    def is_donor_wallet_loaded(self) -> bool:
        """Check if donor wallet is currently loaded and files still exist"""
        if not self.donor_wallet_manager.is_wallet_loaded():
            return False
            
        # Verify that donor wallet files still exist
        from qbitcoin.core.config import UserConfig
        user_config = UserConfig.getInstance()
        donor_wallets_dir = os.path.join(user_config.qrl_dir, 'donor_wallets')
        
        if not os.path.exists(donor_wallets_dir):
            # Directory doesn't exist, unload the wallet
            logger.debug("Donor wallets directory not found, unloading wallet from memory")
            self.donor_wallet_manager.unload_wallet()
            return False
            
        # Check if any donor wallet files exist
        donor_files = [f for f in os.listdir(donor_wallets_dir) if f.endswith('_donor.json')]
        if not donor_files:
            # No donor wallet files exist, unload the wallet
            logger.debug("No donor wallet files found, unloading wallet from memory")
            self.donor_wallet_manager.unload_wallet()
            return False
            
        return True
        
    def get_donor_wallet_address(self) -> Optional[str]:
        """Get donor wallet address"""
        wallet_info = self.donor_wallet_manager.get_wallet_info()
        if wallet_info:
            return wallet_info['address']
        return None
            
    def add_staker(self, address: bytes, peer_ip: str = None) -> bool:
        """
        Add a new staker to the staking pool
        
        Args:
            address: Staker's address
            peer_ip: IP of peer that shared this staker (None for local stakers)
            
        Returns:
            bool: True if staker was added successfully
        """
        if not self.dev_config or not self.dev_config.staking_enabled:
            logger.warning("Staking is not enabled")
            return False
            
        with self.lock:
            # Ensure address is bytes type and handle various formats
            if isinstance(address, str):
                try:
                    if address.startswith('Q'):
                        address_data = hstr2bin(address[1:])  # Remove Q prefix
                    else:
                        address_data = hstr2bin(address)
                    
                    # Convert tuple to bytes if needed (hstr2bin returns tuple in this version)
                    if isinstance(address_data, tuple):
                        address = bytes(address_data)
                    else:
                        address = address_data
                        
                except Exception as e:
                    logger.error("Invalid address format: %s - %s", address, str(e))
                    return False
            elif isinstance(address, tuple):
                # Convert tuple of integers to bytes (this is valid for Qbitcoin addresses)
                if len(address) == 25 and all(isinstance(x, int) and 0 <= x <= 255 for x in address):
                    address = bytes(address)
                    logger.debug("Converted tuple address to bytes: %s", bin2hstr(address)[:10] + "...")
                else:
                    logger.error("Invalid tuple address format: %s", address)
                    return False
            elif not isinstance(address, bytes):
                logger.error("Invalid address type: %s", type(address))
                return False
                
            # Validate address format using existing validation
            from qbitcoin.core.OptimizedAddressState import OptimizedAddressState
            if not OptimizedAddressState.address_is_valid(address):
                logger.warning("Address format is invalid: %s", bin2hstr(address))
                return False
            
            # Check if address is already in the staking list (no duplicates)
            if address in self.stakers:
                logger.info("Address %s is already staking", bin2hstr(address))
                return False
                
            # Verify balance from blockchain
            balance = self.verify_staker_balance(address)
            if balance is None:
                logger.error("Failed to verify balance for address %s", bin2hstr(address))
                return False
                
            # Add staker address to set
            self.stakers.add(address)
            
            # Save to database
            self.save_stakers_to_db()
            
            # Broadcast to peers (only if this is a local staker, not from peer)
            if not peer_ip:
                self.broadcast_staker_to_peers(address, 'add')
            
            logger.info("Staker added: %s with verified balance %d", bin2hstr(address), balance)
            return True
            
    def remove_staker(self, address: bytes, reason: str = "manual") -> bool:
        """
        Remove a staker from the staking pool
        
        Args:
            address: Staker's address
            reason: Reason for removal
            
        Returns:
            bool: True if staker was removed
        """
        with self.lock:
            if address not in self.stakers:
                return False
                
            # Remove from set
            self.stakers.discard(address)
            
            # Save to database
            self.save_stakers_to_db()
            
            # Broadcast removal to peers (only if not removed by peer)
            if not reason.startswith("removed by peer"):
                self.broadcast_staker_to_peers(address, 'remove')
            
            logger.info("Staker removed: %s (reason: %s)", bin2hstr(address), reason)
            return True
            
    def get_active_stakers(self) -> Dict[bytes, int]:
        """Get list of active stakers with verified balances from blockchain"""
        with self.lock:
            active_stakers = {}
            invalid_stakers = []
            
            for address in self.stakers:
                balance = self.verify_staker_balance(address)
                if balance is not None:
                    active_stakers[address] = balance
                else:
                    # Mark for removal if balance verification fails
                    invalid_stakers.append(address)
                    
            # Remove invalid stakers
            for address in invalid_stakers:
                logger.info("Removing invalid staker: %s", bin2hstr(address))
                self.stakers.discard(address)
                
            # Save changes if any stakers were removed
            if invalid_stakers:
                self.save_stakers_to_db()
                
            return active_stakers
            
    def get_total_stake(self) -> int:
        """Get total staking amount from active stakers"""
        active_stakers = self.get_active_stakers()
        return sum(active_stakers.values())
            
    def should_distribute_rewards(self, current_block_number: int) -> bool:
        """Check if it's time to distribute rewards"""
        if not self.dev_config:
            logger.debug("No dev_config available for reward distribution")
            return False
            
        if not self.is_donor_wallet_loaded():
            logger.debug("Donor wallet not loaded for reward distribution")
            return False
            
        blocks_since_last_reward = current_block_number - self.last_reward_block
        should_distribute = blocks_since_last_reward >= self.dev_config.staking_reward_interval
        
        logger.debug("Reward check: current_block=%d, last_reward_block=%d, interval=%d, should_distribute=%s",
                    current_block_number, self.last_reward_block, 
                    self.dev_config.staking_reward_interval, should_distribute)
        
        return should_distribute
        
    def distribute_rewards(self, current_block_number: int) -> List[dict]:
        """
        Distribute staking rewards to active stakers based on their proportional contribution
        
        Args:
            current_block_number: Current block number
            
        Returns:
            List of reward transaction details
        """
        if not self.should_distribute_rewards(current_block_number):
            return []
            
        with self.lock:
            if not self.stakers:
                logger.info("No stakers registered for reward distribution")
                return []
                
            # Verify each staker's balance and collect valid stakers
            valid_stakers = {}  # address -> verified_balance
            total_verified_stake = 0
            
            logger.info("Verifying balances for %d stakers before reward distribution", len(self.stakers))
            
            for address in self.stakers:
                # Verify balance from blockchain
                verified_balance = self.verify_staker_balance(address)
                
                if verified_balance is None:
                    logger.warning("Could not verify balance for staker %s, excluding from rewards", bin2hstr(address))
                    continue
                    
                # Check if balance meets minimum requirements
                if verified_balance <= 0:
                    logger.warning("Staker %s has zero balance, excluding from rewards", bin2hstr(address))
                    continue
                    
                if verified_balance < self.dev_config.staking_min_balance:
                    logger.warning("Staker %s balance below minimum (%d < %d), excluding from rewards", 
                                 bin2hstr(address), verified_balance, self.dev_config.staking_min_balance)
                    continue
                
                # Valid staker - add to distribution list
                valid_stakers[address] = verified_balance
                total_verified_stake += verified_balance
                
            if not valid_stakers:
                logger.info("No valid stakers found for reward distribution")
                return []
                
            if total_verified_stake == 0:
                logger.warning("Total verified stake is zero, cannot distribute rewards")
                return []
                
            total_reward = self.dev_config.staking_reward_amount
            logger.info("Distributing %d QBC total rewards to %d valid stakers (total stake: %d QBC)", 
                       total_reward // 1000000000, len(valid_stakers), total_verified_stake // 1000000000)
            
            # Calculate proportional rewards for each staker
            reward_outputs = []
            total_distributed = 0
            
            for address, verified_balance in valid_stakers.items():
                # Calculate this staker's share of total stake
                stake_percentage = verified_balance / total_verified_stake
                reward_amount = int(total_reward * stake_percentage)
                
                if reward_amount > 0:
                    reward_outputs.append({
                        'recipient': address,
                        'amount': reward_amount,
                        'stake_balance': verified_balance,
                        'stake_percentage': stake_percentage * 100,
                        'block_number': current_block_number
                    })
                    total_distributed += reward_amount
                    
                    logger.debug("Staker %s: %d QBC stake (%.2f%%) = %d QBC reward", 
                               bin2hstr(address), verified_balance // 1000000000, 
                               stake_percentage * 100, reward_amount // 1000000000)
            
            if not reward_outputs:
                logger.warning("No reward outputs generated")
                return []
                
            logger.info("Generated %d reward outputs, total distributed: %d QBC", 
                       len(reward_outputs), total_distributed // 1000000000)
            
            # Create reward transactions if donor wallet is loaded
            if self.is_donor_wallet_loaded() and self.chain_manager:
                try:
                    self._create_reward_transactions(reward_outputs)
                    self.last_reward_block = current_block_number
                    self.save_stakers_to_db()  # Save updated last reward block
                    logger.info("Reward distribution completed for block %d", current_block_number)
                except Exception as e:
                    logger.error("Failed to create reward transactions: %s", str(e))
            else:
                logger.warning("Cannot create reward transactions - donor wallet not loaded or chain manager not available")
            
            return reward_outputs
            
    def _create_reward_transactions(self, reward_outputs: List[dict]) -> List[dict]:
        """
        Create reward transactions with multiple outputs
        Split into multiple transactions if outputs exceed maximum
        
        Args:
            reward_outputs: List of reward output dictionaries
            
        Returns:
            List of created transaction hashes
        """
        if not self.is_donor_wallet_loaded():
            logger.warning("Donor wallet not loaded for reward transactions")
            return []
            
        max_outputs = getattr(self.dev_config, 'staking_max_outputs_per_tx', 100)
        transactions_created = []
        
        # Split rewards into chunks based on max outputs per transaction
        for i in range(0, len(reward_outputs), max_outputs):
            chunk = reward_outputs[i:i + max_outputs]
            
            try:
                tx_hash = self._create_single_reward_transaction(chunk)
                if tx_hash:
                    transactions_created.append({
                        'transaction_hash': tx_hash,
                        'outputs_count': len(chunk),
                        'total_amount': sum(output['amount'] for output in chunk)
                    })
                    logger.info("Created reward transaction %s with %d outputs", 
                              tx_hash, len(chunk))
                else:
                    logger.error("Failed to create reward transaction for chunk %d", i // max_outputs + 1)
                    
            except Exception as e:
                logger.error("Error creating reward transaction chunk %d: %s", 
                           i // max_outputs + 1, str(e))
                
        return transactions_created
        
    def _create_single_reward_transaction(self, reward_outputs: List[dict]) -> Optional[str]:
        """
        Create a single reward transaction with multiple outputs
        
        Args:
            reward_outputs: List of reward outputs for this transaction
            
        Returns:
            Transaction hash if successful, None otherwise
        """
        try:
            donor_address = self.donor_wallet_manager.get_address_bytes()
            donor_private_key = self.donor_wallet_manager.get_private_key_bytes()
            
            if not donor_address or not donor_private_key:
                logger.error("Cannot get donor wallet keys")
                return None
                
            # Prepare transaction outputs
            addrs_to = []
            amounts = []
            
            for output in reward_outputs:
                addrs_to.append(output['recipient'])
                amounts.append(output['amount'])
                
            # Calculate total amount and fee
            total_amount = sum(amounts)
            fee = 1000000  # 0.001 QBC fee in Quarks
            
            # Create transfer transaction using the same pattern as create_transaction.py
            logger.info("Creating reward transaction: %d QBC from %s to %d recipients", 
                       total_amount // 1000000000, 
                       bin2hstr(donor_address), 
                       len(addrs_to))
            
            # Get donor wallet info
            donor_wallet_info = self.donor_wallet_manager.get_wallet_info()
            if not donor_wallet_info:
                logger.error("Cannot get donor wallet info")
                return None
                
            # Convert public key from hex to bytes
            if 'public_key_hex' in donor_wallet_info:
                public_key_bytes = bytes.fromhex(donor_wallet_info['public_key_hex'])
            elif 'public_key' in donor_wallet_info:
                public_key_bytes = bytes.fromhex(donor_wallet_info['public_key'])
            else:
                logger.error("No public key found in donor wallet info")
                return None
                
            logger.debug("Public key type: %s, length: %d", type(public_key_bytes), len(public_key_bytes))
                
            # Create transaction manually (like create_transaction.py does)
            tx = TransferTransaction()
            tx._data.public_key = public_key_bytes
            
            # Add all recipient addresses and amounts
            for i, output in enumerate(reward_outputs):
                recipient_bytes = output['recipient']
                # Ensure recipient is bytes (convert if needed)
                if not isinstance(recipient_bytes, bytes):
                    recipient_bytes = bytes(recipient_bytes)
                    
                logger.debug("Adding recipient %d: type=%s, length=%d", i, type(recipient_bytes), len(recipient_bytes))
                tx._data.transfer.addrs_to.append(recipient_bytes)
                tx._data.transfer.amounts.append(output['amount'])
            
            # Set fee (same as create_transaction.py)
            tx._data.fee = 1000000  # 1 million quark fee
            
            # Set master_addr to donor address (like create_transaction.py)
            tx._data.master_addr = donor_address
            
            # Add optional message data
            tx._data.transfer.message_data = b'Staking Reward'
            
            # Get transaction data hash for signing (like create_transaction.py)
            tx_data = tx.get_data_hash()
            
            # Sign the transaction with donor wallet private key
            from qbitcoin.crypto.falcon import FalconSignature
            signature = FalconSignature.sign_message(tx_data, donor_private_key)
            tx._data.signature = signature
            
            # Update transaction hash after signing (like create_transaction.py)
            tx.update_txhash()
            
            # Submit transaction via gRPC to local node (like create_transaction.py)
            if self._submit_transaction_via_grpc(tx):
                logger.info("Reward transaction submitted via gRPC successfully: %s", bin2hstr(tx.txhash))
                return bin2hstr(tx.txhash)
            else:
                logger.error("Failed to submit reward transaction via gRPC")
                return None
            
        except Exception as e:
            logger.error("Error creating single reward transaction: %s", str(e))
            return None
            
    def _submit_transaction_via_grpc(self, tx) -> bool:
        """
        Submit transaction via gRPC to local node (like create_transaction.py does)
        
        Args:
            tx: The transaction to submit
            
        Returns:
            bool: True if successfully submitted, False otherwise
        """
        try:
            import grpc
            from qbitcoin.generated import qbit_pb2, qbit_pb2_grpc
            
            # Set up the gRPC connection to local node
            channel = grpc.insecure_channel("localhost:19009")
            stub = qbit_pb2_grpc.PublicAPIStub(channel)
            
            # Create the push transaction request (like create_transaction.py)
            push_transaction_req = qbit_pb2.PushTransactionReq(transaction_signed=tx.pbdata)
            
            logger.info("Submitting reward transaction via gRPC to local node...")
            push_transaction_resp = stub.PushTransaction(push_transaction_req, timeout=5)
            
            if push_transaction_resp.error_code == qbit_pb2.PushTransactionResp.SUBMITTED:
                logger.info("Reward transaction successfully submitted via gRPC!")
                return True
            else:
                logger.error("Reward transaction submission failed: %s", push_transaction_resp.error_description)
                return False
                
        except Exception as e:
            logger.error("Error submitting transaction via gRPC: %s", str(e))
            return False
            
        except Exception as e:
            logger.error("Error creating single reward transaction: %s", str(e))
            return None
        
    def _broadcast_staker_update(self, address: bytes, action: str, balance: int):
        """Broadcast staker updates to the network"""
        # Check if node is synced and has peer connections
        if not self.is_node_synced or not self.p2p_factory or self.p2p_factory.num_connections == 0:
            # Queue for later broadcast when node is synced
            with self.lock:
                self.pending_broadcasts.append((address, action, balance))
                logger.info("Queued staker %s: %s for broadcast when synced (connections: %d)", 
                           action, bin2hstr(address), 
                           self.p2p_factory.num_connections if self.p2p_factory else 0)
            return
            
        if self.p2p_factory:
            message = {
                'type': 'staker_update',
                'action': action,  # 'add' or 'remove'
                'address': bin2hstr(address),
                'balance': balance,
                'timestamp': time.time(),
                'node_id': 'local'  # Could be node identifier
            }
            try:
                # Send to all connected peers
                self.p2p_factory.broadcast_staker_message(message)
                logger.info("Broadcasted staker %s: %s", action, bin2hstr(address))
            except Exception as e:
                logger.error("Failed to broadcast staker update: %s", str(e))
        else:
            logger.debug("No P2P factory available for broadcasting staker update")
            
    def on_node_synced(self):
        """Called when the node becomes synced"""
        with self.lock:
            self.is_node_synced = True
            logger.info("Node synced - staking manager ready for P2P operations")
            
    def handle_peer_staker_message(self, message: dict, peer_ip: str):
        """Handle staker messages received from peers"""
        try:
            if message.get('type') != 'staker_update':
                return
                
            action = message.get('action')
            address_hex = message.get('address')
            
            if not address_hex:
                logger.warning("Invalid staker message from %s: missing address", peer_ip)
                return
                
            if not isinstance(address_hex, str):
                logger.error("Invalid address type from peer %s: expected str, got %s", peer_ip, type(address_hex))
                return
                
            try:
                address_bytes = hstr2bin(address_hex)
            except Exception as e:
                logger.error("Failed to convert address from peer %s: %s", peer_ip, str(e))
                return
            
            if action == 'add':
                # Verify balance from blockchain before adding
                balance = self.verify_staker_balance(address_bytes)
                if balance is None:
                    logger.warning("Invalid staker from peer %s: %s", peer_ip, address_hex)
                    return
                
                logger.info("Received valid staker add from peer %s: %s (verified balance: %d)", 
                           peer_ip, address_hex, balance)
                
                # Add the staker
                self.add_staker(address_bytes, peer_ip)
                
            elif action == 'remove':
                logger.info("Received staker remove from peer %s: %s", peer_ip, address_hex)
                self.remove_staker(address_bytes, f"removed by peer {peer_ip}")
            else:
                logger.warning("Unknown staker action from peer %s: %s", peer_ip, action)
                
        except Exception as e:
            logger.error("Error handling peer staker message from %s: %s", peer_ip, str(e))
            
    def get_stakers_for_sync(self) -> List[dict]:
        """Get all valid stakers for peer synchronization"""
        active_stakers = self.get_active_stakers()
        
        return [
            {
                'type': 'staker_update',
                'action': 'add',
                'address': bin2hstr(address),
                'balance': balance,
                'timestamp': time.time()
            }
            for address, balance in active_stakers.items()
        ]
            
     
    def get_validated_stakers_for_sync(self) -> List[dict]:
        """Get validated stakers for peer synchronization - same as get_stakers_for_sync"""
        return self.get_stakers_for_sync()
            
    def get_staking_statistics(self) -> dict:
        """Get current staking statistics"""
        active_stakers = self.get_active_stakers()
        total_stake = sum(active_stakers.values())
        
        return {
            'total_stakers': len(self.stakers),
            'active_stakers': len(active_stakers),
            'total_stake': total_stake,
            'donor_wallet': self.get_donor_wallet_address(),
            'donor_wallet_loaded': self.is_donor_wallet_loaded(),
            'last_reward_block': self.last_reward_block,
            'staking_enabled': self.dev_config.staking_enabled if self.dev_config else False,
            'reward_interval': self.dev_config.staking_reward_interval if self.dev_config else 60,
            'reward_amount_qbc': (self.dev_config.staking_reward_amount // 1000000000) if self.dev_config else 0,
            'min_balance_qbc': (self.dev_config.staking_min_balance // 1000000000) if self.dev_config else 0
        }
        
    def handle_new_block(self, block):
        """Handle new block events for reward distribution"""
        logger.debug("StakingManager.handle_new_block called for block %d", block.block_number)
        logger.debug("Last reward block: %d, Current block: %d, Interval: %d", 
                    self.last_reward_block, block.block_number, 
                    self.dev_config.staking_reward_interval if self.dev_config else 0)
        
        if self.should_distribute_rewards(block.block_number):
            logger.info("Attempting to distribute rewards for block %d", block.block_number)
            rewards = self.distribute_rewards(block.block_number)
            if rewards:
                logger.info("Distributed %d rewards for block %d", len(rewards), block.block_number)
            else:
                logger.warning("Failed to distribute rewards for block %d", block.block_number)
        else:
            logger.debug("Not time to distribute rewards for block %d", block.block_number)
            
    def request_staker_list_from_peer(self, peer_ip: str):
        """Request staker list from a specific peer (like requesting blocks)"""
        if self.p2p_factory:
            try:
                message = {
                    'type': 'staker_list_request',
                    'timestamp': time.time(),
                    'node_id': 'local'
                }
                self.p2p_factory.send_message_to_peer(peer_ip, message)
                logger.info("Requested staker list from peer: %s", peer_ip)
            except Exception as e:
                logger.error("Failed to request staker list from peer %s: %s", peer_ip, str(e))
                
    def handle_staker_list_request(self, peer_ip: str):
        """Handle staker list request from peer and send our staker list"""
        try:
            staker_list = self.get_stakers_for_sync()
            message = {
                'type': 'staker_list_response',
                'stakers': staker_list,
                'timestamp': time.time(),
                'node_id': 'local'
            }
            
            if self.p2p_factory:
                self.p2p_factory.send_message_to_peer(peer_ip, message)
                logger.info("Sent staker list (%d stakers) to peer: %s", len(staker_list), peer_ip)
                
        except Exception as e:
            logger.error("Failed to send staker list to peer %s: %s", peer_ip, str(e))
            
    def handle_staker_list_response(self, staker_list: List[dict], peer_ip: str):
        """Handle staker list response from peer - validate and add stakers"""
        if not staker_list:
            logger.info("Received empty staker list from peer: %s", peer_ip)
            return
            
        logger.info("Received staker list with %d stakers from peer: %s", len(staker_list), peer_ip)
        
        added_count = 0
        for staker_data in staker_list:
            try:
                address_hex = staker_data.get('address')
                if not address_hex:
                    continue
                    
                address_bytes = hstr2bin(address_hex)
                
                # Verify this staker is not already in our list (no duplicates)
                if address_bytes in self.stakers:
                    continue
                    
                # Verify balance from blockchain
                balance = self.verify_staker_balance(address_bytes)
                if balance is None:
                    logger.warning("Invalid staker from peer %s: %s (failed balance verification)", 
                                 peer_ip, address_hex)
                    continue
                    
                # Add the verified staker
                if self.add_staker(address_bytes, peer_ip):
                    added_count += 1
                    
            except Exception as e:
                logger.error("Error processing staker from peer %s: %s", peer_ip, str(e))
                
        logger.info("Added %d new verified stakers from peer: %s", added_count, peer_ip)
        
    def broadcast_staker_to_peers(self, address: bytes, action: str):
        """Broadcast staker add/remove to all connected peers"""
        if not self.p2p_factory or not self.is_node_synced:
            return
            
        try:
            message = {
                'type': 'staker_update',
                'action': action,  # 'add' or 'remove'
                'address': bin2hstr(address),
                'timestamp': time.time(),
                'node_id': 'local'
            }
            
            if self.p2p_factory.num_connections > 0:
                self.p2p_factory.broadcast_staker_message(message)
                logger.info("Broadcasted staker %s to peers: %s", action, bin2hstr(address))
            else:
                logger.debug("No peer connections for broadcasting staker %s: %s", action, bin2hstr(address))
                
        except Exception as e:
            logger.error("Failed to broadcast staker update: %s", str(e))
            
    def _monitor_rewards(self):
        """Monitor and distribute rewards automatically when interval is reached"""
        while self._reward_monitoring:
            try:
                if (self.dev_config and 
                    self.dev_config.staking_enabled and 
                    self.is_donor_wallet_loaded() and 
                    self.chain_manager):
                    
                    # Get current block number
                    try:
                        current_block = self.chain_manager.last_block
                        if current_block and self.should_distribute_rewards(current_block.block_number):
                            logger.info("Reward monitor: Time to distribute rewards for block %d", current_block.block_number)
                            rewards = self.distribute_rewards(current_block.block_number)
                            if rewards:
                                logger.info("Reward monitor: Successfully distributed %d rewards", len(rewards))
                            else:
                                logger.debug("Reward monitor: No rewards distributed (no active stakers or other issue)")
                    except Exception as e:
                        logger.error("Error in reward monitoring: %s", str(e))
                
                # Periodic staker validation (removes stakers with insufficient balance)
                try:
                    self.periodic_staker_validation()
                except Exception as e:
                    logger.error("Error in periodic staker validation: %s", str(e))
                
                # Check every 30 seconds
                time.sleep(30)
                
            except Exception as e:
                logger.error("Error in reward monitoring loop: %s", str(e))
                time.sleep(30)
                
    def stop(self):
        """Stop the staking manager"""
        self._reward_monitoring = False
        if hasattr(self, '_reward_thread') and self._reward_thread.is_alive():
            self._reward_thread.join(timeout=5)
