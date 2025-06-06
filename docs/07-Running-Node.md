# Running a Qbitcoin Node

Complete guide to operating your own Qbitcoin node for network participation and enhanced security.

## Why Run a Node?

Running your own node provides:
- **Full validation**: Verify all transactions and blocks independently
- **Enhanced privacy**: Direct blockchain access without third parties
- **Network support**: Contribute to Qbitcoin's decentralization
- **Faster transactions**: Direct submission to the network
- **Mining capability**: Enable solo or pool mining
- **Development platform**: Test applications and features

## Node Types

### Full Node (Recommended)
- Downloads and validates entire blockchain
- Stores complete transaction history
- Participates in network consensus
- Supports other nodes and wallets

### Light Node
- Validates block headers only
- Requires less storage and bandwidth
- Depends on full nodes for transaction data
- Suitable for resource-constrained devices

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores, 2.0 GHz
- **RAM**: 4 GB
- **Storage**: 50 GB SSD
- **Network**: 10 Mbps unlimited connection
- **OS**: Linux, macOS, Windows

### Recommended Requirements
- **CPU**: 4+ cores, 3.0+ GHz
- **RAM**: 8+ GB
- **Storage**: 200+ GB NVMe SSD
- **Network**: 50+ Mbps unlimited connection
- **OS**: Linux (Ubuntu 20.04+ or similar)

### Growth Planning
```
Current blockchain size: ~15 GB
Growth rate: ~2 GB per month
Plan for: 100 GB within 2 years
```

## Initial Setup

### 1. Installation
Follow the [Installation Guide](./02-Installation.md) to install Qbitcoin.

### 2. Configuration
Create or edit `~/.qbitcoin/config.yml`:

```yaml
# Node configuration
node:
  # Network settings
  network: mainnet          # mainnet, testnet
  port: 9000               # P2P network port
  max_peers: 20            # Maximum peer connections
  
  # Data settings
  data_dir: ~/.qbitcoin    # Blockchain data directory
  
  # Performance settings
  cache_size: 300          # Memory cache in MB
  db_cache: 450           # Database cache in MB
  
  # Logging
  log_level: info         # debug, info, warning, error
  log_file: qbitcoin.log  # Log file location

# Network specific settings
mainnet:
  bootstrap_nodes:
    - "node1.qbitcoin.org:9000"
    - "node2.qbitcoin.org:9000"
    - "node3.qbitcoin.org:9000"

testnet:
  bootstrap_nodes:
    - "testnet1.qbitcoin.org:9000"
    - "testnet2.qbitcoin.org:9000"
```

### 3. First Start
```bash
# Start your node
python start_qbitcoin.py

# Or with custom configuration
python start_qbitcoin.py --config /path/to/config.yml
```

## Node Startup Process

### Initialization Sequence
```
1. Loading configuration
2. Initializing database
3. Starting P2P network
4. Connecting to peers
5. Beginning blockchain sync
6. Node ready for operations
```

### Expected Output
```
[INFO] Qbitcoin Node v1.0.0 starting...
[INFO] Data directory: /home/user/.qbitcoin
[INFO] Network: mainnet
[INFO] Initializing blockchain database...
[INFO] Starting P2P network on port 9000...
[INFO] Connecting to bootstrap nodes...
[INFO] Connected to 5 peers
[INFO] Starting blockchain synchronization...
[INFO] Sync progress: 0.0% (block 0/125847)
[INFO] Node is ready and accepting connections
```

## Blockchain Synchronization

### Initial Sync Process

#### Fast Sync (Default)
- Downloads block headers first
- Validates proof-of-work
- Downloads full blocks in parallel
- Typical time: 2-6 hours

#### Full Sync
- Downloads blocks sequentially
- Validates all transactions
- More secure but slower
- Typical time: 8-24 hours

### Monitor Sync Progress
```bash
# Check sync status
python start_qbitcoin.py --sync-status

# Monitor in real-time
watch "python start_qbitcoin.py --sync-status"

# Detailed sync information
python start_qbitcoin.py --sync-status --verbose
```

