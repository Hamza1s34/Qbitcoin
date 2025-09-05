#!/usr/bin/env python3
# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

"""
Qbitcoin Donor Wallet Management CLI Tool

This tool provides command-line interface for managing donor wallets:
- Create encrypted donor wallet
- Load donor wallet
- Check donor wallet status
- Verify donor wallet password
"""

import argparse
import sys
import getpass
import os
from pyqrllib.pyqrllib import hstr2bin, bin2hstr

from qbitcoin.core.config import config
from qbitcoin.core.DonorWalletManager import DonorWalletManager


def parse_arguments():
    parser = argparse.ArgumentParser(description='Qbitcoin Donor Wallet Management Tool')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create donor wallet command
    create_parser = subparsers.add_parser('create', help='Create encrypted donor wallet')
    create_parser.add_argument('address', help='Donor wallet address (with Q prefix)')
    create_parser.add_argument('private_key', help='Private key in hex format')
    
    # Load donor wallet command  
    load_parser = subparsers.add_parser('load', help='Load and verify donor wallet')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show donor wallet status')
    
    # Verify password command
    verify_parser = subparsers.add_parser('verify', help='Verify donor wallet password')
    
    # Path command
    path_parser = subparsers.add_parser('path', help='Show donor wallet file path')
    
    # Common arguments
    parser.add_argument('--qrldir', '-d', dest='qrl_dir', default=config.user.qrl_dir,
                        help="Use a different directory for node data/configuration")
    parser.add_argument('--network-type', dest='network_type', choices=['mainnet', 'testnet'],
                        default='mainnet', required=False, help="Network type")
    
    return parser.parse_args()


def validate_address(address: str) -> bool:
    """Validate Qbitcoin address format"""
    if not address.startswith('Q'):
        print("❌ Address must start with 'Q'")
        return False
    
    if len(address) != 51:  # Q + 50 hex chars
        print("❌ Invalid address length")
        return False
    
    try:
        bytes(hstr2bin(address[1:]))
        return True
    except Exception as e:
        print(f"❌ Invalid address format: {e}")
        return False


def validate_private_key(private_key: str) -> bool:
    """Validate private key format"""
    if len(private_key) < 64:  # Minimum length for private key
        print("❌ Private key too short")
        return False
    
    try:
        bytes(hstr2bin(private_key))
        return True
    except Exception as e:
        print(f"❌ Invalid private key format: {e}")
        return False


def get_password(prompt: str) -> str:
    """Get password from user with confirmation"""
    while True:
        password = getpass.getpass(prompt)
        if len(password) < 8:
            print("❌ Password must be at least 8 characters long")
            continue
        return password


def get_password_with_confirmation(prompt: str) -> str:
    """Get password from user with confirmation"""
    while True:
        password = get_password(prompt)
        confirm_password = getpass.getpass("Confirm password: ")
        
        if password == confirm_password:
            return password
        else:
            print("❌ Passwords do not match. Please try again.")


def cmd_create_donor_wallet(args):
    """Create encrypted donor wallet"""
    try:
        # Validate inputs
        if not validate_address(args.address):
            return False
            
        if not validate_private_key(args.private_key):
            return False
        
        # Get password
        password = get_password_with_confirmation("Enter password for donor wallet: ")
        
        # Create donor wallet manager
        donor_manager = DonorWalletManager()
        
        # Check if wallet already exists
        if donor_manager.wallet_exists():
            overwrite = input("⚠️  Donor wallet already exists. Overwrite? (y/N): ")
            if overwrite.lower() != 'y':
                print("❌ Operation cancelled")
                return False
        
        # Create wallet
        if donor_manager.create_donor_wallet(args.address, args.private_key, password):
            print(f"✅ Donor wallet created successfully!")
            print(f"📍 Wallet file: {donor_manager.get_wallet_path()}")
            print(f"🏛️  Address: {args.address}")
            print("⚠️  Keep your password safe - it cannot be recovered!")
            return True
        else:
            print("❌ Failed to create donor wallet")
            return False
            
    except Exception as e:
        print(f"❌ Error creating donor wallet: {e}")
        return False


def cmd_load_donor_wallet(args):
    """Load and verify donor wallet"""
    try:
        donor_manager = DonorWalletManager()
        
        if not donor_manager.wallet_exists():
            print("❌ No donor wallet found")
            print(f"📍 Expected location: {donor_manager.get_wallet_path()}")
            return False
        
        # Get password
        password = get_password("Enter donor wallet password: ")
        
        # Load wallet
        wallet_data = donor_manager.load_donor_wallet(password)
        
        if wallet_data:
            print("✅ Donor wallet loaded successfully!")
            print(f"🏛️  Address: {wallet_data['address']}")
            print(f"📅 Created: {wallet_data.get('created_at', 'Unknown')}")
            print(f"🔢 Version: {wallet_data.get('version', 'Unknown')}")
            return True
        else:
            print("❌ Failed to load donor wallet (wrong password?)")
            return False
            
    except Exception as e:
        print(f"❌ Error loading donor wallet: {e}")
        return False


def cmd_show_status(args):
    """Show donor wallet status"""
    try:
        donor_manager = DonorWalletManager()
        
        print("🏛️  DONOR WALLET STATUS")
        print("=" * 40)
        
        if donor_manager.wallet_exists():
            print(f"📍 Wallet File: {donor_manager.get_wallet_path()}")
            print("📁 File Status: ✅ Exists")
            
            # Check if it's loaded
            if donor_manager.is_wallet_loaded():
                wallet_info = donor_manager.get_wallet_info()
                print("🔓 Load Status: ✅ Loaded")
                print(f"🏛️  Address: {wallet_info['address']}")
                print(f"📅 Created: {wallet_info.get('created_at', 'Unknown')}")
            else:
                print("🔓 Load Status: ❌ Not loaded")
        else:
            print(f"📍 Wallet File: {donor_manager.get_wallet_path()}")
            print("📁 File Status: ❌ Not found")
            print("🔓 Load Status: ❌ No wallet")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting donor wallet status: {e}")
        return False


def cmd_verify_password(args):
    """Verify donor wallet password"""
    try:
        donor_manager = DonorWalletManager()
        
        if not donor_manager.wallet_exists():
            print("❌ No donor wallet found")
            return False
        
        # Get password
        password = get_password("Enter password to verify: ")
        
        # Verify password
        if donor_manager.verify_password(password):
            print("✅ Password is correct!")
            return True
        else:
            print("❌ Password is incorrect!")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying password: {e}")
        return False


def cmd_show_path(args):
    """Show donor wallet file path"""
    try:
        donor_manager = DonorWalletManager()
        
        print("📍 DONOR WALLET PATH")
        print("=" * 40)
        print(f"File Path: {donor_manager.get_wallet_path()}")
        print(f"Directory: {os.path.dirname(donor_manager.get_wallet_path())}")
        print(f"Exists: {'✅ Yes' if donor_manager.wallet_exists() else '❌ No'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting path: {e}")
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
    
    if args.command == 'create':
        success = cmd_create_donor_wallet(args)
    elif args.command == 'load':
        success = cmd_load_donor_wallet(args)
    elif args.command == 'status':
        success = cmd_show_status(args)
    elif args.command == 'verify':
        success = cmd_verify_password(args)
    elif args.command == 'path':
        success = cmd_show_path(args)
    else:
        print("❌ No command specified. Use --help for usage information.")
        return 1
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
