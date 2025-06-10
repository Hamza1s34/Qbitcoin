# QBitcoin MultiSig Wallet Guide with Falcon-512

## What is a MultiSig Wallet?

A **MultiSig (Multi-Signature) wallet** is a type of cryptocurrency wallet that requires multiple digital signatures to authorize a transaction. In QBitcoin blockchain, these signatures use **Falcon-512** post-quantum cryptography.

### Key Concepts:

1. **Signatories**: The wallet addresses that can sign transactions
2. **Weights**: Each signatory has a weight (voting power)
3. **Threshold**: Minimum total weight required to authorize a transaction
4. **Proposals**: Spending requests that need approval from signatories

### Example Scenario:
- 3-of-5 MultiSig: 5 signatories, need 3 signatures to spend
- Weighted voting: Alice (40 weight), Bob (35 weight), Charlie (25 weight), threshold 60
- Any two signatures would meet the threshold (40+35=75 ≥ 60)

## MultiSig Transaction Types

### 1. MultiSigCreate
Creates a new multisig wallet address with specified signatories, weights, and threshold.

### 2. MultiSigSpend  
Proposes a transaction from the multisig wallet to transfer funds to other addresses.

### 3. MultiSigVote
Allows signatories to vote (approve/reject) on pending MultiSigSpend proposals.

## Practical Implementation Steps

### Step 1: Create Individual Falcon-512 Wallets

First, create individual wallets for each person who will be a signatory:

```bash
# Create wallet for Alice
python3 qbitcoin/cli.py wallet_gen --encrypt

# Create wallet for Bob  
python3 qbitcoin/cli.py wallet_gen --encrypt

# Create wallet for Charlie
python3 qbitcoin/cli.py wallet_gen --encrypt
```

### Step 2: Get Wallet Addresses

List addresses from each wallet:

```bash
python3 qbitcoin/cli.py wallet_ls
```

Note down the Q-addresses for each signatory.

### Step 3: Create MultiSig Wallet

Use the CLI to create a multisig wallet:

```bash
python3 qbitcoin/cli.py tx_multi_sig_create \
  --src "Q010300a1f9dc35..." \    # Alice's address (creator)
  --master "" \                    # Optional master address
  --threshold 60 \                 # Minimum weight needed
  --fee 0.001                      # Fee in Qbitcoin
```

When prompted, enter signatory addresses and weights:
- Address of Signatory: Q010300a1f9dc35...  (Alice)
- Weight: 40
- Address of Signatory: Q010300b2e8f46...  (Bob)  
- Weight: 35
- Address of Signatory: Q010300c3d7a57...  (Charlie)
- Weight: 25
- Address of Signatory: [Enter] (empty to finish)

This creates the multisig address: `Q110000abc123...`

### Step 4: Fund the MultiSig Wallet

Send funds to the multisig address using regular transfer:

```bash
python3 qbitcoin/cli.py tx_transfer \
  --src "Q010300a1f9dc35..." \     # Your funded wallet
  --dsts "Q110000abc123..." \      # MultiSig address  
  --amounts "100" \                # Amount in Qbitcoin
  --fee 0.001
```

### Step 5: Propose a MultiSig Spend

Any signatory can propose spending from the multisig wallet:

```bash
python3 qbitcoin/cli.py tx_multi_sig_spend \
  --src "Q010300a1f9dc35..." \      # Alice proposes
  --multi_sig_address "Q110000abc123..." \
  --dsts "Q010300d4e9f68..." \      # Destination address
  --amounts "50" \                  # Amount to send
  --expiry_block_number 1000000 \   # Expires at this block
  --fee 0.001
```

This creates a proposal with hash: `abc123def456...`

### Step 6: Vote on the Proposal

Other signatories vote using MultiSigVote transactions. Since this isn't directly available in CLI, you need to create them programmatically or use the demo script.

**Example using our demo script:**

