# Transaction Guide

Complete guide to sending, receiving, and managing Qbitcoin transactions.

## Understanding Qbitcoin Transactions

### What is a Transaction?

A Qbitcoin transaction is a digitally signed transfer of value that:
- **Transfers ownership** of coins between addresses
- **Uses post-quantum cryptography** (FALCON signatures)
- **Is recorded permanently** on the blockchain
- **Requires network confirmation** to be final
- **Includes transaction fees** for miners

### Transaction Components

#### Inputs
- **Previous transaction outputs** being spent
- **FALCON signatures** proving ownership
- **Script unlocking conditions** (if applicable)

#### Outputs
- **Recipient addresses** and amounts
- **Script locking conditions** for future spending
- **Change output** (remaining funds back to sender)

#### Metadata
- **Transaction ID** (unique identifier)
- **Block height** (when confirmed)
- **Timestamp** (when created/confirmed)
- **Fee amount** (paid to miners)

### Transaction Lifecycle

```
1. Creation    → Transaction built and signed
2. Broadcasting → Sent to network peers  
3. Mempool     → Waiting for confirmation
4. Mining      → Included in a block
5. Confirmation → Added to blockchain
6. Finalization → Considered permanent (6+ confirmations)
```

## Sending Qbitcoin

### Prerequisites

Before sending transactions:
- [x] Wallet with sufficient balance
- [x] Recipient's valid Qbitcoin address
- [x] Network connection and sync
- [x] Understanding of transaction fees

### Basic Send Transaction

#### Command Line Method
```bash
# Basic send command
python start_qbitcoin.py --send RECIPIENT_ADDRESS AMOUNT

# Example: Send 1.5 QBC
python start_qbitcoin.py --send qbitcoin1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh 1.5

# Send with custom fee
python start_qbitcoin.py --send qbitcoin1qxy... 1.5 --fee 0.002

# Send from specific wallet
python start_qbitcoin.py --wallet "savings" --send qbitcoin1qxy... 1.5
```

#### Interactive Send Process
```
💰 Sending Qbitcoin Transaction

From wallet: primary
To address: qbitcoin1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
Amount: 1.5 QBC
Fee: 0.001 QBC
Total cost: 1.501 QBC

Current balance: 5.0 QBC
Remaining after: 3.499 QBC

❓ Confirm transaction? (y/N): y
🔐 Enter wallet password: ********

✅ Transaction created successfully!
Transaction ID: 0x1234567890abcdef...
Status: Broadcasting to network...

🎉 Transaction sent! Check status with:
python start_qbitcoin.py --tx-status 0x1234567890abcdef...
```

### Advanced Send Options

#### Send with Comments
```bash
# Add transaction comment
python start_qbitcoin.py --send qbitcoin1qxy... 1.5 \
    --comment "Payment for services" \
    --comment-to "John's design work"
```

#### Send to Multiple Recipients
```bash
# Multiple outputs in one transaction
python start_qbitcoin.py --send-many \
    qbitcoin1abc...=1.0 \
    qbitcoin1def...=0.5 \
    qbitcoin1ghi...=2.0
```

#### Send All Funds
```bash
# Send entire wallet balance (minus fee)
python start_qbitcoin.py --send-all qbitcoin1qxy...

# Send all from specific address
python start_qbitcoin.py --send-all qbitcoin1qxy... --from qbitcoin1myaddr...
```

### GUI Transaction Sending

#### Using Desktop Application
```bash
# Launch GUI
python gui/qbitcoin_gui.py
```

1. **Click "Send" tab**
2. **Enter recipient address**
3. **Enter amount to send**
4. **Set transaction fee**
5. **Add optional comment**
6. **Click "Send"**
7. **Enter wallet password**
8. **Confirm transaction details**

## Receiving Qbitcoin

### Generating Receiving Addresses

#### Create New Address
```bash
# Generate new receiving address
python start_qbitcoin.py --new-address

# Generate with descriptive label
python start_qbitcoin.py --new-address --label "Payment from Alice"

# Generate multiple addresses
python start_qbitcoin.py --new-address --count 5
```

#### Address Management
```bash
# List all addresses
python start_qbitcoin.py --list-addresses

# List with balances
python start_qbitcoin.py --list-addresses --with-balance

# List with labels
python start_qbitcoin.py --list-addresses --with-labels
```

### Sharing Your Address

#### Address Format
```
Qbitcoin addresses always start with "qbitcoin"
Example: qbitcoin1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh

✅ Always verify the full address
✅ Use copy/paste to avoid typos
✅ Generate new address for each payment
```

#### QR Code Generation
```bash
# Generate QR code for address
python start_qbitcoin.py --qr-code qbitcoin1qxy... --output qr.png

# QR code with amount
python start_qbitcoin.py --qr-code qbitcoin1qxy... --amount 1.5 --output qr.png
```

