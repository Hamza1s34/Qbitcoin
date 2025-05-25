# QBITCOIN

<div align="center">
  <img src="https://via.qbit.live/300x150?text=QBITCOIN" alt="QBITCOIN Logo" width="300">
  <br>
  <strong>A Quantum-Resistant Blockchain for the Post-Quantum Era</strong>
</div>

## Overview

QBITCOIN is a quantum-resistant blockchain built from scratch using the Falcon-512 post-quantum signature algorithm. In an era where quantum computing threatens traditional cryptographic systems, QBITCOIN provides a secure platform for digital assets with custom consensus, wallet, and transaction systems - all implemented in Python.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🔒 Quantum Resistance

QBITCOIN uses the Falcon-512 signature scheme, a finalist in the NIST post-quantum cryptography standardization process. This provides:

- **Quantum Resistance**: Protection against attacks from both classical and quantum computers
- **Compact Signatures**: More efficient than many other post-quantum schemes
- **Fast Verification**: Maintains high transaction throughput despite quantum security

## 🛠️ Technical Architecture

### Core Components

- **Blockchain Structure**: Implements a chain of cryptographically linked blocks
- **Consensus Mechanism**: Custom-built consensus to ensure network agreement
- **Transaction Model**: UTXO-based system similar to Bitcoin but with quantum-resistant signatures
- **P2P Network**: Decentralized node discovery and communication
- **Storage Layer**: Efficient blockchain data persistence and retrieval

### Directory Structure

```
QBITCOIN/
├── core/                # Core blockchain implementation
│   ├── block.py         # Block structure and validation
│   ├── blockchain.py    # Chain management and consensus
│   ├── genesis.yaml     # Genesis block configuration
│   ├── consensus/       # Consensus mechanism implementation
│   ├── network/         # P2P networking protocols
│   ├── node/            # Full node implementation
│   └── storage/         # Blockchain data storage
├── crypto/              # Cryptographic primitives
│   └── falcon.py        # Falcon-512 integration
├── scripts/             # Utility scripts
├── tests/               # Test suite
└── utils/               # Helper utilities
```

## 🚀 Getting Started

### Prerequisites

- Python 3.9+ 
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Hamza1s34/Qbitcoin.git
   cd Qbitcoin
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running a Node

To start a QBITCOIN node:

```bash
python  core.node.node_cli.py
```

Additional configuration options:
- `--bootstrap <ip:port>`: Connect to a specific bootstrap node
- `--wallet <wallet_path>`: Specify a wallet file
- `--mining`: Enable mining
- `--debug`: Enable debug logging

### Creating a Wallet

```bash
python scripts/create_wallets.py 
```
by default this will create 2 wallets in data/wallets 
## 📊 Features

- **Quantum-resistant signatures**: Future-proof security
- **Decentralized consensus**: No central authority
- **Web wallet**: User-friendly interface (in progress)
- **API client**: For easy integration with other services

## 🔍 Technical Details

### Block Structure

Each block contains:
- Header (block hash, previous hash, timestamp, nonce, merkle root)
- Transactions list
- Quantum-resistant signatures

### Consensus Algorithm

QBITCOIN uses a Proof-of-Work consensus with quantum-resistant features:
- Block time: 1 minutes (average)
- Difficulty adjustment: Every 2016 blocks
- Mining reward: Decreases by half every 210,000 blocks

### Address Format

QBITCOIN addresses use a Base58 encoding with:
- Version prefix byte
- Public key hash (derived from Falcon-512 public key)
- Checksum for error detection

## 🛣️ Roadmap

- [x] Core blockchain implementation
- [x] Quantum-resistant signatures
- [x] Basic wallet functionality
- [ ] Improved P2P networking
- [ ] Advanced mining optimizations
- [ ] Mobile wallet development
- [ ] Smart contract capabilities

## 🧪 Development Status

**⚠️ IMPORTANT**: QBITCOIN is currently in active development and should be considered experimental. It is not yet ready for production use or for storing valuable assets.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Contact

Project Link: [https://github.com/Hamza1s34/Qbitcoin](https://github.com/Hamza1s34/Qbitcoin)
Email: hamzibro69@gmail.com
whatsapp: +92 3195787106

