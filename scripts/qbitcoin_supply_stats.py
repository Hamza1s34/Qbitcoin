# coding=utf-8
"""
Script to print Qbitcoin block reward, halving, and supply stats for the next 20 years.
"""
import decimal
from decimal import Decimal
from datetime import datetime, timedelta
from qbitcoin.core.formulas import block_reward, remaining_emission, get_halving_interval
from qbitcoin.core.config import DevConfig

# Set decimal precision
decimal.getcontext().prec = 18

INITIAL_REWARD = Decimal('2.5')
BLOCK_TIME_SECONDS = 60
DECIMALS = 9
YEARS = 20

# Example DevConfig (adjust as needed)
class DummyDevConfig:
    quark_per_qbitcoin = Decimal('1e9')
    coin_remaining_at_genesis = Decimal('10_000_000')  # 10M Qbitcoin for mining

dev_config = DummyDevConfig()

start_year = datetime.now().year
start_block = 1

print(f"{'Year':<6} {'Block':<10} {'Reward (QBTC)':<15} {'Remaining Supply':<20} {'Halving?':<8}")
print('-' * 65)

for year in range(YEARS + 1):
    block_number = start_block + year * (365 * 24 * 60 * 60) // BLOCK_TIME_SECONDS
    reward = block_reward(block_number, dev_config) / dev_config.quark_per_qbitcoin
    remaining = remaining_emission(block_number, dev_config) / dev_config.quark_per_qbitcoin
    halving_interval = get_halving_interval(dev_config)
    halving = 'Yes' if (block_number - 1) % halving_interval == 0 and block_number > 1 else ''
    print(f"{start_year + year:<6} {block_number:<10} {reward:<15,.9f} {remaining:<20,.9f} {halving:<8}")


# Optimized: Use binary search to find the block where remaining supply reaches zero
def find_mining_end_block(start_block, max_block, dev_config):
    low = start_block
    high = max_block
    while low < high:
        mid = (low + high) // 2
        if remaining_emission(mid, dev_config) > 0:
            low = mid + 1
        else:
            high = mid
    return low

# Estimate a reasonable upper bound for block search (e.g., 100 years of blocks)
max_block = start_block + int((100 * 365.25 * 24 * 60 * 60) // BLOCK_TIME_SECONDS)
block = find_mining_end_block(start_block, max_block, dev_config)

years_to_finish = (block - start_block) * BLOCK_TIME_SECONDS / (365.25 * 24 * 60 * 60)
print(f"\nEstimated years to mine all 10 million QBTC: {years_to_finish:.2f} years (block {block})")

# Find the last halving block before mining ends
halving_interval_last = get_halving_interval(dev_config, block)
last_halving_block = ((block - 1) // halving_interval_last) * halving_interval_last + 1
last_halving_reward = block_reward(last_halving_block, dev_config) / dev_config.quark_per_qbitcoin
last_halving_remaining = remaining_emission(last_halving_block, dev_config) / dev_config.quark_per_qbitcoin
print(f"Reward at last halving (block {last_halving_block}): {last_halving_reward:.9f} QBTC")
print(f"Remaining supply at last halving: {last_halving_remaining:.9f} QBTC out of 10,000,000 minable")
