#!/usr/bin/env python3
"""
Qbitcoin Wallet Creator Script

This script creates multiple wallets using the Falcon-512 post-quantum signature algorithm
and saves them to the default wallet directory as specified in config.py.
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add the project directory to the Python path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

# Import required modules
from utils.wallet_creator import WalletCreator, create_new_wallet
from core import config 
from utils.logger import get_logger

# Initialize logger
logger = get_logger("wallet_creator_script")

def create_and_save_wallets(num_wallets: int = 2, password: str = "test_password") -> List[Dict[str, Any]]:
    """
    Create and save multiple wallets to the default wallet directory
    
    Args:
        num_wallets: Number of wallets to create
        password: Password to encrypt the wallets
        
    Returns:
        List of created wallet data
    """
    wallets = []
    
    print(f"Creating {num_wallets} wallets and saving to: {config.WALLET_DIR}")
    print(f"Wallet directory exists: {config.WALLET_DIR.exists()}")
    
    # Create wallet directory if it doesn't exist
    config.WALLET_DIR.mkdir(parents=True, exist_ok=True)
    
    for i in range(num_wallets):
        wallet_name = f"wallet_{i+1}_{int(time.time())}"
        print(f"\nCreating wallet: {wallet_name}")
        
        # Create new wallet
        wallet_data = WalletCreator.create_wallet(wallet_name)
        
        # Save the wallet
        wallet_file = WalletCreator.save_wallet(wallet_data, password)
        print(f"Saved wallet to: {wallet_file}")
        print(f"Wallet address: {wallet_data['address']}")
        
        wallets.append(wallet_data)
    
    return wallets

def main():
    """Main entry point for the script"""
    print("=" * 50)
    print("Qbitcoin Wallet Creator")
    print("=" * 50)
    print(f"Wallet directory: {config.WALLET_DIR}")
    
    # Create and save wallets
    wallets = create_and_save_wallets()
    
    print("\nWallet creation complete!")
    print(f"Created {len(wallets)} wallets in {config.WALLET_DIR}")
    print("=" * 50)
    
    # List created wallets
    print("\nCreated wallets:")
    for idx, wallet in enumerate(wallets, 1):
        print(f"{idx}. Name: {wallet['name']}, Address: {wallet['address']}")

if __name__ == "__main__":
    main()