### Sync Status Output
```
🔄 Synchronization Status:
Progress: 67.3% (84,719/125,847 blocks)
Sync Speed: 45 blocks/minute
ETA: 2 hours, 15 minutes
Connected Peers: 12
Download Rate: 2.3 MB/s
```

## Network Operations

### Peer Management

#### View Connected Peers
```bash
# List current peers
python start_qbitcoin.py --peers

# Detailed peer information
python start_qbitcoin.py --peers --detailed
```

#### Peer Information
```
🌐 Connected Peers (12/20):
ID: abc123...def789
Address: 203.0.113.1:9000
Version: 1.0.0
Height: 125,847
Ping: 45ms
Connected: 2h 34m
```

#### Manual Peer Management
```bash
# Add specific peer
python start_qbitcoin.py --add-peer 203.0.113.1:9000

# Remove peer
python start_qbitcoin.py --remove-peer abc123...def789

# Ban misbehaving peer
python start_qbitcoin.py --ban-peer 203.0.113.1
```

### Network Diagnostics

#### Connection Testing
```bash
# Test network connectivity
python start_qbitcoin.py --test-network

# Ping specific node
python start_qbitcoin.py --ping-node node1.qbitcoin.org:9000

# Network latency analysis
python start_qbitcoin.py --network-latency
```

#### Bandwidth Monitoring
```bash
# Show bandwidth usage
python start_qbitcoin.py --bandwidth-stats

# Network I/O in real-time
python start_qbitcoin.py --network-io --live
```

## Node Maintenance

### Regular Maintenance Tasks

#### Daily Tasks
```bash
# Check node health
python start_qbitcoin.py --health-check

# View system resources
python start_qbitcoin.py --system-stats

# Check for updates
python start_qbitcoin.py --check-updates
```

#### Weekly Tasks
```bash
# Database optimization
python start_qbitcoin.py --optimize-db

# Clear unnecessary cache
python start_qbitcoin.py --clear-cache

# Backup node data
python start_qbitcoin.py --backup-node --dest /backup/location/
```

#### Monthly Tasks
```bash
# Full database verification
python start_qbitcoin.py --verify-blockchain

# Performance analysis
python start_qbitcoin.py --performance-report

# Security audit
python start_qbitcoin.py --security-check
```

### Database Management

#### Database Operations
```bash
# Check database integrity
python start_qbitcoin.py --check-db

# Repair corrupted database
python start_qbitcoin.py --repair-db

# Compact database (reduce size)
python start_qbitcoin.py --compact-db

# Rebuild database index
python start_qbitcoin.py --reindex
```

#### Storage Management
```bash
# Check disk usage
python start_qbitcoin.py --disk-usage

# Clean old temporary files
python start_qbitcoin.py --cleanup-temp

# Archive old data
python start_qbitcoin.py --archive-old-blocks --before-height 100000
```

## Performance Optimization

### CPU Optimization

#### Thread Configuration
```yaml
# In config.yml
performance:
  worker_threads: 4        # Number of worker threads
  network_threads: 2       # Network I/O threads
  db_threads: 2           # Database operation threads
```

#### CPU Usage Monitoring
```bash
# Monitor CPU usage
python start_qbitcoin.py --cpu-stats

# Adjust thread priority
python start_qbitcoin.py --set-priority high
```

### Memory Optimization

#### Cache Settings
```yaml
# In config.yml
performance:
  block_cache_mb: 256     # Block cache size
  tx_cache_mb: 128        # Transaction cache size
  utxo_cache_mb: 300      # UTXO set cache size
```

#### Memory Monitoring
```bash
# Check memory usage
python start_qbitcoin.py --memory-stats

# Garbage collection
python start_qbitcoin.py --gc-collect
```

### Network Optimization

#### Connection Limits
```yaml
# In config.yml
network:
  max_peers: 20           # Total peer connections
  max_outbound: 8         # Outbound connections
  max_inbound: 12         # Inbound connections
```

