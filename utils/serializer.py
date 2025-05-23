#!/usr/bin/env python3
"""
Serializer for Qbitcoin

This module provides functions to serialize and deserialize blockchain data structures
for efficient storage and network transmission.
"""

import json
import struct
import time
import base64
from typing import Dict, Any, List, Optional

# Import local modules
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logger import get_logger

# Initialize logger
logger = get_logger("serializer")

def serialize_block(block) -> bytes:
    """
    Serialize a block object to binary format
    
    Args:
        block: The Block object to serialize
        
    Returns:
        Binary representation of the block
    """
    try:
        # First convert to dictionary
        block_dict = block.to_dict()
        
        logger.debug(f"Serializing block: hash={block_dict['hash']}, " +
                   f"height={block_dict['height']}, " +
                   f"merkle_root={block_dict['merkle_root']}, " +
                   f"prev_hash={block_dict['prev_hash']}")
        
        # HEADER SECTION - Fixed format
        # =============================
        
        # Create a binary buffer for the header (fixed size)
        header = bytearray()
        
        # Version (4 bytes)
        header.extend(struct.pack('<I', block_dict['version']))
        
        # Previous hash (32 bytes)
        if block_dict['prev_hash']:
            prev_hash_bytes = bytes.fromhex(block_dict['prev_hash'])
        else:
            prev_hash_bytes = bytes(32)  # All zeros for genesis block
        header.extend(prev_hash_bytes)
        
        # Merkle root (32 bytes)
        merkle_root_bytes = bytes.fromhex(block_dict['merkle_root'])
        header.extend(merkle_root_bytes)
        
        # Timestamp (8 bytes)
        header.extend(struct.pack('<Q', int(block_dict['timestamp'])))
        
        # Height (4 bytes)
        header.extend(struct.pack('<I', block_dict['height']))
        
        # Difficulty (8 bytes as double)
        header.extend(struct.pack('<d', block_dict['difficulty']))
        
        # Nonce (8 bytes)
        header.extend(struct.pack('<Q', block_dict['nonce']))
        
        # Block hash (32 bytes) - The hash of all the above fields
        hash_bytes = bytes.fromhex(block_dict['hash'])
        header.extend(hash_bytes)
        
        logger.debug(f"Header serialized: {len(header)} bytes")
        
        # DATA SECTION - Variable format
        # ==============================
        
        # Create a binary buffer for the data (variable size)
        data = bytearray()
        
        # Transactions count (4 bytes)
        transactions = block_dict['transactions']
        data.extend(struct.pack('<I', len(transactions)))
        
        # Serialize each transaction in binary format
        for tx in transactions:
            tx_binary = serialize_transaction(tx)
            # Transaction length (4 bytes) + binary data
            data.extend(struct.pack('<I', len(tx_binary)))
            data.extend(tx_binary)
        
        # Extra data - Convert to binary format
        extra_data = block_dict.get('extra_data', {})
        if extra_data:
            # Serialize extra_data fields to binary where possible
            extra_data_binary = bytearray()
            
            # Count of key-value pairs (4 bytes)
            extra_data_binary.extend(struct.pack('<I', len(extra_data)))
            
            # Store each key-value pair
            for key, value in extra_data.items():
                # Key (string)
                key_bytes = key.encode('utf-8')
                extra_data_binary.extend(struct.pack('<I', len(key_bytes)))
                extra_data_binary.extend(key_bytes)
                
                # Value handling based on type
                if isinstance(value, int):
                    # Type marker (1 byte): 1 = integer
                    extra_data_binary.extend(b'\x01')
                    extra_data_binary.extend(struct.pack('<q', value))
                elif isinstance(value, float):
                    # Type marker (1 byte): 2 = float
                    extra_data_binary.extend(b'\x02')
                    extra_data_binary.extend(struct.pack('<d', value))
                elif isinstance(value, str):
                    # Type marker (1 byte): 3 = string
                    extra_data_binary.extend(b'\x03')
                    value_bytes = value.encode('utf-8')
                    extra_data_binary.extend(struct.pack('<I', len(value_bytes)))
                    extra_data_binary.extend(value_bytes)
                else:
                    # Type marker (1 byte): 4 = json for complex types
                    extra_data_binary.extend(b'\x04')
                    value_bytes = json.dumps(value).encode('utf-8')
                    extra_data_binary.extend(struct.pack('<I', len(value_bytes)))
                    extra_data_binary.extend(value_bytes)
            
            # Add the binary extra data
            data.extend(struct.pack('<I', len(extra_data_binary)))
            data.extend(extra_data_binary)
        else:
            # No extra data
            data.extend(struct.pack('<I', 0))
        
        logger.debug(f"Data serialized: {len(data)} bytes")
        
        # Combine header and data
        combined = bytearray()
        
        # Add a consistent magic marker to indicate start of block header
        combined.extend(b'QBTH')  # Qbitcoin Block Header
        
        # Add header size (4 bytes)
        combined.extend(struct.pack('<I', len(header)))
        
        # Add header
        combined.extend(header)
        
        # Add data
        combined.extend(data)
        
        logger.debug(f"Total serialized block size: {len(combined)} bytes")
        return bytes(combined)
        
    except Exception as e:
        logger.error(f"Error serializing block: {e}")
        raise

