# Quick Start Guide

Welcome to Qbitcoin! This guide will get you up and running in 15 minutes.

## What You'll Learn

By the end of this guide, you'll have:
- ✅ A running Qbitcoin node
- ✅ A wallet with your first addresses
- ✅ Basic understanding of key commands
- ✅ Connected to the Qbitcoin network

## Before You Start

Make sure you have:
- [ ] Completed [installation](./02-Installation.md)
- [ ] At least 4 GB RAM available
- [ ] Stable internet connection
- [ ] 20+ GB free disk space

## Step 1: First Launch (2 minutes)

### Start Your Node
Open terminal in your Qbitcoin directory and run:
```bash
python start_qbitcoin.py
```

You should see output like:
```
[INFO] Qbitcoin Node Starting...
[INFO] Loading configuration...
[INFO] Initializing blockchain...
[INFO] Starting P2P network...
[INFO] Node is ready on port 9000
```

**🎉 Congratulations!** Your node is now running.

### Stop Your Node
To stop the node, press `Ctrl+C` in the terminal.

## Step 2: Create Your First Wallet (3 minutes)

### Generate New Wallet
```bash
python start_qbitcoin.py --create-wallet
```

You'll be prompted to:
1. **Set a password** (remember this!)
2. **Backup your seed phrase** (write it down safely!)

Example output:
```
Enter wallet password: ********
Confirm password: ********

🔐 Wallet created successfully!

Your seed phrase (WRITE THIS DOWN SAFELY):
abandon ability able about above absent absorb abstract...

Wallet address: qbitcoin1234567890abcdef...
```

### Important Security Notes
- **Never share your seed phrase**
- **Store it offline and securely**
- **Your password is needed to access the wallet**

## Step 3: Check Your Wallet (1 minute)

### View Wallet Information
```bash
python start_qbitcoin.py --wallet-info
```

Output:
```
💰 Wallet Information:
Balance: 0.00000000 QBC
Addresses: 1
Status: Ready
```

### Generate New Address
```bash
python start_qbitcoin.py --new-address
```

## Step 4: Start the GUI (Optional - 2 minutes)

### Launch Desktop Interface
```bash
python gui/qbitcoin_gui.py
```

This opens a user-friendly desktop application with:
- 📊 Real-time balance and transactions
- 🏗️ Built-in mining interface
- 📤 Easy transaction sending
- ⚙️ Configuration management

## Step 5: Connect to Network (5 minutes)

### Check Network Status
```bash
python start_qbitcoin.py --network-info
```

Expected output:
```
🌐 Network Information:
Connected Peers: 8
Network: mainnet
Sync Status: Syncing (45.2%)
Best Block: 125,847
```

### Monitor Synchronization
Your node needs to download the blockchain. This can take several hours depending on:
- Internet speed
- Computer performance
- Network congestion

**Tip**: Leave your node running overnight for initial sync.

## Step 6: Basic Commands Reference

### Node Operations
```bash
# Start node
python start_qbitcoin.py

# Start with custom config
python start_qbitcoin.py --config /path/to/config.yml

# Start in testnet mode
python start_qbitcoin.py --network testnet

# Check node status
python start_qbitcoin.py --node-info
```

### Wallet Operations
```bash
# Create wallet
python start_qbitcoin.py --create-wallet

# Check balance
python start_qbitcoin.py --balance

# New address
python start_qbitcoin.py --new-address

# Send transaction
python start_qbitcoin.py --send <address> <amount>
```

### Mining Commands
```bash
# Start mining
python start_qbitcoin.py --mine

# Check mining status
python start_qbitcoin.py --mining-info

# Set mining threads
python start_qbitcoin.py --mine --threads 4
```

## Step 7: First Transaction (When Ready)

### Prerequisites
- Node fully synchronized
- Wallet with balance > 0
- Recipient address

### Send Your First Transaction
```bash
python start_qbitcoin.py --send qbitcoin1recipient_address_here 0.1
```

You'll be prompted for your wallet password.

## Common Beginner Scenarios

### Scenario 1: Getting Test Coins
For testing, use the testnet:
```bash
python start_qbitcoin.py --network testnet --create-wallet
```
Join our Discord for testnet faucet access.

### Scenario 2: Mining Your First Coins
```bash
# Start mining (after full sync)
python start_qbitcoin.py --mine --threads 2
```

### Scenario 3: Setting Up Multiple Wallets
```bash
# Create additional wallet
python start_qbitcoin.py --create-wallet --wallet-name "savings"

# Use specific wallet
python start_qbitcoin.py --wallet "savings" --balance
```

## Troubleshooting Quick Fixes

### ❌ "Port already in use"
```bash
# Check what's using the port
netstat -tulpn | grep 9000

# Kill the process or change port
python start_qbitcoin.py --port 9002
```

### ❌ "Cannot connect to peers"
- Check internet connection
- Verify firewall settings
- Try different network: `--network testnet`

### ❌ "Wallet not found"
```bash
# List available wallets
python start_qbitcoin.py --list-wallets

# Create if missing
python start_qbitcoin.py --create-wallet
```

### ❌ "Sync taking too long"
- This is normal for first sync
- Check peers: `--network-info`
- Consider using fast-sync (see advanced guides)

## Configuration Basics

### Default Configuration File
Located at: `~/.qbitcoin/config.yml`

### Basic Configuration
```yaml
# Network settings
network:
  port: 9000
  max_peers: 20

# Mining settings
mining:
  enabled: false
  threads: 2

# Wallet settings
wallet:
  default_fee: 0.001
```

## What's Next?

Now that you're up and running, explore these guides:

### Immediate Next Steps
1. **[Wallet Creation](./10-Wallet-Creation.md)** - Advanced wallet management
2. **[Transaction Guide](./11-Transaction-Guide.md)** - Sending and receiving QBC
3. **[Running a Node](./07-Running-Node.md)** - Node operation best practices

### When Ready to Mine
4. **[Mining Basics](./13-Mining-Basics.md)** - Start earning QBC
5. **[Mining Optimization](./14-Mining-Advanced.md)** - Maximize your hashrate

### Advanced Features
6. **[MultiSig Wallets](./12-MultiSig-Wallets.md)** - Enhanced security
7. **[Web Interface](./16-Web-Wallet-Setup.md)** - Browser-based access
8. **[Post-Quantum Cryptography](./04-Post-Quantum-Cryptography.md)** - Understand the technology

## Get Help and Support

### Community Resources
- **Discord**: [Join our community](https://discord.gg/qbitcoin)
- **Forum**: [Community discussions](https://forum.qbitcoin.org)
- **Reddit**: [r/qbitcoin](https://reddit.com/r/qbitcoin)

### Technical Support
- **GitHub Issues**: [Report bugs](https://github.com/qbitcoin/qbitcoin/issues)
- **Documentation**: [Full documentation](./00-README.md)
- **FAQ**: [Common questions](./24-FAQ.md)

### Development
- **Contributing**: [How to contribute](./25-Contributing.md)
- **API Reference**: [API documentation](./23-API-Reference.md)
- **CLI Reference**: [Command line usage](./05-CLI-Usage.md)

## Success Checklist

Before moving to advanced features, make sure you can:

- [ ] Start and stop your node
- [ ] Create and access wallets
- [ ] Generate new addresses
- [ ] Check your balance
- [ ] View network status
- [ ] Navigate the GUI (if using)
- [ ] Access help for any command
- [ ] Understand basic security practices

**🎊 Well done!** You're now ready to explore the full power of Qbitcoin.

---

**Remember**: 
- Always backup your wallets
- Never share private keys or seed phrases
- Keep your node updated
- Join the community for support and updates
