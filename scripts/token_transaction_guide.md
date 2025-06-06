# QRL Token Transaction System - Complete Guide

## Overview

The QRL blockchain implements a comprehensive token system that allows users to create and transfer custom tokens. There are two main types of token transactions:

1. **TokenTransaction** - Creates a new token type
2. **TransferTokenTransaction** - Transfers existing tokens between addresses

## Token Transaction Types

### 1. TokenTransaction (Token Creation)

This transaction type is used to create new tokens on the QRL blockchain.

**Key Properties:**
- **Symbol**: Unique token identifier (max length based on config)
- **Name**: Human-readable token name (max length based on config)
- **Owner**: Address that owns the token (can be different from creator)
- **Decimals**: Number of decimal places (0-19)
- **Initial Balances**: List of addresses and their initial token amounts
- **Fee**: Transaction fee in Quanta (QRL's base currency)

**Example Structure:**
```python
token_tx = TokenTransaction.create(
    symbol=b'MYTOKEN',
    name=b'My Custom Token',
    owner=owner_address,
    decimals=2,
    initial_balances=[
        AddressAmount(address=address1, amount=1000000),  # 10000.00 tokens
        AddressAmount(address=address2, amount=500000)    # 5000.00 tokens
    ],
    fee=1000000,  # 1 Quanta fee
    xmss_pk=public_key,
    master_addr=master_address  # Optional
)
```

### 2. TransferTokenTransaction (Token Transfer)

This transaction type is used to transfer existing tokens between addresses.

**Key Properties:**
- **Token TxHash**: Hash of the original TokenTransaction that created the token
- **Addresses To**: List of recipient addresses
- **Amounts**: List of amounts to transfer (must match addresses)
- **Fee**: Transaction fee in Quanta
- **Source**: The address sending the tokens (derived from signature)

**Example Structure:**
```python
transfer_tx = TransferTokenTransaction.create(
    token_txhash=original_token_txhash,
    addrs_to=[recipient_address1, recipient_address2],
    amounts=[100000, 200000],  # Transfer amounts
    fee=1000000,  # 1 Quanta fee
    xmss_pk=public_key,
    master_addr=master_address  # Optional
)
```

## Token System Architecture

### Token Identification
- Each token is uniquely identified by the transaction hash of its creation transaction
- This hash serves as the token ID throughout the system
- Token metadata (symbol, name, decimals) is stored with this hash

### Token Storage
- Token balances are stored in a key-value structure: `(address, token_txhash) -> TokenBalance`
- TokenBalance contains: balance, decimals, tx_hash, delete flag
- The system uses pagination for efficient token queries

### Validation Rules

#### TokenTransaction Validation:
1. Symbol and name cannot be empty
2. Must have at least one initial balance
3. Decimals cannot exceed 19
4. All initial amounts must be positive
5. Sender must have sufficient QRL for fee
6. Symbol/name length must not exceed configured limits

#### TransferTokenTransaction Validation:
1. Sender must own the tokens being transferred
2. Sufficient token balance required
3. Amounts cannot be zero
4. Number of addresses must match number of amounts
5. Sender must have sufficient QRL for fee
6. Cannot exceed multi-output transaction limits

## CLI Commands

### Creating a Token (`tx_token`)

```bash
qrl tx_token
```

This command will prompt for:
- **src**: Source QRL address (token creator)
- **master**: Master address (optional, for slave transactions)
- **symbol**: Token symbol (e.g., "MYTOKEN")
- **name**: Token name (e.g., "My Custom Token")
- **owner**: Owner address (can be different from creator)
- **decimals**: Number of decimal places (0-19)
- **fee**: Transaction fee in Quanta

Then it will ask for initial balances:
- Address and amount pairs
- Enter empty address to finish

### Transferring Tokens (`tx_transfertoken`)

```bash
qrl tx_transfertoken
```

This command will prompt for:
- **src**: Source QRL address (token sender)
- **master**: Master address (optional)
- **token_txhash**: Hash of the token creation transaction
- **dsts**: Comma-separated list of destination addresses
- **amounts**: Comma-separated list of amounts to transfer
- **decimals**: Token decimal places (for display purposes)
- **fee**: Transaction fee in Quanta

## Practical Examples

Let me create practical scripts to demonstrate token creation and transfer:
