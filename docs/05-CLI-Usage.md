# CLI Usage Guide

Complete reference for Qbitcoin command-line interface (CLI).

## Overview

The Qbitcoin CLI provides powerful command-line tools for:
- Node management and monitoring
- Wallet operations and transactions
- Mining control and optimization
- Network diagnostics and maintenance
- Configuration and administration

## Basic Command Structure

### Standard Format
```bash
python start_qbitcoin.py [OPTIONS] [COMMAND] [ARGS]
```

### Global Options
```bash
--config PATH          # Specify custom configuration file
--data-dir PATH        # Set custom data directory
--network NAME         # Choose network (mainnet/testnet)
--port PORT           # Set custom port
--verbose             # Enable verbose logging
--quiet               # Suppress output
--help                # Show help information
```

## Node Management Commands

### Starting and Stopping

#### Start Node
```bash
# Start with default settings
python start_qbitcoin.py

# Start with custom configuration
python start_qbitcoin.py --config /path/to/config.yml

# Start on testnet
python start_qbitcoin.py --network testnet

# Start with custom port
python start_qbitcoin.py --port 9002

# Start with verbose logging
python start_qbitcoin.py --verbose
```

#### Stop Node
```bash
# Graceful shutdown (from another terminal)
python start_qbitcoin.py --stop

# Force stop (Ctrl+C in running terminal)
```

### Node Information

#### Node Status
```bash
# Basic node information
python start_qbitcoin.py --node-info

# Detailed node status
python start_qbitcoin.py --node-status --verbose

# Check if node is running
python start_qbitcoin.py --ping
```

Example output:
```
🔗 Node Information:
Version: 1.0.0
Status: Running
Uptime: 2 hours, 34 minutes
Data Directory: /home/user/.qbitcoin
Network: mainnet
Port: 9000
Peers: 12
```

#### Network Information
```bash
# Network statistics
python start_qbitcoin.py --network-info

# Peer information
python start_qbitcoin.py --peers

# Connection status
python start_qbitcoin.py --connection-status
```

### Blockchain Information

#### Blockchain Status
```bash
# Current blockchain height
python start_qbitcoin.py --height

# Sync status
python start_qbitcoin.py --sync-status

# Block information
python start_qbitcoin.py --block-info [BLOCK_HASH]

# Latest block
python start_qbitcoin.py --latest-block
```

#### Chain Statistics
```bash
# Blockchain statistics
python start_qbitcoin.py --chain-stats

# Difficulty information
python start_qbitcoin.py --difficulty

# Hash rate
python start_qbitcoin.py --hashrate
```

## Wallet Commands

### Wallet Management

#### Create Wallet
```bash
# Create new wallet
python start_qbitcoin.py --create-wallet

# Create named wallet
python start_qbitcoin.py --create-wallet --name "savings"

# Create wallet with custom path
python start_qbitcoin.py --create-wallet --wallet-path /path/to/wallet
```

#### Wallet Information
```bash
# Default wallet info
python start_qbitcoin.py --wallet-info

# Specific wallet
python start_qbitcoin.py --wallet-info --name "savings"

# List all wallets
python start_qbitcoin.py --list-wallets

# Wallet balance
python start_qbitcoin.py --balance
```

### Address Management

#### Generate Addresses
```bash
# Generate new address
python start_qbitcoin.py --new-address

# Generate with label
python start_qbitcoin.py --new-address --label "Mining rewards"

# Generate multiple addresses
python start_qbitcoin.py --new-address --count 5
```

#### List Addresses
```bash
# List all addresses
python start_qbitcoin.py --list-addresses

# List with balances
python start_qbitcoin.py --list-addresses --with-balance

# List with labels
python start_qbitcoin.py --list-addresses --with-labels
```

### Transaction Commands

#### Send Transactions
```bash
# Basic send
python start_qbitcoin.py --send RECIPIENT_ADDRESS AMOUNT

# Send with custom fee
python start_qbitcoin.py --send RECIPIENT_ADDRESS AMOUNT --fee 0.001

# Send from specific wallet
python start_qbitcoin.py --send RECIPIENT_ADDRESS AMOUNT --wallet "savings"

# Send with comment
python start_qbitcoin.py --send RECIPIENT_ADDRESS AMOUNT --comment "Payment for services"
```

#### Transaction History
```bash
# Recent transactions
python start_qbitcoin.py --transactions

# Specific number of transactions
python start_qbitcoin.py --transactions --limit 20

# Transactions for specific address
python start_qbitcoin.py --transactions --address QBITCOIN_ADDRESS

# Export transaction history
python start_qbitcoin.py --export-transactions --file transactions.csv
```

#### Transaction Details
```bash
# Get transaction details
python start_qbitcoin.py --transaction TX_HASH

# Check transaction status
python start_qbitcoin.py --tx-status TX_HASH

# Verify transaction
python start_qbitcoin.py --verify-tx TX_HASH
```

## Mining Commands

### Mining Control

