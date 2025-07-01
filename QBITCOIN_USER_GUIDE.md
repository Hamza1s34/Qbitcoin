# Qbitcoin User Guide

Welcome to Qbitcoin! This guide will help you understand how to use all the available commands after installing the package.

## Installation

First, install qbitcoin using pip:

```bash
pip install qbitcoin
```

## Available Commands


```bash
qbitcoin 
```
start qbitcoin 

**Node Options:**
```bash
# Run with specific mining threads
qbitcoin  --mining_thread_count 4

# Run with custom mining address
qbitcoin --miningAddress Q01050092ac9b5e0ffa8d8cf12db6d4dd14b9e18dc766d9aae05a5a3e7dcf30c889b1b2bfb56

# Run in testnet mode
qbitcoin  --network-type testnet

# Run in development mode (low difficulty)
qbitcoin --dev-mode

# Run with custom data directory
qbitcoin  --qrldir /custom/path/to/data

# Run quietly (minimal output)
qbitcoin  --quiet

# Set log level
qbitcoin  --loglevel INFO

# Enable debug mode
qbitcoin  --debug
```


## Wallet Management Commands

### Create a New Wallet
```bash
# Generate a new wallet with one Falcon-512 address
qbitcoin wallet_gen

# Generate an encrypted wallet
qbitcoin wallet_gen --encrypt
```

### List Wallet Addresses
```bash
# List all addresses in your wallet
qbitcoin wallet_ls

# Verbose output with signature types
qbitcoin --verbose wallet_ls
```

### Add New Address to Wallet
```bash
# Add a new Falcon-512 address to existing wallet
qbitcoin wallet_add
```

### Wallet Security Commands
```bash
# Encrypt an existing wallet
qbitcoin wallet_encrypt

# Decrypt a wallet
qbitcoin wallet_decrypt

# Show wallet secret keys (use carefully!)
qbitcoin wallet_secret

# Remove an address from wallet
qbitcoin wallet_rm
```

## Balance and Account Information

### Check Balance
```bash
# Check balance of wallet addresses
qbitcoin balance

# Check balance of specific address
qbitcoin balance --address Q01050092ac9b5e0ffa8d8cf12db6d4dd14b9e18dc766d9aae05a5a3e7dcf30c889b1b2bfb56
```

### List Tokens
```bash
# List all tokens owned by an address
qbitcoin token_list --owner Q01050092ac9b5e0ffa8d8cf12db6d4dd14b9e18dc766d9aae05a5a3e7dcf30c889b1b2bfb56
```

## Transaction Commands

### Send Qbitcoin (Transfer Transaction)
```bash
# Send Qbitcoin to another address
qbitcoin tx_transfer --src 0 --dst Q01050092ac9b5e0ffa8d8cf12db6d4dd14b9e18dc766d9aae05a5a3e7dcf30c889b1b2bfb56 --amount 100

# Send with custom fee
qbitcoin tx_transfer --src 0 --dst Q01050092ac9b5e0ffa8d8cf12db6d4dd14b9e18dc766d9aae05a5a3e7dcf30c889b1b2bfb56 --amount 100 --fee 1

# Send and broadcast immediately
qbitcoin tx_transfer --src 0 --dst Q01050092ac9b5e0ffa8d8cf12db6d4dd14b9e18dc766d9aae05a5a3e7dcf30c889b1b2bfb56 --amount 100 --broadcast
```

### Send Message Transaction
```bash
# Send a message on the blockchain
qbitcoin tx_message --src 0 --message "Hello Qbitcoin Network!" --fee 1

# Send message and broadcast
qbitcoin tx_message --src 0 --message "Hello World" --broadcast
```

### Create and Transfer Tokens

#### Create a New Token
```bash
# Create a new token
qbitcoin tx_token --src 0 --symbol "MYTOKEN" --name "My Token" --initial_balances Q01050092ac9b5e0ffa8d8cf12db6d4dd14b9e18dc766d9aae05a5a3e7dcf30c889b1b2bfb56:1000000

# Create token with multiple initial holders
qbitcoin tx_token --src 0 --symbol "TEST" --name "Test Token" --initial_balances Q01050092ac9b5e0ffa8d8cf12db6d4dd14b9e18dc766d9aae05a5a3e7dcf30c889b1b2bfb56:500000,Q01060092ac9b5e0ffa8d8cf12db6d4dd14b9e18dc766d9aae05a5a3e7dcf30c889b1b2bfb57:500000
```