### Monitoring Incoming Payments

#### Check Balance
```bash
# Current balance
python start_qbitcoin.py --balance

# Balance for specific address
python start_qbitcoin.py --balance --address qbitcoin1qxy...

# Detailed balance breakdown
python start_qbitcoin.py --balance --detailed
```

#### Transaction Monitoring
```bash
# Recent transactions
python start_qbitcoin.py --transactions --limit 10

# Watch for incoming transactions
python start_qbitcoin.py --monitor-address qbitcoin1qxy...

# Notifications for new transactions
python start_qbitcoin.py --notify-on-payment qbitcoin1qxy...
```

## Transaction Fees

### Understanding Fees

#### Why Pay Fees?
- **Mining incentive**: Reward miners for including transactions
- **Network security**: Maintain blockchain security
- **Priority processing**: Higher fees get faster confirmation
- **Spam prevention**: Prevent network abuse

#### Fee Structure
```
Base fee: 0.001 QBC (minimum)
Fee rate: 0.0001 QBC per byte
Average transaction: ~690 bytes (due to FALCON signatures)
Typical fee: 0.069 QBC for standard transaction
```

### Fee Calculation

#### Automatic Fee Estimation
```bash
# Get recommended fee for transaction
python start_qbitcoin.py --estimate-fee qbitcoin1qxy... 1.5

# Fee estimation output
Recommended fees:
- Economy (30+ minutes): 0.001 QBC
- Standard (10-30 minutes): 0.002 QBC  
- Priority (1-10 minutes): 0.005 QBC
```

#### Manual Fee Setting
```bash
# Low fee (slower confirmation)
python start_qbitcoin.py --send qbitcoin1qxy... 1.5 --fee 0.001

# High fee (faster confirmation)  
python start_qbitcoin.py --send qbitcoin1qxy... 1.5 --fee 0.01

# Calculate fee based on size
python start_qbitcoin.py --send qbitcoin1qxy... 1.5 --fee-rate 0.0002
```

### Fee Optimization

#### Batch Transactions
```bash
# Send to multiple recipients (saves fees)
python start_qbitcoin.py --send-many \
    qbitcoin1abc...=1.0 \
    qbitcoin1def...=0.5 \
    qbitcoin1ghi...=2.0 \
    --fee 0.003
```

#### Timing Optimization
- **Off-peak hours**: Lower network congestion
- **Weekends**: Generally lower fees
- **Non-urgent**: Use economy fee rates
- **Monitor mempool**: Check network conditions

## Transaction Status and Confirmation

### Checking Transaction Status

#### Transaction Lookup
```bash
# Check transaction status
python start_qbitcoin.py --tx-status TX_HASH

# Detailed transaction information
python start_qbitcoin.py --transaction TX_HASH --detailed

# Verify transaction
python start_qbitcoin.py --verify-transaction TX_HASH
```

#### Status Output Example
```
📊 Transaction Status:
ID: 0x1234567890abcdef...
Status: Confirmed ✅
Block: 125,849
Confirmations: 12/6 required
Amount: 1.5 QBC
Fee: 0.002 QBC
From: qbitcoin1abc... (Your wallet)
To: qbitcoin1def...
Time: 2024-01-15 14:30:25 UTC
Age: 2 hours, 15 minutes
```

### Understanding Confirmations

#### Confirmation Levels
```
0 confirmations: Unconfirmed (in mempool)
1 confirmation: Included in latest block
3 confirmations: Reasonably safe
6 confirmations: Standard requirement
12+ confirmations: Very secure
```

#### Confirmation Timeline
```
Average block time: 10 minutes
1 confirmation: ~10 minutes
6 confirmations: ~60 minutes
12 confirmations: ~120 minutes
```

### Transaction States

#### Pending States
- **Creating**: Transaction being built
- **Signing**: Adding cryptographic signatures
- **Broadcasting**: Sending to network
- **Mempool**: Waiting for mining
- **Confirming**: Being added to blocks

#### Final States
- **Confirmed**: Successfully added to blockchain
- **Failed**: Transaction rejected or invalid
- **Dropped**: Removed from mempool (rare)

## Troubleshooting Transactions

### Common Issues

#### Transaction Not Confirming
```bash
# Check if transaction is in mempool
python start_qbitcoin.py --mempool-status TX_HASH

# Check fee adequacy
python start_qbitcoin.py --analyze-fee TX_HASH

# Replace with higher fee (if supported)
python start_qbitcoin.py --replace-by-fee TX_HASH --new-fee 0.005
```

