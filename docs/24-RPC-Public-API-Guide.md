# Qbitcoin RPC and Public API Guide

Complete documentation for Qbitcoin's Remote Procedure Call (RPC) and Public API interfaces.

## Table of Contents

- [Overview](#overview)
- [API Configuration](#api-configuration)
- [Public Node Configuration](#public-node-configuration)
- [Public API Reference](#public-api-reference)
- [Node Information](#node-information)
- [Blockchain Data](#blockchain-data)
- [Address Operations](#address-operations)
- [Transaction Operations](#transaction-operations)
- [Network Information](#network-information)
- [Mining Information](#mining-information)
- [API Examples](#api-examples)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Security Considerations](#security-considerations)

## Overview

Qbitcoin provides multiple API interfaces for interacting with the blockchain:

### API Types

#### 1. Public API
- **Port**: 19009 (default)
- **Purpose**: Read-only blockchain data access
- **Security**: Safe for public exposure
- **Usage**: Explorers, wallets, applications

#### 2. Wallet API  
- **Port**: 19010 (default)
- **Purpose**: Wallet management and transactions
- **Security**: Private use only
- **Usage**: Personal wallets, services

#### 3. Mining API
- **Port**: 19007 (default)
- **Purpose**: Mining pool integration
- **Security**: Mining pool specific
- **Usage**: Mining pools, miners

#### 4. Admin API
- **Port**: 19008 (default)
- **Purpose**: Node administration
- **Security**: Local access only
- **Usage**: Node management

#### 5. Debug API
- **Port**: 52134 (default)
- **Purpose**: Development and debugging
- **Security**: Development only
- **Usage**: Developers, testing

### Protocol Support

- **gRPC**: Primary protocol (all APIs)
- **HTTP/JSON**: Available via gRPC-Gateway
- **WebSocket**: Real-time subscriptions (planned)

## API Configuration

### Configuration File Location

The main configuration is in `/path/to/qrl_dir/config.yml`:

```yaml
# Public API Configuration
public_api_enabled: true
public_api_host: "0.0.0.0"  # Change from 127.0.0.1 to expose publicly
public_api_port: 19009
public_api_threads: 1
public_api_max_concurrent_rpc: 100

# Wallet API Configuration  
wallet_api_enabled: true
wallet_api_host: "127.0.0.1"  # Keep private for security
wallet_api_port: 19010
wallet_api_threads: 1
wallet_api_max_concurrent_rpc: 100

# Mining API Configuration
mining_api_enabled: false
mining_api_host: "127.0.0.1"
mining_api_port: 19007
mining_api_threads: 1
mining_api_max_concurrent_rpc: 100

# Admin API Configuration
admin_api_enabled: false
admin_api_host: "127.0.0.1"
admin_api_port: 19008
admin_api_threads: 1
admin_api_max_concurrent_rpc: 100

# Debug API Configuration
debug_api_enabled: false
debug_api_host: "127.0.0.1"
debug_api_port: 52134
debug_api_threads: 1
debug_api_max_concurrent_rpc: 100
```

### Programmatic Configuration

You can also configure APIs programmatically by modifying `qbitcoin/core/config.py`:

```python
# In UserConfig.__init__()
self.public_api_enabled = True
self.public_api_host = "0.0.0.0"  # Expose to public
self.public_api_port = 19009
self.public_api_threads = 4  # Increase for load
self.public_api_max_concurrent_rpc = 500
```

## Public Node Configuration

### Making Your Node Public

To expose your Qbitcoin node's API to the public internet:

#### Step 1: Update Configuration

Edit your `config.yml` file:

```yaml
# Change from 127.0.0.1 to 0.0.0.0
public_api_host: "0.0.0.0"
public_api_enabled: true
public_api_port: 19009

# Increase capacity for public load
public_api_threads: 4
public_api_max_concurrent_rpc: 1000
```

#### Step 2: Update config.py (Alternative)

Modify `/qbitcoin/core/config.py`:

```python
# Line ~87 in UserConfig.__init__():
self.public_api_host = "0.0.0.0"  # Change from "127.0.0.1"
self.public_api_threads = 4       # Increase from 1
self.public_api_max_concurrent_rpc = 1000  # Increase from 100
```

#### Step 3: Firewall Configuration

Open the port in your firewall:

```bash
# Ubuntu/Debian
sudo ufw allow 19009

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=19009/tcp
sudo firewall-cmd --reload

# Check if port is accessible
netstat -tlnp | grep 19009
```

#### Step 4: Network Configuration

For cloud instances or routers:
- **AWS**: Add inbound rule for port 19009
- **Router**: Forward port 19009 to your node
- **Docker**: Map port with `-p 19009:19009`

#### Step 5: Restart Node

```bash
# Stop node
pkill -f start_qbitcoin.py

# Start with new configuration
python start_qbitcoin.py
```

#### Step 6: Verify Public Access

Test from external network:

```bash
# Test gRPC connection
grpcurl -plaintext YOUR_PUBLIC_IP:19009 qrl.PublicAPI/GetNodeState

# Test with curl (if HTTP gateway enabled)
curl http://YOUR_PUBLIC_IP:19009/api/GetNodeState
```

### Security Recommendations

#### For Public Nodes

1. **Enable Only Public API**
   ```yaml
   public_api_enabled: true
   wallet_api_enabled: false  # Never expose publicly
   admin_api_enabled: false   # Never expose publicly
   mining_api_enabled: false  # Only if mining pool
   debug_api_enabled: false   # Never expose publicly
   ```

2. **Firewall Rules**
   ```bash
   # Allow only public API port
   sudo ufw allow 19009
   
   # Block other API ports from external access
   sudo ufw deny from any to any port 19010  # Wallet API
   sudo ufw deny from any to any port 19008  # Admin API
   sudo ufw deny from any to any port 19007  # Mining API
   sudo ufw deny from any to any port 52134  # Debug API
   ```

3. **Rate Limiting**
   ```yaml
   public_api_max_concurrent_rpc: 1000
   # Consider using nginx or HAProxy for additional rate limiting
   ```

4. **Monitoring**
   ```bash
   # Monitor API usage
   netstat -an | grep :19009 | wc -l
   
   # Monitor logs
   tail -f ~/.qrl/qrl.log | grep "PublicAPI"
   ```

## Public API Reference

### Connection

#### gRPC Connection

```python
import grpc
from qbitcoin.generated import qbit_pb2_grpc, qbit_pb2

# Connect to public API
channel = grpc.insecure_channel('localhost:19009')
stub = qbit_pb2_grpc.PublicAPIStub(channel)

# For public nodes
channel = grpc.insecure_channel('node.example.com:19009')
stub = qbit_pb2_grpc.PublicAPIStub(channel)
```

#### Command Line Tools

```bash
# Install grpcurl for testing
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest

# List available services
grpcurl -plaintext localhost:19009 list

# List methods for PublicAPI
grpcurl -plaintext localhost:19009 list qrl.PublicAPI
```

## Node Information

### GetNodeState

Get current node status and information.

#### Request
```protobuf
message GetNodeStateReq {}
```

#### Response
```protobuf
message GetNodeStateResp {
    NodeInfo info = 1;
}

message NodeInfo {
    string version = 1;           // Node version
    State state = 2;              // Sync state
    uint32 num_connections = 3;   // Active peer connections
    uint32 num_known_peers = 4;   // Known peers count
    uint64 uptime = 5;            // Node uptime in seconds
    uint64 block_height = 6;      // Current block height
    uint64 block_last_reward = 7; // Last block reward
    string network_id = 8;        // Network identifier
}
```

#### Examples

**gRPC (Python)**
```python
request = qbit_pb2.GetNodeStateReq()
response = stub.GetNodeState(request)

print(f"Version: {response.info.version}")
print(f"Height: {response.info.block_height}")
print(f"Connections: {response.info.num_connections}")
print(f"State: {response.info.state}")
```

**grpcurl**
```bash
grpcurl -plaintext localhost:19009 qrl.PublicAPI/GetNodeState
```

**Response Example**
```json
{
  "info": {
    "version": "4.0.0 python",
    "state": "SYNCED",
    "numConnections": 12,
    "numKnownPeers": 45,
    "uptime": 86400,
    "blockHeight": 125849,
    "blockLastReward": "6656250000",
    "networkId": "mainnet"
  }
}
```

### GetKnownPeers

Get list of known peer nodes.

#### Examples

**gRPC (Python)**
```python
request = qbit_pb2.GetKnownPeersReq()
response = stub.GetKnownPeers(request)

for peer in response.known_peers:
    print(f"Peer: {peer.ip}")
```

**grpcurl**
```bash
grpcurl -plaintext localhost:19009 qrl.PublicAPI/GetKnownPeers
```

### GetPeersStat

Get detailed statistics about connected peers.

#### Examples

**gRPC (Python)**
```python
request = qbit_pb2.GetPeersStatReq()
response = stub.GetPeersStat(request)

for peer_stat in response.peers_stat:
    print(f"Peer: {peer_stat.peer_ip}")
    print(f"Port: {peer_stat.port}")
    print(f"Connected: {peer_stat.connected_at}")
    print(f"Valid Messages: {peer_stat.valid_message_count}")
```

### GetStats

Get blockchain statistics and metrics.

#### Examples

**gRPC (Python)**
```python
request = qbit_pb2.GetStatsReq(include_timeseries=True)
response = stub.GetStats(request)

print(f"Nodes Estimate: {response.node_info.nodes_estimate}")
print(f"Block Time Mean: {response.block_time_mean}")
print(f"Block Time SD: {response.block_time_sd}")
print(f"Coins Total Supply: {response.coins_total_supply}")
print(f"Coins Emitted: {response.coins_emitted}")
```

**Response Example**
```json
{
  "nodeInfo": {
    "version": "4.0.0 python",
    "state": "SYNCED",
    "numConnections": 12,
    "blockHeight": 125849,
    "networkId": "mainnet"
  },
  "epoch": 1258,
  "uptimeNetwork": 91728000,
  "blockTimeMean": 60,
  "blockTimeSd": 5.2,
  "coinsTotalSupply": "105000000000000000",
  "coinsEmitted": "65847321000000000"
}
```

## Blockchain Data

### GetHeight

Get current blockchain height.

#### Examples

**gRPC (Python)**
```python
request = qbit_pb2.GetHeightReq()
response = stub.GetHeight(request)
print(f"Current Height: {response.height}")
```

**grpcurl**
```bash
grpcurl -plaintext localhost:19009 qrl.PublicAPI/GetHeight
```

### GetBlock

Get block by header hash.

#### Request
```protobuf
message GetBlockReq {
    bytes header_hash = 1;
}
```

#### Examples

**gRPC (Python)**
```python
from pyqrllib.pyqrllib import hstr2bin

header_hash = hstr2bin("010500063abcdef...")
request = qbit_pb2.GetBlockReq(header_hash=header_hash)
response = stub.GetBlock(request)

block = response.block
print(f"Block Number: {block.header.block_number}")
print(f"Timestamp: {block.header.timestamp_seconds}")
print(f"Transactions: {len(block.transactions)}")
```

### GetBlockByNumber

Get block by block number.

#### Request
```protobuf
message GetBlockByNumberReq {
    uint64 block_number = 1;
}
```

#### Examples

**gRPC (Python)**
```python
request = qbit_pb2.GetBlockByNumberReq(block_number=125849)
response = stub.GetBlockByNumber(request)

block = response.block
print(f"Header Hash: {block.header.hash_header.hex()}")
print(f"Previous Hash: {block.header.hash_header_prev.hex()}")
print(f"Merkle Root: {block.header.merkle_root.hex()}")
```

**grpcurl**
```bash
grpcurl -plaintext -d '{"block_number": 125849}' \
  localhost:19009 qrl.PublicAPI/GetBlockByNumber
```

## Address Operations

### GetAddressState

Get address balance and transaction count.

#### Request
```protobuf
message GetAddressStateReq {
    bytes address = 1;
}
```

#### Examples

**gRPC (Python)**
```python
from pyqrllib.pyqrllib import hstr2bin

address = hstr2bin("010500063abcdef...")  # Remove 'Q' prefix
request = qbit_pb2.GetAddressStateReq(address=address)
response = stub.GetAddressState(request)

state = response.state
print(f"Balance: {state.balance}")
print(f"Nonce: {state.nonce}")
print(f"OTS Bitfield: {state.ots_bitfield}")
```

**Example with Qbitcoin Address**
```python
def qaddress_to_bin(qaddress: str):
    """Convert Qbitcoin address to binary"""
    from pyqrllib.pyqrllib import hstr2bin
    return hstr2bin(qaddress[1:])  # Remove 'Q' prefix

qaddress = "qbitcoin1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
address = qaddress_to_bin(qaddress)
request = qbit_pb2.GetAddressStateReq(address=address)
response = stub.GetAddressState(request)

print(f"Balance: {response.state.balance / 1e9} QBC")
```

### GetOptimizedAddressState

Get optimized address state for Falcon addresses.

#### Examples

**gRPC (Python)**
```python
qaddress = "qbitcoin1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
address = qaddress_to_bin(qaddress)
request = qbit_pb2.GetAddressStateReq(address=address)
response = stub.GetOptimizedAddressState(request)

state = response.state
print(f"Balance: {state.balance / 1e9} QBC")
print(f"Nonce: {state.nonce}")
```

### ParseAddress

Validate and parse address information.

#### Request
```protobuf
message ParseAddressReq {
    bytes address = 1;
}
```

#### Examples

**gRPC (Python)**
```python
qaddress = "qbitcoin1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
address = qaddress_to_bin(qaddress)
request = qbit_pb2.ParseAddressReq(address=address)
response = stub.ParseAddress(request)

if response.is_valid:
    print(f"Address is valid")
    print(f"Hash Function: {response.desc.hash_function}")
    print(f"Signature Scheme: {response.desc.signature_scheme}")
    print(f"Address Format: {response.desc.address_format}")
else:
    print("Invalid address")
```

### GetAddressFromPK

Generate address from public key.

#### Request
```protobuf
message GetAddressFromPKReq {
    bytes pk = 1;
}
```

#### Examples

**gRPC (Python)**
```python
# For Falcon-512 public key (1793 bytes)
falcon_pk = bytes(1793)  # Your Falcon public key
request = qbit_pb2.GetAddressFromPKReq(pk=falcon_pk)
response = stub.GetAddressFromPK(request)

if response.address:
    qaddress = "Q" + response.address.hex()
    print(f"Generated Address: {qaddress}")
```

## Transaction Operations

### GetTransaction

Get transaction details by hash.

#### Request
```protobuf
message GetTransactionReq {
    bytes tx_hash = 1;
}
```

#### Examples

**gRPC (Python)**
```python
tx_hash = hstr2bin("0123456789abcdef...")
request = qbit_pb2.GetTransactionReq(tx_hash=tx_hash)
response = stub.GetTransaction(request)

tx = response.tx
confirmations = response.confirmations

print(f"Type: {tx.transaction_type}")
print(f"Fee: {tx.fee}")
print(f"Confirmations: {confirmations}")
print(f"Block Number: {response.block_number}")
```

### GetTransactionsByAddress

Get transactions for an address with pagination.

#### Request
```protobuf
message GetTransactionsByAddressReq {
    bytes address = 1;
    uint64 item_per_page = 2;
    uint64 page_number = 3;
}
```

#### Examples

**gRPC (Python)**
```python
qaddress = "qbitcoin1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
address = qaddress_to_bin(qaddress)

request = qbit_pb2.GetTransactionsByAddressReq(
    address=address,
    item_per_page=10,
    page_number=1
)
response = stub.GetTransactionsByAddress(request)

print(f"Total Pages: {response.total_pages}")
for tx_detail in response.transactions_detail:
    tx = tx_detail.tx
    print(f"TX Hash: {tx.transaction_hash.hex()}")
    print(f"Amount: {get_transfer_amount(tx)} QBC")
    print(f"Block: {tx_detail.block_number}")
```

### GetMiniTransactionsByAddress

Get lightweight transaction list for an address.

#### Examples

**gRPC (Python)**
```python
request = qbit_pb2.GetMiniTransactionsByAddressReq(
    address=address,
    item_per_page=20,
    page_number=1
)
response = stub.GetMiniTransactionsByAddress(request)

for mini_tx in response.mini_transactions:
    print(f"TX Hash: {mini_tx.transaction_hash.hex()}")
    print(f"Amount: {mini_tx.amount}")
    print(f"Out: {mini_tx.out}")
```

### PushTransaction

Submit a signed transaction to the network.

#### Request
```protobuf
message PushTransactionReq {
    Transaction transaction_signed = 1;
}
```

#### Examples

**gRPC (Python)**
```python
# Assuming you have a signed transaction
signed_tx = create_and_sign_transaction()

request = qbit_pb2.PushTransactionReq(transaction_signed=signed_tx)
response = stub.PushTransaction(request)

if response.error_code == qbit_pb2.PushTransactionResp.SUBMITTED:
    print(f"Transaction submitted: {signed_tx.transaction_hash.hex()}")
else:
    print(f"Error: {response.error_description}")
```

## Network Information

### GetChainStats

Get blockchain statistics.

#### Examples

**gRPC (Python)**
```python
request = qbit_pb2.GetChainStatsReq()
response = stub.GetChainStats(request)

print(f"Block Height: {response.block_height}")
print(f"Block Time Mean: {response.block_time_mean}")
print(f"Stake Validators: {response.stake_validators_count}")
print(f"Last Block Difficulty: {response.last_block_difficulty}")
```

### Network Health Check

**Example Health Monitor**
```python
import time
import grpc
from qbitcoin.generated import qbit_pb2_grpc, qbit_pb2

def check_node_health(host="localhost", port=19009):
    try:
        channel = grpc.insecure_channel(f'{host}:{port}')
        stub = qbit_pb2_grpc.PublicAPIStub(channel)
        
        # Test basic connectivity
        request = qbit_pb2.GetNodeStateReq()
        response = stub.GetNodeState(request, timeout=5)
        
        node_info = response.info
        
        health = {
            'status': 'healthy',
            'version': node_info.version,
            'height': node_info.block_height,
            'connections': node_info.num_connections,
            'state': str(node_info.state),
            'uptime': node_info.uptime
        }
        
        # Check if synced
        if node_info.state != 2:  # SYNCED = 2
            health['status'] = 'syncing'
            
        # Check connections
        if node_info.num_connections < 3:
            health['status'] = 'low_peers'
            
        return health
        
    except grpc.RpcError as e:
        return {
            'status': 'error',
            'error': str(e)
        }
    except Exception as e:
        return {
            'status': 'unreachable',
            'error': str(e)
        }

# Usage
health = check_node_health()
print(f"Node Status: {health['status']}")
```

## Mining Information

### GetLastBlockHeader

Get the most recent block header for mining.

#### Examples

**gRPC (Mining API)**
```python
import grpc
from qbitcoin.generated import qbitmining_pb2_grpc, qbitmining_pb2

# Connect to mining API
channel = grpc.insecure_channel('localhost:19007')
mining_stub = qbitmining_pb2_grpc.MiningAPIStub(channel)

request = qbitmining_pb2.GetLastBlockHeaderReq()
response = mining_stub.GetLastBlockHeader(request)

header = response.block_header
print(f"Block Number: {header.block_number}")
print(f"Difficulty: {header.difficulty}")
```

### GetBlockToMine

Get block template for mining.

#### Examples

**gRPC (Mining API)**
```python
request = qbitmining_pb2.GetBlockToMineReq(
    miner_address=miner_address
)
response = mining_stub.GetBlockToMine(request)

block_template = response.blocktemplate
print(f"Height: {block_template.block_number}")
print(f"Difficulty: {block_template.difficulty}")
```

## API Examples

### Complete Node Monitor

```python
#!/usr/bin/env python3
"""
Comprehensive Qbitcoin Node Monitor
Monitors node health, blockchain stats, and network status
"""

import grpc
import time
import json
from datetime import datetime
from qbitcoin.generated import qbit_pb2_grpc, qbit_pb2

class QbitcoinMonitor:
    def __init__(self, host="localhost", port=19009):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = qbit_pb2_grpc.PublicAPIStub(self.channel)
        
    def get_node_status(self):
        """Get comprehensive node status"""
        try:
            # Node state
            node_req = qbit_pb2.GetNodeStateReq()
            node_resp = self.stub.GetNodeState(node_req)
            
            # Height
            height_req = qbit_pb2.GetHeightReq()
            height_resp = self.stub.GetHeight(height_req)
            
            # Stats
            stats_req = qbit_pb2.GetStatsReq(include_timeseries=True)
            stats_resp = self.stub.GetStats(stats_req)
            
            # Known peers
            peers_req = qbit_pb2.GetKnownPeersReq()
            peers_resp = self.stub.GetKnownPeers(peers_req)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'node': {
                    'version': node_resp.info.version,
                    'state': str(node_resp.info.state),
                    'uptime': node_resp.info.uptime,
                    'connections': node_resp.info.num_connections,
                    'known_peers': len(peers_resp.known_peers)
                },
                'blockchain': {
                    'height': height_resp.height,
                    'last_reward': node_resp.info.block_last_reward,
                    'epoch': stats_resp.epoch,
                    'network_uptime': stats_resp.uptime_network
                },
                'network': {
                    'block_time_mean': stats_resp.block_time_mean,
                    'block_time_sd': stats_resp.block_time_sd,
                    'coins_emitted': stats_resp.coins_emitted,
                    'coins_total_supply': stats_resp.coins_total_supply
                }
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def check_address_balance(self, qaddress):
        """Check balance for Qbitcoin address"""
        try:
            from pyqrllib.pyqrllib import hstr2bin
            
            address = hstr2bin(qaddress[1:])  # Remove 'Q'
            request = qbit_pb2.GetAddressStateReq(address=address)
            response = self.stub.GetOptimizedAddressState(request)
            
            return {
                'address': qaddress,
                'balance': response.state.balance / 1e9,  # Convert to QBC
                'nonce': response.state.nonce,
                'transaction_count': response.state.transaction_count
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def monitor_loop(self, interval=60):
        """Continuous monitoring loop"""
        while True:
            try:
                status = self.get_node_status()
                print(json.dumps(status, indent=2))
                time.sleep(interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(interval)

# Usage
if __name__ == "__main__":
    monitor = QbitcoinMonitor("localhost", 19009)
    
    # Get single status
    status = monitor.get_node_status()
    print(json.dumps(status, indent=2))
    
    # Check specific address
    balance = monitor.check_address_balance("qbitcoin1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh")
    print(json.dumps(balance, indent=2))
    
    # Start monitoring (uncomment to run)
    # monitor.monitor_loop(60)
```

### Balance Checker Service

```python
#!/usr/bin/env python3
"""
Qbitcoin Balance Checker
RESTful service to check address balances
"""

from flask import Flask, jsonify, request
import grpc
from qbitcoin.generated import qbit_pb2_grpc, qbit_pb2
from pyqrllib.pyqrllib import hstr2bin

app = Flask(__name__)

# Connect to Qbitcoin node
channel = grpc.insecure_channel('localhost:19009')
stub = qbit_pb2_grpc.PublicAPIStub(channel)

@app.route('/balance/<qaddress>')
def get_balance(qaddress):
    """Get balance for Qbitcoin address"""
    try:
        # Validate address format
        if not qaddress.startswith('qbitcoin'):
            return jsonify({'error': 'Invalid address format'}), 400
            
        # Convert to binary
        address = hstr2bin(qaddress[1:])
        
        # Get address state
        request = qbit_pb2.GetAddressStateReq(address=address)
        response = stub.GetOptimizedAddressState(request)
        
        return jsonify({
            'address': qaddress,
            'balance': response.state.balance / 1e9,
            'balance_raw': str(response.state.balance),
            'nonce': response.state.nonce,
            'transaction_count': response.state.transaction_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/transactions/<qaddress>')
def get_transactions(qaddress):
    """Get transactions for address"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # Convert address
        address = hstr2bin(qaddress[1:])
        
        # Get transactions
        request = qbit_pb2.GetMiniTransactionsByAddressReq(
            address=address,
            item_per_page=per_page,
            page_number=page
        )
        response = stub.GetMiniTransactionsByAddress(request)
        
        transactions = []
        for mini_tx in response.mini_transactions:
            transactions.append({
                'hash': mini_tx.transaction_hash.hex(),
                'amount': mini_tx.amount,
                'out': mini_tx.out,
                'block_number': mini_tx.block_number
            })
        
        return jsonify({
            'address': qaddress,
            'page': page,
            'per_page': per_page,
            'total_pages': response.total_pages,
            'transactions': transactions
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/node/status')
def get_node_status():
    """Get node status"""
    try:
        request = qbit_pb2.GetNodeStateReq()
        response = stub.GetNodeState(request)
        
        return jsonify({
            'version': response.info.version,
            'state': str(response.info.state),
            'height': response.info.block_height,
            'connections': response.info.num_connections,
            'uptime': response.info.uptime
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

### Block Explorer API

```python
#!/usr/bin/env python3
"""
Simple Block Explorer API for Qbitcoin
"""

import grpc
from flask import Flask, jsonify, request
from qbitcoin.generated import qbit_pb2_grpc, qbit_pb2
from pyqrllib.pyqrllib import hstr2bin, bin2hstr

app = Flask(__name__)
channel = grpc.insecure_channel('localhost:19009')
stub = qbit_pb2_grpc.PublicAPIStub(channel)

@app.route('/block/<int:block_number>')
def get_block(block_number):
    """Get block by number"""
    try:
        request = qbit_pb2.GetBlockByNumberReq(block_number=block_number)
        response = stub.GetBlockByNumber(request)
        
        block = response.block
        header = block.header
        
        # Process transactions
        transactions = []
        for tx in block.transactions:
            tx_data = {
                'hash': tx.transaction_hash.hex(),
                'type': str(tx.transaction_type),
                'fee': tx.fee,
                'public_key': tx.public_key.hex(),
                'signature': tx.signature.hex()
            }
            
            # Add type-specific data
            if hasattr(tx, 'transfer'):
                tx_data['transfer'] = {
                    'addrs_to': [addr.hex() for addr in tx.transfer.addrs_to],
                    'amounts': list(tx.transfer.amounts)
                }
            
            transactions.append(tx_data)
        
        return jsonify({
            'block_number': header.block_number,
            'header_hash': header.hash_header.hex(),
            'previous_hash': header.hash_header_prev.hex(),
            'merkle_root': header.merkle_root.hex(),
            'timestamp': header.timestamp_seconds,
            'difficulty': header.difficulty,
            'nonce': header.nonce,
            'block_reward': header.block_reward,
            'fee_reward': header.fee_reward,
            'transaction_count': len(transactions),
            'transactions': transactions
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tx/<tx_hash>')
def get_transaction(tx_hash):
    """Get transaction by hash"""
    try:
        tx_hash_bytes = hstr2bin(tx_hash)
        request = qbit_pb2.GetTransactionReq(tx_hash=tx_hash_bytes)
        response = stub.GetTransaction(request)
        
        tx = response.tx
        
        return jsonify({
            'hash': tx.transaction_hash.hex(),
            'type': str(tx.transaction_type),
            'fee': tx.fee,
            'block_number': response.block_number,
            'confirmations': response.confirmations,
            'timestamp': response.timestamp,
            'public_key': tx.public_key.hex(),
            'signature': tx.signature.hex()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search/<query>')
def search(query):
    """Search for block, transaction, or address"""
    try:
        results = []
        
        # Try as block number
        if query.isdigit():
            block_num = int(query)
            try:
                request = qbit_pb2.GetBlockByNumberReq(block_number=block_num)
                response = stub.GetBlockByNumber(request)
                results.append({
                    'type': 'block',
                    'number': block_num,
                    'hash': response.block.header.hash_header.hex()
                })
            except:
                pass
        
        # Try as transaction hash
        if len(query) == 64:  # Hex hash length
            try:
                tx_hash_bytes = hstr2bin(query)
                request = qbit_pb2.GetTransactionReq(tx_hash=tx_hash_bytes)
                response = stub.GetTransaction(request)
                results.append({
                    'type': 'transaction',
                    'hash': query,
                    'block_number': response.block_number
                })
            except:
                pass
        
        # Try as address
        if query.startswith('qbitcoin'):
            try:
                address = hstr2bin(query[1:])
                request = qbit_pb2.GetAddressStateReq(address=address)
                response = stub.GetOptimizedAddressState(request)
                results.append({
                    'type': 'address',
                    'address': query,
                    'balance': response.state.balance / 1e9
                })
            except:
                pass
        
        return jsonify({
            'query': query,
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
```

## Error Handling

### Common Error Codes

#### gRPC Status Codes
- `UNAVAILABLE`: Node not running or unreachable
- `DEADLINE_EXCEEDED`: Request timeout
- `INVALID_ARGUMENT`: Invalid request parameters
- `NOT_FOUND`: Resource not found (block, transaction, etc.)
- `INTERNAL`: Internal server error

#### Qbitcoin Specific Errors
- `INVALID_ADDRESS`: Address format incorrect
- `INSUFFICIENT_BALANCE`: Not enough balance for transaction
- `TRANSACTION_POOL_FULL`: Transaction pool at capacity
- `INVALID_SIGNATURE`: Transaction signature invalid

### Error Handling Example

```python
import grpc
from qbitcoin.generated import qbit_pb2_grpc, qbit_pb2

def safe_api_call(stub, request_func, *args, **kwargs):
    """Safe wrapper for API calls with error handling"""
    try:
        return request_func(*args, **kwargs)
    except grpc.RpcError as e:
        error_code = e.code()
        error_details = e.details()
        
        if error_code == grpc.StatusCode.UNAVAILABLE:
            return {'error': 'Node unavailable', 'retry': True}
        elif error_code == grpc.StatusCode.DEADLINE_EXCEEDED:
            return {'error': 'Request timeout', 'retry': True}
        elif error_code == grpc.StatusCode.INVALID_ARGUMENT:
            return {'error': f'Invalid request: {error_details}', 'retry': False}
        elif error_code == grpc.StatusCode.NOT_FOUND:
            return {'error': 'Resource not found', 'retry': False}
        else:
            return {'error': f'gRPC error: {error_details}', 'retry': False}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}', 'retry': False}

# Usage
result = safe_api_call(stub, stub.GetNodeState, qbit_pb2.GetNodeStateReq())
if 'error' in result:
    print(f"Error: {result['error']}")
    if result['retry']:
        # Implement retry logic
        pass
else:
    # Process successful response
    print(f"Node version: {result.info.version}")
```

## Rate Limiting

### Server-Side Configuration

Configure rate limiting in `config.yml`:

```yaml
public_api_max_concurrent_rpc: 1000
public_api_threads: 4

# Additional rate limiting with nginx (recommended)
# /etc/nginx/sites-available/qbitcoin-api
server {
    listen 80;
    server_name api.yournode.com;
    
    location / {
        limit_req zone=api burst=10 nodelay;
        proxy_pass http://localhost:19009;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# In nginx.conf http block:
# limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
```

### Client-Side Rate Limiting

```python
import time
import threading
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_calls=100, window=60):
        self.max_calls = max_calls
        self.window = window
        self.calls = defaultdict(list)
        self.lock = threading.Lock()
    
    def is_allowed(self, client_id="default"):
        with self.lock:
            now = time.time()
            # Clean old calls
            self.calls[client_id] = [
                call_time for call_time in self.calls[client_id]
                if now - call_time < self.window
            ]
            
            if len(self.calls[client_id]) < self.max_calls:
                self.calls[client_id].append(now)
                return True
            return False
    
    def wait_if_needed(self, client_id="default"):
        if not self.is_allowed(client_id):
            # Calculate wait time
            oldest_call = min(self.calls[client_id])
            wait_time = self.window - (time.time() - oldest_call)
            if wait_time > 0:
                time.sleep(wait_time)

# Usage
limiter = RateLimiter(max_calls=60, window=60)  # 60 calls per minute

def rate_limited_api_call(stub, request):
    limiter.wait_if_needed("my_client")
    return stub.GetNodeState(request)
```

## Security Considerations

### Network Security

#### 1. Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw allow 19009  # Public API
sudo ufw deny 19010   # Wallet API (keep private)
sudo ufw deny 19008   # Admin API (keep private)

# Allow SSH for management
sudo ufw allow ssh

# Enable firewall
sudo ufw enable
```

#### 2. TLS/SSL Encryption (Recommended)
```python
# Server-side TLS configuration
import grpc
from grpc import ssl_channel_credentials

# Generate certificates first
credentials = grpc.ssl_server_credentials([
    (private_key, certificate_chain)
])

server.add_secure_port('0.0.0.0:19009', credentials)

# Client-side TLS
channel = grpc.secure_channel(
    'api.yournode.com:19009',
    ssl_channel_credentials()
)
```

#### 3. Reverse Proxy (Recommended)
```nginx
# nginx configuration for Qbitcoin API
server {
    listen 443 ssl http2;
    server_name api.yournode.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Rate limiting
    limit_req zone=api burst=20 nodelay;
    
    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    
    location / {
        grpc_pass grpc://localhost:19009;
        grpc_set_header Host $host;
        grpc_set_header X-Real-IP $remote_addr;
    }
}
```

### Access Control

#### 1. IP Whitelisting
```yaml
# In config.yml
public_api_allowed_ips:
  - "192.168.1.0/24"
  - "10.0.0.0/8"
  - "203.0.113.0/24"
```

#### 2. Authentication (Custom Implementation)
```python
# Custom authentication interceptor
class AuthInterceptor(grpc.ServerInterceptor):
    def __init__(self, api_keys):
        self.api_keys = api_keys
    
    def intercept_service(self, continuation, handler_call_details):
        # Extract API key from metadata
        metadata = dict(handler_call_details.invocation_metadata)
        api_key = metadata.get('authorization')
        
        if api_key not in self.api_keys:
            return self._deny_request()
        
        return continuation(handler_call_details)
    
    def _deny_request(self):
        # Return authentication error
        pass

# Usage
auth_interceptor = AuthInterceptor(['your-api-key-1', 'your-api-key-2'])
server = grpc.server(ThreadPoolExecutor(), interceptors=[auth_interceptor])
```

### Monitoring and Logging

#### 1. Request Logging
```python
import logging
from datetime import datetime

class RequestLogger:
    def __init__(self):
        self.logger = logging.getLogger('qbitcoin_api')
        handler = logging.FileHandler('/var/log/qbitcoin_api.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_request(self, method, client_ip, response_time):
        self.logger.info(f"{method} - {client_ip} - {response_time}ms")

# Usage in API calls
logger = RequestLogger()
start_time = time.time()
# ... process request ...
response_time = (time.time() - start_time) * 1000
logger.log_request("GetNodeState", client_ip, response_time)
```

#### 2. Health Monitoring
```python
import psutil
import time

class NodeHealthMonitor:
    def __init__(self):
        self.alerts = []
    
    def check_health(self):
        health = {}
        
        # CPU usage
        health['cpu_percent'] = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        health['memory_percent'] = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        health['disk_percent'] = (disk.used / disk.total) * 100
        
        # Network connections
        connections = psutil.net_connections(kind='inet')
        health['network_connections'] = len(connections)
        
        # Check for alerts
        if health['cpu_percent'] > 90:
            self.alerts.append("High CPU usage")
        if health['memory_percent'] > 90:
            self.alerts.append("High memory usage")
        if health['disk_percent'] > 90:
            self.alerts.append("High disk usage")
        
        return health
    
    def get_alerts(self):
        alerts = self.alerts.copy()
        self.alerts.clear()
        return alerts

# Continuous monitoring
monitor = NodeHealthMonitor()
while True:
    health = monitor.check_health()
    alerts = monitor.get_alerts()
    
    if alerts:
        for alert in alerts:
            print(f"ALERT: {alert}")
    
    time.sleep(60)  # Check every minute
```

## Advanced Usage

### Streaming API (Custom Implementation)

```python
import grpc
import asyncio
from typing import AsyncGenerator

class QbitcoinStreamer:
    def __init__(self, host="localhost", port=19009):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = qbit_pb2_grpc.PublicAPIStub(self.channel)
        self.running = False
    
    async def stream_blocks(self) -> AsyncGenerator:
        """Stream new blocks as they arrive"""
        last_height = 0
        
        while self.running:
            try:
                # Get current height
                height_req = qbit_pb2.GetHeightReq()
                height_resp = self.stub.GetHeight(height_req)
                current_height = height_resp.height
                
                # Check for new blocks
                if current_height > last_height:
                    for block_num in range(last_height + 1, current_height + 1):
                        try:
                            block_req = qbit_pb2.GetBlockByNumberReq(
                                block_number=block_num
                            )
                            block_resp = self.stub.GetBlockByNumber(block_req)
                            yield block_resp.block
                        except:
                            pass
                    
                    last_height = current_height
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                print(f"Stream error: {e}")
                await asyncio.sleep(10)
    
    def start_streaming(self):
        self.running = True
    
    def stop_streaming(self):
        self.running = False

# Usage
async def main():
    streamer = QbitcoinStreamer()
    streamer.start_streaming()
    
    async for block in streamer.stream_blocks():
        print(f"New block: {block.header.block_number}")
        print(f"Transactions: {len(block.transactions)}")

# Run
# asyncio.run(main())
```

### Batch Operations

```python
class BatchAPIClient:
    def __init__(self, host="localhost", port=19009):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = qbit_pb2_grpc.PublicAPIStub(self.channel)
    
    def get_multiple_balances(self, addresses):
        """Get balances for multiple addresses efficiently"""
        results = {}
        
        for qaddress in addresses:
            try:
                address = hstr2bin(qaddress[1:])
                request = qbit_pb2.GetAddressStateReq(address=address)
                response = self.stub.GetOptimizedAddressState(request)
                
                results[qaddress] = {
                    'balance': response.state.balance / 1e9,
                    'nonce': response.state.nonce
                }
            except Exception as e:
                results[qaddress] = {'error': str(e)}
        
        return results
    
    def get_block_range(self, start_block, end_block):
        """Get multiple blocks in range"""
        blocks = {}
        
        for block_num in range(start_block, end_block + 1):
            try:
                request = qbit_pb2.GetBlockByNumberReq(block_number=block_num)
                response = self.stub.GetBlockByNumber(request)
                
                blocks[block_num] = {
                    'hash': response.block.header.hash_header.hex(),
                    'timestamp': response.block.header.timestamp_seconds,
                    'tx_count': len(response.block.transactions)
                }
            except Exception as e:
                blocks[block_num] = {'error': str(e)}
        
        return blocks

# Usage
batch_client = BatchAPIClient()

# Check multiple address balances
addresses = [
    "qbitcoin1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    "qbitcoin1qzy3kgdygjrsqtzq2n0yrf2493p83kkfjhx0abc"
]
balances = batch_client.get_multiple_balances(addresses)

# Get block range
blocks = batch_client.get_block_range(125840, 125850)
```

This comprehensive guide covers all aspects of Qbitcoin's RPC and Public API. For wallet-specific operations, see the [Wallet API Guide](./25-Wallet-API-Guide.md).

---

**Next Steps:**
- [Wallet API Guide](./25-Wallet-API-Guide.md) - Complete wallet API documentation
- [Mining API Guide](./26-Mining-API-Guide.md) - Mining pool integration
- [API Security](./27-API-Security.md) - Advanced security practices
- [Performance Tuning](./28-Performance-Guide.md) - Optimizing API performance