def deserialize_block(data: bytes):
    """
    Deserialize binary data to a Block object
    
    Args:
        data: Binary block data
        
    Returns:
        Block object
    """
    try:
        from core.block import Block  # Import here to avoid circular imports
        
        # Create a dictionary to hold block data
        block_dict = {}
        
        # Current position in the buffer
        pos = 0
        
        # Magic marker (4 bytes)
        magic_marker = data[pos:pos+4]
        if magic_marker != b'QBTH':
            raise ValueError("Invalid block data: missing magic marker")
        pos += 4
        
        # Header size (4 bytes)
        header_size = struct.unpack('<I', data[pos:pos+4])[0]
        pos += 4
        
        # Header (fixed size)
        header = data[pos:pos+header_size]
        pos += header_size
        
        # Deserialize header
        header_pos = 0
        
        # Version (4 bytes)
        block_dict['version'] = struct.unpack('<I', header[header_pos:header_pos+4])[0]
        header_pos += 4
        
        # Previous hash (32 bytes)
        prev_hash_bytes = header[header_pos:header_pos+32]
        prev_hash = prev_hash_bytes.hex()
        # For genesis block, ensure the previous hash is properly handled 
        # even if it's all zeros
        if prev_hash == "0" * 64:
            block_dict['prev_hash'] = "0" * 64
        else:
            block_dict['prev_hash'] = prev_hash
        header_pos += 32
        
        # Merkle root (32 bytes)
        merkle_root_bytes = header[header_pos:header_pos+32]
        block_dict['merkle_root'] = merkle_root_bytes.hex()
        header_pos += 32
        
        # Timestamp (8 bytes)
        block_dict['timestamp'] = struct.unpack('<Q', header[header_pos:header_pos+8])[0]
        header_pos += 8
        
        # Height (4 bytes)
        block_dict['height'] = struct.unpack('<I', header[header_pos:header_pos+4])[0]
        header_pos += 4
        
        # Difficulty (8 bytes as double)
        block_dict['difficulty'] = struct.unpack('<d', header[header_pos:header_pos+8])[0]
        header_pos += 8
        
        # Nonce (8 bytes)
        block_dict['nonce'] = struct.unpack('<Q', header[header_pos:header_pos+8])[0]
        header_pos += 8
        
        # Block hash (32 bytes)
        hash_bytes = header[header_pos:header_pos+32]
        block_dict['hash'] = hash_bytes.hex()
        header_pos += 32
        
        # Transactions
        tx_count = struct.unpack('<I', data[pos:pos+4])[0]
        pos += 4
        
        transactions = []
        for _ in range(tx_count):
            # Transaction length
            tx_len = struct.unpack('<I', data[pos:pos+4])[0]
            pos += 4
            
            # Transaction data
            tx_data = data[pos:pos+tx_len]
            tx = deserialize_transaction(tx_data)
            transactions.append(tx)
            pos += tx_len
            
        block_dict['transactions'] = transactions
        
        # Extra data
        if pos < len(data):
            extra_data_len = struct.unpack('<I', data[pos:pos+4])[0]
            pos += 4
            
            if extra_data_len > 0:
                extra_data_binary = data[pos:pos+extra_data_len]
                pos += extra_data_len
                
                # Deserialize extra data
                extra_data = {}
                extra_data_pos = 0
                
                # Count of key-value pairs
                kv_count = struct.unpack('<I', extra_data_binary[extra_data_pos:extra_data_pos+4])[0]
                extra_data_pos += 4
                
                for _ in range(kv_count):
                    # Key (string)
                    key_len = struct.unpack('<I', extra_data_binary[extra_data_pos:extra_data_pos+4])[0]
                    extra_data_pos += 4
                    key = extra_data_binary[extra_data_pos:extra_data_pos+key_len].decode('utf-8')
                    extra_data_pos += key_len
                    
                    # Value type marker
                    value_type = extra_data_binary[extra_data_pos]
                    extra_data_pos += 1
                    
                    # Value based on type
                    if value_type == 1:
                        value = struct.unpack('<q', extra_data_binary[extra_data_pos:extra_data_pos+8])[0]
                        extra_data_pos += 8
                    elif value_type == 2:
                        value = struct.unpack('<d', extra_data_binary[extra_data_pos:extra_data_pos+8])[0]
                        extra_data_pos += 8
                    elif value_type == 3:
                        value_len = struct.unpack('<I', extra_data_binary[extra_data_pos:extra_data_pos+4])[0]
                        extra_data_pos += 4
                        value = extra_data_binary[extra_data_pos:extra_data_pos+value_len].decode('utf-8')
                        extra_data_pos += value_len
                    else:
                        value_len = struct.unpack('<I', extra_data_binary[extra_data_pos:extra_data_pos+4])[0]
                        extra_data_pos += 4
                        value = json.loads(extra_data_binary[extra_data_pos:extra_data_pos+value_len].decode('utf-8'))
                        extra_data_pos += value_len
                    
                    extra_data[key] = value
                
                block_dict['extra_data'] = extra_data
            else:
                block_dict['extra_data'] = {}
        
        # Log deserialized block details for debugging
        logger.debug(f"Deserialized block: hash={block_dict['hash']}, " +
                     f"height={block_dict['height']}, " +
                     f"merkle_root={block_dict['merkle_root']}, " +
                     f"prev_hash={block_dict['prev_hash']}")
        
        # Create block from dictionary
        return Block.from_dict(block_dict)
        
    except Exception as e:
        logger.error(f"Error deserializing block: {e}")
        raise

