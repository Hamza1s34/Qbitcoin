![QBitcoin Logo](https://www.qbitcoin.live/qbitcoin_logo)
# QBitcoin
[![PyPI](https://img.shields.io/pypi/v/qbitcoin.svg)](https://pypi.org/project/qbitcoin/)
[![License](https://img.shields.io/github/license/Hamza1s34/Qbitcoin)](LICENSE)
[![Website](https://img.shields.io/badge/website-qbitcoin.live-blue)](https://qbitcoin.live/)
[![Whitepaper](https://img.shields.io/badge/whitepaper-PDF-green)](https://qbitcoin.live/whitepaper)
[![For Sale](https://img.shields.io/badge/status-For%20Sale%20%2412%2C000-red)](mailto:qbitcoin@qbitcoin.live)

A professional-grade, quantum-resistant blockchain built from scratch in Python using Falcon-512. QBitcoin secures digital assets in the post-quantum era, featuring a robust wallet, transaction system, mining capabilities, and a modern web-based GUI.

---

> ## 🔴 This Project is For Sale — $12,000 USD
>
> QBitcoin is available for acquisition as a complete, turnkey blockchain project.
>
> **What's included:**
> - Full blockchain node source code (Python)
> - Web wallet + Desktop wallet + Mobile wallet source code
> - Block explorer source code
> - Live website + domain (qbitcoin.live) + email
> - PyPI package + brand assets + logo
> - 1,500,000 QBC coins (founder allocation)
> - All social media accounts
> - 30 days post-sale technical support
>
> **Why buy:**
> - 8+ months stable mainnet — zero chain halts
> - Live on Exbitron Exchange + rPlant mining pool
> - ~3M QBC in active circulation
> - One of the only deployed Falcon-512 blockchains in existence
> - Previous private sale completed at $5,000 — current package includes significantly more
>
> **Contact:** qbitcoin@qbitcoin.live
> **Payment:** USDT / BTC / ETH
> **Escrow:** Available for buyer protection
>
> [📧 Email to inquire](mailto:qbitcoin@qbitcoin.live) | [🌐 Live Site](https://www.qbitcoin.live/) | [🌍 Explorer](https://explorer.qbitcoin.live/)

---

## Features

- **Quantum-resistant cryptography** using Falcon-512 signatures (NIST PQC standard)
- **Proof-of-Work consensus mechanism** with RandomX algorithm
- **Multi-signature support**
- **Token transactions**
- **Web-based GUI interface**
- **gRPC API services**
- **Comprehensive testing suite**

---

## Project Structure

```
qbitcoin/        # Core blockchain implementation
  ├─ core/         # Blockchain core components (blocks, transactions, miners)
  ├─ crypto/       # Cryptographic functions and quantum-resistant algorithms
  ├─ daemon/       # Wallet daemon services
  ├─ services/     # Network and API services
  ├─ generated/    # Protocol buffer generated files
gui/            # Web-based graphical user interface
scripts/        # Utility scripts for various operations
tests/          # Comprehensive test suite
```

---

## Ecosystem

| Resource | Link |
|----------|------|
| 🌐 Website | https://www.qbitcoin.live/ |
| 🌍 Explorer | https://explorer.qbitcoin.live/ |
| 💳 Web Wallet | https://wallet.qbitcoin.live/ |
| 📚 Documentation | https://qbitcoin.live/documentation |
| 📗 Medium | https://qbitcoinm.medium.com/ |
| ✈️ Telegram | https://t.me/Qbitcoin512 |
| 🐦 X / Twitter | http://x.com/QbitcoinX |
| 🖥️ Desktop Wallet | https://github.com/Hamza1s34/Qdesktop_wallet |
| 📱 Mobile Wallet | https://github.com/Hamza1s34/qbitcoin-mwallet |

---

## Installation

### Install via PyPI
```bash
pip install qbitcoin
```

Install build dependencies:
```bash
sudo apt install -y build-essential cmake swig python3-dev libssl-dev libboost-all-dev libuv1-dev
```

Run the smart installer:
```bash
python3 -m qbitcoin.smart_installer
```

Start the node:
```bash
qbitcoin
```

For mining:
```bash
qbitcoin --miningAddress 
```

### Manual Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/Hamza1s34/Qbitcoin.git
    cd Qbitcoin
    ```

2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Run the node:
    ```bash
    python start_qbitcoin.py
    ```

---

## Usage

### CLI Mode
```bash
python -m qbitcoin.cli
```

### Utility Scripts
Handy scripts are available in the `scripts/` directory for:
- Creating transactions
- Token management
- Multi-signature operations
- Address debugging

---

## Testing

```bash
pytest tests/
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

---

## License

[![License](https://img.shields.io/github/license/Hamza1s34/Qbitcoin)](LICENSE)

This project is open source. Please see the [LICENSE](LICENSE) file for details.
