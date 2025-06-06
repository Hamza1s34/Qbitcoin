#!/usr/bin/env python3
import base64
import os

# Function to properly encode addresses in the format QRL expects
def encode_qrl_address(name_or_identifier=None):
    # QRL addresses are 39 bytes in total
    # Format: prefix(1) + hash(32) + checksum(4) + nonce(2)
    
    # 1 byte prefix (0x01 for QRL)
    prefix = bytes([0x01])
    
    # 32 bytes hash - use os.urandom for random data if no name given
    if name_or_identifier:
        # Use the name as a seed, ensuring it's exactly 32 bytes
        seed = name_or_identifier.encode('utf-8')
        hash_bytes = seed.ljust(32, b'\x00')[:32]
    else:
        hash_bytes = os.urandom(32)
    
    # 4 byte checksum (all zeros for simplicity)
    checksum = bytes([0x00, 0x00, 0x00, 0x00])
    
    # 2 byte nonce (all zeros)
    nonce = bytes([0x00, 0x00])
    
    # Combine all parts
    address_bytes = prefix + hash_bytes + checksum + nonce
    
    # Convert to base64
    return base64.b64encode(address_bytes).decode('utf-8')

# Generate our addresses
addresses = {
    "ICO_Public": "ICOPublicAddr",
    "Marketing": "MarketingAddr",
    "Development": "DevFundAddr", 
    "Reserve": "ReserveFund",
    "Special": "SpecialAddr"
}

print("Encoded addresses for genesis.yml:")
print("=================================")
for name, identifier in addresses.items():
    encoded_address = encode_qrl_address(identifier)
    print(f"{name}: {encoded_address}")
    
# Also generate a completely random address
random_addr = encode_qrl_address()
print(f"Random address: {random_addr}")

# Print YAML examples for easy copy-paste
print("\nYAML entries for genesis.yml:")
print("===========================")
for name, identifier in addresses.items():
    encoded_address = encode_qrl_address(identifier)
    print(f"# {name} allocation")
    print(f"- {{address: {encoded_address}, balance: '5000000000000000'}}\n")
