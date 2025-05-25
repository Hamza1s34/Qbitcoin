
"""
Difficulty Adjustment Algorithm for Qbitcoin

This module implements the difficulty adjustment algorithm used by Qbitcoin
to maintain a target block time. The algorithm is designed to adjust the mining
difficulty based on how quickly blocks are being found compared to the target time.
"""

import os
import sys
from typing import Dict, Any

# Import configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from core import config

# Import required utilities
from utils.logger import get_logger

# Initialize logger
logger = get_logger("difficulty_adjuster")

def adjust_difficulty(prev_difficulty: float, actual_timespan: int, 
                      expected_timespan: int, min_difficulty: float, log_info: bool = True) -> float:
    """
    Calculate the new mining difficulty based on previous blocks timespan.
    
    Args:
        prev_difficulty: Previous difficulty value
        actual_timespan: Actual time (in seconds) it took to mine the last N blocks
        expected_timespan: Expected time (in seconds) it should have taken
        min_difficulty: Minimum allowed difficulty
        log_info: Whether to log information about the difficulty calculation
        
    Returns:
        New difficulty value
    """
    # Log adjustment parameters
    if log_info:
        logger.info(f"Adjusting difficulty. Previous: {prev_difficulty:.8f}")
        logger.info(f"Actual timespan: {actual_timespan}s, Expected: {expected_timespan}s")
    
    # Handle edge cases
    if actual_timespan <= 0:
        if log_info:
            logger.warning("Invalid actual timespan (≤ 0), using expected timespan")
        actual_timespan = expected_timespan
    
    # Limit adjustment to prevent extreme difficulty swings
    # Don't allow the timespan to be less than 1/4 or more than 4x the expected
    if actual_timespan < expected_timespan // 4:
        actual_timespan = expected_timespan // 4
        if log_info:
            logger.info(f"Limiting minimum actual timespan to {actual_timespan}s")
    
    if actual_timespan > expected_timespan * 4:
        actual_timespan = expected_timespan * 4
        if log_info:
            logger.info(f"Limiting maximum actual timespan to {actual_timespan}s")
    
    # Calculate new difficulty with precision
    ratio = float(expected_timespan) / float(actual_timespan)
    new_difficulty = prev_difficulty * ratio
    
    # Ensure minimum difficulty
    if new_difficulty < min_difficulty:
        new_difficulty = min_difficulty
        if log_info:
            logger.info(f"Enforcing minimum difficulty: {min_difficulty:.8f}")
    
    # Round to specified precision to avoid floating point issues
    new_difficulty = round(new_difficulty, config.DIFFICULTY_PRECISION)
    
    # Log the adjustment
    if log_info:
        change_pct = (new_difficulty - prev_difficulty) / prev_difficulty * 100
        logger.info(f"New difficulty: {new_difficulty:.8f} ({change_pct:+.2f}%)")
    
    return new_difficulty

def calculate_work_from_difficulty(difficulty: float) -> float:
    """
    Calculate the amount of computational work represented by a difficulty value.
    This is used for chain work calculations and comparing chains.
    
    Args:
        difficulty: Block difficulty value
        
    Returns:
        Work value (higher means more work)
    """
    # Work is proportional to 2^difficulty (exponential relationship)
    # This is the standard way to calculate work from difficulty
    return 2.0 ** difficulty

def calculate_difficulty_from_target(target: int) -> float:
    """
    Convert a target value to a difficulty value
    
    Args:
        target: Target value (lower means more difficult)
        
    Returns:
        Difficulty value (higher means more difficult)
    """
    # Maximum target (lowest difficulty)
    max_target = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
    
    # Difficulty is the ratio between max_target and current target
    if target <= 0:
        return config.INITIAL_DIFFICULTY  # Avoid division by zero
        
    difficulty = float(max_target) / float(target)
    
    # Round to specified precision
    difficulty = round(difficulty, config.DIFFICULTY_PRECISION)
    
    return max(difficulty, config.MINIMUM_DIFFICULTY)

def calculate_next_retarget_block(current_height: int) -> int:
    """
    Calculate the next block height where difficulty will be adjusted
    
    Args:
        current_height: Current block height
        
    Returns:
        Next retarget block height
    """
    adjustment_blocks = config.DIFFICULTY_ADJUSTMENT_BLOCKS
    
    # Get the next multiple of adjustment_blocks
    next_retarget = ((current_height // adjustment_blocks) + 1) * adjustment_blocks
    
    return next_retarget

def get_difficulty_info(blockchain, log_info: bool = True) -> Dict[str, Any]:
    """
    Get detailed information about current difficulty
    
    Args:
        blockchain: Reference to the blockchain object
        log_info: Whether to log information about the difficulty calculation
        
    Returns:
        Dictionary with difficulty information
    """
    # Get current block
    current_block = blockchain.get_best_block()
    
    if not current_block:
        return {
            "current_difficulty": config.INITIAL_DIFFICULTY,
            "next_difficulty": config.INITIAL_DIFFICULTY,
            "blocks_until_adjustment": config.DIFFICULTY_ADJUSTMENT_BLOCKS,
            "next_adjustment_height": config.DIFFICULTY_ADJUSTMENT_BLOCKS,
            "estimated_adjustment_percent": 0,
            "mining_algorithm": config.MINING_ALGORITHM
        }
    
    current_height = current_block.height
    current_difficulty = current_block.difficulty
    
    # Calculate next adjustment height
    next_adjustment_height = calculate_next_retarget_block(current_height)
    blocks_until_adjustment = next_adjustment_height - current_height
    
    # If we're at an adjustment block or we don't have enough history, return current difficulty
    if blocks_until_adjustment == config.DIFFICULTY_ADJUSTMENT_BLOCKS or current_height < config.DIFFICULTY_ADJUSTMENT_BLOCKS:
        estimated_next_difficulty = current_difficulty
        estimated_adjustment_percent = 0
    else:
        # Try to estimate next difficulty based on recent blocks
        start_height = next_adjustment_height - config.DIFFICULTY_ADJUSTMENT_BLOCKS
        start_block = blockchain.get_block_by_height(start_height)
        
        if start_block:
            # Calculate current timespan
            current_timespan = current_block.timestamp - start_block.timestamp
            blocks_mined = current_height - start_height
            
            # Estimate the full timespan based on the current rate
            if blocks_mined > 0:
                block_time_avg = current_timespan / blocks_mined
                estimated_total_timespan = block_time_avg * config.DIFFICULTY_ADJUSTMENT_BLOCKS
                
                # Estimate difficulty change
                estimated_next_difficulty = adjust_difficulty(
                    current_difficulty,
                    estimated_total_timespan,
                    config.DIFFICULTY_ADJUSTMENT_TIMESPAN,
                    config.MINIMUM_DIFFICULTY,
                    log_info=log_info
                )
                
                estimated_adjustment_percent = (estimated_next_difficulty - current_difficulty) / current_difficulty * 100
            else:
                estimated_next_difficulty = current_difficulty
                estimated_adjustment_percent = 0
        else:
            estimated_next_difficulty = current_difficulty
            estimated_adjustment_percent = 0
    
    return {
        "current_difficulty": current_difficulty,
        "next_difficulty": estimated_next_difficulty,
        "blocks_until_adjustment": blocks_until_adjustment,
        "next_adjustment_height": next_adjustment_height,
        "estimated_adjustment_percent": estimated_adjustment_percent,
        "mining_algorithm": config.MINING_ALGORITHM
    }