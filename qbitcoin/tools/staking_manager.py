#!/usr/bin/env python3
# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

"""
Qbitcoin Staking Management CLI Tool

This tool provides command-line interface for managing staking operations:
- Start/stop staking
- View staking information
- Set donor wallet
- Monitor staker status
"""

import argparse
import sys
from pyqrllib.pyqrllib import hstr2bin, bin2hstr

from qbitcoin.core.config import config
from qbitcoin.core.Staker import StakingManager
from qbitcoin.core.ChainManager import ChainManager
from qbitcoin.core.State import State
from qbitcoin.core.GenesisBlock import GenesisBlock
from qbitcoin.core.Block import Block


def parse_arguments():
    parser = argparse.ArgumentParser(description='Qbitcoin Staking Management Tool')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start staking command
    start_parser = subparsers.add_parser('start', help='Start staking for an address')
    start_parser.add_argument('address', help='Qbitcoin address to start staking (with Q prefix)')
    
    # Stop staking command  
    stop_parser = subparsers.add_parser('stop', help='Stop staking for an address')
    stop_parser.add_argument('address', help='Qbitcoin address to stop staking (with Q prefix)')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show staking status and information')
    
    # List stakers command
    list_parser = subparsers.add_parser('list', help='List all active stakers')
    
    # Set donor wallet command
    donor_parser = subparsers.add_parser('donor', help='Set donor wallet for rewards')
    donor_parser.add_argument('address', help='Donor wallet address (with Q prefix)')
    
    # Heartbeat command
    heartbeat_parser = subparsers.add_parser('heartbeat', help='Send heartbeat for a staker')
    heartbeat_parser.add_argument('address', help='Staker address (with Q prefix)')
    
    # Common arguments
    parser.add_argument('--qrldir', '-d', dest='qrl_dir', default=config.user.qrl_dir,
                        help="Use a different directory for node data/configuration")
    parser.add_argument('--network-type', dest='network_type', choices=['mainnet', 'testnet'],
                        default='mainnet', required=False, help="Network type")
    
    return parser.parse_args()


def validate_address(address: str) -> bytes:
    """Validate and convert Qbitcoin address"""
    if not address.startswith('Q'):
        raise ValueError("Address must start with 'Q'")
    
    if len(address) != 51:  # Q + 50 hex chars
        raise ValueError("Invalid address length")
    
    try:
        address_bytes = bytes(hstr2bin(address[1:]))
        return address_bytes
    except Exception as e:
        raise ValueError(f"Invalid address format: {e}")


def initialize_chain_manager():
    """Initialize chain manager for staking operations"""
    persistent_state = State()
    chain_manager = ChainManager(state=persistent_state)
    chain_manager.load(Block.deserialize(GenesisBlock().serialize()))
    return chain_manager


def cmd_start_staking(args):
    """Start staking for an address"""
    try:
        address_bytes = validate_address(args.address)
        
        chain_manager = initialize_chain_manager()
        staking_manager = StakingManager()
        staking_manager.set_chain_manager(chain_manager)
        
        dev_config = chain_manager.get_config_by_block_number(chain_manager.height)
        staking_manager.set_dev_config(dev_config)
        
        if staking_manager.add_staker(address_bytes):
            print(f"✅ Successfully started staking for address: {args.address}")
            return True
        else:
            print(f"❌ Failed to start staking for address: {args.address}")
            print("Check if the address has sufficient balance and meets requirements.")
            return False
            
    except Exception as e:
        print(f"❌ Error starting staking: {e}")
        return False


def cmd_stop_staking(args):
    """Stop staking for an address"""
    try:
        address_bytes = validate_address(args.address)
        
        staking_manager = StakingManager()
        
        if staking_manager.remove_staker(address_bytes, "manual_stop"):
            print(f"✅ Successfully stopped staking for address: {args.address}")
            return True
        else:
            print(f"❌ Failed to stop staking for address: {args.address}")
            print("Address may not be currently staking.")
            return False
            
    except Exception as e:
        print(f"❌ Error stopping staking: {e}")
        return False


