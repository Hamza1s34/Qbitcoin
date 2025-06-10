#!/usr/bin/env python3
"""
QRL Real Token Creation Script

This script creates a real token on the QRL blockchain using genesis keys
and actual node connection.
"""

import sys
import os
import grpc
import json
import traceback
from decimal import Decimal

# Add QRL modules to path
sys.path.append('/workspaces/QRL')

from qbitcoin.core.txs.TokenTransaction import TokenTransaction
from qbitcoin.generated import qbit_pb2, qbit_pb2_grpc
from qbitcoin.crypto.falcon import FalconSignature
from qbitcoin.core.misc import logger
from binascii import hexlify
from pyqrllib.pyqrllib import hstr2bin, bin2hstr

# Constants
NODE_GRPC_ENDPOINT = "localhost:19009"
CONNECTION_TIMEOUT = 10

def load_wallet(file_path):
    """Load wallet from JSON file"""
    try:
        with open(file_path, 'r') as f:
            wallet_data = json.load(f)
        
        return {
            'address': wallet_data['address'],
            'address_bytes': bytes(hstr2bin(wallet_data['address'][1:])),  # Remove 'Q' prefix
            'public_key': bytes.fromhex(wallet_data['public_key_hex']),
            'private_key': bytes.fromhex(wallet_data['private_key_hex'])
        }
    except Exception as e:
        print(f"❌ Error loading wallet from {file_path}: {e}")
        return None

def get_address_balance(address):
    """Get the balance of an address from the node"""
    try:
        channel = grpc.insecure_channel(NODE_GRPC_ENDPOINT)
        stub = qbit_pb2_grpc.PublicAPIStub(channel)
        
        # Convert address to bytes for the request
        address_bytes = bytes(hstr2bin(address[1:]))  # Remove 'Q' prefix
        
        get_address_state_req = qbit_pb2.GetAddressStateReq(address=address_bytes)
        get_address_state_resp = stub.GetAddressState(get_address_state_req, timeout=CONNECTION_TIMEOUT)
        
        return get_address_state_resp.state.balance
    except Exception as e:
        print(f"❌ Error getting balance for {address}: {e}")
        return 0

def create_real_token():
    """
    Create a real token on QRL blockchain using genesis keys
    """
    print("=== Creating Real Token on QRL Blockchain ===\n")
    
    # Load genesis wallet
    genesis_wallet = load_wallet('genesis_keys.json')
    if not genesis_wallet:
        return None
    
    # Load new wallet for initial distribution
    new_wallet = load_wallet('new_wallet.json')
    if not new_wallet:
        print("Creating new wallet for token distribution...")
        # If new wallet doesn't exist, we'll only distribute to genesis address
        new_wallet = None
    
    print(f"Genesis Address: {genesis_wallet['address']}")
    if new_wallet:
        print(f"New Wallet Address: {new_wallet['address']}")
    
    # Check genesis balance
    genesis_balance = get_address_balance(genesis_wallet['address'])
    print(f"Genesis Balance: {genesis_balance / 1000000000:.3f} Qbitcoin")
    
    if genesis_balance < 10000000000:  # Less than 10 Qbitcoin
        print("❌ Insufficient balance for token creation (need at least 10 Qbitcoin)")
        return None
    
    # Token parameters
    token_symbol = b'DEMO'
    token_name = b'Demo Token Real'
    decimals = 2
    fee = 5000000000  # 5 Qbitcoin fee
    
    # Initial token distribution
    initial_balances = [
        qbit_pb2.AddressAmount(
            address=genesis_wallet['address_bytes'],
            amount=1000000  # 10000.00 tokens (with 2 decimals)
        )
    ]
    
    # Add new wallet if available
    if new_wallet:
        initial_balances.append(
            qbit_pb2.AddressAmount(
                address=new_wallet['address_bytes'],
                amount=500000  # 5000.00 tokens
            )
        )
    
    total_supply = sum(balance.amount for balance in initial_balances)
    
    print(f"\nToken Details:")
    print(f"  Symbol: {token_symbol.decode()}")
    print(f"  Name: {token_name.decode()}")
    print(f"  Decimals: {decimals}")
    print(f"  Total Supply: {total_supply / (10 ** decimals):,} tokens")
    print(f"  Creation Fee: {fee / 1000000000} Qbitcoin")
    
    try:
        # Create the token transaction manually like create_transaction.py does
        print("\n📝 Creating token transaction...")
        token_tx = TokenTransaction()
        token_tx._data.public_key = genesis_wallet['public_key']
        
        # Set token data manually
        token_tx._data.token.symbol = token_symbol
        token_tx._data.token.name = token_name
        token_tx._data.token.owner = genesis_wallet['address_bytes']  # Genesis is the owner
        token_tx._data.token.decimals = decimals
        
        # Add initial balances
        for initial_balance in initial_balances:
            token_tx._data.token.initial_balances.extend([initial_balance])
        
        # Set fee
        token_tx._data.fee = fee
        
        # Important: Set master_addr like create_transaction.py does
        # This bypasses the QRLHelper.getAddress() call that fails with Falcon keys
        token_tx._data.master_addr = genesis_wallet['address_bytes']
        
        print(f"✓ Token transaction created")
        
        # Sign the transaction properly like create_transaction.py
        print("\n🔐 Signing transaction with genesis key...")
        tx_data = token_tx.get_data_hash()  # Use get_data_hash() like create_transaction.py
        signature = FalconSignature.sign_message(tx_data, genesis_wallet['private_key'])
        print(f"DEBUG: Generated signature length: {len(signature)} bytes")
        print(f"DEBUG: Expected max signature size: {FalconSignature.get_algorithm_details()['signature_size']} bytes")
        print(f"DEBUG: Signature hash: {signature[:20].hex()}...")
        token_tx._data.signature = signature
        
        # Update transaction hash after signing (important!)
        token_tx.update_txhash()
        
        print(f"✓ Transaction signed and hash updated")
        print(f"  Final Transaction Hash: {bin2hstr(token_tx.txhash)}")
        
        # Submit to network
        print("\n📤 Submitting transaction to QRL network...")
        channel = grpc.insecure_channel(NODE_GRPC_ENDPOINT)
        stub = qbit_pb2_grpc.PublicAPIStub(channel)
        
        push_transaction_req = qbit_pb2.PushTransactionReq(transaction_signed=token_tx.pbdata)
        push_transaction_resp = stub.PushTransaction(push_transaction_req, timeout=CONNECTION_TIMEOUT)
        
        if push_transaction_resp.error_code == qbit_pb2.PushTransactionResp.SUBMITTED:
            print("✅ Token creation transaction submitted successfully!")
            print(f"   Transaction Hash: {bin2hstr(token_tx.txhash)}")
            print(f"   Token ID: {bin2hstr(token_tx.txhash)}")
            
            # Save token info for future use
            token_info = {
                "token_txhash": bin2hstr(token_tx.txhash),
                "symbol": token_symbol.decode(),
                "name": token_name.decode(),
                "decimals": decimals,
                "owner": genesis_wallet['address'],
                "total_supply": total_supply,
                "creation_block": "pending"
            }
            
            with open('token_info.json', 'w') as f:
                json.dump(token_info, f, indent=4)
            
            print("💾 Token info saved to token_info.json")
            return token_tx
            
        else:
            print(f"❌ Token creation failed: {push_transaction_resp.error_description}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating token: {e}")
        import traceback
        traceback.print_exc()
        return None

