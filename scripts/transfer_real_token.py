#!/usr/bin/env python3
"""
QRL Real Token Transfer Script

This script transfers real tokens on the QRL blockchain between actual wallets
using the tokens created by create_real_token.py
"""

import sys
import os
import grpc
import json
from decimal import Decimal

# Add QRL modules to path
sys.path.append('/workspaces/QRL')

from qbitcoin.core.txs.TransferTokenTransaction import TransferTokenTransaction
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

def load_token_info():
    """Load token information from token_info.json"""
    try:
        with open('token_info.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading token info: {e}")
        print("   Make sure to run create_real_token.py first")
        return None

def get_address_balance(address):
    """Get the QRL balance of an address"""
    try:
        channel = grpc.insecure_channel(NODE_GRPC_ENDPOINT)
        stub = qbit_pb2_grpc.PublicAPIStub(channel)
        
        address_bytes = bytes(hstr2bin(address[1:]))
        get_address_state_req = qbit_pb2.GetAddressStateReq(address=address_bytes)
        get_address_state_resp = stub.GetAddressState(get_address_state_req, timeout=CONNECTION_TIMEOUT)
        
        return get_address_state_resp.state.balance
    except Exception as e:
        print(f"❌ Error getting balance: {e}")
        return 0

def get_token_balance(address, token_txhash):
    """Get the token balance of an address"""
    try:
        channel = grpc.insecure_channel(NODE_GRPC_ENDPOINT)
        stub = qbit_pb2_grpc.PublicAPIStub(channel)
        
        address_bytes = bytes(hstr2bin(address[1:]))
        token_txhash_bytes = bytes.fromhex(token_txhash)
        
        get_address_state_req = qbit_pb2.GetAddressStateReq(address=address_bytes)
        get_address_state_resp = stub.GetAddressState(get_address_state_req, timeout=CONNECTION_TIMEOUT)
        
        # Look for token balance in the address state
        for token in get_address_state_resp.state.tokens:
            if token.token_txhash == token_txhash_bytes:
                return token.balance
        
        return 0
    except Exception as e:
        print(f"❌ Error getting token balance: {e}")
        return 0

def transfer_real_tokens():
    """
    Transfer real tokens between wallets on QRL blockchain
    """
    print("=== Transferring Real Tokens on QRL Blockchain ===\n")
    
    # Load token information
    token_info = load_token_info()
    if not token_info:
        return None
    
    print(f"Token: {token_info['symbol']} ({token_info['name']})")
    print(f"Token ID: {token_info['token_txhash']}")
    print(f"Decimals: {token_info['decimals']}")
    
    # Load wallets
    genesis_wallet = load_wallet('genesis_keys.json')
    new_wallet = load_wallet('new_wallet.json')
    
    if not genesis_wallet or not new_wallet:
        print("❌ Both genesis_keys.json and new_wallet.json are required")
        return None
    
    print(f"\nSender (Genesis): {genesis_wallet['address']}")
    print(f"Receiver (New Wallet): {new_wallet['address']}")
    
    # Check balances
    genesis_qrl_balance = get_address_balance(genesis_wallet['address'])
    genesis_token_balance = get_token_balance(genesis_wallet['address'], token_info['token_txhash'])
    
    print(f"\nGenesis QRL Balance: {genesis_qrl_balance / 1000000000:.3f} Quanta")
    print(f"Genesis Token Balance: {genesis_token_balance / (10 ** token_info['decimals']):,} {token_info['symbol']}")
    
    if genesis_qrl_balance < 2000000000:  # Less than 2 Quanta
        print("❌ Insufficient QRL balance for transfer fee")
        return None
    
    if genesis_token_balance == 0:
        print("❌ No tokens to transfer")
        return None
    
    # Transfer parameters
    transfer_amount = min(genesis_token_balance // 2, 250000)  # Transfer half or 2500 tokens max
    fee = 1000000000  # 1 Quanta fee
    
    print(f"\nTransfer Details:")
    print(f"  Amount: {transfer_amount} token units ({transfer_amount / (10 ** token_info['decimals']):,} {token_info['symbol']})")
    print(f"  Fee: {fee / 1000000000} Quanta")
    
    try:
        # Create the token transfer transaction
        print("\n📝 Creating token transfer transaction...")
        transfer_tx = TransferTokenTransaction.create(
            token_txhash=bytes.fromhex(token_info['token_txhash']),
            addrs_to=[new_wallet['address_bytes']],
            amounts=[transfer_amount],
            fee=fee,
            xmss_pk=genesis_wallet['public_key'],
            master_addr=None
        )
        
        print(f"✓ Transfer transaction created")
        print(f"  Transaction Hash: {bin2hstr(transfer_tx.txhash)}")
        
        # Sign the transaction
        print("\n🔐 Signing transaction with genesis key...")
        tx_data = transfer_tx.get_data_bytes()
        signature = FalconSignature.sign_message(tx_data, genesis_wallet['private_key'])
        transfer_tx._data.signature = signature
        
        print(f"✓ Transaction signed (signature length: {len(signature)} bytes)")
        
        # Submit to network
        print("\n📤 Submitting transfer transaction to QRL network...")
        channel = grpc.insecure_channel(NODE_GRPC_ENDPOINT)
        stub = qbit_pb2_grpc.PublicAPIStub(channel)
        
        push_transaction_req = qbit_pb2.PushTransactionReq(transaction_signed=transfer_tx.pbdata)
        push_transaction_resp = stub.PushTransaction(push_transaction_req, timeout=CONNECTION_TIMEOUT)
        
        if push_transaction_resp.error_code == qbit_pb2.PushTransactionResp.SUBMITTED:
            print("✅ Token transfer transaction submitted successfully!")
            print(f"   Transaction Hash: {bin2hstr(transfer_tx.txhash)}")
            
            # Save transfer info
            transfer_info = {
                "transfer_txhash": bin2hstr(transfer_tx.txhash),
                "token_txhash": token_info['token_txhash'],
                "from_address": genesis_wallet['address'],
                "to_address": new_wallet['address'],
                "amount": transfer_amount,
                "display_amount": transfer_amount / (10 ** token_info['decimals']),
                "symbol": token_info['symbol'],
                "fee": fee,
                "timestamp": "pending"
            }
            
            with open('transfer_info.json', 'w') as f:
                json.dump(transfer_info, f, indent=4)
            
            print("💾 Transfer info saved to transfer_info.json")
            return transfer_tx
            
        else:
            print(f"❌ Token transfer failed: {push_transaction_resp.error_description}")
            return None
            
    except Exception as e:
        print(f"❌ Error transferring tokens: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_transfer_status(transfer_txhash):
    """Check the status of a transfer transaction"""
    try:
        print(f"\n🔍 Checking transfer status for: {transfer_txhash}")
        
        channel = grpc.insecure_channel(NODE_GRPC_ENDPOINT)
        stub = qbit_pb2_grpc.PublicAPIStub(channel)
        
        txhash_bytes = bytes.fromhex(transfer_txhash)
        get_transaction_req = qbit_pb2.GetTransactionReq(tx_hash=txhash_bytes)
        get_transaction_resp = stub.GetTransaction(get_transaction_req, timeout=CONNECTION_TIMEOUT)
        
        if get_transaction_resp.found:
            tx = get_transaction_resp.tx
            print("✅ Transfer confirmed on blockchain!")
            print(f"   Block Number: {get_transaction_resp.block_number}")
            print(f"   Block Hash: {bin2hstr(get_transaction_resp.block_hash)}")
            print(f"   Confirmations: {get_transaction_resp.confirmations}")
            
            if tx.transfer_token:
                print(f"   Token ID: {bin2hstr(tx.transfer_token.token_txhash)}")
                print(f"   Recipients: {len(tx.transfer_token.addrs_to)}")
                
                for i, (addr, amount) in enumerate(zip(tx.transfer_token.addrs_to, tx.transfer_token.amounts)):
                    recipient = f"Q{bin2hstr(addr)}"
                    print(f"     {i+1}. {recipient}: {amount} token units")
            
            return True
        else:
            print("❌ Transfer not found on blockchain yet (may still be pending)")
            return False
            
    except Exception as e:
        print(f"❌ Error checking transfer status: {e}")
        return False

def show_final_balances():
    """Show final token balances after transfer"""
    print("\n" + "="*60)
    print("📊 Final Token Balances")
    
    token_info = load_token_info()
    genesis_wallet = load_wallet('genesis_keys.json')
    new_wallet = load_wallet('new_wallet.json')
    
    if token_info and genesis_wallet and new_wallet:
        genesis_balance = get_token_balance(genesis_wallet['address'], token_info['token_txhash'])
        new_balance = get_token_balance(new_wallet['address'], token_info['token_txhash'])
        
        decimals = token_info['decimals']
        symbol = token_info['symbol']
        
        print(f"Genesis Wallet: {genesis_balance / (10 ** decimals):,} {symbol}")
        print(f"New Wallet: {new_balance / (10 ** decimals):,} {symbol}")
        print(f"Total: {(genesis_balance + new_balance) / (10 ** decimals):,} {symbol}")

if __name__ == "__main__":
    # Transfer the tokens
    transfer_tx = transfer_real_tokens()
    
    if transfer_tx:
        tx_hash = bin2hstr(transfer_tx.txhash)
        
        print(f"\n⏳ Waiting for transfer confirmation...")
        print(f"   Transaction Hash: {tx_hash}")
        
        # Try to check status (may not be available immediately)
        print("\n" + "="*60)
        check_transfer_status(tx_hash)
        
        # Show balances
        show_final_balances()
        
        print(f"\n=== Summary ===")
        print("✅ Token transfer transaction submitted successfully")
        print(f"   Transfer Hash: {tx_hash}")
        print("   Check transfer_info.json for details")
    else:
        print("❌ Token transfer failed")
