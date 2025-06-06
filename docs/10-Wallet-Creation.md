# Wallet Creation and Management

Complete guide to creating, managing, and securing Qbitcoin wallets.

## Understanding Qbitcoin Wallets

### What is a Wallet?

A Qbitcoin wallet is a software program that:
- **Stores private keys**: Securely holds your cryptographic keys
- **Manages addresses**: Creates and tracks your Qbitcoin addresses
- **Signs transactions**: Authorizes spending of your coins
- **Monitors balance**: Tracks incoming and outgoing transactions
- **Interfaces with blockchain**: Communicates with the Qbitcoin network

### Wallet Components

#### Private Keys (FALCON)
- **256-bit random numbers** that control coin ownership
- **Quantum-resistant**: Uses FALCON post-quantum cryptography
- **Must be kept secret**: Anyone with private key controls the coins
- **Cannot be recovered**: Loss means permanent loss of coins

#### Public Keys
- **Derived from private keys** using FALCON algorithm
- **Safe to share**: Used to receive coins
- **Address generation**: Hashed to create receiving addresses
- **Signature verification**: Used to verify transaction signatures

#### Addresses
- **Human-readable identifiers** for receiving coins
- **Start with "qbitcoin"**: Easy identification
- **Derived from public keys**: One-way hash function
- **Reusable**: Can receive multiple transactions

## Creating Your First Wallet

### Prerequisites

Ensure you have:
- [x] Qbitcoin installed and working
- [x] Secure computer environment
- [x] Paper and pen for backup
- [x] Safe storage location
- [x] Strong password in mind

### Method 1: Command Line (Recommended)

#### Basic Wallet Creation
```bash
# Create new wallet with default name
python start_qbitcoin.py --create-wallet

# Create named wallet
python start_qbitcoin.py --create-wallet --name "primary"

# Create wallet with custom location
python start_qbitcoin.py --create-wallet --path "/secure/location/"
```

#### Interactive Creation Process
```
🚀 Creating new Qbitcoin wallet...

Enter wallet name (default: wallet): primary
Enter strong password: ********
Confirm password: ********

⚠️  IMPORTANT: Write down your seed phrase!

Your 24-word recovery phrase:
abandon ability able about above absent absorb abstract...

📝 Write this down on paper and store safely!
❌ Never store electronically or share with anyone!
✅ You will need this to recover your wallet!

Wallet created successfully!
📍 Location: /home/user/.qbitcoin/wallets/primary/
```

### Method 2: GUI Application

#### Using Desktop GUI
```bash
# Launch GUI
python gui/qbitcoin_gui.py
```

1. **Click "Create New Wallet"**
2. **Enter wallet name and password**
3. **Write down seed phrase**
4. **Confirm seed phrase**
5. **Wallet ready for use**

### Method 3: Programmatic Creation

#### Python Script Example
```python
from qbitcoin.wallet import Wallet
from qbitcoin.crypto.falcon import FalconKeyPair

# Generate key pair
key_pair = FalconKeyPair.generate()

# Create wallet
wallet = Wallet.create(
    name="my_wallet",
    password="strong_password",
    key_pair=key_pair
)

# Save wallet
wallet.save("/path/to/wallet/")

print(f"Wallet created: {wallet.get_address()}")
```

## Wallet Types

### Standard Wallet
- **Single private key** controls all funds
- **Simple to use** for basic operations
- **Quick transactions** with immediate signing
- **Suitable for**: Daily use, small amounts

### MultiSig Wallet
- **Multiple private keys** required for transactions
- **Enhanced security** through key distribution
- **Requires coordination** between key holders
- **Suitable for**: Business, large amounts, shared funds

### HD (Hierarchical Deterministic) Wallet
- **Single seed** generates unlimited keys
- **Organized structure** for key management
- **Better privacy** with unique addresses
- **Suitable for**: Advanced users, privacy-focused

### Watch-Only Wallet
- **No private keys** stored locally
- **Monitor addresses** without spending ability
- **Safe for public computers** or monitoring
- **Suitable for**: Portfolio tracking, auditing

## Wallet Security

### Password Security

