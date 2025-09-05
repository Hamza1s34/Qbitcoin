# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

from qbitcoin.core.txs.Transaction import Transaction
from qbitcoin.core.StateContainer import StateContainer
from qbitcoin.core.misc import logger
from pyqrllib.pyqrllib import bin2hstr


class StakingTransaction(Transaction):
    """
    StakingTransaction is used for off-chain staking operations
    It includes staking start/stop commands and heartbeat messages
    """

    def __init__(self, protobuf_transaction=None):
        super(StakingTransaction, self).__init__(protobuf_transaction)

    @property
    def staking_action(self):
        """Action: 'start', 'stop', 'heartbeat'"""
        return self._data.staking.action.decode('utf-8')

    @property
    def staker_address(self):
        """Address of the staker"""
        return self._data.staking.staker_address

    @property
    def stake_amount(self):
        """Amount being staked (for start action)"""
        return self._data.staking.stake_amount

    def get_data_bytes(self):
        return (self.master_addr +
                self._data.staking.action +
                self._data.staking.staker_address +
                self.stake_amount.to_bytes(8, byteorder='big', signed=False) +
                self.nonce.to_bytes(8, byteorder='big', signed=False))

    @staticmethod
    def create(action: str,
               staker_address: bytes,
               stake_amount: int,
               fee: int,
               xmss_pk: bytes,
               master_addr: bytes = None):
        """
        Create a staking transaction
        
        Args:
            action: 'start', 'stop', or 'heartbeat'
            staker_address: Address of the staker
            stake_amount: Amount to stake (for start action)
            fee: Transaction fee
            xmss_pk: XMSS public key
            master_addr: Master address (defaults to staker_address)
        """
        transaction = StakingTransaction()
        
        if master_addr is None:
            master_addr = staker_address
            
        transaction._data.master_addr = master_addr
        transaction._data.fee = fee
        transaction._data.public_key = xmss_pk
        
        transaction._data.staking.action = action.encode('utf-8')
        transaction._data.staking.staker_address = staker_address
        transaction._data.staking.stake_amount = stake_amount
        
        transaction._data.transaction_hash = transaction.get_data_hash()
        
        return transaction

    def _validate_custom(self):
        """Custom validation for staking transactions"""
        # Validate action
        valid_actions = ['start', 'stop', 'heartbeat']
        if self.staking_action not in valid_actions:
            logger.warning('Invalid staking action: %s', self.staking_action)
            return False
            
        # Validate staker address
        if len(self.staker_address) != 32:  # Assuming 32-byte addresses
            logger.warning('Invalid staker address length')
            return False
            
        # For start action, stake amount should be positive
        if self.staking_action == 'start' and self.stake_amount <= 0:
            logger.warning('Stake amount must be positive for start action')
            return False
            
        return True

    def _validate_extended(self, state_container: StateContainer):
        """Extended validation for staking transactions"""
        dev_config = state_container.current_dev_config
        
        # Check if staking is enabled
        if not hasattr(dev_config, 'staking_enabled') or not dev_config.staking_enabled:
            logger.warning('Staking is not enabled')
            return False
            
        # For start action, validate minimum balance
        if self.staking_action == 'start':
            if hasattr(dev_config, 'staking_min_balance'):
                if self.stake_amount < dev_config.staking_min_balance:
                    logger.warning('Stake amount %d is below minimum %d', 
                                 self.stake_amount, dev_config.staking_min_balance)
                    return False
                    
        return self._validate_custom()

    def set_affected_address(self, addresses_set: set):
        """Set affected addresses for this transaction"""
        addresses_set.add(self.master_addr)
        addresses_set.add(self.staker_address)

    def apply(self, state_container: StateContainer) -> bool:
        """
        Apply staking transaction effects
        This is mainly for off-chain operations
        """
        # For off-chain staking, this doesn't modify the state
        # The actual staking logic is handled by StakingManager
        logger.info('Applied staking transaction: %s for %s', 
                   self.staking_action, bin2hstr(self.staker_address))
        return True

    def revert(self, state_container: StateContainer) -> bool:
        """
        Revert staking transaction effects
        """
        # For off-chain staking, this doesn't modify the state
        logger.info('Reverted staking transaction: %s for %s', 
                   self.staking_action, bin2hstr(self.staker_address))
        return True