#### Bandwidth Control
```bash
# Set bandwidth limits
python start_qbitcoin.py --set-bandwidth-limit 10MB

# Monitor bandwidth usage
python start_qbitcoin.py --bandwidth-monitor
```

## Security Configuration

### Firewall Setup

#### Linux (UFW)
```bash
# Allow Qbitcoin P2P port
sudo ufw allow 9000/tcp

# Allow API port (if enabled)
sudo ufw allow 9001/tcp comment "Qbitcoin API"

# Enable firewall
sudo ufw enable
```

#### Advanced Firewall Rules
```bash
# Limit connection rate
sudo ufw limit 9000/tcp

# Allow specific IPs only
sudo ufw allow from 203.0.113.0/24 to any port 9000
```

### Access Control

#### API Security
```yaml
# In config.yml
api:
  enabled: true
  port: 9001
  bind_address: "127.0.0.1"  # Local access only
  auth_required: true
  username: "your_username"
  password_hash: "your_hashed_password"
```

#### SSL/TLS Configuration
```yaml
# In config.yml
ssl:
  enabled: true
  cert_file: "/path/to/cert.pem"
  key_file: "/path/to/private.pem"
```

### Monitoring and Alerts

#### Log Monitoring
```bash
# Real-time log monitoring
tail -f ~/.qbitcoin/qbitcoin.log

# Error log filtering
grep "ERROR" ~/.qbitcoin/qbitcoin.log | tail -20

# Security event monitoring
grep -E "(WARN|ERROR|SECURITY)" ~/.qbitcoin/qbitcoin.log
```

#### Alert Setup
```bash
#!/bin/bash
# Node monitoring script
LAST_HEIGHT=$(python start_qbitcoin.py --height --quiet)
PEER_COUNT=$(python start_qbitcoin.py --peer-count --quiet)

if [ "$PEER_COUNT" -lt 5 ]; then
    echo "ALERT: Low peer count ($PEER_COUNT)"
    # Send notification
fi
```

## Troubleshooting

### Common Issues

#### Node Won't Start
```bash
# Check port availability
netstat -tulpn | grep 9000

# Check configuration
python start_qbitcoin.py --validate-config

# Reset to defaults
python start_qbitcoin.py --reset-config
```

#### Sync Problems
```bash
# Force resync from genesis
python start_qbitcoin.py --resync --from-genesis

# Clear peer list and reconnect
python start_qbitcoin.py --clear-peers

# Use different bootstrap nodes
python start_qbitcoin.py --bootstrap-nodes node1.qbitcoin.org:9000,node2.qbitcoin.org:9000
```

#### Connection Issues
```bash
# Test internet connectivity
ping google.com

# Check DNS resolution
nslookup node1.qbitcoin.org

# Manual peer connection
python start_qbitcoin.py --connect-peer 203.0.113.1:9000
```

#### Performance Issues
```bash
# Check system resources
python start_qbitcoin.py --system-stats

# Optimize database
python start_qbitcoin.py --optimize-db

# Restart with more resources
python start_qbitcoin.py --cache-size 512 --db-cache 1024
```

### Recovery Procedures

#### Database Corruption
```bash
# Stop node
python start_qbitcoin.py --stop

# Backup current state
cp -r ~/.qbitcoin ~/.qbitcoin.backup

# Repair database
python start_qbitcoin.py --repair-db

# If repair fails, resync
python start_qbitcoin.py --resync
```

#### Network Fork Issues
```bash
# Check if on correct chain
python start_qbitcoin.py --chain-info

# Force chain validation
python start_qbitcoin.py --validate-chain

# Reset to trusted checkpoint
python start_qbitcoin.py --reset-to-checkpoint BLOCK_HASH
```

## Advanced Configuration

### Custom Network Settings

#### Private Network Setup
```yaml
# In config.yml
network:
  type: private
  network_id: "my_private_network"
  genesis_block: "path/to/genesis.json"
  bootstrap_nodes: []
```

