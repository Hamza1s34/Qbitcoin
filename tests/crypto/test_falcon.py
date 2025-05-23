#!/usr/bin/env python3
"""
Test script for Qbitcoin's wallet creation, signing, and verification functionality.
Demonstrates the use of Falcon-512 post-quantum signatures.
"""

import os
import sys
import json

# Add the project root directory to the Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now import the modules using their correct paths
from utils.wallet_creator import create_new_wallet, hex_to_keys
from crypto.falcon import FalconSignature


def main():
    # Step 1: Create a new wallet
    print("===== CREATING NEW QBITCOIN WALLET =====")
    wallet = create_new_wallet(wallet_name="my_wallet")
    
    # Display wallet information
    print(f"Address: {wallet['address']}")
    print(f"Public Key Size: {wallet['public_key_size']} bytes")
    print(f"Private Key Size: {wallet['private_key_size']} bytes")
    print(f"Algorithm: {wallet['algorithm']}")
    print("\n")
    
    # Step 2: Create a message to sign
    message = "This is a test transaction from QBitcoin wallet using Falcon-512 post-quantum signatures!"
    print(f"Message to sign: \"{message}\"")
    
    # Step 3: Convert hex keys to bytes
    pub_key_bytes = bytes.fromhex(wallet['public_key'])
    priv_key_bytes = bytes.fromhex(wallet['private_key'])
    
    # Step 4: Sign the message using FalconSignature implementation
    print("\n===== SIGNING MESSAGE =====")
    signature = FalconSignature.sign_message(message, priv_key_bytes)
    print(f"Signature size: {len(signature)} bytes")
    print(f"Signature (hex): {signature.hex()[:64]}...{signature.hex()[-64:]}")
    
    # Step 5: Verify the signature
    print("\n===== VERIFYING SIGNATURE =====")
    is_valid = FalconSignature.verify_signature(message, signature, pub_key_bytes)
    print(f"Signature valid: {is_valid}")
    
    # Step 6: Create a tampered message to demonstrate verification failure
    print("\n===== VERIFYING WITH TAMPERED MESSAGE =====")
    tampered_message = message + " [TAMPERED]"
    is_valid_tampered = FalconSignature.verify_signature(tampered_message, signature, pub_key_bytes)
    print(f"Tampered message: \"{tampered_message}\"")
    print(f"Tampered signature valid: {is_valid_tampered}")
    
    # Step 7: Create a full signature object with metadata
    print("\n===== SIGNATURE OBJECT =====")
    sig_object = FalconSignature.create_signature_object(message, signature, pub_key_bytes)
    print(json.dumps(sig_object, indent=2))
    
    # Step 8: Save wallet to disk
    print("\n===== SAVING WALLET =====")
    create_new_wallet(wallet_name="my_wallet", save=True, password="secure_password")
    
    # Step 9: Algorithm details
    print("\n===== FALCON-512 ALGORITHM DETAILS =====")
    algo_details = FalconSignature.get_algorithm_details()
    print(f"Public Key Size (spec): {algo_details['public_key_size']} bytes")
    print(f"Secret Key Size (spec): {algo_details['secret_key_size']} bytes")
    print(f"Signature Size (spec): {algo_details['signature_size']} bytes")
    

if __name__ == "__main__":
    main()