```bash
python3 multisig_falcon_guide.py
```

## Security Considerations

### 1. Key Management
- Each signatory must securely store their Falcon-512 private keys
- Use encrypted wallets with strong passwords
- Consider hardware wallet integration for high-value multisigs

### 2. Threshold Selection
- **2-of-3**: Good for small teams, any 2 can spend
- **3-of-5**: Better for larger groups, more resilient to key loss
- **Weighted**: Allows different levels of authority (CEO has more weight)

### 3. Expiry Blocks
- Set reasonable expiry times for proposals
- Expired proposals cannot be executed
- Consider network block time when setting expiry

### 4. Emergency Procedures
- Plan for lost keys or unavailable signatories
- Consider time-locked recovery mechanisms
- Document the multisig setup and access procedures

## Common Use Cases

### 1. Corporate Treasury
```
CEO: 40 weight, CFO: 35 weight, CTO: 25 weight
Threshold: 60 (any 2 executives can authorize)
```

### 2. Joint Accounts
```
Partner A: 50 weight, Partner B: 50 weight  
Threshold: 100 (both must agree)
```

### 3. DAO Governance
```
5 board members: 20 weight each
Threshold: 60 (need 3 of 5 members)
```

### 4. Escrow Services
```
Buyer: 30 weight, Seller: 30 weight, Escrow: 40 weight
Threshold: 70 (buyer+seller OR escrow+either party)
```

## Advanced Features

### 1. Nested MultiSig
- MultiSig addresses can be signatories of other MultiSig wallets
- Creates complex governance structures
- Example: Department multisigs feeding into company multisig

### 2. Time-locked Proposals
- Proposals have expiry blocks for automatic rejection
- Prevents old proposals from being executed unexpectedly
- Signatories must vote within the time window

### 3. Vote Revocation
- Signatories can change their vote using `unvote=true`
- Allows flexibility during long voting periods
- Final execution happens when threshold is met

## Troubleshooting

### Common Issues:

1. **"Insufficient weight"**: Total approved weight < threshold
   - Solution: Get more signatories to vote

2. **"Proposal expired"**: Current block > expiry_block_number
   - Solution: Create a new proposal with later expiry

3. **"Address not in signatories"**: Voter is not authorized
   - Solution: Only signatories can vote on proposals

4. **"Insufficient funds"**: MultiSig wallet doesn't have enough balance
   - Solution: Fund the multisig address first

### Debugging Steps:

1. Check multisig address balance:
```bash
python3 qbitcoin/cli.py balance Q110000abc123...
```

2. Verify signatory addresses and weights
3. Ensure proposal hasn't expired
4. Confirm all votes were properly submitted

## Example Script Walkthrough

The provided script (`multisig_falcon_guide.py`) demonstrates:

1. **Wallet Creation**: Creates 4 Falcon-512 wallets (3 signatories + 1 destination)
2. **MultiSig Setup**: Creates a 3-signatory wallet with weights [40, 35, 25] and threshold 60
3. **Spend Proposal**: Alice proposes sending 10 Qbitcoin to destination
4. **Voting Process**: Bob and Charlie vote to approve
5. **Execution**: Transaction would execute once threshold is met

Run the script to see the complete workflow:

```bash
python3 multisig_falcon_guide.py
```

This generates all the transaction blobs that can be submitted to a running QBitcoin node using the `tx_push` command.

## Integration with QBitcoin Node

To use multisig wallets with a live QBitcoin network:

1. **Start QBitcoin node**: Run your QBitcoin node with proper configuration
2. **Submit transactions**: Use `qbitcoin/cli.py tx_push --txblob <hex>` 
3. **Monitor status**: Check transaction confirmations and wallet balances
4. **Automate workflows**: Build applications that create and manage multisig proposals

The Falcon-512 signatures provide post-quantum security, making your multisig wallets resistant to quantum computer attacks while maintaining the collaborative spending features of traditional multisig wallets.
