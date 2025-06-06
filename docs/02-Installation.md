# Installation Guide

This guide will walk you through installing Qbitcoin on different operating systems.

## System Requirements

### Minimum Requirements
- **OS**: Linux (Ubuntu 18.04+), macOS (10.14+), Windows 10+
- **RAM**: 4 GB minimum, 8 GB recommended
- **Storage**: 20 GB free space for blockchain data
- **CPU**: Dual-core processor, quad-core recommended
- **Network**: Stable internet connection

### Recommended Requirements
- **RAM**: 16 GB or more
- **Storage**: SSD with 100+ GB free space
- **CPU**: 8+ cores for efficient mining
- **Network**: High-speed broadband connection

## Prerequisites

### Python Installation
Qbitcoin requires Python 3.5 or higher. Python 3.8+ is recommended.

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git
```

#### macOS
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python git
```

#### Windows
1. Download Python from [python.org](https://python.org)
2. Install Git from [git-scm.com](https://git-scm.com)
3. Ensure Python and Git are added to PATH

## Installation Methods

### Method 1: Clone from GitHub (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/qbitcoin/qbitcoin.git
   cd qbitcoin
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv qbitcoin-env
   source qbitcoin-env/bin/activate  # On Windows: qbitcoin-env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**
   ```bash
   python start_qbitcoin.py --help
   ```

### Method 2: Download Release Archive

1. **Download latest release**
   - Visit [GitHub Releases](https://github.com/qbitcoin/qbitcoin/releases)
   - Download the latest source code archive
   - Extract to your desired directory

2. **Follow steps 2-4 from Method 1**

## Post-Installation Setup

### 1. Configuration
Create your configuration directory:
```bash
mkdir -p ~/.qbitcoin
```

### 2. Generate Wallet
```bash
python start_qbitcoin.py --create-wallet
```

### 3. Initial Sync
Start the node to begin blockchain synchronization:
```bash
python start_qbitcoin.py
```

## Verification

### Check Node Status
```bash
python start_qbitcoin.py --node-info
```

### Check Wallet
```bash
python start_qbitcoin.py --wallet-info
```

### Test CLI Commands
```bash
python start_qbitcoin.py --help
```

## Common Installation Issues

### Issue 1: Python Version Error
**Error**: "This application requires at least Python 3.5"
**Solution**: Upgrade Python to version 3.5 or higher

### Issue 2: Missing Dependencies
**Error**: "ModuleNotFoundError: No module named 'xyz'"
**Solution**: 
```bash
pip install -r requirements.txt
pip install -r test_requirements.txt
```

### Issue 3: Permission Errors (Linux/macOS)
**Error**: Permission denied when creating directories
**Solution**: 
```bash
sudo chown -R $USER:$USER ~/.qbitcoin
```

### Issue 4: Port Already in Use
**Error**: "Port 9000 already in use"
**Solution**: Change the port in configuration or kill the process using the port

### Issue 5: Firewall Issues
**Error**: Cannot connect to peers
**Solution**: Configure firewall to allow:
- Port 9000 (P2P network)
- Port 9001 (API/RPC)

## Docker Installation (Advanced)

### Using Docker Compose
1. **Create docker-compose.yml**
```yaml
version: '3.8'
services:
  qbitcoin:
    build: .
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - qbitcoin-data:/root/.qbitcoin
volumes:
  qbitcoin-data:
```

2. **Run with Docker Compose**
```bash
docker-compose up -d
```

### Manual Docker Build
```bash
docker build -t qbitcoin .
docker run -d -p 9000:9000 -p 9001:9001 -v qbitcoin-data:/root/.qbitcoin qbitcoin
```

## Development Installation

For developers who want to contribute:

### 1. Fork and Clone
```bash
git clone https://github.com/YOUR_USERNAME/qbitcoin.git
cd qbitcoin
git remote add upstream https://github.com/qbitcoin/qbitcoin.git
```

### 2. Install Development Dependencies
```bash
pip install -r requirements.txt
pip install -r test_requirements.txt
```

### 3. Install Pre-commit Hooks
```bash
pip install pre-commit
pre-commit install
```

### 4. Run Tests
```bash
python -m pytest tests/
```

## Updating Qbitcoin

### From Git Repository
```bash
cd qbitcoin
git pull origin main
pip install -r requirements.txt --upgrade
```

### Backup Before Update
```bash
# Backup wallet and configuration
cp -r ~/.qbitcoin ~/.qbitcoin.backup
```

## Uninstalling Qbitcoin

### Remove Application
```bash
rm -rf /path/to/qbitcoin
```

### Remove Data (Optional)
**⚠️ Warning**: This will delete your wallet and blockchain data
```bash
rm -rf ~/.qbitcoin
```

### Remove Virtual Environment
```bash
rm -rf qbitcoin-env
```

## Network Configuration

### Mainnet (Default)
Default configuration connects to mainnet automatically.

### Testnet
To connect to testnet:
```bash
python start_qbitcoin.py --network testnet
```

### Custom Network
Create network configuration in `~/.qbitcoin/config.yml`

## Security Considerations

1. **Backup Your Wallet**: Always backup your wallet files
2. **Secure Your Keys**: Store private keys securely
3. **Firewall**: Configure appropriate firewall rules
4. **Updates**: Keep Qbitcoin updated to the latest version
5. **Environment**: Use virtual environments for isolation

## Getting Help

- **Documentation**: [Full Documentation](./00-README.md)
- **Quick Start**: [Quick Start Guide](./03-Quick-Start.md)
- **Community**: [Discord Server](https://discord.gg/qbitcoin)
- **Issues**: [GitHub Issues](https://github.com/qbitcoin/qbitcoin/issues)
- **Support**: [Support Forum](https://forum.qbitcoin.org)

## Next Steps

After successful installation:
1. [Quick Start Guide](./03-Quick-Start.md) - Get up and running quickly
2. [Running a Node](./07-Running-Node.md) - Learn to operate your node
3. [Wallet Creation](./10-Wallet-Creation.md) - Create and manage wallets
4. [Mining Guide](./13-Mining-Basics.md) - Start mining Qbitcoin

---

**Note**: If you encounter any issues during installation, please check our [FAQ](./24-FAQ.md) or reach out to the community for help.
