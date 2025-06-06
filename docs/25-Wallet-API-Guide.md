# Qbitcoin Wallet API Guide

Complete documentation for Qbitcoin's Wallet API - the **private** interface for wallet management and transaction creation.

## Table of Contents

- [Overview](#overview)
- [Security Warning](#security-warning)
- [API Configuration](#api-configuration)
- [Connection Setup](#connection-setup)
- [Wallet Management](#wallet-management)
- [Address Operations](#address-operations)
- [Transaction Operations](#transaction-operations)
- [Query Operations](#query-operations)
- [Advanced Features](#advanced-features)
- [Error Handling](#error-handling)
- [Security Best Practices](#security-best-practices)
- [Examples](#examples)

## Overview

The Qbitcoin Wallet API provides **private** functionality for wallet management, transaction creation, and account operations. Unlike the Public API (port 19009), the Wallet API should **never** be exposed to the public internet.

### Key Features

- **Wallet Management**: Create, encrypt, lock/unlock wallets
- **Address Generation**: Create new addresses with various configurations
- **Transaction Creation**: Send transfers, tokens, messages
- **Private Operations**: Access to sensitive wallet functions
- **Slave Key Support**: Advanced key management for high-frequency operations

### API Types Comparison

| API Type | Port | Purpose | Security | Exposure |
|----------|------|---------|----------|----------|
| **Wallet API** | 19010 | Private wallet operations | 🔒 Critical | **Never public** |
| Public API | 19009 | Read-only blockchain data | ✅ Safe | Public OK |
| Mining API | 19007 | Mining pool integration | ⚠️ Restricted | Mining pools only |
| Admin API | 19008 | Node administration | 🔒 Critical | Local only |

## Security Warning

⚠️ **CRITICAL SECURITY WARNING** ⚠️

**NEVER expose the Wallet API (port 19010) to the public internet!**

- Contains sensitive wallet operations
- Can create and sign transactions
- Has access to private keys and wallet data
- Should only be accessible from localhost or trusted private networks

## API Configuration

### Configuration File

Edit your `config.yml`:

```yaml
# Wallet API Configuration (KEEP PRIVATE!)
wallet_api_enabled: true
wallet_api_host: "127.0.0.1"  # NEVER change to 0.0.0.0
wallet_api_port: 19010
wallet_api_threads: 1
wallet_api_max_concurrent_rpc: 100

# Security: Ensure other APIs don't conflict
public_api_port: 19009   # Different port
admin_api_port: 19008    # Different port
```

### Programmatic Configuration

In `qbitcoin/core/config.py`:

```python
# UserConfig.__init__()
self.wallet_api_enabled = True
self.wallet_api_host = "127.0.0.1"  # NEVER expose publicly
self.wallet_api_port = 19010
self.wallet_api_threads = 1
self.wallet_api_max_concurrent_rpc = 100
```

## Connection Setup

### Python gRPC Connection

```python
import grpc
from qbitcoin.generated import qbitwallet_pb2_grpc, qbitwallet_pb2

# Connect to local wallet API
channel = grpc.insecure_channel('localhost:19010')
wallet_stub = qbitwallet_pb2_grpc.WalletAPIStub(channel)

# For remote private network (VPN/trusted network only)
# channel = grpc.insecure_channel('192.168.1.100:19010')
# wallet_stub = qbitwallet_pb2_grpc.WalletAPIStub(channel)
```

### Command Line Testing

```bash
# Install grpcurl for testing
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest

# List wallet API methods
grpcurl -plaintext localhost:19010 list qrl.WalletAPI

# Test basic connection
grpcurl -plaintext localhost:19010 qrl.WalletAPI/GetWalletInfo
```

## Wallet Management

### Create New Wallet

```python
# Add a new address to wallet
request = qbitwallet_pb2.AddNewAddressReq()
response = wallet_stub.AddNewAddress(request)

if response.code == 0:
    print(f"New address created: {response.address}")
else:
    print(f"Error: {response.error}")
```

### Encrypt Wallet

```python
# Encrypt wallet with passphrase
request = qbitwallet_pb2.EncryptWalletReq(
    passphrase="your_secure_passphrase"
)
response = wallet_stub.EncryptWallet(request)

if response.code == 0:
    print("Wallet encrypted successfully")
    print("Wallet is now locked - unlock to use")
```

### Lock/Unlock Wallet

```python
# Lock wallet
lock_request = qbitwallet_pb2.LockWalletReq()
lock_response = wallet_stub.LockWallet(lock_request)

# Unlock wallet
unlock_request = qbitwallet_pb2.UnlockWalletReq(
    passphrase="your_secure_passphrase"
)
unlock_response = wallet_stub.UnlockWallet(unlock_request)

if unlock_response.code == 0:
    print("Wallet unlocked successfully")
```

### Get Wallet Information

```python
request = qbitwallet_pb2.GetWalletInfoReq()
response = wallet_stub.GetWalletInfo(request)

print(f"Wallet Version: {response.version}")
print(f"Address Count: {response.address_count}")
print(f"Is Encrypted: {response.is_encrypted}")
```

## Address Operations

### List All Addresses

```python
request = qbitwallet_pb2.ListAddressesReq()
response = wallet_stub.ListAddresses(request)

if response.code == 0:
    for addr_info in response.addresses:
        print(f"Address: {addr_info.address}")
        print(f"Balance: {addr_info.balance}")
        print(f"Index: {addr_info.index}")
else:
    print(f"Error (wallet locked?): {response.error}")
```

### Create Address with Slave Keys

```python
# Create address with slave keys for high-frequency operations
request = qbitwallet_pb2.AddNewAddressWithSlavesReq()
response = wallet_stub.AddNewAddressWithSlaves(request)

if response.code == 0:
    print(f"Master address: {response.address}")
    print("Slave keys created for high-frequency use")
```

### Add Address from Seed

```python
# Recover address from hexseed or mnemonic
request = qbitwallet_pb2.AddAddressFromSeedReq(
    seed="your_hexseed_or_mnemonic_here"
)
response = wallet_stub.AddAddressFromSeed(request)

if response.code == 0:
    print(f"Address recovered: {response.address}")
```

### Remove Address

```python
# Remove address from wallet
request = qbitwallet_pb2.RemoveAddressReq(
    address="Q0103004f6da98043000b1e8ca0a139cc32c72f23b7d7d1ba1b0c79e4c9e5ac4618b5b9b2f4"
)
response = wallet_stub.RemoveAddress(request)

if response.code == 0:
    print("Address removed from wallet")
```

### Validate Address

```python
request = qbitwallet_pb2.ValidAddressReq(
    address="Q0103004f6da98043000b1e8ca0139cc32c72f23b7d7d1ba1b0c79e4c9e5ac4618b5b9b2f4"
)
response = wallet_stub.IsValidAddress(request)

print(f"Valid address: {response.valid}")
```

## Transaction Operations

### Send QRL Transfer

```python
# Send QRL coins to one or more addresses
addresses_to = [
    "Q010300a9c861c8dbb8e3f4b651f7ab0b75e8b2b2d2f3e4c5d6a7b8c9d0e1f2g3h4i5j6k7",
    "Q010300b8d752b9c8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3b2c1d0"
]
amounts = [1000000000, 500000000]  # In Shor (1e9 Shor = 1 QRL)
fee = 100000000  # 0.1 QRL

request = qbitwallet_pb2.RelayTransferTxnReq(
    addresses_to=addresses_to,
    amounts=amounts,
    fee=fee,
    master_address=None,  # Use if paying from master of slave keys
    signer_address="Q0103...",  # Your address
    ots_index=0  # One-time signature index
)

response = wallet_stub.RelayTransferTxn(request)

if response.code == 0:
    print(f"Transaction sent successfully!")
    print(f"Transaction hash: {response.tx.transaction_hash}")
else:
    print(f"Error: {response.error}")
```

### Send Transfer via Slave Key

```python
# High-frequency transactions using slave keys
request = qbitwallet_pb2.RelayTransferTxnBySlaveReq(
    addresses_to=addresses_to,
    amounts=amounts,
    fee=fee,
    master_address="Q0103..."  # Master address that owns the slave
)

response = wallet_stub.RelayTransferTxnBySlave(request)
```

### Send Message Transaction

```python
# Send a message transaction
request = qbitwallet_pb2.RelayMessageTxnReq(
    message=b"Hello Qbitcoin!",
    fee=100000000,
    master_address=None,
    signer_address="Q0103...",
    ots_index=1
)

response = wallet_stub.RelayMessageTxn(request)

if response.code == 0:
    print("Message transaction sent!")
```

### Create Token

```python
# Create a new token
request = qbitwallet_pb2.RelayTokenTxnReq(
    symbol=b"MYTOKEN",
    name=b"My Custom Token",
    owner="Q0103...",  # Token owner address
    decimals=2,
    addresses=["Q0103...", "Q0104..."],  # Initial holders
    amounts=[1000000, 500000],  # Initial balances
    fee=100000000,
    master_address=None,
    signer_address="Q0103...",
    ots_index=2
)

response = wallet_stub.RelayTokenTxn(request)

if response.code == 0:
    print(f"Token created! Transaction hash: {response.tx.transaction_hash}")
```

### Transfer Tokens

```python
# Transfer existing tokens
request = qbitwallet_pb2.RelayTransferTokenTxnReq(
    addresses_to=["Q0104..."],
    amounts=[100000],  # Token amounts (consider decimals)
    token_txhash="token_creation_transaction_hash",
    fee=100000000,
    master_address=None,
    signer_address="Q0103...",
    ots_index=3
)

response = wallet_stub.RelayTransferTokenTxn(request)
```

### Create Slave Keys

```python
# Create slave keys for an address
alice_pk = bytes.fromhex("alice_public_key_hex")
bob_pk = bytes.fromhex("bob_public_key_hex")

request = qbitwallet_pb2.RelaySlaveTxnReq(
    slave_pks=[alice_pk, bob_pk],
    access_types=[0, 0],  # 0 = full access
    fee=100000000,
    master_address=None,
    signer_address="Q0103...",
    ots_index=4
)

response = wallet_stub.RelaySlaveTxn(request)
```

## Query Operations

### Get Balance

```python
# Get balance for specific address
request = qbitwallet_pb2.BalanceReq(
    address="Q0103004f6da98043000b1e8ca0139cc32c72f23b7d7d1ba1b0c79e4c9e5ac4618b5b9b2f4"
)
response = wallet_stub.GetBalance(request)

if response.code == 0:
    print(f"Balance: {response.balance} Shor")
    print(f"Balance: {response.balance / 1e9} QRL")
```

### Get Total Balance

```python
# Get total balance across all wallet addresses
request = qbitwallet_pb2.TotalBalanceReq()
response = wallet_stub.GetTotalBalance(request)

if response.code == 0:
    print(f"Total Balance: {response.balance / 1e9} QRL")
```

### Get Transaction History

```python
# Get transactions for an address
request = qbitwallet_pb2.TransactionsByAddressReq(
    address="Q0103..."
)
response = wallet_stub.GetTransactionsByAddress(request)

if response.code == 0:
    for tx in response.mini_transactions:
        print(f"TX Hash: {tx.transaction_hash}")
        print(f"Amount: {tx.amount}")
        print(f"Block: {tx.block_number}")
```

### Get Paginated Transactions

```python
# Get paginated transaction history
request = qbitwallet_pb2.PaginatedTransactionsByAddressReq(
    address="Q0103...",
    item_per_page=10,
    page_number=1
)
response = wallet_stub.GetPaginatedTransactionsByAddress(request)

if response.code == 0:
    print(f"Total transactions: {len(response.mini_transactions)}")
    print(f"Balance: {response.balance}")
```

### Get Specific Transaction

```python
# Get details of specific transaction
request = qbitwallet_pb2.TransactionReq(
    tx_hash="transaction_hash_here"
)
response = wallet_stub.GetTransaction(request)

if response.code == 0:
    print(f"Confirmations: {response.confirmations}")
    print(f"Block Number: {response.block_number}")
    print(f"Transaction: {response.tx}")
```

### Get OTS Status

```python
# Check One-Time Signature status
request = qbitwallet_pb2.OTSReq(
    address="Q0103..."
)
response = wallet_stub.GetOTS(request)

if response.code == 0:
    print(f"Next OTS Index: {response.next_unused_ots_index}")
    print(f"Available: {response.unused_ots_index_found}")
```

## Advanced Features

### Recovery Seeds

```python
# Get recovery seeds for wallet addresses
request = qbitwallet_pb2.GetRecoverySeedsReq(
    address="Q0103..."
)
response = wallet_stub.GetRecoverySeeds(request)

if response.code == 0:
    print(f"Hexseed: {response.hexseed}")
    print(f"Mnemonic: {response.mnemonic}")
```

### Change Wallet Passphrase

```python
request = qbitwallet_pb2.ChangePassphraseReq(
    oldPassphrase="old_passphrase",
    newPassphrase="new_secure_passphrase"
)
response = wallet_stub.ChangePassphrase(request)

if response.code == 0:
    print("Passphrase changed successfully")
```

### Get Node Information

```python
# Get node information through wallet API
request = qbitwallet_pb2.NodeInfoReq()
response = wallet_stub.GetNodeInfo(request)

print(f"Node Version: {response.version}")
print(f"Connections: {response.num_connections}")
print(f"Block Height: {response.block_height}")
```

## Error Handling

### Common Error Codes

```python
def handle_wallet_response(response):
    if response.code == 0:
        return True  # Success
    elif response.code == 1:
        # General error - check response.error for details
        if "wallet locked" in response.error.lower():
            print("Wallet is locked - please unlock first")
        elif "insufficient" in response.error.lower():
            print("Insufficient balance")
        elif "invalid address" in response.error.lower():
            print("Invalid address format")
        else:
            print(f"Error: {response.error}")
        return False
    else:
        print(f"Unknown error code: {response.code}")
        return False

# Usage
response = wallet_stub.ListAddresses(request)
if handle_wallet_response(response):
    # Process successful response
    pass
```

### Connection Error Handling

```python
import grpc

def safe_wallet_call(stub, method, request):
    try:
        response = method(request)
        return response, None
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.UNAVAILABLE:
            return None, "Wallet API unavailable - is the node running?"
        elif e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            return None, "Request timeout"
        else:
            return None, f"gRPC error: {e.details()}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

# Usage
response, error = safe_wallet_call(
    wallet_stub, 
    wallet_stub.GetWalletInfo, 
    qbitwallet_pb2.GetWalletInfoReq()
)

if error:
    print(f"Error: {error}")
elif response.code == 0:
    print("Success!")
```

## Security Best Practices

### Network Security

1. **Never expose wallet API publicly**:
   ```bash
   # Good - localhost only
   wallet_api_host: "127.0.0.1"
   
   # NEVER do this
   # wallet_api_host: "0.0.0.0"
   ```

2. **Firewall protection**:
   ```bash
   # Block wallet API from external access
   sudo ufw deny from any to any port 19010
   
   # Allow only specific trusted IPs if needed
   sudo ufw allow from 192.168.1.0/24 to any port 19010
   ```

3. **VPN/SSH tunneling** for remote access:
   ```bash
   # SSH tunnel for secure remote access
   ssh -L 19010:localhost:19010 user@your-node-server
   
   # Then connect to localhost:19010 from your local machine
   ```

### Wallet Security

1. **Always encrypt your wallet**:
   ```python
   # Encrypt with strong passphrase
   encrypt_request = qbitwallet_pb2.EncryptWalletReq(
       passphrase="very_strong_passphrase_123!"
   )
   wallet_stub.EncryptWallet(encrypt_request)
   ```

2. **Lock wallet when not in use**:
   ```python
   # Lock after operations
   lock_request = qbitwallet_pb2.LockWalletReq()
   wallet_stub.LockWallet(lock_request)
   ```

3. **Backup recovery seeds securely**:
   ```python
   # Get and securely store recovery information
   recovery_request = qbitwallet_pb2.GetRecoverySeedsReq(address="Q0103...")
   recovery_response = wallet_stub.GetRecoverySeeds(recovery_request)
   
   # Store hexseed and mnemonic securely offline
   ```

### Application Security

1. **Environment variables for sensitive data**:
   ```python
   import os
   
   passphrase = os.getenv('WALLET_PASSPHRASE')
   wallet_api_host = os.getenv('WALLET_API_HOST', 'localhost')
   ```

2. **Input validation**:
   ```python
   def validate_qrl_address(address):
       if not address.startswith('Q'):
           return False
       if len(address) != 79:
           return False
       return True
   
   def validate_amount(amount):
       if amount <= 0:
           return False
       if amount < 100000000:  # Minimum 0.1 QRL
           print("Warning: very small amount")
       return True
   ```

## Examples

### Complete Wallet Manager

```python
#!/usr/bin/env python3
"""
Qbitcoin Wallet Manager
Comprehensive wallet operations example
"""

import grpc
import os
import getpass
from qbitcoin.generated import qbitwallet_pb2_grpc, qbitwallet_pb2

class QbitcoinWallet:
    def __init__(self, host='localhost', port=19010):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = qbitwallet_pb2_grpc.WalletAPIStub(self.channel)
    
    def create_wallet(self, passphrase=None):
        """Create and encrypt a new wallet"""
        # Create first address
        add_req = qbitwallet_pb2.AddNewAddressReq()
        add_resp = self.stub.AddNewAddress(add_req)
        
        if add_resp.code != 0:
            return False, f"Failed to create address: {add_resp.error}"
        
        print(f"Address created: {add_resp.address}")
        
        # Encrypt wallet
        if passphrase:
            encrypt_req = qbitwallet_pb2.EncryptWalletReq(passphrase=passphrase)
            encrypt_resp = self.stub.EncryptWallet(encrypt_req)
            
            if encrypt_resp.code != 0:
                return False, f"Failed to encrypt: {encrypt_resp.error}"
            
            print("Wallet encrypted successfully")
        
        return True, add_resp.address
    
    def unlock_wallet(self, passphrase):
        """Unlock encrypted wallet"""
        unlock_req = qbitwallet_pb2.UnlockWalletReq(passphrase=passphrase)
        unlock_resp = self.stub.UnlockWallet(unlock_req)
        
        if unlock_resp.code == 0:
            print("Wallet unlocked")
            return True
        else:
            print(f"Failed to unlock: {unlock_resp.error}")
            return False
    
    def get_addresses_with_balances(self):
        """Get all addresses with their balances"""
        list_req = qbitwallet_pb2.ListAddressesReq()
        list_resp = self.stub.ListAddresses(list_req)
        
        if list_resp.code != 0:
            return None, list_resp.error
        
        addresses = []
        for addr_info in list_resp.addresses:
            balance_req = qbitwallet_pb2.BalanceReq(address=addr_info.address)
            balance_resp = self.stub.GetBalance(balance_req)
            
            balance = balance_resp.balance if balance_resp.code == 0 else 0
            addresses.append({
                'address': addr_info.address,
                'balance': balance,
                'balance_qrl': balance / 1e9
            })
        
        return addresses, None
    
    def send_transaction(self, to_address, amount_qrl, from_address, ots_index=None):
        """Send QRL transaction"""
        amount_shor = int(amount_qrl * 1e9)
        fee = 100000000  # 0.1 QRL
        
        # Get next OTS index if not provided
        if ots_index is None:
            ots_req = qbitwallet_pb2.OTSReq(address=from_address)
            ots_resp = self.stub.GetOTS(ots_req)
            
            if ots_resp.code != 0:
                return False, f"Failed to get OTS: {ots_resp.error}"
            
            ots_index = ots_resp.next_unused_ots_index
        
        # Create transaction
        tx_req = qbitwallet_pb2.RelayTransferTxnReq(
            addresses_to=[to_address],
            amounts=[amount_shor],
            fee=fee,
            signer_address=from_address,
            ots_index=ots_index
        )
        
        tx_resp = self.stub.RelayTransferTxn(tx_req)
        
        if tx_resp.code == 0:
            return True, tx_resp.tx.transaction_hash
        else:
            return False, tx_resp.error

def main():
    wallet = QbitcoinWallet()
    
    print("Qbitcoin Wallet Manager")
    print("======================")
    
    while True:
        print("\nOptions:")
        print("1. Create new wallet")
        print("2. Unlock wallet")
        print("3. Show addresses and balances")
        print("4. Send transaction")
        print("5. Exit")
        
        choice = input("Choose option: ")
        
        if choice == '1':
            passphrase = getpass.getpass("Enter passphrase (optional): ")
            if not passphrase:
                passphrase = None
            
            success, result = wallet.create_wallet(passphrase)
            if success:
                print(f"Wallet created with address: {result}")
            else:
                print(f"Error: {result}")
        
        elif choice == '2':
            passphrase = getpass.getpass("Enter passphrase: ")
            wallet.unlock_wallet(passphrase)
        
        elif choice == '3':
            addresses, error = wallet.get_addresses_with_balances()
            if error:
                print(f"Error: {error}")
            else:
                print("\nAddresses and Balances:")
                for addr in addresses:
                    print(f"  {addr['address']}: {addr['balance_qrl']:.9f} QRL")
        
        elif choice == '4':
            from_addr = input("From address: ")
            to_addr = input("To address: ")
            amount = float(input("Amount (QRL): "))
            
            success, result = wallet.send_transaction(to_addr, amount, from_addr)
            if success:
                print(f"Transaction sent! Hash: {result}")
            else:
                print(f"Error: {result}")
        
        elif choice == '5':
            break

if __name__ == "__main__":
    main()
```

### Automated Token Creator

```python
#!/usr/bin/env python3
"""
Automated Token Creation Tool
"""

import grpc
from qbitcoin.generated import qbitwallet_pb2_grpc, qbitwallet_pb2

def create_token(symbol, name, owner_address, decimals, initial_distributions):
    """
    Create a new token with initial distribution
    
    initial_distributions: [(address, amount), ...]
    """
    channel = grpc.insecure_channel('localhost:19010')
    stub = qbitwallet_pb2_grpc.WalletAPIStub(channel)
    
    # Prepare addresses and amounts
    addresses = [addr for addr, amount in initial_distributions]
    amounts = [amount for addr, amount in initial_distributions]
    
    # Create token
    request = qbitwallet_pb2.RelayTokenTxnReq(
        symbol=symbol.encode(),
        name=name.encode(),
        owner=owner_address,
        decimals=decimals,
        addresses=addresses,
        amounts=amounts,
        fee=100000000,  # 0.1 QRL
        signer_address=owner_address,
        ots_index=0  # Should get from OTS status
    )
    
    response = stub.RelayTokenTxn(request)
    
    if response.code == 0:
        return True, response.tx.transaction_hash
    else:
        return False, response.error

# Example usage
if __name__ == "__main__":
    distributions = [
        ("Q0103...", 1000000),  # 1M tokens to address 1
        ("Q0104...", 500000),   # 500K tokens to address 2
    ]
    
    success, result = create_token(
        symbol="DEMO",
        name="Demo Token",
        owner_address="Q0103...",
        decimals=2,
        initial_distributions=distributions
    )
    
    if success:
        print(f"Token created! Transaction: {result}")
    else:
        print(f"Error: {result}")
```

This Wallet API guide provides comprehensive documentation for all private wallet operations. Remember to always keep the Wallet API secure and never expose it publicly!
