#!/usr/bin/env python3
"""
Test Script for QbitcoinAPIClient

This script tests all the methods provided by the QbitcoinAPIClient class one by one,
to ensure they are working properly with a running Qbitcoin node.
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, Any, List
from datetime import datetime

# Import the QbitcoinAPIClient class
from qbitcoin_api_client import QbitcoinAPIClient, print_json

class QbitcoinAPIClientTester:
    """
    A class to test all methods of the QbitcoinAPIClient
    """
    
    def __init__(self, host: str = "localhost", port: int = 9568, api_key: str = None):
        """
        Initialize the tester with a QbitcoinAPIClient instance
        """
        self.client = QbitcoinAPIClient(host=host, port=port, api_key=api_key)
        self.test_results = {}
        
        # Sample values for testing
        # These values should be updated with real values from your network
        self.sample_block_height = 1
        self.sample_block_hash = "sample_block_hash"  # Replace with a real block hash
        self.sample_tx_hash = "sample_tx_hash"  # Replace with a real transaction hash
        self.sample_address = "sample_address"  # Replace with a real wallet address
        self.sample_private_key = "sample_private_key"  # Replace with a real private key
        
    def run_test(self, test_name: str, test_func, *args, **kwargs) -> bool:
        """
        Run a single test and record the result
        
        Args:
            test_name: The name of the test
            test_func: The function to test
            *args, **kwargs: Arguments to pass to the test function
            
        Returns:
            bool: Whether the test was successful
        """
        print(f"\n{'=' * 50}")
        print(f"Testing: {test_name}")
        print(f"{'=' * 50}")
        
        try:
            result = test_func(*args, **kwargs)
            print("Response:")
            print_json(result)
            self.test_results[test_name] = "SUCCESS"
            return True
        except Exception as e:
            print(f"Error: {e}")
            self.test_results[test_name] = f"FAILED: {str(e)}"
            return False
            
    def print_summary(self):
        """
        Print a summary of all test results
        """
        print("\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)
        
        success_count = 0
        failure_count = 0
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result == "SUCCESS" else "❌ FAIL"
            print(f"{status} - {test_name}")
            
            if result == "SUCCESS":
                success_count += 1
            else:
                failure_count += 1
                
        print("\nResults:")
        print(f"Total tests: {len(self.test_results)}")
        print(f"Passed: {success_count}")
        print(f"Failed: {failure_count}")
        
    def test_all(self):
        """
        Run all available tests
        """
        # General Information Methods
        self.run_test("Get Node Info", self.client.get_node_info)
        self.run_test("Get Blockchain Status", self.client.get_blockchain_status)
        
        # Block Methods
        self.run_test("Get Latest Blocks", self.client.get_latest_blocks, limit=5)
        
        # Get block by height/hash - only run if we have real values
        if self.sample_block_height > 0:
            self.run_test("Get Block by Height", self.client.get_block_by_height, self.sample_block_height)
        
        if self.sample_block_hash != "sample_block_hash":
            self.run_test("Get Block by Hash", self.client.get_block_by_hash, self.sample_block_hash)
        
        if self.sample_block_height > 1:
            self.run_test("Get Blocks in Range", self.client.get_blocks_in_range, 1, self.sample_block_height)
        
        # Transaction Methods
        if self.sample_tx_hash != "sample_tx_hash":
            self.run_test("Get Transaction", self.client.get_transaction, self.sample_tx_hash)
        
        self.run_test("Get Mempool Transactions", self.client.get_mempool_transactions, limit=10)
        
        # Account/Address Methods
        if self.sample_address != "sample_address":
            self.run_test("Get Account Info", self.client.get_account_info, self.sample_address)
            self.run_test("Get Account Transactions", self.client.get_account_transactions, 
                         self.sample_address, limit=5)
        
        self.run_test("Get Top Accounts", self.client.get_top_accounts, limit=5)
        
        # Network Status Methods
        self.run_test("Get Peers", self.client.get_peers)
        self.run_test("Get Network Stats", self.client.get_network_stats)
        
         
        
        # Utility Methods
        if self.sample_address != "sample_address":
            self.run_test("Validate Address", self.client.validate_address, self.sample_address)
        
        # Print the summary of all tests
        self.print_summary()
    
    def run_interactive_tests(self):
        """
        Run tests that require user input or confirmation
        """
        print("\n" + "=" * 50)
        print("INTERACTIVE TESTS")
        print("=" * 50)
        
        # Test creating a wallet
        if input("\nDo you want to test wallet creation? (y/n): ").lower() == 'y':
            wallet_name = input("Enter wallet name: ")
            passphrase = input("Enter passphrase (optional, press Enter to skip): ") or None
            self.run_test("Create Wallet", self.client.create_wallet, wallet_name, passphrase)
        
        # Test sending a transaction
        if input("\nDo you want to test sending a transaction? (y/n): ").lower() == 'y':
            sender = input("Enter sender address: ")
            recipient = input("Enter recipient address: ")
            amount = float(input("Enter amount to send: "))
            private_key = input("Enter private key: ")
            fee = input("Enter fee (optional, press Enter to skip): ")
            fee = float(fee) if fee else None
            data = input("Enter data (optional, press Enter to skip): ") or None
            
            self.run_test("Send Transaction", self.client.send_transaction, 
                         sender, recipient, amount, private_key, fee, data)
        
        # Test signature verification
        if input("\nDo you want to test signature verification? (y/n): ").lower() == 'y':
            message = input("Enter message: ")
            signature = input("Enter signature: ")
            public_key = input("Enter public key: ")
            
            self.run_test("Verify Signature", self.client.verify_signature, 
                         message, signature, public_key)

def load_test_configuration():
    """
    Load test configuration from a JSON file if it exists
    """
    config_path = os.path.join(os.path.dirname(__file__), 'api_test_config.json')
    config = {
        'sample_block_height': 1,
        'sample_block_hash': "sample_block_hash",
        'sample_tx_hash': "sample_tx_hash",
        'sample_address': "sample_address",
        'sample_private_key': "sample_private_key"
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                loaded_config = json.load(f)
                config.update(loaded_config)
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
    
    return config

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test Qbitcoin API Client')
    parser.add_argument('-H', '--host', default='localhost', help='Host address (default: localhost)')
    parser.add_argument('-p', '--port', type=int, default=9568, help='Port number (default: 9568)')
    parser.add_argument('-k', '--api-key', help='API key for authenticated endpoints')
    parser.add_argument('-c', '--create-config', action='store_true', help='Create a template config file')
    parser.add_argument('-i', '--interactive', action='store_true', help='Run interactive tests')
    
    args = parser.parse_args()
    
    # Create a template config file if requested
    if args.create_config:
        config_path = os.path.join(os.path.dirname(__file__), 'api_test_config.json')
        config = {
            'sample_block_height': 1,
            'sample_block_hash': "sample_block_hash",  # Replace with a real block hash
            'sample_tx_hash': "sample_tx_hash",  # Replace with a real transaction hash
            'sample_address': "sample_address",  # Replace with a real wallet address
            'sample_private_key': "sample_private_key"  # Replace with a real private key
        }
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        print(f"Created template config file: {config_path}")
        print("Please update the file with real values before running tests.")
        sys.exit(0)
    
    # Load test configuration
    config = load_test_configuration()
    
    # Create and run the tester
    tester = QbitcoinAPIClientTester(host=args.host, port=args.port, api_key=args.api_key)
    
    # Update tester with config values
    tester.sample_block_height = config['sample_block_height']
    tester.sample_block_hash = config['sample_block_hash']
    tester.sample_tx_hash = config['sample_tx_hash']
    tester.sample_address = config['sample_address']
    tester.sample_private_key = config['sample_private_key']
    
    # Run tests
    tester.test_all()
    
    # Run interactive tests if requested
    if args.interactive:
        tester.run_interactive_tests()