#!/usr/bin/env python3
# coding=utf-8
# Script to create and send a transaction using genesis keys in QRL/Qbitcoin

import os
import sys
import json
import grpc

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

def main():
    try:
        # Path to genesis keys JSON file
        genesis_keys_path = os.path.join(os.path.dirname(__file__), 'genesis_keys.json')
        
        # Load genesis keys
        genesis_keys = load_genesis_keys(genesis_keys_path)
        print(f"Genesis public key length: {len(genesis_keys['public_key'])} bytes")
        
        # Create a new wallet
        new_wallet = create_new_wallet()
        print(f"New wallet public key length: {len(new_wallet['public_key'])} bytes")
        
        # Amount to send (in quark)
        amount_to_send = 1000 * QUARK_PER_QBITCOIN  # 1000 Qbitcoin
        
        # Create and sign a transaction
        tx = create_and_sign_transaction(genesis_keys, new_wallet['address'], amount_to_send)
        print(f"Transaction created with txhash: {bin2hstr(tx.txhash)}")
        
        # Send the transaction to the node
        success = send_transaction(tx)
        
        if success:
            print(f"\nSuccessfully sent {amount_to_send/QUARK_PER_QBITCOIN} Qbitcoin from genesis address")
            print(f"Source address: {genesis_keys['address']}")
            print(f"Destination address: {new_wallet['address']}")
            
            # Save the new wallet to a file for future use
            wallet_data = {
                "address": new_wallet['address'],
                "public_key_hex": new_wallet['public_key'].hex(),
                "private_key_hex": new_wallet['private_key'].hex(),
                "algorithm": "falcon-512"
            }
            
            with open('new_wallet.json', 'w') as f:
                json.dump(wallet_data, f, indent=4)
                print("New wallet saved to new_wallet.json")
        else:
            print("Transaction failed.")
            
    except Exception as e:
        print(f"Error in main function: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