def cmd_show_status(args):
    """Show staking status and information"""
    try:
        staking_manager = StakingManager()
        stats = staking_manager.get_staking_statistics()
        
        print("🏛️  QBITCOIN STAKING STATUS")
        print("=" * 50)
        print(f"Staking Enabled:      {stats['staking_enabled']}")
        print(f"Total Stakers:        {stats['total_stakers']}")
        print(f"Active Stakers:       {stats['active_stakers']}")
        print(f"Total Stake:          {stats['total_stake'] // 1000000000} QBC")
        print(f"Donor Wallet:         {stats['donor_wallet'] or 'Not set'}")
        print(f"Donor Wallet Loaded:  {stats.get('donor_wallet_loaded', False)}")
        print(f"Last Reward Block:    {stats['last_reward_block']}")
        print(f"Reward Interval:      {stats.get('reward_interval', 60)} blocks")
        print(f"Reward Amount:        {stats.get('reward_amount_qbc', 0)} QBC")
        print(f"Min Balance:          {stats.get('min_balance_qbc', 0)} QBC")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting staking status: {e}")
        return False


def cmd_list_stakers(args):
    """List all active stakers"""
    try:
        staking_manager = StakingManager()
        active_stakers = staking_manager.get_active_stakers()
        
        if not active_stakers:
            print("📭 No active stakers found.")
            return True
        
        print("👥 ACTIVE STAKERS")
        print("=" * 90)
        print(f"{'Address':<51} {'Balance (QBC)':<15} {'Share %':<10} {'Online':<8}")
        print("-" * 90)
        
        total_stake = staking_manager.get_total_stake()
        
        for address, stake_info in active_stakers.items():
            address_str = 'Q' + bin2hstr(address)
            balance_qbc = stake_info.balance // 1000000000  # Convert Quarks to QBC
            share_percent = stake_info.get_stake_share(total_stake) * 100
            online_status = "✅" if stake_info.is_online else "❌"
            
            print(f"{address_str:<51} {balance_qbc:<15} {share_percent:<10.2f} {online_status:<8}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error listing stakers: {e}")
        return False


def cmd_set_donor_wallet(args):
    """Set donor wallet for staking rewards"""
    try:
        address_bytes = validate_address(args.address)
        
        staking_manager = StakingManager()
        staking_manager.set_donor_wallet(address_bytes)
        
        print(f"Successfully set donor wallet: {args.address}")
        return True
        
    except Exception as e:
        print(f" Error setting donor wallet: {e}")
        return False


def cmd_heartbeat(args):
    """Send heartbeat for a staker"""
    try:
        address_bytes = validate_address(args.address)
        
        staking_manager = StakingManager()
        staking_manager.update_staker_online_status(address_bytes)
        
        print(f"💓 Heartbeat sent for address: {args.address}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending heartbeat: {e}")
        return False


def main():
    args = parse_arguments()
    
    # Set up configuration
    if args.network_type == 'testnet':
        config.dev.hard_fork_heights = list(config.dev.testnet_hard_fork_heights)
        config.dev.hard_fork_node_disconnect_delay = list(config.dev.testnet_hard_fork_node_disconnect_delay)
    
    config.user.qrl_dir = args.qrl_dir
    config.create_path(config.user.qrl_dir)
    
    # Execute command
    success = False
    
    if args.command == 'start':
        success = cmd_start_staking(args)
    elif args.command == 'stop':
        success = cmd_stop_staking(args)
    elif args.command == 'status':
        success = cmd_show_status(args)
    elif args.command == 'list':
        success = cmd_list_stakers(args)
    elif args.command == 'donor':
        success = cmd_set_donor_wallet(args)
    elif args.command == 'heartbeat':
        success = cmd_heartbeat(args)
    else:
        print("❌ No command specified. Use --help for usage information.")
        return 1
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
