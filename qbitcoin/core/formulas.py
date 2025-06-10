# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
import decimal
from decimal import Decimal
from qbitcoin.core.config import DevConfig


def get_halving_interval(dev_config: DevConfig) -> int:
    """
    Return the number of blocks between halvings (2 years at 1 minute per block)
    2 years * 365.25 days/year * 24 hours/day * 60 minutes/hour = 1,051,200 blocks
    """
    return 2 * 365 * 24 * 60  # 2 years in minutes = 1,051,200 blocks


def get_initial_block_reward(dev_config: DevConfig) -> Decimal:
    """
    Return the initial block reward: 2.5 Qbitcoin = 2.5 * 10^9 Quark
    """
    return Decimal('2.5') * dev_config.quark_per_qbitcoin


def remaining_emission(block_n, dev_config: DevConfig) -> Decimal:
    """
    Calculate remaining emission at block_n using halving mechanism.
    Starting with 10M QRL available for mining (30M max - 20M genesis)
    Initial reward: 2.5 Qbitcoin per block
    Halving every 2 years (1,051,200 blocks)
    """
    if block_n <= 0:
        return dev_config.coin_remaining_at_genesis * dev_config.quark_per_qbitcoin
    
    halving_interval = get_halving_interval(dev_config)
    initial_reward = get_initial_block_reward(dev_config)
    
    total_mined = Decimal('0')
    current_reward = initial_reward
    blocks_processed = 0
    
    while blocks_processed < block_n:
        # How many blocks in current halving period?
        blocks_in_period = min(halving_interval, block_n - blocks_processed)
        
        # Add rewards for this period
        total_mined += current_reward * blocks_in_period
        
        blocks_processed += blocks_in_period
        current_reward = current_reward / 2  # Halve the reward
    
    remaining = dev_config.coin_remaining_at_genesis * dev_config.quark_per_qbitcoin - total_mined
    return remaining.quantize(Decimal('1.'), rounding=decimal.ROUND_DOWN)


def block_reward(block_number: int, dev_config: DevConfig) -> Decimal:
    """
    Calculate block reward using halving mechanism.
    Initial reward: 2.5 Qbitcoin per block
    Halving every 2 years (1,051,200 blocks)
    """
    if block_number <= 0:
        return Decimal('0')
    
    halving_interval = get_halving_interval(dev_config)
    initial_reward = get_initial_block_reward(dev_config)
    
    # Calculate which halving period we're in (0-based)
    halving_period = (block_number - 1) // halving_interval
    
    # Calculate current reward (halved for each period)
    current_reward = initial_reward / (Decimal('2') ** halving_period)
    
    return current_reward.quantize(Decimal('1.'), rounding=decimal.ROUND_DOWN)
