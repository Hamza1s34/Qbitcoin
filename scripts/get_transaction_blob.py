#!/usr/bin/env python3
"""
Script to get transaction blob from transaction hash using QRL node API
"""

import grpc
import sys
from binascii import hexlify, unhexlify

# Import QRL modules
from qbitcoin.generated import qbit_pb2_grpc, qbit_pb2

NODE_GRPC_ENDPOINT = 'localhost:19009'
CONNECTION_TIMEOUT = 10


def get_transaction_blob_from_hash(tx_hash_hex: str) -> str:
    """
    Get transaction blob from transaction hash
    
    Args:
        tx_hash_hex: Transaction hash in hexadecimal format
        
    Returns:
        Transaction blob in hexadecimal format, or None if not found
    """
    try:
        # Convert hex hash to bytes
        tx_hash_bytes = bytes.fromhex(tx_hash_hex)
        
        # Connect to QRL node
        channel = grpc.insecure_channel(NODE_GRPC_ENDPOINT)
        stub = qbit_pb2_grpc.PublicAPIStub(channel)
        
        # Create GetTransaction request
        request = qbit_pb2.GetTransactionReq(tx_hash=tx_hash_bytes)
        
        # Get transaction from node
        print(f"Requesting transaction {tx_hash_hex} from node...")
        response = stub.GetTransaction(request, timeout=CONNECTION_TIMEOUT)
        
        if response.tx.WhichOneof('transactionType'):
            # Transaction found, serialize to get blob
            tx_blob = response.tx.SerializeToString()
            tx_blob_hex = hexlify(tx_blob).decode()
            
            print(f"✓ Transaction found!")
            print(f"Block number: {response.block_number}")
            print(f"Confirmations: {response.confirmations}")
            print(f"Transaction blob: {tx_blob_hex}")
            
            return tx_blob_hex
        else:
            print("✗ Transaction not found in blockchain")
            return None
            
    except grpc.RpcError as e:
        print(f"✗ gRPC error: {e}")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def main():
    if len(sys.argv) != 2:
        print("Usage: python get_transaction_blob.py <transaction_hash>")
        print("Example: python get_transaction_blob.py 83731d90694f8baf11224063a094b0be1a80ac01161bc97225fb7cec6d00d7d7")
        sys.exit(1)
    
    tx_hash = sys.argv[1]
    
    # Remove '0x' prefix if present
    if tx_hash.startswith('0x'):
        tx_hash = tx_hash[2:]
    
    print(f"Getting transaction blob for hash: {tx_hash}")
    print(f"Connecting to QRL node at: {NODE_GRPC_ENDPOINT}")
    print("-" * 60)
    
    blob = get_transaction_blob_from_hash(tx_hash)
    
    if blob:
        print("\n" + "=" * 60)
        print("SUCCESS: You can now use this blob with tx_inspect:")
        print(f"python qbitcoin/cli.py tx_inspect --txblob {blob}")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("FAILED: Could not retrieve transaction blob")
        print("Make sure:")
        print("1. QRL node is running on localhost:19009")
        print("2. Transaction hash is correct")
        print("3. Transaction exists in the blockchain")
        print("=" * 60)


if __name__ == "__main__":
    main()
