# Qbitcoin Installation Guide

## Quick Installation

### Option 1: Automatic Installation (Recommended)
```bash
# This will automatically detect your OS and install all dependencies
pip install qbitcoin

# If you want full quantum features (may require compilation)
pip install qbitcoin[quantum]
```

### Option 2: Manual Smart Installation
If the automatic installation doesn't work:

```bash
# Install basic version first
pip install qbitcoin --no-deps

# Run the smart installer
python -c "from qbitcoin.smart_installer import SmartInstaller; SmartInstaller().install()"
```

### Option 3: Force Auto-Installation
Set environment variable to automatically install dependencies:

```bash
# Linux/macOS
export QBITCOIN_AUTO_INSTALL=1
pip install qbitcoin

# Windows
set QBITCOIN_AUTO_INSTALL=1
pip install qbitcoin
```

## Platform-Specific Instructions

### 🐧 Linux (Ubuntu/Debian)
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y build-essential cmake pkg-config libssl-dev libffi-dev python3-dev git

# Install Qbitcoin
pip install qbitcoin
```

### 🐧 Linux (CentOS/RHEL/Fedora)
```bash
# Install system dependencies
sudo yum install -y gcc-c++ cmake pkgconfig openssl-devel libffi-devel python3-devel git
# OR for newer systems:
sudo dnf install -y gcc-c++ cmake pkgconfig openssl-devel libffi-devel python3-devel git

# Install Qbitcoin
pip install qbitcoin
```

### 🍎 macOS
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install cmake pkg-config openssl libffi git

# Install Qbitcoin
pip install qbitcoin
```

### 🪟 Windows
```bash
# Option 1: Use conda (recommended)
conda install -c conda-forge cmake git m2w64-gcc
pip install qbitcoin

# Option 2: Use chocolatey
choco install cmake git mingw
pip install qbitcoin

# Option 3: Install Visual Studio Build Tools manually
# Download from: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
pip install qbitcoin
```

## Troubleshooting

### Common Issues

**1. Build failures on quantum libraries:**
```bash
# Install without quantum features first
pip install qbitcoin --no-deps
pip install plyvel ntplib Twisted colorlog simplejson PyYAML grpcio-tools grpcio google-api-python-client google-auth httplib2 service_identity protobuf pyopenssl six click cryptography Flask json-rpc idna base58 mock daemonize pqcrypto
```

**2. Permission errors:**
```bash
# Use --user flag
pip install --user qbitcoin

# Or use virtual environment
python -m venv qbitcoin_env
source qbitcoin_env/bin/activate  # Linux/macOS
# qbitcoin_env\Scripts\activate  # Windows
pip install qbitcoin
```

**3. Compilation errors:**
```bash
# Update build tools
pip install --upgrade pip setuptools wheel

# Install with verbose output to see errors
pip install qbitcoin -v
```

**4. Missing system dependencies:**
```bash
# Run the dependency checker
python -c "from qbitcoin.smart_installer import SmartInstaller; SmartInstaller().install_system_dependencies()"
```

## Verification

Test your installation:

```python
# Test basic import
import qbitcoin
print(f"Qbitcoin version: {qbitcoin.__version__}")

# Test core functionality
from qbitcoin.core import node
print("✅ Qbitcoin core imported successfully!")

# Test quantum features (if installed)
try:
    from qbitcoin.crypto import falcon
    print("✅ Quantum-resistant features available!")
except ImportError:
    print("⚠️  Quantum features not available (install with: pip install qbitcoin[quantum])")
```

## Advanced Installation

### Development Installation
```bash
# Clone the repository
git clone https://github.com/Hamza1s34/Qbitcoin.git
cd Qbitcoin

# Install in development mode
pip install -e .[dev,quantum]
```

### Docker Installation
```bash
# Pull from Docker Hub (when available)
docker pull qbitcoin/qbitcoin:latest

# Or build locally
docker build -t qbitcoin .
docker run -p 8080:8080 qbitcoin
```

## Getting Help

If you encounter issues:

1. **Check the logs:** Look for error messages during installation
2. **Update your system:** Ensure you have the latest package managers
3. **Use virtual environments:** Avoid conflicts with system packages
4. **Report issues:** Open an issue on GitHub with your OS, Python version, and error message

## Environment Variables

- `QBITCOIN_AUTO_INSTALL=1`: Automatically install dependencies without prompting
- `QBITCOIN_DATA_DIR`: Set custom data directory
- `QBITCOIN_LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)

## Next Steps

After installation, check out:
- [Quick Start Guide](docs/03-Quick-Start.md)
- [Running a Node](docs/07-Running-Node.md)
- [Wallet Creation](docs/10-Wallet-Creation.md)
