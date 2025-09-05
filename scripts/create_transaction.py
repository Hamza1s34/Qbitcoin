#!/usr/bin/env python3
# coding=utf-8
# Script to create and send a transaction using genesis keys in QRL/Qbitcoin

import os
import sys
import json
import grpc
import time

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
NODE_GRPC_ENDPOINT = "localhost:19009"  # Default QRL gRPC endpoint
QUARK_PER_QBITCOIN = 10**9  # 1 Qbitcoin = 10^9 quark (smallest unit)
CONNECTION_TIMEOUT = 5  # seconds

def load_genesis_keys(file_path):
    """Load the genesis keys from the provided JSON file"""
    with open(file_path, 'r') as f:
        genesis_data = json.load(f)
    
    print(f"Loaded genesis address: {genesis_data['address']}")
    
    # Convert hex to bytes
    public_key = bytes.fromhex(genesis_data['public_key_hex'])
    private_key = bytes.fromhex(genesis_data['private_key_hex'])
    
    # Verify the algorithm
    if genesis_data['algorithm'] != "falcon-512":
        raise ValueError(f"Expected falcon-512 algorithm, got {genesis_data['algorithm']}")
    
    return {
        'address': genesis_data['address'],
        'address_bytes': bytes(hstr2bin(genesis_data['address'][1:])),  # Remove the 'Q' prefix
        'public_key': public_key,
        'private_key': private_key
    }

def create_new_wallet():
    """Create a new wallet using Falcon-512"""
    # Generate a new key pair
    private_key, public_key = WalletCreator.create_keypair()
    
    # Use WalletCreator to generate address directly from public key
    address = WalletCreator.generate_address(public_key)
    address_bytes = bytes(hstr2bin(address[1:]))  # Remove 'Q' prefix and convert to bytes
    
    print(f"Created new wallet address: {address}")
    
    return {
        'address': address,
        'address_bytes': address_bytes,
        'public_key': public_key,
        'private_key': private_key
    }

def create_and_sign_transaction(sender, receiver_address, amount_quark):
    """Create and sign a transfer transaction"""
    print(f"Creating transaction: {sender['address']} -> {receiver_address} ({amount_quark} quark)")
    
    # We need to manually handle the transaction since the addr_from is derived incorrectly
    tx = TransferTransaction()
    tx._data.public_key = sender['public_key']
    
    # Add receiver address (remove 'Q' prefix and convert to bytes)
    tx._data.transfer.addrs_to.append(bytes(hstr2bin(receiver_address[1:])))
    
    # Add amount
    tx._data.transfer.amounts.append(amount_quark)
    
    # Set fee
    tx._data.fee = 1000000  # 1 million quark fee
    
    # Important: Override the default Transaction behavior by directly setting addr_from
    # This bypasses the QRLHelper.getAddress() call that fails with Falcon keys
    addr_bytes = sender['address_bytes']
    tx._data.master_addr = addr_bytes
    
    # Get transaction data to sign
    tx_data = tx.get_data_hash()
    
    # Sign with Falcon-512
    print("Signing transaction with genesis key...")
    signature = FalconSignature.sign_message(tx_data, sender['private_key'])
    print(f"DEBUG: Generated signature length: {len(signature)} bytes")
    print(f"DEBUG: Expected max signature size: {FalconSignature.get_algorithm_details()['signature_size']} bytes")
    print(f"DEBUG: Signature hash: {signature[:20].hex()}...")
    tx._data.signature = signature
    
    # Update transaction hash after signing
    tx.update_txhash()
    
    return tx

def validate_transaction(tx):
    """
    Custom validation for transaction before sending to the node
    This bypasses the default validation that uses QRLHelper
    """
    if not tx._data.transfer.addrs_to:
        print("Transaction has no recipient addresses")
        return False
    
    if not tx._data.transfer.amounts:
        print("Transaction has no amounts")
        return False
    
    for amount in tx._data.transfer.amounts:
        if amount <= 0:
            print(f"Invalid amount: {amount}")
            return False
    
    if tx._data.fee < 0:
        print(f"Invalid fee: {tx._data.fee}")
        return False
    
    if not tx._data.signature:
        print("Transaction is not signed")
        return False
    
    return True