#### Insufficient Balance Error
```bash
# Check available balance
python start_qbitcoin.py --balance

# Check unconfirmed balance
python start_qbitcoin.py --balance --include-unconfirmed

# List unspent outputs
python start_qbitcoin.py --list-unspent
```

#### Invalid Address Error
```bash
# Validate recipient address
python start_qbitcoin.py --validate-address qbitcoin1qxy...

# Check address format
# Ensure address starts with "qbitcoin"
# Verify full address length and characters
```

#### Network Issues
```bash
# Check network connectivity
python start_qbitcoin.py --network-info

# Check peer connections
python start_qbitcoin.py --peers

# Rebroadcast transaction
python start_qbitcoin.py --rebroadcast TX_HASH
```

### Recovery Procedures

#### Stuck Transaction
1. **Wait longer**: Sometimes just needs patience
2. **Check fee**: May be too low for current network
3. **Rebroadcast**: Send transaction again
4. **Replace by fee**: Increase fee if supported
5. **Contact support**: If all else fails

#### Lost Transaction
```bash
# Search by various criteria
python start_qbitcoin.py --find-transaction --address qbitcoin1qxy...
python start_qbitcoin.py --find-transaction --amount 1.5
python start_qbitcoin.py --find-transaction --date "2024-01-15"

# Rescan wallet
python start_qbitcoin.py --rescan-wallet
```

## Advanced Transaction Features

### Raw Transactions

#### Creating Raw Transactions
```bash
# Create unsigned transaction
python start_qbitcoin.py --create-raw-tx \
    --to qbitcoin1qxy... \
    --amount 1.5 \
    --fee 0.002

# Sign raw transaction
python start_qbitcoin.py --sign-raw-tx RAW_TX_HEX

# Broadcast raw transaction
python start_qbitcoin.py --broadcast-raw-tx SIGNED_TX_HEX
```

#### Use Cases for Raw Transactions
- **Offline signing**: Cold storage wallets
- **Multi-signature**: Complex signing workflows
- **Custom scripts**: Advanced transaction types
- **Testing**: Development and debugging

### Scripting Transactions

#### Python Transaction Example
```python
from qbitcoin.transaction import Transaction
from qbitcoin.wallet import Wallet

# Load wallet
wallet = Wallet.load("primary", password="your_password")

# Create transaction
tx = Transaction()
tx.add_input(wallet.get_utxo())
tx.add_output("qbitcoin1recipient...", 1.5)
tx.add_output(wallet.get_change_address(), 2.49)  # Change
tx.set_fee(0.01)

# Sign transaction
signed_tx = wallet.sign_transaction(tx)

# Broadcast
tx_hash = wallet.broadcast_transaction(signed_tx)
print(f"Transaction sent: {tx_hash}")
```

#### Batch Processing
```python
# Process multiple transactions
recipients = [
    ("qbitcoin1abc...", 1.0),
    ("qbitcoin1def...", 2.0),
    ("qbitcoin1ghi...", 0.5)
]

for address, amount in recipients:
    tx_hash = wallet.send(address, amount, fee=0.002)
    print(f"Sent {amount} to {address}: {tx_hash}")
    time.sleep(1)  # Rate limiting
```

### Transaction Privacy

#### Privacy Best Practices
1. **Use new addresses** for each transaction
2. **Avoid address reuse** to prevent linking
3. **Consider coin mixing** when available
4. **Use Tor network** for transaction broadcasting
5. **Manage UTXO set** to avoid correlation

#### Address Management for Privacy
```bash
# Generate new address for each payment
python start_qbitcoin.py --new-address --label "Payment 1"
python start_qbitcoin.py --new-address --label "Payment 2"

# Avoid consolidating small UTXOs unnecessarily
python start_qbitcoin.py --list-unspent --min-amount 0.1
```

## API Integration

### REST API Transactions

#### Send Transaction via API
```bash
# Using curl
curl -X POST http://localhost:9001/api/v1/wallet/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "qbitcoin1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    "amount": 1.5,
    "fee": 0.002,
    "comment": "API payment"
  }'
```

#### Check Transaction Status
```bash
curl http://localhost:9001/api/v1/transaction/0x1234567890abcdef...
```

### Programming Integration

#### Node.js Example
```javascript
const axios = require('axios');

async function sendQbitcoin(to, amount, fee = 0.001) {
  try {
    const response = await axios.post('http://localhost:9001/api/v1/wallet/send', {
      to: to,
      amount: amount,
      fee: fee
    });
    
    console.log('Transaction sent:', response.data.txid);
    return response.data.txid;
  } catch (error) {
    console.error('Send failed:', error.response.data);
    throw error;
  }
}

// Usage
sendQbitcoin('qbitcoin1qxy...', 1.5, 0.002)
  .then(txid => console.log('Success:', txid))
  .catch(err => console.error('Error:', err));
```

