#!/usr/bin/env python3
# coding=utf-8
# Comprehensive transaction security testing script for QRL/Qbitcoin node
# Tests various valid and invalid transaction scenarios to verify node security

import os
import sys
import json
import grpc
import time
import secrets
from typing import Dict, Any

from pyqrllib.pyqrllib import hstr2bin, bin2hstr

# Add QRL modules to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from qbitcoin.generated import qbit_pb2, qbit_pb2_grpc
from qbitcoin.core.txs.TransferTransaction import TransferTransaction
from qbitcoin.core.txs.Transaction import Transaction
from qbitcoin.crypto.falcon import FalconSignature
from qbitcoin.tools.wallet_creator import WalletCreator
from qbitcoin.core.AddressState import AddressState
from qbitcoin.core import config

# Constants
NODE_GRPC_ENDPOINT = "localhost:19009"
QUARK_PER_QBITCOIN = 10**9
CONNECTION_TIMEOUT = 10
TEST_AMOUNT = 100 * QUARK_PER_QBITCOIN  # 100 Qbitcoin

class TransactionTester:
    def __init__(self):
        self.genesis_keys = None
        self.new_wallet = None
        self.test_results = []
        
    def load_genesis_keys(self, file_path):
        """Load the genesis keys from JSON file"""
        with open(file_path, 'r') as f:
            genesis_data = json.load(f)
        
        public_key = bytes.fromhex(genesis_data['public_key_hex'])
        private_key = bytes.fromhex(genesis_data['private_key_hex'])
        
        self.genesis_keys = {
            'address': genesis_data['address'],
            'address_bytes': bytes(hstr2bin(genesis_data['address'][1:])),
            'public_key': public_key,
            'private_key': private_key
        }
        print(f"✓ Loaded genesis address: {genesis_data['address']}")
        
    def create_new_wallet(self):
        """Create a new wallet with zero balance"""
        private_key, public_key = WalletCreator.create_keypair()
        address = WalletCreator.generate_address(public_key)
        address_bytes = bytes(hstr2bin(address[1:]))
        
        self.new_wallet = {
            'address': address,
            'address_bytes': address_bytes,
            'public_key': public_key,
            'private_key': private_key
        }
        print(f"✓ Created new wallet: {address}")
        
    def send_transaction(self, tx, test_name):
        """Send transaction to node and record result"""
        try:
            channel = grpc.insecure_channel(NODE_GRPC_ENDPOINT)
            stub = qbit_pb2_grpc.PublicAPIStub(channel)
            
            push_transaction_req = qbit_pb2.PushTransactionReq(transaction_signed=tx.pbdata)
            push_transaction_resp = stub.PushTransaction(push_transaction_req, timeout=CONNECTION_TIMEOUT)
            
            success = push_transaction_resp.error_code == qbit_pb2.PushTransactionResp.SUBMITTED
            error_desc = push_transaction_resp.error_description if not success else "Success"
            
            result = {
                'test_name': test_name,
                'success': success,
                'error': error_desc,
                'txhash': bin2hstr(tx.txhash) if hasattr(tx, 'txhash') else 'N/A'
            }
            
            self.test_results.append(result)
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"{status} {test_name}: {error_desc}")
            
            return success
            
        except Exception as e:
            result = {
                'test_name': test_name,
                'success': False,
                'error': str(e),
                'txhash': 'N/A'
            }
            self.test_results.append(result)
            print(f"✗ ERROR {test_name}: {str(e)}")
            return False
    
    def create_basic_transaction(self, sender, receiver_address, amount):
        """Create a basic valid transaction"""
        tx = TransferTransaction()
        tx._data.public_key = sender['public_key']
        tx._data.transfer.addrs_to.append(bytes(hstr2bin(receiver_address[1:])))
        tx._data.transfer.amounts.append(amount)
        tx._data.fee = 1000000  # 1M quark fee
        tx._data.master_addr = sender['address_bytes']
        
        tx_data = tx.get_data_hash()
        signature = FalconSignature.sign_message(tx_data, sender['private_key'])
        tx._data.signature = signature
        tx.update_txhash()
        
        return tx
    
    def test_1_valid_genesis_transaction(self):
        """Test 1: Valid transaction from genesis (has balance)"""
        print("\n=== Test 1: Valid Genesis Transaction ===")
        tx = self.create_basic_transaction(self.genesis_keys, self.new_wallet['address'], TEST_AMOUNT)
        return self.send_transaction(tx, "Valid Genesis Transaction")
    
    def test_2_zero_balance_transaction(self):
        """Test 2: Transaction from wallet with zero balance"""
        print("\n=== Test 2: Zero Balance Transaction ===")
        tx = self.create_basic_transaction(self.new_wallet, self.genesis_keys['address'], TEST_AMOUNT)
        return self.send_transaction(tx, "Zero Balance Transaction")
    
    def test_3_missing_public_key(self):
        """Test 3: Transaction without public key"""
        print("\n=== Test 3: Missing Public Key ===")
        tx = TransferTransaction()
        # Intentionally not setting public_key
        tx._data.transfer.addrs_to.append(self.new_wallet['address_bytes'])
        tx._data.transfer.amounts.append(TEST_AMOUNT)
        tx._data.fee = 1000000
        tx._data.master_addr = self.genesis_keys['address_bytes']
        
        # Try to sign without public key
        try:
            tx_data = tx.get_data_hash()
            signature = FalconSignature.sign_message(tx_data, self.genesis_keys['private_key'])
            tx._data.signature = signature
            tx.update_txhash()
        except:
            pass  # Expected to fail
            
        return self.send_transaction(tx, "Missing Public Key")
    
    def test_4_invalid_public_key(self):
        """Test 4: Transaction with invalid/random public key"""
        print("\n=== Test 4: Invalid Public Key ===")
        tx = TransferTransaction()
        
        # Generate random bytes for invalid public key
        invalid_pk = secrets.token_bytes(897)  # Random 897 bytes
        
        tx._data.public_key = invalid_pk
        tx._data.transfer.addrs_to.append(self.new_wallet['address_bytes'])
        tx._data.transfer.amounts.append(TEST_AMOUNT)
        tx._data.fee = 1000000
        tx._data.master_addr = self.genesis_keys['address_bytes']
        
        # Sign with genesis key but use invalid public key
        tx_data = tx.get_data_hash()
        signature = FalconSignature.sign_message(tx_data, self.genesis_keys['private_key'])
        tx._data.signature = signature
        tx.update_txhash()
        
        return self.send_transaction(tx, "Invalid Public Key")
    
    def test_5_tampered_signature(self):
        """Test 5: Valid transaction with tampered signature"""
        print("\n=== Test 5: Tampered Signature ===")
        tx = self.create_basic_transaction(self.genesis_keys, self.new_wallet['address'], TEST_AMOUNT)
        
        # Tamper with signature by flipping some bits
        original_sig = tx._data.signature
        tampered_sig = bytearray(original_sig)
        tampered_sig[0] = tampered_sig[0] ^ 0xFF  # Flip first byte
        tampered_sig[10] = tampered_sig[10] ^ 0xFF  # Flip another byte
        tx._data.signature = bytes(tampered_sig)
        tx.update_txhash()
        
        return self.send_transaction(tx, "Tampered Signature")
    
    def test_6_duplicate_transaction(self):
        """Test 6: Send the same transaction twice (replay attack)"""
        print("\n=== Test 6: Duplicate Transaction (Replay Attack) ===")
        
        # Create a valid transaction
        tx = self.create_basic_transaction(self.genesis_keys, self.new_wallet['address'], TEST_AMOUNT // 2)
        
        # Send first time
        result1 = self.send_transaction(tx, "First Duplicate Transaction")
        
        # Wait a moment
        time.sleep(2)
        
        # Send same transaction again
        result2 = self.send_transaction(tx, "Second Duplicate Transaction (Replay)")
        
        return result1 and result2
    
    def test_7_negative_amount(self):
        """Test 7: Transaction with negative amount"""
        print("\n=== Test 7: Negative Amount ===")
        tx = TransferTransaction()
        tx._data.public_key = self.genesis_keys['public_key']
        tx._data.transfer.addrs_to.append(self.new_wallet['address_bytes'])
        tx._data.transfer.amounts.append(-1000000)  # Negative amount
        tx._data.fee = 1000000
        tx._data.master_addr = self.genesis_keys['address_bytes']
        
        tx_data = tx.get_data_hash()
        signature = FalconSignature.sign_message(tx_data, self.genesis_keys['private_key'])
        tx._data.signature = signature
        tx.update_txhash()
        
        return self.send_transaction(tx, "Negative Amount")
    
    def test_8_excessive_amount(self):
        """Test 8: Transaction with amount exceeding balance"""
        print("\n=== Test 8: Excessive Amount ===")
        excessive_amount = 999999999 * QUARK_PER_QBITCOIN  # Very large amount
        tx = self.create_basic_transaction(self.genesis_keys, self.new_wallet['address'], excessive_amount)
        return self.send_transaction(tx, "Excessive Amount")
    
    def test_9_zero_fee(self):
        """Test 9: Transaction with zero fee"""
        print("\n=== Test 9: Zero Fee ===")
        tx = TransferTransaction()
        tx._data.public_key = self.genesis_keys['public_key']
        tx._data.transfer.addrs_to.append(self.new_wallet['address_bytes'])
        tx._data.transfer.amounts.append(TEST_AMOUNT)
        tx._data.fee = 0  # Zero fee
        tx._data.master_addr = self.genesis_keys['address_bytes']
        
        tx_data = tx.get_data_hash()
        signature = FalconSignature.sign_message(tx_data, self.genesis_keys['private_key'])
        tx._data.signature = signature
        tx.update_txhash()
        
        return self.send_transaction(tx, "Zero Fee")
    
    def test_10_invalid_recipient_address(self):
        """Test 10: Transaction to invalid recipient address"""
        print("\n=== Test 10: Invalid Recipient Address ===")
        tx = TransferTransaction()
        tx._data.public_key = self.genesis_keys['public_key']
        
        # Invalid address (wrong length)
        invalid_address = b'\x01' + b'\x00' * 10  # Too quarkt
        tx._data.transfer.addrs_to.append(invalid_address)
        tx._data.transfer.amounts.append(TEST_AMOUNT)
        tx._data.fee = 1000000
        tx._data.master_addr = self.genesis_keys['address_bytes']
        
        tx_data = tx.get_data_hash()
        signature = FalconSignature.sign_message(tx_data, self.genesis_keys['private_key'])
        tx._data.signature = signature
        tx.update_txhash()
        
        return self.send_transaction(tx, "Invalid Recipient Address")
    
    def test_11_wrong_signature_key(self):
        """Test 11: Sign with different private key than public key"""
        print("\n=== Test 11: Wrong Signature Key ===")
        tx = TransferTransaction()
        tx._data.public_key = self.genesis_keys['public_key']
        tx._data.transfer.addrs_to.append(self.new_wallet['address_bytes'])
        tx._data.transfer.amounts.append(TEST_AMOUNT)
        tx._data.fee = 1000000
        tx._data.master_addr = self.genesis_keys['address_bytes']
        
        # Sign with new wallet's private key but use genesis public key
        tx_data = tx.get_data_hash()
        signature = FalconSignature.sign_message(tx_data, self.new_wallet['private_key'])
        tx._data.signature = signature
        tx.update_txhash()
        
        return self.send_transaction(tx, "Wrong Signature Key")
    
    def test_12_malformed_transaction_data(self):
        """Test 12: Transaction with malformed data"""
        print("\n=== Test 12: Malformed Transaction Data ===")
        tx = TransferTransaction()
        tx._data.public_key = self.genesis_keys['public_key']
        # Don't set any transfer data - malformed
        tx._data.fee = 1000000
        tx._data.master_addr = self.genesis_keys['address_bytes']
        
        try:
            tx_data = tx.get_data_hash()
            signature = FalconSignature.sign_message(tx_data, self.genesis_keys['private_key'])
            tx._data.signature = signature
            tx.update_txhash()
        except:
            pass
            
        return self.send_transaction(tx, "Malformed Transaction Data")
    
    def run_all_tests(self):
        """Run all security tests"""
        print("🔒 Starting QRL/Qbitcoin Node Security Tests")
        print("=" * 50)
        
        # Load genesis keys
        genesis_path = os.path.join(os.path.dirname(__file__), 'genesis_keys.json')
        self.load_genesis_keys(genesis_path)
        
        # Create new wallet
        self.create_new_wallet()
        
        # Run all tests
        tests = [
            self.test_1_valid_genesis_transaction,
            self.test_2_zero_balance_transaction,
            self.test_3_missing_public_key,
            self.test_4_invalid_public_key,
            self.test_5_tampered_signature,
            self.test_6_duplicate_transaction,
            self.test_7_negative_amount,
            self.test_8_excessive_amount,
            self.test_9_zero_fee,
            self.test_10_invalid_recipient_address,
            self.test_11_wrong_signature_key,
            self.test_12_malformed_transaction_data
        ]
        
        for test_func in tests:
            try:
                test_func()
                time.sleep(1)  # Small delay between tests
            except Exception as e:
                print(f"✗ ERROR in {test_func.__name__}: {str(e)}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("🔒 SECURITY TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result['success'])
        failed = len(self.test_results) - passed
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print()
        
        print("DETAILED RESULTS:")
        print("-" * 50)
        for result in self.test_results:
            status = "✓ PASS" if result['success'] else "✗ FAIL"
            print(f"{status} {result['test_name']}")
            if not result['success']:
                print(f"    Error: {result['error']}")
            print(f"    TxHash: {result['txhash']}")
            print()
        
        # Security analysis
        print("SECURITY ANALYSIS:")
        print("-" * 50)
        
        # Check if dangerous transactions were rejected
        dangerous_tests = [
            "Zero Balance Transaction",
            "Missing Public Key", 
            "Invalid Public Key",
            "Tampered Signature",
            "Second Duplicate Transaction (Replay)",
            "Negative Amount",
            "Wrong Signature Key",
            "Invalid Recipient Address"
        ]
        
        security_good = True
        for result in self.test_results:
            if result['test_name'] in dangerous_tests and result['success']:
                print(f"⚠️  SECURITY CONCERN: {result['test_name']} was accepted!")
                security_good = False
        
        if security_good:
            print("✅ Node properly rejected dangerous transactions")
        else:
            print("❌ Node accepted some dangerous transactions - SECURITY RISK!")
        
        # Save results to file
        with open('security_test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=4)
        print(f"\n📄 Detailed results saved to security_test_results.json")

def main():
    tester = TransactionTester()
    tester.run_all_tests()

if __name__ == '__main__':
    main()
