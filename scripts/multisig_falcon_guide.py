#!/usr/bin/env python3
"""
QBitcoin MultiSig Wallet Guide with Falcon-512
==================================================

This script demonstrates how to create and use MultiSig wallets in QBitcoin blockchain
with Falcon-512 post-quantum signatures.

MultiSig Wallet Concept:
- A multisig wallet requires multiple signatures to authorize transactions
- Each signatory has a weight, and transactions need to meet a threshold
- For example: 3 signers with weights [30, 40, 30] and threshold 60 means
  any two signatures are enough to authorize a transaction

Components:
1. MultiSigCreate: Creates a new multisig address
2. MultiSigSpend: Proposes a transaction from multisig address
3. MultiSigVote: Signatories vote to approve/reject the proposed transaction
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from decimal import Decimal
from binascii import hexlify
from pyqrllib.pyqrllib import bin2hstr, hstr2bin

# QBitcoin imports
from qbitcoin.core import config
from qbitcoin.core.misc.helper import parse_qaddress
from qbitcoin.core.MultiSigAddressState import MultiSigAddressState
from qbitcoin.core.txs.multisig.MultiSigCreate import MultiSigCreate
from qbitcoin.core.txs.multisig.MultiSigSpend import MultiSigSpend
from qbitcoin.core.txs.multisig.MultiSigVote import MultiSigVote
from qbitcoin.crypto.falcon import FalconSignature
from qbitcoin.tools.wallet_creator import WalletCreator


def create_falcon_wallet(name):
    """Create a new Falcon-512 wallet"""
    print(f"\n=== Creating Falcon-512 wallet: {name} ===")
    
    # Generate Falcon-512 key pair
    private_key, public_key = WalletCreator.create_keypair()
    
    # Generate QBitcoin address from public key
    address = WalletCreator.generate_address(public_key)
    
    wallet = {
        'name': name,
        'address': address,
        'address_bytes': bytes(hstr2bin(address[1:])),  # Remove 'Q' prefix
        'public_key_bytes': public_key,
        'private_key_bytes': private_key
    }
    
    print(f"Address: {address}")
    print(f"Public Key: {hexlify(public_key).decode()}")
    print(f"Private Key: {hexlify(private_key).decode()}")
    
    return wallet


def create_multisig_wallet(creator_wallet, signatories, weights, threshold, fee=0):
    """
    Create a MultiSig wallet
    
    Args:
        creator_wallet: The wallet creating the multisig (pays fees)
        signatories: List of signatory address bytes
        weights: List of weights for each signatory
        threshold: Minimum weight required to authorize transactions
        fee: Transaction fee in quark (smallest unit)
    """
    print(f"\n=== Creating MultiSig Wallet ===")
    print(f"Creator: {creator_wallet['name']} ({creator_wallet['address']})")
    print(f"Signatories: {len(signatories)}")
    print(f"Weights: {weights}")
    print(f"Threshold: {threshold}")
    print(f"Total Weight: {sum(weights)}")
    
    # Create MultiSigCreate transaction
    tx = MultiSigCreate.create(
        signatories=signatories,
        weights=weights,
        threshold=threshold,
        fee=fee,
        xmss_pk=creator_wallet['public_key_bytes']
    )
    
    # Sign transaction with Falcon-512
    tx_data = tx.get_data_bytes()
    signature = FalconSignature.sign_message(tx_data, creator_wallet['private_key_bytes'])
    tx._data.signature = signature
    
    # Generate the multisig address that will be created
    multisig_address = MultiSigAddressState.generate_multi_sig_address(tx.txhash)
    multisig_address_str = f"Q{bin2hstr(multisig_address)}"
    
    print(f"MultiSig Address: {multisig_address_str}")
    print(f"Transaction Hash: {bin2hstr(tx.txhash)}")
    print(f"Transaction Blob: {hexlify(tx.pbdata.SerializeToString()).decode()}")
    
    return {
        'transaction': tx,
        'multisig_address': multisig_address,
        'multisig_address_str': multisig_address_str,
        'signatories': signatories,
        'weights': weights,
        'threshold': threshold
    }


def create_multisig_spend(proposer_wallet, multisig_address, destinations, amounts, expiry_block, fee=0):
    """
    Create a MultiSig spend transaction proposal
    
    Args:
        proposer_wallet: Wallet proposing the transaction (must be a signatory)
        multisig_address: MultiSig address bytes
        destinations: List of destination address bytes
        amounts: List of amounts to send (in quark)
        expiry_block: Block number when this proposal expires
        fee: Transaction fee in quark
    """
    print(f"\n=== Creating MultiSig Spend Proposal ===")
    print(f"Proposer: {proposer_wallet['name']} ({proposer_wallet['address']})")
    print(f"MultiSig Address: Q{bin2hstr(multisig_address)}")
    print(f"Destinations: {[f'Q{bin2hstr(addr)}' for addr in destinations]}")
    print(f"Amounts: {amounts} quark")
    print(f"Expiry Block: {expiry_block}")
    
    # Create MultiSigSpend transaction
    tx = MultiSigSpend.create(
        multi_sig_address=multisig_address,
        addrs_to=destinations,
        amounts=amounts,
        expiry_block_number=expiry_block,
        fee=fee,
        xmss_pk=proposer_wallet['public_key_bytes']
    )
    
    # Sign transaction with Falcon-512
    tx_data = tx.get_data_bytes()
    signature = FalconSignature.sign_message(tx_data, proposer_wallet['private_key_bytes'])
    tx._data.signature = signature
    
    print(f"Spend Proposal Hash: {bin2hstr(tx.txhash)}")
    print(f"Transaction Blob: {hexlify(tx.pbdata.SerializeToString()).decode()}")
    
    return {
        'transaction': tx,
        'spend_hash': tx.txhash,
        'proposer': proposer_wallet['address']
    }


def create_multisig_vote(voter_wallet, spend_proposal_hash, vote_approve=True, fee=0):
    """
    Create a vote on a MultiSig spend proposal
    
    Args:
        voter_wallet: Wallet voting (must be a signatory)
        spend_proposal_hash: Hash of the MultiSigSpend proposal
        vote_approve: True to approve, False to reject/unvote
        fee: Transaction fee in quark
    """
    print(f"\n=== Creating MultiSig Vote ===")
    print(f"Voter: {voter_wallet['name']} ({voter_wallet['address']})")
    print(f"Proposal Hash: {bin2hstr(spend_proposal_hash)}")
    print(f"Vote: {'APPROVE' if vote_approve else 'REJECT/UNVOTE'}")
    
    # Create MultiSigVote transaction
    tx = MultiSigVote.create(
        shared_key=spend_proposal_hash,
        unvote=not vote_approve,  # unvote=False means approve
        fee=fee,
        xmss_pk=voter_wallet['public_key_bytes']
    )
    
    # Sign transaction with Falcon-512
    tx_data = tx.get_data_bytes()
    signature = FalconSignature.sign_message(tx_data, voter_wallet['private_key_bytes'])
    tx._data.signature = signature
    
    print(f"Vote Transaction Hash: {bin2hstr(tx.txhash)}")
    print(f"Transaction Blob: {hexlify(tx.pbdata.SerializeToString()).decode()}")
    
    return {
        'transaction': tx,
        'vote_hash': tx.txhash,
        'voter': voter_wallet['address'],
        'approved': vote_approve
    }


def qbitcoin_to_quark(qbitcoin_amount):
    """Convert Qbitcoin to quark (smallest unit)"""
    return int(Decimal(qbitcoin_amount) * Decimal(config.dev.quark_per_qbitcoin))


def quark_to_qbitcoin(quark_amount):
    """Convert quark to Qbitcoin"""
    return Decimal(quark_amount) / Decimal(config.dev.quark_per_qbitcoin)


def main():
    """Demonstrate complete MultiSig workflow"""
    print("QBitcoin MultiSig Wallet Demo with Falcon-512")
    print("=" * 50)
    
    # Step 1: Create three Falcon-512 wallets for signatories
    alice = create_falcon_wallet("Alice")
    bob = create_falcon_wallet("Bob")
    charlie = create_falcon_wallet("Charlie")
    
    # Step 2: Create a MultiSig wallet
    # Scenario: 3 signatories, Alice has weight 40, Bob has 35, Charlie has 25
    # Threshold is 60, so any two signatures are enough
    signatories = [alice['address_bytes'], bob['address_bytes'], charlie['address_bytes']]
    weights = [40, 35, 25]  # Total: 100
    threshold = 60  # Need at least 60 weight to authorize
    
    multisig_info = create_multisig_wallet(
        creator_wallet=alice,
        signatories=signatories,
        weights=weights,
        threshold=threshold,
        fee=qbitcoin_to_quark(0.001)  # 0.001 Qbitcoin fee
    )
    
    # Step 3: Create a destination wallet for the transfer
    destination = create_falcon_wallet("Destination")
    
    # Step 4: Create a MultiSig spend proposal
    # Alice proposes to send 10 Qbitcoin to the destination
    spend_info = create_multisig_spend(
        proposer_wallet=alice,
        multisig_address=multisig_info['multisig_address'],
        destinations=[destination['address_bytes']],
        amounts=[qbitcoin_to_quark(10)],  # 10 Qbitcoin
        expiry_block=1000000,  # Expires at block 1,000,000
        fee=qbitcoin_to_quark(0.001)
    )
    
    # Step 5: Bob votes to approve the proposal
    bob_vote = create_multisig_vote(
        voter_wallet=bob,
        spend_proposal_hash=spend_info['spend_hash'],
        vote_approve=True,
        fee=qbitcoin_to_quark(0.001)
    )
    
    # Step 6: Charlie also votes to approve
    charlie_vote = create_multisig_vote(
        voter_wallet=charlie,
        spend_proposal_hash=spend_info['spend_hash'],
        vote_approve=True,
        fee=qbitcoin_to_quark(0.001)
    )
    
    print("\n" + "=" * 60)
    print("MULTISIG WORKFLOW SUMMARY")
    print("=" * 60)
    print(f"1. Created MultiSig wallet with 3 signatories")
    print(f"   - Address: {multisig_info['multisig_address_str']}")
    print(f"   - Weights: Alice({weights[0]}), Bob({weights[1]}), Charlie({weights[2]})")
    print(f"   - Threshold: {threshold}")
    print(f"")
    print(f"2. Alice proposed spend of 10 Qbitcoin")
    print(f"   - Proposal Hash: {bin2hstr(spend_info['spend_hash'])}")
    print(f"   - Destination: {destination['address']}")
    print(f"")
    print(f"3. Voting Results:")
    print(f"   - Alice (proposer): Weight {weights[0]} - Implicit approval")
    print(f"   - Bob: Weight {weights[1]} - {'APPROVED' if bob_vote['approved'] else 'REJECTED'}")
    print(f"   - Charlie: Weight {weights[2]} - {'APPROVED' if charlie_vote['approved'] else 'REJECTED'}")
    print(f"")
    print(f"4. Total Weight: {weights[0] + weights[1] + weights[2]} >= {threshold} ✓")
    print(f"   Transaction would be EXECUTED when submitted to network")
    
    print("\n" + "=" * 60)
    print("CLI COMMANDS TO SUBMIT TO NETWORK")
    print("=" * 60)
    print("To submit these transactions to a running QBitcoin node:")
    print()
    print("1. Create MultiSig wallet:")
    print(f"   python3 qbitcoin/cli.py tx_push --txblob {hexlify(multisig_info['transaction'].pbdata.SerializeToString()).decode()}")
    print()
    print("2. Propose MultiSig spend:")
    print(f"   python3 qbitcoin/cli.py tx_push --txblob {hexlify(spend_info['transaction'].pbdata.SerializeToString()).decode()}")
    print()
    print("3. Submit Bob's vote:")
    print(f"   python3 qbitcoin/cli.py tx_push --txblob {hexlify(bob_vote['transaction'].pbdata.SerializeToString()).decode()}")
    print()
    print("4. Submit Charlie's vote:")
    print(f"   python3 qbitcoin/cli.py tx_push --txblob {hexlify(charlie_vote['transaction'].pbdata.SerializeToString()).decode()}")


if __name__ == "__main__":
    main()
