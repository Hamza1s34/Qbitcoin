# Qbitcoin

A Python-based cryptocurrency implementation with quantum-resistant features.

## Features

- Quantum-resistant cryptography using Falcon signatures
- Proof-of-Work consensus mechanism
- Multi-signature support
- Token transactions
- Web-based GUI interface
- gRPC API services
- Comprehensive testing suite

## Project Structure

- `qbitcoin/` - Core blockchain implementation
  - `core/` - Blockchain core components (blocks, transactions, miners)
  - `crypto/` - Cryptographic functions and quantum-resistant algorithms
  - `daemon/` - Wallet daemon services
  - `services/` - Network and API services
  - `generated/` - Protocol buffer generated files
- `gui/` - Web-based graphical user interface
- `scripts/` - Utility scripts for various operations
- `tests/` - Comprehensive test suite

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Hamza1s34/Qbitcoin.git
cd Qbitcoin
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python start_qbitcoin.py
```

## Usage

### GUI Mode
Launch the graphical interface:
```bash
python gui/qbitcoin_gui.py
```

### CLI Mode
Use the command-line interface:
```bash
python -m qbitcoin.cli
```

### Scripts
Various utility scripts are available in the `scripts/` directory for operations like:
- Creating transactions
- Token management
- Multi-signature operations
- Address debugging

## Testing

Run the test suite:
```bash
pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is open source. Please see the LICENSE file for details.