## Security Best Practices

### Transaction Security

#### Before Sending
1. **Verify recipient address** completely
2. **Double-check amount** and fee
3. **Test with small amount** first
4. **Ensure sufficient balance** plus fees
5. **Use secure network connection**

#### During Sending
1. **Enter password securely**
2. **Review transaction details** carefully
3. **Confirm all details** before final send
4. **Note transaction ID** for records
5. **Wait for confirmation** before considering final

#### After Sending
1. **Monitor transaction status**
2. **Keep transaction records**
3. **Verify recipient confirmation**
4. **Update accounting/records**
5. **Backup wallet** if significant amounts

### Protecting Against Errors

#### Address Verification
```bash
# Always validate before sending
python start_qbitcoin.py --validate-address qbitcoin1qxy...

# Use address book for frequent recipients
python start_qbitcoin.py --add-contact "Alice" qbitcoin1qxy...
python start_qbitcoin.py --send-to-contact "Alice" 1.5
```

#### Test Transactions
```bash
# Send small test amount first
python start_qbitcoin.py --send qbitcoin1qxy... 0.001 --comment "Test transaction"

# Confirm receipt before sending full amount
python start_qbitcoin.py --send qbitcoin1qxy... 1.5 --comment "Main payment"
```

## Common Transaction Patterns

### Business Use Cases

#### Point of Sale
```python
def create_payment_request(amount, description):
    # Generate new address for this payment
    address = wallet.get_new_address(description)
    
    # Create payment request
    return {
        'address': address,
        'amount': amount,
        'description': description,
        'expires': time.time() + 3600  # 1 hour
    }

def check_payment(address, expected_amount):
    balance = wallet.get_address_balance(address)
    return balance >= expected_amount
```

#### Recurring Payments
```python
def setup_recurring_payment(recipient, amount, interval_days):
    schedule = {
        'recipient': recipient,
        'amount': amount,
        'interval': interval_days,
        'next_payment': time.time() + (interval_days * 86400)
    }
    return schedule

def process_recurring_payments():
    for payment in get_scheduled_payments():
        if time.time() >= payment['next_payment']:
            send_payment(payment['recipient'], payment['amount'])
            payment['next_payment'] += payment['interval'] * 86400
```

### Personal Use Cases

#### Savings Transfers
```bash
# Weekly savings transfer
python start_qbitcoin.py --send-from "checking" --send-to "savings" 50.0

# Dollar cost averaging
python start_qbitcoin.py --buy-schedule --amount 100 --frequency weekly
```

#### Bill Payments
```bash
# Set up bill payment
python start_qbitcoin.py --add-contact "Electric Company" qbitcoin1electric...
python start_qbitcoin.py --schedule-payment "Electric Company" 75.0 --monthly

# Pay bills
python start_qbitcoin.py --pay-bills --confirm
```

## Performance Optimization

### Transaction Batching

#### Combine Multiple Payments
```bash
# Instead of multiple transactions:
python start_qbitcoin.py --send qbitcoin1abc... 1.0
python start_qbitcoin.py --send qbitcoin1def... 2.0
python start_qbitcoin.py --send qbitcoin1ghi... 0.5

# Use single batched transaction:
python start_qbitcoin.py --send-many \
    qbitcoin1abc...=1.0 \
    qbitcoin1def...=2.0 \
    qbitcoin1ghi...=0.5
```

### UTXO Management

#### Optimize Transaction Inputs
```bash
# View current UTXOs
python start_qbitcoin.py --list-unspent

# Consolidate small UTXOs during low-fee periods
python start_qbitcoin.py --consolidate-utxos --threshold 0.1 --fee 0.001
```

## Monitoring and Analytics

### Transaction Analytics

#### Historical Analysis
```bash
# Transaction statistics
python start_qbitcoin.py --tx-stats --period month

# Fee analysis
python start_qbitcoin.py --fee-stats --period week

# Address usage patterns
python start_qbitcoin.py --address-stats
```

#### Export and Reporting
```bash
# Export transactions for accounting
python start_qbitcoin.py --export-transactions \
    --format csv \
    --from "2024-01-01" \
    --to "2024-01-31" \
    --file january_transactions.csv

# Generate tax report
python start_qbitcoin.py --tax-report --year 2024 --file tax_report.pdf
```

---

This comprehensive transaction guide covers all aspects of sending, receiving, and managing Qbitcoin transactions. For more specific use cases, see the related documentation:

- [Wallet Creation](./10-Wallet-Creation.md) - Managing wallets
- [MultiSig Wallets](./12-MultiSig-Wallets.md) - Enhanced security
- [Web Interface](./16-Web-Wallet-Setup.md) - Browser-based transactions
- [API Reference](./23-API-Reference.md) - Programming integration