#### Strong Password Requirements
- **Minimum 12 characters** (20+ recommended)
- **Mixed case letters** (A-Z, a-z)
- **Numbers** (0-9)
- **Special characters** (!@#$%^&*)
- **No dictionary words** or personal information
- **Unique to this wallet** only

#### Password Examples
```
❌ Bad: password123
❌ Bad: myname1990
❌ Bad: qbitcoin2024

✅ Good: Tr7$mK9#pL2@nQ8
✅ Good: My!D0g&L0ves#C00kies99
✅ Good: Q8b!tc0in$W4ll3t@2024
```

### Seed Phrase Security

#### What is a Seed Phrase?
- **24 words** that can restore your entire wallet
- **BIP-39 standard** for word selection
- **Mathematically equivalent** to your private keys
- **Ultimate backup** of your wallet

#### Seed Phrase Storage
```
✅ DO:
- Write on paper with pen
- Store in fireproof safe
- Make multiple copies
- Store copies in different locations
- Use metal backup plates for durability

❌ DON'T:
- Store in digital files
- Take photos of seed phrase
- Store in cloud services
- Share with anyone
- Store near computer
```

#### Example Seed Phrase Storage
```
QBITCOIN WALLET BACKUP
Date: January 15, 2024
Wallet Name: Primary

Seed Phrase (24 words):
1. abandon    7. abstract   13. academy   19. action
2. ability    8. absurd     14. accent    20. actual
3. able       9. abuse      15. accept    21. addict
4. about     10. access     16. account   22. address
5. above     11. accident   17. accuse    23. adjust
6. absent    12. accord     18. achieve   24. admit

⚠️ KEEP THIS SAFE AND SECRET! ⚠️
```

## Wallet Management

### Viewing Wallet Information

#### Basic Information
```bash
# View wallet summary
python start_qbitcoin.py --wallet-info

# Check balance
python start_qbitcoin.py --balance

# List all wallets
python start_qbitcoin.py --list-wallets
```

#### Detailed Information
```bash
# Detailed wallet information
python start_qbitcoin.py --wallet-info --detailed

# Transaction history
python start_qbitcoin.py --transactions

# Address list with balances
python start_qbitcoin.py --list-addresses --with-balance
```

### Multiple Wallet Management

#### Working with Named Wallets
```bash
# Create multiple wallets
python start_qbitcoin.py --create-wallet --name "daily"
python start_qbitcoin.py --create-wallet --name "savings"
python start_qbitcoin.py --create-wallet --name "business"

# Use specific wallet
python start_qbitcoin.py --wallet "savings" --balance
python start_qbitcoin.py --wallet "business" --new-address

# Switch default wallet
python start_qbitcoin.py --set-default-wallet "daily"
```

#### Wallet Directory Structure
```
~/.qbitcoin/wallets/
├── daily/
│   ├── wallet.dat          # Encrypted wallet file
│   ├── addresses.json      # Address book
│   └── transactions.db     # Transaction history
├── savings/
│   └── ...
└── business/
    └── ...
```

### Address Management

#### Generating New Addresses

```bash
# Generate single address
python start_qbitcoin.py --new-address

# Generate with label
python start_qbitcoin.py --new-address --label "Mining rewards"

# Generate multiple addresses
python start_qbitcoin.py --new-address --count 5

# Generate for specific purpose
python start_qbitcoin.py --new-address --label "Online store payments"
```

#### Address Types in Qbitcoin

##### Standard Addresses
```
Format: qbitcoin1[39 characters]
Example: qbitcoin1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
Purpose: Regular transactions
```

##### MultiSig Addresses
```
Format: qbitcoin3[39 characters]  
Example: qbitcoin3qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
Purpose: Multi-signature wallets
```

### Transaction Management

#### Viewing Transactions
```bash
# Recent transactions
python start_qbitcoin.py --transactions --limit 10

# Transactions by date range
python start_qbitcoin.py --transactions --from "2024-01-01" --to "2024-01-31"

# Specific address transactions
python start_qbitcoin.py --transactions --address qbitcoin1abc...

# Export to CSV
python start_qbitcoin.py --export-transactions --file transactions.csv
```

#### Transaction Details
```bash
# Get transaction details
python start_qbitcoin.py --transaction 0x1234abcd...

# Verify transaction
python start_qbitcoin.py --verify-transaction 0x1234abcd...

# Transaction status
python start_qbitcoin.py --tx-status 0x1234abcd...
```

## Backup and Recovery

### Creating Backups

#### Wallet File Backup
```bash
# Backup entire wallet
python start_qbitcoin.py --backup-wallet --dest /backup/location/

# Backup specific wallet
python start_qbitcoin.py --backup-wallet --name "savings" --dest /backup/

# Encrypted backup
python start_qbitcoin.py --backup-wallet --encrypt --password backup_password
```

#### Seed Phrase Backup
The seed phrase is your ultimate backup:
1. **Write it down** immediately after wallet creation
2. **Verify accuracy** by checking each word
3. **Store securely** in multiple safe locations
4. **Test recovery** on testnet before storing large amounts

### Wallet Recovery

#### From Seed Phrase
```bash
# Recover wallet from seed phrase
python start_qbitcoin.py --recover-wallet

# You'll be prompted:
Enter your 24-word seed phrase: abandon ability able...
Enter new wallet name: recovered_wallet
Enter new password: ********
Confirm password: ********

🎉 Wallet recovered successfully!
```

#### From Backup File
```bash
# Restore from backup file
python start_qbitcoin.py --restore-wallet --file /backup/wallet_backup.dat

# Restore encrypted backup
python start_qbitcoin.py --restore-wallet --file backup.dat --password backup_pass
```

#### Emergency Recovery
If you lose access to Qbitcoin software:
1. **Install Qbitcoin** on new computer
2. **Use seed phrase** to recover wallet
3. **Wait for sync** to see full balance
4. **Create new backup** immediately

## Security Best Practices

### Physical Security

#### Computer Security
- **Use dedicated computer** for large amounts
- **Keep OS updated** with security patches
- **Use antivirus software** and firewall
- **Avoid public WiFi** for wallet operations
- **Lock screen** when away from computer

#### Storage Security
- **Hardware wallets** for large amounts (when available)
- **Air-gapped computers** for cold storage
- **Physical safes** for seed phrase storage
- **Multiple locations** for backup distribution

### Operational Security

#### Transaction Security
```bash
# Always verify recipient address
python start_qbitcoin.py --validate-address qbitcoin1abc...

# Use small test transaction first
python start_qbitcoin.py --send qbitcoin1abc... 0.001

# Verify transaction before confirmation
python start_qbitcoin.py --preview-transaction --to qbitcoin1abc... --amount 1.0
```

#### Regular Security Practices
1. **Regular backups** of wallet files
2. **Test recovery process** periodically
3. **Update software** promptly
4. **Monitor transactions** regularly
5. **Use strong passwords** everywhere

### Privacy Considerations

#### Address Reuse
```bash
# Generate new address for each transaction
python start_qbitcoin.py --new-address --label "Payment #1"
python start_qbitcoin.py --new-address --label "Payment #2"

# Avoid reusing addresses
# ❌ Bad: Use same address repeatedly
# ✅ Good: New address for each transaction
```

#### Transaction Privacy
- **Use different addresses** for different purposes
- **Avoid linking addresses** through transactions
- **Consider coin mixing** (when available)
- **Use Tor network** for enhanced privacy

## Troubleshooting

### Common Issues

#### "Wallet not found"
```bash
# List available wallets
python start_qbitcoin.py --list-wallets

# Check wallet location
ls ~/.qbitcoin/wallets/

# Create new wallet if missing
python start_qbitcoin.py --create-wallet
```

#### "Incorrect password"
```bash
# Try different password variations
# Check caps lock status
# Consider password manager recovery

# If password is lost and you have seed phrase:
python start_qbitcoin.py --recover-wallet
```

#### "Wallet corruption"
```bash
# Restore from backup
python start_qbitcoin.py --restore-wallet --file backup.dat

# If no backup, use seed phrase
python start_qbitcoin.py --recover-wallet

# Check wallet integrity
python start_qbitcoin.py --verify-wallet
```

#### "Transaction not appearing"
```bash
# Check if transaction is confirmed
python start_qbitcoin.py --tx-status TX_HASH

# Refresh wallet
python start_qbitcoin.py --rescan-wallet

# Check network synchronization
python start_qbitcoin.py --sync-status
```

### Recovery Scenarios

#### Lost Password, Have Seed Phrase
1. **Start recovery process**
2. **Enter seed phrase** correctly
3. **Create new password**
4. **Wait for wallet sync**
5. **Create new backup**

#### Lost Seed Phrase, Have Password
1. **Access current wallet** with password
2. **Export private keys** immediately
3. **Create new wallet** with new seed phrase
4. **Transfer funds** to new wallet
5. **Secure new seed phrase** properly

#### Computer Crashed
1. **Install Qbitcoin** on new computer
2. **Recover from seed phrase** or backup file
3. **Wait for blockchain sync**
4. **Verify balance** matches expected
5. **Create fresh backup**

## Advanced Wallet Features

### Watch-Only Wallets

#### Creating Watch-Only Wallets
```bash
# Create watch-only wallet from address
python start_qbitcoin.py --create-watch-wallet --address qbitcoin1abc...

# Import multiple addresses
python start_qbitcoin.py --import-addresses addresses.txt --watch-only
```

#### Use Cases
- **Portfolio monitoring** without risk
- **Auditing** business wallets
- **Public computer** usage
- **Shared monitoring** of fund addresses

### Cold Storage Setup

#### Air-Gapped Wallet Creation
```bash
# On offline computer:
python start_qbitcoin.py --create-wallet --offline

# Generate addresses and save public keys
python start_qbitcoin.py --export-public-keys --file pubkeys.txt

# Transfer pubkeys.txt to online computer for monitoring
```

#### Offline Transaction Signing
```bash
# On online computer (watch-only):
python start_qbitcoin.py --create-unsigned-tx --to qbitcoin1xyz... --amount 1.0 --file unsigned.tx

# Transfer unsigned.tx to offline computer
# On offline computer:
python start_qbitcoin.py --sign-transaction --file unsigned.tx --output signed.tx

# Transfer signed.tx back to online computer
# On online computer:
python start_qbitcoin.py --broadcast-tx --file signed.tx
```

### Paper Wallets

#### Generating Paper Wallets
```bash
# Generate paper wallet
python start_qbitcoin.py --generate-paper-wallet --output paperwallet.html

# Print and store securely
# Use for long-term cold storage
```

#### Paper Wallet Security
- **Generate offline** on air-gapped computer
- **Print on secure printer** (not network-connected)
- **Store in fireproof safe**
- **Make multiple copies**
- **Test small amount** first

## Integration Examples

### Python Wallet Integration

#### Basic Wallet Operations
```python
from qbitcoin.wallet import Wallet

# Load existing wallet
wallet = Wallet.load("primary", password="your_password")

# Get balance
balance = wallet.get_balance()
print(f"Balance: {balance} QBC")

# Generate new address
address = wallet.get_new_address("Payment from customer")
print(f"New address: {address}")

# Send transaction
tx_hash = wallet.send(
    to_address="qbitcoin1recipient...",
    amount=1.5,
    fee=0.001
)
print(f"Transaction sent: {tx_hash}")
```

#### Advanced Operations
```python
# Export private key for specific address
private_key = wallet.export_private_key("qbitcoin1myaddress...")

# Import private key
wallet.import_private_key(private_key, "Imported key")

# Sign arbitrary message
signature = wallet.sign_message("Hello World", "qbitcoin1myaddress...")

# Verify message signature
is_valid = wallet.verify_message("Hello World", signature, "qbitcoin1myaddress...")
```

### Web Application Integration

#### Flask Example
```python
from flask import Flask, request, jsonify
from qbitcoin.wallet import Wallet

app = Flask(__name__)
wallet = Wallet.load("webapp_wallet", password="secure_password")

@app.route('/api/balance')
def get_balance():
    return jsonify({
        'balance': wallet.get_balance(),
        'addresses': len(wallet.get_addresses())
    })

@app.route('/api/address', methods=['POST'])
def new_address():
    label = request.json.get('label', '')
    address = wallet.get_new_address(label)
    return jsonify({'address': address})

@app.route('/api/send', methods=['POST'])
def send_coins():
    data = request.json
    tx_hash = wallet.send(
        to_address=data['to'],
        amount=data['amount'],
        fee=data.get('fee', 0.001)
    )
    return jsonify({'transaction': tx_hash})
```

## Best Practices Summary

### Daily Operations
1. **Use different addresses** for different transactions
2. **Verify addresses** before sending
3. **Keep software updated**
4. **Monitor transactions** regularly
5. **Backup regularly**

### Security Practices
1. **Strong passwords** for all wallets
2. **Secure seed phrase** storage
3. **Multiple backup locations**
4. **Test recovery process**
5. **Use cold storage** for large amounts

### Privacy Practices
1. **Avoid address reuse**
2. **Use descriptive labels**
3. **Keep transaction records**
4. **Consider network privacy**
5. **Regular wallet maintenance**

## Next Steps

After mastering wallet creation and management:

1. **[Transaction Guide](./11-Transaction-Guide.md)** - Learn to send and receive
2. **[MultiSig Wallets](./12-MultiSig-Wallets.md)** - Enhanced security
3. **[Mining Guide](./13-Mining-Basics.md)** - Earn rewards
4. **[Web Wallet](./16-Web-Wallet-Setup.md)** - Browser access
5. **[API Reference](./23-API-Reference.md)** - Development integration

---

**Remember**: Your wallet security is your responsibility. Always backup your seed phrase and keep it secure!