#### Start Mining
```bash
# Start mining with default settings
python start_qbitcoin.py --mine

# Start with specific thread count
python start_qbitcoin.py --mine --threads 4

# Start with specific mining address
python start_qbitcoin.py --mine --address MINING_ADDRESS

# Start with intensity setting
python start_qbitcoin.py --mine --intensity 80
```

#### Stop Mining
```bash
# Stop mining
python start_qbitcoin.py --stop-mining

# Stop mining gracefully
python start_qbitcoin.py --stop-mining --graceful
```

### Mining Information

#### Mining Status
```bash
# Current mining status
python start_qbitcoin.py --mining-info

# Mining statistics
python start_qbitcoin.py --mining-stats

# Hashrate information
python start_qbitcoin.py --hashrate --detailed
```

#### Mining Configuration
```bash
# Show mining configuration
python start_qbitcoin.py --mining-config

# Set mining threads
python start_qbitcoin.py --set-mining-threads 6

# Set mining intensity
python start_qbitcoin.py --set-mining-intensity 75
```

## Configuration Commands

### View Configuration
```bash
# Show current configuration
python start_qbitcoin.py --show-config

# Show specific section
python start_qbitcoin.py --show-config --section mining

# Show configuration file path
python start_qbitcoin.py --config-path
```

### Update Configuration
```bash
# Set configuration value
python start_qbitcoin.py --set-config network.port 9001

# Update mining threads
python start_qbitcoin.py --set-config mining.threads 4

# Enable/disable features
python start_qbitcoin.py --set-config mining.enabled true
```

## Utility Commands

### Import/Export Operations

#### Export Data
```bash
# Export wallet
python start_qbitcoin.py --export-wallet --file wallet_backup.json

# Export private keys
python start_qbitcoin.py --export-keys --file keys_backup.txt

# Export blockchain data
python start_qbitcoin.py --export-blockchain --file blockchain_backup.dat
```

#### Import Data
```bash
# Import wallet
python start_qbitcoin.py --import-wallet --file wallet_backup.json

# Import private key
python start_qbitcoin.py --import-key PRIVATE_KEY

# Import from seed phrase
python start_qbitcoin.py --import-seed "word1 word2 word3..."
```

### Backup and Restore

#### Create Backups
```bash
# Backup wallet
python start_qbitcoin.py --backup-wallet --dest /backup/location/

# Backup configuration
python start_qbitcoin.py --backup-config --dest /backup/location/

# Full backup
python start_qbitcoin.py --backup-all --dest /backup/location/
```

#### Restore from Backup
```bash
# Restore wallet
python start_qbitcoin.py --restore-wallet --source /backup/wallet.json

# Restore configuration
python start_qbitcoin.py --restore-config --source /backup/config.yml
```

## Advanced Commands

### Debugging and Diagnostics

#### Debug Information
```bash
# Debug node state
python start_qbitcoin.py --debug-info

# Memory usage
python start_qbitcoin.py --memory-usage

# Performance metrics
python start_qbitcoin.py --performance-metrics
```

#### Network Diagnostics
```bash
# Test network connectivity
python start_qbitcoin.py --test-network

# Ping specific peer
python start_qbitcoin.py --ping-peer PEER_ADDRESS

# Network latency test
python start_qbitcoin.py --latency-test
```

### Maintenance Commands

#### Database Operations
```bash
# Verify blockchain database
python start_qbitcoin.py --verify-db

# Repair database
python start_qbitcoin.py --repair-db

# Compact database
python start_qbitcoin.py --compact-db

# Reindex blockchain
python start_qbitcoin.py --reindex
```

#### Cleanup Operations
```bash
# Clean temporary files
python start_qbitcoin.py --cleanup

# Clear cache
python start_qbitcoin.py --clear-cache

# Reset to genesis
python start_qbitcoin.py --reset-chain --confirm
```

## Batch Operations

### Multiple Commands
```bash
# Chain commands with &&
python start_qbitcoin.py --wallet-info && python start_qbitcoin.py --balance

# Use shell scripts for complex operations
#!/bin/bash
python start_qbitcoin.py --stop-mining
python start_qbitcoin.py --backup-wallet --dest /backup/
python start_qbitcoin.py --mine --threads 2
```

### Scripting Examples

#### Daily Backup Script
```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/backups/qbitcoin/$DATE"
mkdir -p "$BACKUP_DIR"

echo "Starting daily backup..."
python start_qbitcoin.py --backup-wallet --dest "$BACKUP_DIR/"
python start_qbitcoin.py --backup-config --dest "$BACKUP_DIR/"
echo "Backup completed: $BACKUP_DIR"
```

#### Mining Status Monitor
```bash
#!/bin/bash
while true; do
    echo "=== Mining Status $(date) ==="
    python start_qbitcoin.py --mining-info
    python start_qbitcoin.py --hashrate
    sleep 300  # Check every 5 minutes
done
```

## Command Examples by Use Case

### First-Time Setup
```bash
# Complete setup sequence
python start_qbitcoin.py --create-wallet
python start_qbitcoin.py --new-address --label "Primary"  
python start_qbitcoin.py --backup-wallet --dest ~/qbitcoin-backup/
python start_qbitcoin.py --show-config
```