def send_transaction(tx):
    """Send a transaction to the QRL node"""
    try:
        # First validate the transaction locally
        if not validate_transaction(tx):
            print("Invalid transaction, cannot submit to node")
            return False
        
        # Set up the gRPC connection
        channel = grpc.insecure_channel(NODE_GRPC_ENDPOINT)
        stub = qbit_pb2_grpc.PublicAPIStub(channel)
        
        # Create the push transaction request
        push_transaction_req = qbit_pb2.PushTransactionReq(transaction_signed=tx.pbdata)
        
        print("Sending transaction to node...")
        push_transaction_resp = stub.PushTransaction(push_transaction_req, timeout=CONNECTION_TIMEOUT)
        
        if push_transaction_resp.error_code == qbit_pb2.PushTransactionResp.SUBMITTED:
            print("Transaction successfully submitted!")
            print(f"Transaction hash: {bin2hstr(tx.txhash)}")
            return True
        else:
            print(f"Transaction submission failed with error: {push_transaction_resp.error_description}")
            return False
            
    except Exception as e:
        print(f"Error sending transaction: {str(e)}")
        return False

def get_user_input():
    """Get user input for recipient address and amount"""
    print("=== Qbitcoin Transaction Creator ===")
    print()
    
    # Get recipient address
    print("Enter recipient address (or press Enter to generate a new wallet):")
    recipient_address = input("Recipient address: ").strip()
    
    # If no address provided, create a new wallet
    if not recipient_address:
        print("\nNo address provided. Generating a new wallet...")
        new_wallet = create_new_wallet()
        recipient_address = new_wallet['address']
        
        # Save the new wallet
        wallet_data = {
            "address": new_wallet['address'],
            "public_key": new_wallet['public_key'].hex(),
            "private_key": new_wallet['private_key'].hex(),
            "algorithm": "falcon-512"
        }
        
        wallet_filename = f"generated_wallet_{int(time.time())}.json"
        with open(wallet_filename, 'w') as f:
            json.dump(wallet_data, f, indent=4)
        print(f"New wallet saved to: {wallet_filename}")
        print(f"Generated recipient address: {recipient_address}")
    else:
        # Validate the provided address
        if not recipient_address.startswith('Q'):
            print("Error: Qbitcoin addresses must start with 'Q'")
            return None, None
        if len(recipient_address) != 51:  # Q + 50 hex chars
            print("Error: Invalid address length. Qbitcoin addresses should be 51 characters long")
            return None, None
        
        # Try to validate the hex format
        try:
            address_bytes = bytes(hstr2bin(recipient_address[1:]))
        except Exception as e:
            print(f"Error: Invalid address format: {e}")
            return None, None
    
    print()
    
    # Get amount to send
    print("Enter amount to send in QBC (or press Enter for default 1000 QBC):")
    amount_input = input("Amount (QBC): ").strip()
    
    if not amount_input:
        amount_qbc = 1000  # Default amount
        print(f"Using default amount: {amount_qbc} QBC")
    else:
        try:
            amount_qbc = float(amount_input)
            if amount_qbc <= 0:
                print("Error: Amount must be positive")
                return None, None
        except ValueError:
            print("Error: Invalid amount format")
            return None, None
    
    # Convert to quark (smallest unit)
    amount_quark = int(amount_qbc * QUARK_PER_QBITCOIN)
    
    print(f"\nTransaction details:")
    print(f"Recipient: {recipient_address}")
    print(f"Amount: {amount_qbc} QBC ({amount_quark} quark)")
    print()
    
    # Confirm transaction
    confirm = input("Proceed with transaction? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Transaction cancelled.")
        return None, None
    
    return recipient_address, amount_quark

def main():
    try:
        # Get user input
        recipient_address, amount_quark = get_user_input()
        if recipient_address is None or amount_quark is None:
            return
        
        # Path to genesis keys JSON file
        genesis_keys_path = os.path.join(os.path.dirname(__file__), '..', 'genesis_keys.json')
        
        # Check if genesis keys exist
        if not os.path.exists(genesis_keys_path):
            print(f"Error: Genesis keys file not found at {genesis_keys_path}")
            print("Please ensure genesis_keys.json exists in the project root directory.")
            return
        
        # Load genesis keys (sender)
        genesis_keys = load_genesis_keys(genesis_keys_path)
        print(f"Loaded sender address: {genesis_keys['address']}")
        print(f"Genesis public key length: {len(genesis_keys['public_key'])} bytes")
        
        # Create and sign a transaction
        print(f"\nCreating transaction...")
        tx = create_and_sign_transaction(genesis_keys, recipient_address, amount_quark)
        print(f"Transaction created with txhash: {bin2hstr(tx.txhash)}")
        
        # Send the transaction to the node
        print(f"Sending transaction to node...")
        success = send_transaction(tx)
        
        if success:
            print(f"\n✅ Transaction successful!")
            print(f"Amount sent: {amount_quark/QUARK_PER_QBITCOIN} QBC")
            print(f"From: {genesis_keys['address']}")
            print(f"To: {recipient_address}")
            print(f"Transaction hash: {bin2hstr(tx.txhash)}")
        else:
            print("\n❌ Transaction failed.")
            
    except Exception as e:
        print(f"Error in main function: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