def serialize_transaction(transaction) -> bytes:
    """
    Serialize a transaction object to binary format
    
    Args:
        transaction: The Transaction object to serialize
        
    Returns:
        Binary representation of the transaction
    """
    # Get transaction as dict if it's an object
    tx_dict = transaction.to_dict() if hasattr(transaction, 'to_dict') else transaction
    
    # Create binary buffer
    data = bytearray()
    
    # Version (4 bytes)
    data.extend(struct.pack('<I', tx_dict.get('version', 1)))
    
    # Timestamp (8 bytes)
    data.extend(struct.pack('<Q', int(tx_dict.get('timestamp', int(time.time())))))
    
    # Fee (8 bytes - double)
    data.extend(struct.pack('<d', float(tx_dict.get('fee', 0))))
    
    # Transaction data (string, variable length)
    tx_data = tx_dict.get('data', '')
    tx_data_bytes = tx_data.encode('utf-8') if tx_data else b''
    data.extend(struct.pack('<I', len(tx_data_bytes)))  # Length (4 bytes)
    data.extend(tx_data_bytes)
    
    # Inputs (variable length)
    inputs = tx_dict.get('inputs', [])
    data.extend(struct.pack('<I', len(inputs)))  # Count (4 bytes)
    
    for tx_input in inputs:
        # Input address (variable length)
        addr = tx_input.get('address', '').encode('utf-8')
        data.extend(struct.pack('<I', len(addr)))  # Length (4 bytes)
        data.extend(addr)
        
        # Input amount (8 bytes - double)
        data.extend(struct.pack('<d', float(tx_input.get('amount', 0))))
        
        # Previous transaction hash (variable length)
        prev_tx = tx_input.get('prev_tx', '').encode('utf-8')
        data.extend(struct.pack('<I', len(prev_tx)))  # Length (4 bytes)
        data.extend(prev_tx)
        
        # Output index (4 bytes)
        data.extend(struct.pack('<I', int(tx_input.get('output_index', 0))))
    
    # Outputs (variable length)
    outputs = tx_dict.get('outputs', [])
    data.extend(struct.pack('<I', len(outputs)))  # Count (4 bytes)
    
    for tx_output in outputs:
        # Output address (variable length)
        addr = tx_output.get('address', '').encode('utf-8')
        data.extend(struct.pack('<I', len(addr)))  # Length (4 bytes)
        data.extend(addr)
        
        # Output amount (8 bytes - double)
        data.extend(struct.pack('<d', float(tx_output.get('amount', 0))))
    
    # Public key (variable length)
    pub_key = tx_dict.get('public_key', '')
    if pub_key:
        pub_key_bytes = pub_key.encode('utf-8')
    else:
        pub_key_bytes = b''
    data.extend(struct.pack('<I', len(pub_key_bytes)))  # Length (4 bytes)
    data.extend(pub_key_bytes)
    
    # Signature (variable length)
    sig = tx_dict.get('signature', '')
    if sig:
        sig_bytes = sig.encode('utf-8')
    else:
        sig_bytes = b''
    data.extend(struct.pack('<I', len(sig_bytes)))  # Length (4 bytes)
    data.extend(sig_bytes)
    
    # Hash (variable length) - We store this even though it could be recalculated
    tx_hash = tx_dict.get('hash', '')
    tx_hash_bytes = tx_hash.encode('utf-8') if tx_hash else b''
    data.extend(struct.pack('<I', len(tx_hash_bytes)))  # Length (4 bytes)
    data.extend(tx_hash_bytes)
    
    return bytes(data)