#### Bridge Node Configuration
```yaml
# In config.yml
bridge:
  enabled: true
  networks:
    - mainnet
    - testnet
  ports:
    mainnet: 9000
    testnet: 9010
```

### Plugin System

#### Enable Plugins
```yaml
# In config.yml
plugins:
  enabled: true
  directory: "~/.qbitcoin/plugins"
  load:
    - monitoring
    - api_extensions
    - custom_validators
```

#### Plugin Development
```python
# Example plugin structure
class MyPlugin:
    def on_block_received(self, block):
        # Custom block processing
        pass
    
    def on_transaction_received(self, tx):
        # Custom transaction processing
        pass
```

## Monitoring and Metrics

### Built-in Monitoring

#### Health Metrics
```bash
# Comprehensive health check
python start_qbitcoin.py --health-report

# Export metrics to file
python start_qbitcoin.py --export-metrics --file metrics.json
```

#### Performance Metrics
```bash
# Real-time performance dashboard
python start_qbitcoin.py --dashboard

# Historical performance data
python start_qbitcoin.py --performance-history --days 7
```

### External Monitoring

#### Prometheus Integration
```yaml
# In config.yml
monitoring:
  prometheus:
    enabled: true
    port: 9100
    metrics_path: /metrics
```

#### Grafana Dashboard
- Import Qbitcoin dashboard template
- Connect to Prometheus data source
- Monitor node health and performance

## API Access

### REST API

#### Enable API
```yaml
# In config.yml
api:
  rest:
    enabled: true
    port: 9001
    cors_enabled: true
```

#### API Usage Examples
```bash
# Get node information
curl http://localhost:9001/api/v1/node/info

# Get blockchain height
curl http://localhost:9001/api/v1/blockchain/height

# Get peer information
curl http://localhost:9001/api/v1/network/peers
```

### JSON-RPC API

#### Enable JSON-RPC
```yaml
# In config.yml
api:
  jsonrpc:
    enabled: true
    port: 9002
    methods:
      - getinfo
      - getblockcount
      - getpeerinfo
```

#### JSON-RPC Usage
```bash
# Using curl
curl -X POST -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"getinfo","id":1}' \
     http://localhost:9002/

# Using Python
import requests
response = requests.post('http://localhost:9002/', 
                        json={"jsonrpc":"2.0","method":"getinfo","id":1})
```

## Best Practices

### Operational Excellence

1. **Regular Updates**: Keep node software current
2. **Backup Strategy**: Regular backups of wallet and configuration
3. **Monitoring**: Continuous health and performance monitoring
4. **Security**: Regular security audits and updates
5. **Documentation**: Maintain operational runbooks

### Performance Best Practices

1. **SSD Storage**: Use fast SSD storage for blockchain data
2. **Adequate RAM**: Ensure sufficient memory for caching
3. **Network Quality**: Use reliable, high-speed internet
4. **System Tuning**: Optimize OS for blockchain operations
5. **Regular Maintenance**: Perform routine database optimization

### Security Best Practices

1. **Firewall Configuration**: Proper network security
2. **Access Control**: Restrict API access appropriately
3. **Regular Audits**: Review logs and security events
4. **Backup Security**: Secure backup storage and access
5. **Update Management**: Timely security updates

## Getting Help

### Support Resources
- **Documentation**: [Complete documentation](./00-README.md)
- **Community Forum**: [Node operators forum](https://forum.qbitcoin.org/node-ops)
- **Discord**: [Node operators channel](https://discord.gg/qbitcoin-nodes)
- **GitHub Issues**: [Technical issues](https://github.com/qbitcoin/qbitcoin/issues)

### Professional Support
- **Enterprise Support**: Commercial support options
- **Consulting Services**: Professional node setup and optimization
- **Training Programs**: Node operator certification

---

**Note**: This guide covers standard node operations. For specialized deployments (mining pools, exchanges, etc.), see the [Advanced Topics](./19-Advanced-Topics.md) section.