### Daily Operations
```bash
# Check status
python start_qbitcoin.py --node-info
python start_qbitcoin.py --balance
python start_qbitcoin.py --sync-status

# Start mining
python start_qbitcoin.py --mine --threads 4
```

### Transaction Workflow
```bash
# Prepare transaction
python start_qbitcoin.py --balance
python start_qbitcoin.py --new-address --label "Recipient"

# Send transaction
python start_qbitcoin.py --send qbitcoin1abc... 1.5 --fee 0.001

# Monitor transaction
python start_qbitcoin.py --transactions --limit 1
```

### Troubleshooting
```bash
# Diagnose issues
python start_qbitcoin.py --debug-info
python start_qbitcoin.py --test-network
python start_qbitcoin.py --verify-db

# Fix common issues
python start_qbitcoin.py --repair-db
python start_qbitcoin.py --clear-cache
python start_qbitcoin.py --reindex
```

## Error Handling

### Common Error Messages

#### "Wallet not found"
```bash
# Check available wallets
python start_qbitcoin.py --list-wallets

# Create wallet if missing
python start_qbitcoin.py --create-wallet
```

#### "Node not running"
```bash
# Start the node first
python start_qbitcoin.py &

# Then run other commands
python start_qbitcoin.py --wallet-info
```

#### "Insufficient balance"
```bash
# Check current balance
python start_qbitcoin.py --balance

# Check transaction fee
python start_qbitcoin.py --estimate-fee
```

#### "Port already in use"
```bash
# Use different port
python start_qbitcoin.py --port 9001

# Or stop existing process
pkill -f qbitcoin
```

## Output Formats

### JSON Output
```bash
# Get output in JSON format
python start_qbitcoin.py --wallet-info --format json

# Pretty-printed JSON
python start_qbitcoin.py --wallet-info --format json --pretty
```

### CSV Output
```bash
# Export transactions as CSV
python start_qbitcoin.py --transactions --format csv --file transactions.csv
```

### Quiet Mode
```bash
# Suppress non-essential output
python start_qbitcoin.py --balance --quiet

# Only show the balance value
python start_qbitcoin.py --balance --quiet --format value
```

## Environment Variables

### Configuration via Environment
```bash
# Set via environment variables
export QBITCOIN_DATA_DIR="/custom/data/dir"
export QBITCOIN_NETWORK="testnet"
export QBITCOIN_AUTO_MINE="true"

# Use in commands
python start_qbitcoin.py  # Uses environment settings
```

### Common Environment Variables
```bash
QBITCOIN_DATA_DIR      # Custom data directory
QBITCOIN_CONFIG_FILE   # Configuration file path
QBITCOIN_NETWORK       # Network selection
QBITCOIN_PORT          # Default port
QBITCOIN_LOG_LEVEL     # Logging verbosity
```

## Integration Examples

### With System Services
```bash
# Create systemd service file
sudo tee /etc/systemd/system/qbitcoin.service << EOF
[Unit]
Description=Qbitcoin Node
After=network.target

[Service]
Type=simple
User=qbitcoin
ExecStart=/usr/bin/python3 /opt/qbitcoin/start_qbitcoin.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable qbitcoin
sudo systemctl start qbitcoin
```

### With Monitoring Scripts
```bash
#!/bin/bash
# Health check script
STATUS=$(python start_qbitcoin.py --ping --quiet)
if [ $? -ne 0 ]; then
    echo "Qbitcoin node is down, restarting..."
    python start_qbitcoin.py --restart
fi
```

## Best Practices

### Security
1. **Use strong passwords** for wallet encryption
2. **Backup regularly** with `--backup-wallet`
3. **Verify transactions** before sending
4. **Use testnet** for experimentation

### Performance
1. **Optimize thread count** for your hardware
2. **Monitor resource usage** with `--performance-metrics`
3. **Regular maintenance** with `--compact-db`
4. **Use appropriate logging levels**

### Automation
1. **Script routine operations** for consistency
2. **Use configuration files** instead of command-line options
3. **Implement proper error handling** in scripts
4. **Log important operations** for audit trails

## Quick Reference

### Most Common Commands
```bash
# Node operations
python start_qbitcoin.py                    # Start node
python start_qbitcoin.py --node-info        # Check status

# Wallet operations
python start_qbitcoin.py --balance          # Check balance
python start_qbitcoin.py --new-address      # New address
python start_qbitcoin.py --send ADDR AMT    # Send coins

# Mining operations
python start_qbitcoin.py --mine             # Start mining
python start_qbitcoin.py --mining-info      # Mining status
```

### Emergency Commands
```bash
# Recovery operations
python start_qbitcoin.py --repair-db        # Fix database
python start_qbitcoin.py --reindex          # Rebuild index
python start_qbitcoin.py --restore-wallet   # Restore backup
```

---

**For more detailed information about specific features, see the corresponding guides in the [documentation index](./00-README.md).**
