#!/usr/bin/env python3
"""
QRL Token and Wallet Details Script

This script shows detailed information about wallets, tokens, and transactions
"""

import sys
import os
import grpc
import json

# Add QRL modules to path
sys.path.append('/workspaces/QRL')

from qbitcoin.generated import qbit_pb2, qbit_pb2_grpc
from pyqrllib.pyqrllib import hstr2bin, bin2hstr

# Constants
NODE_GRPC_ENDPOINT = "localhost:19009"
CONNECTION_TIMEOUT = 10

def load_wallet(file_path):
    """Load wallet from JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        return None

def get_address_details(address):
    """Get comprehensive address details from the node"""
    try:
        channel = grpc.insecure_channel(NODE_GRPC_ENDPOINT)
        stub = qbit_pb2_grpc.PublicAPIStub(channel)
        
        address_bytes = bytes(hstr2bin(address[1:]))  # Remove 'Q' prefix
        get_address_state_req = qbit_pb2.GetAddressStateReq(address=address_bytes)
        get_address_state_resp = stub.GetAddressState(get_address_state_req, timeout=CONNECTION_TIMEOUT)
        
        state = get_address_state_resp.state
        
        print(f"📍 Address: {address}")
        print(f"   QRL Balance: {state.balance / 1000000000:,.6f} Qbitcoin")
        print(f"   Nonce: {state.nonce}")
        print(f"   OTS Key Index: {state.ots_bitfield_used_page}")
        print(f"   Tokens Owned: {len(state.tokens)}")
        
        if state.tokens:
            print(f"   Token Balances:")
            for i, token in enumerate(state.tokens):
                token_hash = bin2hstr(token.token_txhash)
                balance = token.balance / (10 ** token.decimals)
                print(f"     {i+1}. Token {token_hash[:16]}...: {balance:,} (decimals: {token.decimals})")
        
        return state
        
    except Exception as e:
        print(f"❌ Error getting address details: {e}")
        return None

def get_transaction_details(tx_hash):
    """Get transaction details from the blockchain"""
    try:
        channel = grpc.insecure_channel(NODE_GRPC_ENDPOINT)
        stub = qbit_pb2_grpc.PublicAPIStub(channel)
        
        txhash_bytes = bytes.fromhex(tx_hash)
        get_transaction_req = qbit_pb2.GetTransactionReq(tx_hash=txhash_bytes)
        get_transaction_resp = stub.GetTransaction(get_transaction_req, timeout=CONNECTION_TIMEOUT)
        
        if get_transaction_resp.found:
            tx = get_transaction_resp.tx
            
            print(f"📄 Transaction: {tx_hash}")
            print(f"   Block Number: {get_transaction_resp.block_number}")
            print(f"   Block Hash: {bin2hstr(get_transaction_resp.block_hash)}")
            print(f"   Confirmations: {get_transaction_resp.confirmations}")
            print(f"   Fee: {tx.fee / 1000000000:,.6f} Qbitcoin")
            print(f"   From: Q{bin2hstr(tx.master_addr)}")
            
            # Check transaction type
            if tx.token:
                print(f"   Type: Token Creation")
                print(f"   Symbol: {tx.token.symbol.decode()}")
                print(f"   Name: {tx.token.name.decode()}")
                print(f"   Decimals: {tx.token.decimals}")
                print(f"   Owner: Q{bin2hstr(tx.token.owner)}")
                print(f"   Initial Distribution:")
                
                total_supply = 0
                for i, balance in enumerate(tx.token.initial_balances):
                    address = f"Q{bin2hstr(balance.address)}"
                    amount = balance.amount / (10 ** tx.token.decimals)
                    total_supply += balance.amount
                    print(f"     {i+1}. {address}: {amount:,} tokens")
                
                print(f"   Total Supply: {total_supply / (10 ** tx.token.decimals):,} tokens")
                
            elif tx.transfer_token:
                print(f"   Type: Token Transfer")
                print(f"   Token ID: {bin2hstr(tx.transfer_token.token_txhash)}")
                print(f"   Recipients:")
                
                total_transferred = 0
                for i, (addr, amount) in enumerate(zip(tx.transfer_token.addrs_to, tx.transfer_token.amounts)):
                    recipient = f"Q{bin2hstr(addr)}"
                    total_transferred += amount
                    print(f"     {i+1}. {recipient}: {amount} token units")
                
                print(f"   Total Transferred: {total_transferred} token units")
                
            elif tx.transfer:
                print(f"   Type: QRL Transfer")
                print(f"   Recipients:")
                
                total_sent = 0
                for i, (addr, amount) in enumerate(zip(tx.transfer.addrs_to, tx.transfer.amounts)):
                    recipient = f"Q{bin2hstr(addr)}"
                    total_sent += amount
                    print(f"     {i+1}. {recipient}: {amount / 1000000000:,.6f} Qbitcoin")
                
                print(f"   Total Sent: {total_sent / 1000000000:,.6f} Qbitcoin")
            
            return tx
        else:
            print(f"❌ Transaction {tx_hash} not found")
            return None
            
    except Exception as e:
        print(f"❌ Error getting transaction details: {e}")
        return None

def show_wallet_info():
    """Show information about all available wallets"""
    print("=== Wallet Information ===\n")
    
    # Genesis wallet
    genesis = load_wallet('genesis_keys.json')
    if genesis:
        print("🔑 Genesis Wallet:")
        get_address_details(genesis['address'])
        print()
    
    # New wallet
    new_wallet = load_wallet('new_wallet.json')
    if new_wallet:
        print("🆕 New Wallet:")
        get_address_details(new_wallet['address'])
        print()

def show_token_info():
    """Show information about created tokens"""
    print("=== Token Information ===\n")
    
    try:
        with open('token_info.json', 'r') as f:
            token_info = json.load(f)
        
        print("🪙 Created Token:")
        print(f"   Symbol: {token_info['symbol']}")
        print(f"   Name: {token_info['name']}")
        print(f"   Decimals: {token_info['decimals']}")
        print(f"   Owner: {token_info['owner']}")
        print(f"   Total Supply: {token_info['total_supply'] / (10 ** token_info['decimals']):,} tokens")
        print(f"   Token ID: {token_info['token_txhash']}")
        print()
        
        # Get transaction details
        print("📄 Token Creation Transaction:")
        get_transaction_details(token_info['token_txhash'])
        print()
        
    except FileNotFoundError:
        print("❌ No token_info.json found. Run create_real_token.py first.")
        print()

def show_transfer_info():
    """Show information about token transfers"""
    print("=== Transfer Information ===\n")
    
    try:
        with open('transfer_info.json', 'r') as f:
            transfer_info = json.load(f)
        
        print("💸 Token Transfer:")
        print(f"   Token: {transfer_info['symbol']}")
        print(f"   From: {transfer_info['from_address']}")
        print(f"   To: {transfer_info['to_address']}")
        print(f"   Amount: {transfer_info['display_amount']:,} {transfer_info['symbol']}")
        print(f"   Fee: {transfer_info['fee'] / 1000000000} Qbitcoin")
        print(f"   Transfer ID: {transfer_info['transfer_txhash']}")
        print()
        
        # Get transaction details
        print("📄 Transfer Transaction:")
        get_transaction_details(transfer_info['transfer_txhash'])
        print()
        
    except FileNotFoundError:
        print("❌ No transfer_info.json found. Run transfer_real_token.py first.")
        print()

def main():
    """Main function to display all information"""
    print("🔍 QRL Token and Wallet Details\n")
    print("="*60)
    
    # Show wallet information
    show_wallet_info()
    
    print("="*60)
    
    # Show token information
    show_token_info()
    
    print("="*60)
    
    # Show transfer information
    show_transfer_info()
    
    print("="*60)
    print("✅ Details displayed successfully")

if __name__ == "__main__":
    main()