#### Transfer Tokens
```bash
# Transfer tokens to another address
qbitcoin tx_transfertoken --src 0 --dst Q01050092ac9b5e0ffa8d8cf12db6d4dd14b9e18dc766d9aae05a5a3e7dcf30c889b1b2bfb56 --token_hash abcd1234... --amount 1000
```

## Multi-Signature Commands

### Create Multi-Signature Address
```bash
# Create a 2-of-3 multisig address
qbitcoin tx_multi_sig_create --src 0 --threshold 2 --signatories Q010...,Q020...,Q030...
```

### Spend from Multi-Signature Address
```bash
# Spend from multisig (requires multiple signatures)
qbitcoin tx_multi_sig_spend --src 0 --multi_sig_address Q040... --dst Q050... --amount 100
```

## Advanced Commands

### Transaction Management
```bash
# Inspect a transaction before broadcasting
qbitcoin tx_inspect --txblob 01020304...

# Push/broadcast a transaction to the network
qbitcoin tx_push --txblob 01020304...
```

### Slave Transaction (Hierarchical Signatures)
```bash
# Generate slave transaction for delegated signing
qbitcoin slave_tx_generate --src 0 --slave_pks pk1,pk2,pk3 --access_types 0,1,2
```

### Node State Information
```bash
# Get current node state and blockchain info
qbitcoin state

# Get state in JSON format
qbitcoin --json state
```

## Global Options

These options can be used with any command:

```bash
# Connect to remote node
qbitcoin --host 192.168.1.100 --port_pub 19009 wallet_ls

# Use custom wallet directory
qbitcoin --wallet_dir /path/to/wallet balance

# Verbose output
qbitcoin --verbose wallet_ls

# JSON output format
qbitcoin --json state
```

## Common Usage Examples

### Setting Up and Using a Wallet

1. **Create your first wallet:**
   ```bash
   qbitcoin wallet_gen --encrypt
   ```

2. **Check your wallet addresses:**
   ```bash
   qbitcoin wallet_ls
   ```

3. **Check your balance:**
   ```bash
   qbitcoin balance
   ```

4. **Send Qbitcoin to someone:**
   ```bash
   qbitcoin tx_transfer --src 0 --dst Q01050092ac9b5e0ffa8d8cf12db6d4dd14b9e18dc766d9aae05a5a3e7dcf30c889b1b2bfb56 --amount 50 --broadcast
   ```

### Running a Mining Node

1. **Start a node with mining:**
   ```bash
   qbitcoin-node --mining_thread_count 4 --miningAddress Q01050092ac9b5e0ffa8d8cf12db6d4dd14b9e18dc766d9aae05a5a3e7dcf30c889b1b2bfb56
   ```

2. **Check node status:**
   ```bash
   qbitcoin state
   ```

### Creating and Managing Tokens

1. **Create a new token:**
   ```bash
   qbitcoin tx_token --src 0 --symbol "MYCOIN" --name "My Coin" --initial_balances Q01050092ac9b5e0ffa8d8cf12db6d4dd14b9e18dc766d9aae05a5a3e7dcf30c889b1b2bfb56:1000000 --broadcast
   ```

2. **Check your tokens:**
   ```bash
   qbitcoin token_list --owner Q01050092ac9b5e0ffa8d8cf12db6d4dd14b9e18dc766d9aae05a5a3e7dcf30c889b1b2bfb56
   ```

3. **Transfer tokens:**
   ```bash
   qbitcoin tx_transfertoken --src 0 --dst Q01060092ac9b5e0ffa8d8cf12db6d4dd14b9e18dc766d9aae05a5a3e7dcf30c889b1b2bfb57 --token_hash <token_hash> --amount 100 --broadcast
   ```

## Security Notes

- **Always encrypt your wallet** with a strong password
- **Back up your wallet file** securely
- **Never share your wallet secret keys** 
- **Use testnet for experimentation** before mainnet transactions
- **Verify transaction details** before broadcasting

## Getting Help

For help with any command, use the `--help` flag:

```bash
qbitcoin --help
qbitcoin wallet_gen --help
qbitcoin tx_transfer --help
```

## Environment Variables

- `ENV_QRL_WALLET_DIR`: Set default wallet directory

```bash
export ENV_QRL_WALLET_DIR=/path/to/wallet
qbitcoin wallet_ls  # Will use the directory from environment variable
```

This guide covers all the main functionality of Qbitcoin. The quantum-resistant blockchain features make it perfect for secure, future-proof cryptocurrency transactions!
