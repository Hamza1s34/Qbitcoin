# coding=utf-8
from __future__ import print_function
import simplejson as json
import yaml
import sys
import os 
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from qbitcoin.generated import qbit_pb2
from qbitcoin.core import config
from qbitcoin.core.txs.TransferTransaction import TransferTransaction
from qbitcoin.core.Block import Block
from qbitcoin.crypto.falcon import FalconSignature
from qbitcoin.tools.wallet_creator import WalletCreator


def create_tx(addrs_to, amounts, signing_falcon, nonce):
    """Create a transaction using Falcon-512 signatures"""
    tx = TransferTransaction.create(addrs_to=addrs_to,
                                    amounts=amounts,
                                    message_data=None,
                                    fee=0,
                                    xmss_pk=signing_falcon['public_key_bytes'])
    
    # Sign the transaction using Falcon-512
    tx_data = tx.get_data_bytes()
    signature = FalconSignature.sign_message(tx_data, signing_falcon['private_key_bytes'])
    tx._data.signature = signature
    tx._data.nonce = nonce
    return tx


def get_migration_transactions(signing_falcon, filename):
    transactions = []

    with open(filename, 'r') as f:
        json_data = json.load(f)

    count = 1
    addrs_to = []
    amounts = []
    output_limit = config.dev.transaction_multi_output_limit

    for addr in json_data:
        try:
            # Remove Q prefix and convert hex to bytes
            if addr.startswith('Q'):
                addr_hex = addr[1:]
            else:
                addr_hex = addr
            addrs_to.append(bytes.fromhex(addr_hex))
        except:  # noqa
            print("Invalid Address ", addr)
            raise Exception
        amounts.append(json_data[addr])

        count += 1
        if count % output_limit == 0:
            transactions.append(create_tx(addrs_to, amounts, signing_falcon, count // output_limit))

            addrs_to = []
            amounts = []

    if addrs_to:
        transactions.append(create_tx(addrs_to, amounts, signing_falcon, (count // output_limit) + 1))

    return transactions


def main():
    exclude_migration_tx = False
    if len(sys.argv) > 2:
        print("Unexpected arguments")
        sys.exit(0)
    elif len(sys.argv) == 1:
        exclude_migration_tx = True

    # Generate a new Falcon-512 key pair for the genesis block (miner address)
    print("Generating Falcon-512 key pair for genesis miner address...")
    private_key_bytes, public_key_bytes = FalconSignature.generate_keypair()
    
    # Create address from public key
    address = WalletCreator.generate_address(public_key_bytes)
    address_bytes = bytes.fromhex(address[1:])  # Remove Q prefix and convert to bytes
    
    # Create signing falcon object
    signing_falcon = {
        'private_key_bytes': private_key_bytes,
        'public_key_bytes': public_key_bytes,
        'address': address,
        'address_bytes': address_bytes
    }
    
    print(f"Genesis miner address: {address}")
    print(f"Public key size: {len(public_key_bytes)} bytes")
    print(f"Private key size: {len(private_key_bytes)} bytes")    # No additional transactions - just the coinbase transaction that will be created by Block.create()
    transactions = []
    
    # Process migration transactions if provided (for compatibility)
    if not exclude_migration_tx:
        filename = sys.argv[1]
        transactions = get_migration_transactions(signing_falcon=signing_falcon, filename=filename)

    # Create genesis block - no special coinbase reward, just standard genesis
    print("Creating genesis block...")
    block = Block.create(dev_config=config.dev,
                         block_number=0,
                         prev_headerhash=config.user.genesis_prev_headerhash,
                         prev_timestamp=config.user.genesis_timestamp,
                         transactions=transactions,
                         miner_address=address_bytes,
                         seed_height=None,
                         seed_hash=None)

    # Set mining nonces
    block.set_nonces(config.dev, 0, 0)
    
    # Clear any existing genesis balances 
    del block._data.genesis_balance[:]

    # Add 20 million QRL (20,000,000 * 10^9 shor) as genesis balance to the miner address
    twenty_million_shor = 20000000 * int(config.dev.shor_per_quanta)
    block._data.genesis_balance.extend([qbit_pb2.GenesisBalance(address=address_bytes,
                                                               balance=twenty_million_shor)])

    # Recalculate the block hash with the updated genesis balances
    block.blockheader.generate_headerhash(config.dev)

    # Save the genesis block
    with open('genesis.yml', 'w') as f:
        yaml.dump(json.loads(block.to_json()), f)
    
    print(f"Genesis block created successfully!")
    print(f"Genesis file saved as: genesis.yml")
    print(f"Genesis block hash: {block.headerhash.hex()}")
    print(f"Genesis miner allocation: {twenty_million_shor} shor (20,000,000 QRL)")
    print(f"Remaining for mining rewards: 10,000,000 QRL")
    print(f"Initial block reward: 2.5 QRL per block")
    print(f"Halving every 2 years (1,051,200 blocks)")
    print(f"Total genesis allocation: 20,000,000 Qbit  to {address}")
    
    # Save the genesis keys for reference
    genesis_keys = {
        'address': address,
        'public_key_hex': public_key_bytes.hex(),
        'private_key_hex': private_key_bytes.hex(),
        'algorithm': 'falcon-512',
        'genesis_balance': f"{twenty_million_shor} shor",
        'genesis_balance_qrl': "20,000,000 QRL"
    }
    
    with open('genesis_keys.json', 'w') as f:
        json.dump(genesis_keys, f, indent=2)
    
    print(f"Genesis keys saved as: genesis_keys.json")


if __name__ == '__main__':
    main()