def wait_for_confirmation(tx_hash):
    """Wait for transaction confirmation"""
    print(f"\n⏳ Waiting for transaction confirmation...")
    print(f"   Transaction Hash: {tx_hash}")
    print("   You can check status with: qrl tx_inspect --txblob <blob>")
    print("   Or check in QRL explorer when available")

def get_token_details(token_txhash):
    """Get token details from the blockchain"""
    try:
        print(f"\n🔍 Getting token details for: {token_txhash}")
        
        channel = grpc.insecure_channel(NODE_GRPC_ENDPOINT)
        stub = qbit_pb2_grpc.PublicAPIStub(channel)
        
        # Convert hash to bytes
        txhash_bytes = bytes.fromhex(token_txhash)
        
        get_transaction_req = qbit_pb2.GetTransactionReq(tx_hash=txhash_bytes)
        get_transaction_resp = stub.GetTransaction(get_transaction_req, timeout=CONNECTION_TIMEOUT)
        
        if get_transaction_resp.found:
            tx = get_transaction_resp.tx
            print("✅ Token found on blockchain!")
            print(f"   Block Number: {get_transaction_resp.block_number}")
            print(f"   Block Hash: {bin2hstr(get_transaction_resp.block_hash)}")
            print(f"   Confirmations: {get_transaction_resp.confirmations}")
            
            if tx.token:
                print(f"   Symbol: {tx.token.symbol.decode()}")
                print(f"   Name: {tx.token.name.decode()}")
                print(f"   Decimals: {tx.token.decimals}")
                print(f"   Owner: Q{bin2hstr(tx.token.owner)}")
                print(f"   Initial Balances: {len(tx.token.initial_balances)}")
                
                for i, balance in enumerate(tx.token.initial_balances):
                    address = f"Q{bin2hstr(balance.address)}"
                    amount = balance.amount / (10 ** tx.token.decimals)
                    print(f"     {i+1}. {address}: {amount:,} tokens")
            
            return True
        else:
            print("❌ Token not found on blockchain yet (may still be pending)")
            return False
            
    except Exception as e:
        print(f"❌ Error getting token details: {e}")
        return False

if __name__ == "__main__":
    # Create the token
    token_tx = create_real_token()
    
    if token_tx:
        tx_hash = bin2hstr(token_tx.txhash)
        wait_for_confirmation(tx_hash)
        
        # Try to get token details (may not be available immediately)
        print("\n" + "="*60)
        get_token_details(tx_hash)
        
        print(f"\n=== Summary ===")
        print("✅ Token creation transaction submitted successfully")
        print(f"   Token ID: {tx_hash}")
        print("   Check token_info.json for details")
        print("   Use transfer_real_token.py to transfer tokens")
    else:
        print("❌ Token creation failed")
