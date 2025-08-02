![QBitcoin Logo](https://q-bit.live/qbitcoin_logo)

# QBitcoin

[![PyPI](https://img.shields.io/pypi/v/qbitcoin.svg)](https://pypi.org/project/qbitcoin/)
[![License](https://img.shields.io/github/license/Hamza1s34/Qbitcoin)](LICENSE)
[![Website](https://img.shields.io/badge/website-qbitcoin.live-blue)](https://qbitcoin.live/)
[![Whitepaper](https://img.shields.io/badge/whitepaper-PDF-green)](https://qbitcoin.live/whitepaper)

A professional-grade, quantum-resistant blockchain built from scratch in Python using Falcon-512. QBitcoin secures digital assets in the post-quantum era, featuring a robust wallet, transaction system, mining capabilities, and a modern web-based GUI.

---

## Features

- **Quantum-resistant cryptography** using Falcon signatures
- **Proof-of-Work consensus mechanism**
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
qbitcoin --miningAddress <your qbitcoin address>
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

Use the command-line interface:

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

Run the test suite to ensure stability and correctness:

```bash
pytest tests/
```

---

## Contributing

We welcome contributions from the community!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

---

## License

[![License](https://img.shields.io/github/license/Hamza1s34/Qbitcoin)](LICENSE)

This project is open source. Please see the [LICENSE](LICENSE) file for details.