def deserialize_transaction(data: bytes):
    """
    Deserialize binary data to a Transaction object/dictionary
    
    Args:
        data: Binary transaction data
        
    Returns:
        Transaction object or dictionary
    """
    from core.transaction import Transaction  # Import here to avoid circular imports
    
    # Create a dictionary to hold transaction data
    tx_dict = {}
    
    # Current position in the buffer
    pos = 0
    
    # Version (4 bytes)
    tx_dict['version'] = struct.unpack('<I', data[pos:pos+4])[0]
    pos += 4
    
    # Timestamp (8 bytes)
    tx_dict['timestamp'] = struct.unpack('<Q', data[pos:pos+8])[0]
    pos += 8
    
    # Fee (8 bytes - double)
    tx_dict['fee'] = struct.unpack('<d', data[pos:pos+8])[0]
    pos += 8
    
    # Transaction data
    data_len = struct.unpack('<I', data[pos:pos+4])[0]
    pos += 4
    if data_len > 0:
        tx_dict['data'] = data[pos:pos+data_len].decode('utf-8')
        pos += data_len
    else:
        tx_dict['data'] = ''
    
    # Inputs
    input_count = struct.unpack('<I', data[pos:pos+4])[0]
    pos += 4
    
    inputs = []
    for _ in range(input_count):
        tx_input = {}
        
        # Input address
        addr_len = struct.unpack('<I', data[pos:pos+4])[0]
        pos += 4
        if addr_len > 0:
            tx_input['address'] = data[pos:pos+addr_len].decode('utf-8')
            pos += addr_len
        else:
            tx_input['address'] = ''
        
        # Input amount
        tx_input['amount'] = struct.unpack('<d', data[pos:pos+8])[0]
        pos += 8
        
        # Previous transaction hash
        prev_tx_len = struct.unpack('<I', data[pos:pos+4])[0]
        pos += 4
        if prev_tx_len > 0:
            tx_input['prev_tx'] = data[pos:pos+prev_tx_len].decode('utf-8')
            pos += prev_tx_len
        else:
            tx_input['prev_tx'] = ''
        
        # Output index
        tx_input['output_index'] = struct.unpack('<I', data[pos:pos+4])[0]
        pos += 4
        
        inputs.append(tx_input)
    
    tx_dict['inputs'] = inputs
    
    # Outputs
    output_count = struct.unpack('<I', data[pos:pos+4])[0]
    pos += 4
    
    outputs = []
    for _ in range(output_count):
        tx_output = {}
        
        # Output address
        addr_len = struct.unpack('<I', data[pos:pos+4])[0]
        pos += 4
        if addr_len > 0:
            tx_output['address'] = data[pos:pos+addr_len].decode('utf-8')
            pos += addr_len
        else:
            tx_output['address'] = ''
        
        # Output amount
        tx_output['amount'] = struct.unpack('<d', data[pos:pos+8])[0]
        pos += 8
        
        outputs.append(tx_output)
    
    tx_dict['outputs'] = outputs
    
    # Public key
    pub_key_len = struct.unpack('<I', data[pos:pos+4])[0]
    pos += 4
    if pub_key_len > 0:
        tx_dict['public_key'] = data[pos:pos+pub_key_len].decode('utf-8')
        pos += pub_key_len
    else:
        tx_dict['public_key'] = None
    
    # Signature
    sig_len = struct.unpack('<I', data[pos:pos+4])[0]
    pos += 4
    if sig_len > 0:
        tx_dict['signature'] = data[pos:pos+sig_len].decode('utf-8')
        pos += sig_len
    else:
        tx_dict['signature'] = None
    
    # Hash
    hash_len = struct.unpack('<I', data[pos:pos+4])[0]
    pos += 4
    if hash_len > 0:
        tx_dict['hash'] = data[pos:pos+hash_len].decode('utf-8')
        pos += hash_len
    else:
        tx_dict['hash'] = ''
    
    # Return as Transaction object if available, otherwise return dict
    try:
        return Transaction.from_dict(tx_dict)
    except:
        return tx_dict