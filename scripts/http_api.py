#!/usr/bin/env python3
"""
Fixed Qbitcoin HTTP API Client Test Script
Tests various API endpoints through the gRPC proxy with proper address handling
"""

import requests
import json
import time
import hashlib

from typing import Dict
from qbitcoin.crypto.falcon import FalconSignature
from qbitcoin.tools.wallet_creator import WalletCreator


class QbitcoinHTTPClient:
    def __init__(self, base_url: str = "http://207.154.252.226:18090"):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api"
        self.json_rpc_url = f"{self.base_url}/json_rpc"
        
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make HTTP GET request to API endpoint"""
        try:
            url = f"{self.api_base}/{endpoint}"
            print(f"🌐 Making request to: {url}")
            if params:
                print(f"📋 Parameters: {params}")
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code}: {response.text}")
                return {"error": f"HTTP {response.status_code}", "details": response.text}
            
            result = response.json()
            print(f"✅ Response received successfully")
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode failed: {e}")
            return {"error": "Invalid JSON response", "raw_response": response.text[:200]}
    
    def _make_json_rpc_request(self, method: str, params: Dict = None) -> Dict:
        """Make JSON-RPC POST request"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
                "id": int(time.time())
            }
            
            print(f"🌐 Making JSON-RPC request: {method}")
            if params:
                print(f"📋 Parameters: {params}")
            
            response = requests.post(
                self.json_rpc_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code}: {response.text}")
                return {"error": f"HTTP {response.status_code}", "details": response.text}
            
            result = response.json()
            print(f"✅ JSON-RPC response received")
            return result
            
        except Exception as e:
            print(f"❌ JSON-RPC request failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def qaddress_to_hex(qaddress: str) -> str:
        """Convert Qbitcoin address to hex format for API"""
        if qaddress.startswith('Q'):
            return qaddress[1:]  # Remove 'Q' prefix
        return qaddress

    @staticmethod
    def generate_test_address() -> str:
        """Generate a test address in hex format"""
        # Generate a 35-byte test address (Qbitcoin address format)
        import os
        random_bytes = os.urandom(35)
        return random_bytes.hex()

    # Node Information APIs
    def get_node_state(self) -> Dict:
        """Get node state information"""
        return self._make_request("GetNodeState")
    
    def get_height(self) -> Dict:
        """Get current blockchain height"""
        return self._make_request("GetHeight")
    
    def get_stats(self, include_timeseries: bool = False) -> Dict:
        """Get blockchain statistics"""
        params = {"include_timeseries": str(include_timeseries).lower()}
        return self._make_request("GetStats", params)
    
    def get_known_peers(self) -> Dict:
        """Get list of known peers"""
        return self._make_request("GetKnownPeers")
    
    def get_peers_stat(self) -> Dict:
        """Get peers statistics"""
        return self._make_request("GetPeersStat")
    
    def get_chain_stats(self) -> Dict:
        """Get chain statistics"""
        return self._make_request("GetChainStats")

    # Balance APIs
    def get_balance(self, address: str) -> Dict:
        """Get balance for an address"""
        params = {"address": address}
        return self._make_request("GetBalance", params)
    
    def get_address_state(self, address: str) -> Dict:
        """Get full address state"""
        params = {"address": address}
        return self._make_request("GetAddressState", params)
    
    def get_optimized_address_state(self, address: str) -> Dict:
        """Get optimized address state"""
        params = {"address": address}
        return self._make_request("GetOptimizedAddressState", params)

    # Transaction APIs
    def get_transaction(self, tx_hash: str) -> Dict:
        """Get transaction by hash"""
        params = {"tx_hash": tx_hash}
        return self._make_request("GetTransaction", params)
    
    def get_transactions_by_address(self, address: str, item_per_page: int = 10, page_number: int = 1) -> Dict:
        """Get transactions for an address with pagination"""
        params = {
            "address": address,
            "item_per_page": item_per_page,
            "page_number": page_number
        }
        return self._make_request("GetTransactionsByAddress", params)
    
    def get_mini_transactions_by_address(self, address: str, item_per_page: int = 10, page_number: int = 1) -> Dict:
        """Get mini transactions for an address"""
        params = {
            "address": address,
            "item_per_page": item_per_page,
            "page_number": page_number
        }
        return self._make_request("GetMiniTransactionsByAddress", params)

    # Block APIs
    def get_block_by_number(self, block_number: int) -> Dict:
        """Get block by block number"""
        params = {"block_number": block_number}
        return self._make_request("GetBlockByNumber", params)
    
    def get_block(self, header_hash: str) -> Dict:
        """Get block by header hash"""
        params = {"header_hash": header_hash}
        return self._make_request("GetBlock", params)

    # JSON-RPC APIs
    def get_last_block_header_rpc(self, height: int = 0) -> Dict:
        """Get last block header via JSON-RPC"""
        params = {"height": height} if height > 0 else {}
        return self._make_json_rpc_request("getlastblockheader", params)
    
    def get_height_rpc(self) -> Dict:
        """Get height via JSON-RPC"""
        return self._make_json_rpc_request("getheight")

    # Transaction creation and submission methods
    def create_transfer_transaction(self, from_address: str, to_address: str, amount: int, private_key_hex: str, public_key_hex: str, fee: int = 1000000) -> str:
        """Create a transfer transaction and return hex-encoded protobuf transaction"""
        try:
            # Convert keys from hex to bytes
            private_key_bytes = bytes.fromhex(private_key_hex)
            public_key_bytes = bytes.fromhex(public_key_hex)
            
            # Convert Q-addresses to bytes (remove Q prefix and convert hex to bytes)
            from_addr_bytes = bytes.fromhex(from_address[1:])  # Remove Q prefix
            to_addr_bytes = bytes.fromhex(to_address[1:])      # Remove Q prefix
            
            # Get current nonce for the from_address
            nonce = self._get_address_nonce(from_address)
            
            # Create transaction message for signing (before signature)
            transaction_message = self._create_transaction_signing_message(
                from_addr_bytes, fee, public_key_bytes, nonce + 1, to_addr_bytes, amount
            )
            
            # Sign transaction using Falcon
            signature = FalconSignature.sign_message(transaction_message, private_key_bytes)
            print(f"🔐 Created signature, length: {len(signature)} bytes")
            
            # Verify the signature before proceeding
            print(f"🔍 Verifying signature...")
            try:
                # Import the verify function from falcon module
                from qbitcoin.crypto.falcon import verify_signature
                
                # Verify the signature
                is_valid = verify_signature(transaction_message, signature.hex(), public_key_bytes.hex())
                
                if is_valid:
                    print(f"✅ Signature verification successful!")
                else:
                    print(f"❌ Signature verification FAILED!")
                    print(f"   Message length: {len(transaction_message)}")
                    print(f"   Signature length: {len(signature)}")
                    print(f"   Public key length: {len(public_key_bytes)}")
                    return None
                    
            except Exception as e:
                print(f"❌ Signature verification error: {e}")
                print(f"   Trying alternative verification method...")
                
                # Try with FalconSignature.verify_signature method
                try:
                    is_valid = FalconSignature.verify_signature(transaction_message, signature, public_key_bytes)
                    if is_valid:
                        print(f"✅ Alternative signature verification successful!")
                    else:
                        print(f"❌ Alternative signature verification FAILED!")
                        return None
                except Exception as e2:
                    print(f"❌ Alternative verification also failed: {e2}")
                    return None
            
            # Calculate transaction hash (includes signature)
            full_message = transaction_message + signature
            tx_hash = hashlib.sha256(full_message).digest()
            print(f"🧮 Calculated transaction hash: {tx_hash.hex()[:16]}...")
            
            # Create protobuf-compatible binary transaction
            protobuf_data = self._create_protobuf_transaction(
                master_addr=from_addr_bytes,
                fee=fee,
                public_key=public_key_bytes,
                signature=signature,
                nonce=nonce + 1,
                transaction_hash=tx_hash,
                addrs_to=[to_addr_bytes],
                amounts=[amount]
            )
            
            return protobuf_data.hex()
            
        except Exception as e:
            print(f"Error creating transaction: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _create_transaction_signing_message(self, master_addr: bytes, fee: int, public_key: bytes, nonce: int, to_addr: bytes, amount: int) -> bytes:
        """Create message for signing following TransferTransaction.get_data_bytes format"""
        print(f"📝 Creating signing message using TransferTransaction format...")
        
        # Following TransferTransaction.get_data_bytes() format:
        # tmptxhash = (self.master_addr +
        #              self.fee.to_bytes(8, byteorder='big', signed=False) +
        #              self.message_data)
        # for index in range(0, len(self.addrs_to)):
        #     tmptxhash = (tmptxhash +
        #                  self.addrs_to[index] +
        #                  self.amounts[index].to_bytes(8, byteorder='big', signed=False))
        
        # 1. Master address (20 bytes)
        data = master_addr
        print(f"   Master addr: {master_addr.hex()}")
        
        # 2. Fee (8 bytes, big-endian)
        fee_bytes = fee.to_bytes(8, byteorder='big', signed=False)
        data += fee_bytes
        print(f"   Fee bytes: {fee_bytes.hex()}")
        
        # 3. Message data (empty for simple transfer)
        message_data = b''
        data += message_data
        print(f"   Message data: empty")
        
        # 4. For each recipient: addr_to + amount (big-endian)
        addr_amount = to_addr + amount.to_bytes(8, byteorder='big', signed=False)
        data += addr_amount
        print(f"   Recipient: {to_addr.hex()} + {amount.to_bytes(8, byteorder='big', signed=False).hex()}")
        
        print(f"   Total signing data length: {len(data)} bytes")
        
        # Hash the data (this is what actually gets signed)
        data_hash = hashlib.sha256(data).digest()
        print(f"   Data hash for signing: {data_hash.hex()}")
        
        return data_hash  # Return the hash, not the raw data

    def _create_protobuf_transaction(self, master_addr: bytes, fee: int, public_key: bytes, 
                                   signature: bytes, nonce: int, transaction_hash: bytes,
                                   addrs_to: list, amounts: list) -> bytes:
        """Create protobuf-compatible binary transaction data"""
        
        # This creates a simplified protobuf format manually
        # Protobuf uses varint encoding and field tags
        
        protobuf_data = b""
        
        # Field 1: master_addr (bytes) - tag: 0x0A (field 1, wire type 2)
        protobuf_data += self._encode_protobuf_bytes_field(1, master_addr)
        
        # Field 2: fee (uint64) - tag: 0x10 (field 2, wire type 0)  
        protobuf_data += self._encode_protobuf_varint_field(2, fee)
        
        # Field 3: public_key (bytes) - tag: 0x1A (field 3, wire type 2)
        protobuf_data += self._encode_protobuf_bytes_field(3, public_key)
        
        # Field 4: signature (bytes) - tag: 0x22 (field 4, wire type 2)
        protobuf_data += self._encode_protobuf_bytes_field(4, signature)
        
        # Field 5: nonce (uint64) - tag: 0x28 (field 5, wire type 0)
        protobuf_data += self._encode_protobuf_varint_field(5, nonce)
        
        # Field 6: transaction_hash (bytes) - tag: 0x32 (field 6, wire type 2)
        protobuf_data += self._encode_protobuf_bytes_field(6, transaction_hash)
        
        # Field 7: Transfer message (nested) - tag: 0x3A (field 7, wire type 2)
        transfer_data = self._create_protobuf_transfer(addrs_to, amounts)
        protobuf_data += self._encode_protobuf_bytes_field(7, transfer_data)
        
        return protobuf_data

    def _create_protobuf_transfer(self, addrs_to: list, amounts: list) -> bytes:
        """Create Transfer submessage"""
        transfer_data = b""
        
        # Field 1: addrs_to (repeated bytes)
        for i, addr in enumerate(addrs_to):
            # tag: 0x0A (field 1, wire type 2)
            transfer_data += self._encode_protobuf_bytes_field(1, addr)
        
        # Field 2: amounts (repeated uint64)  
        for amount in amounts:
            # tag: 0x10 (field 2, wire type 0)
            transfer_data += self._encode_protobuf_varint_field(2, amount)
            
        return transfer_data

    def _encode_protobuf_varint_field(self, field_num: int, value: int) -> bytes:
        """Encode protobuf varint field (for uint64)"""
        # Wire type 0 (varint)
        tag = (field_num << 3) | 0
        return self._encode_varint(tag) + self._encode_varint(value)

    def _encode_protobuf_bytes_field(self, field_num: int, data: bytes) -> bytes:
        """Encode protobuf bytes field"""
        # Wire type 2 (length-delimited)
        tag = (field_num << 3) | 2
        return self._encode_varint(tag) + self._encode_varint(len(data)) + data

    def _encode_varint(self, value: int) -> bytes:
        """Encode varint (variable-length integer) as used in protobuf"""
        result = b""
        while value >= 0x80:
            result += bytes([value & 0x7F | 0x80])
            value >>= 7
        result += bytes([value & 0x7F])
        return result

    def _get_address_nonce(self, address: str) -> int:
        """Get current nonce for address"""
        try:
            result = self.get_address_state(address)
            if 'state' in result and 'nonce' in result['state']:
                return int(result['state']['nonce'])
            return 0
        except:
            return 0

    def push_transaction(self, transaction_hex: str) -> Dict:
        """Submit transaction via HTTP API"""
        try:
            params = {"transaction_signed": transaction_hex}
            return self._make_request("PushTransaction", params)
        except Exception as e:
            return {"error": f"Transaction submission failed: {e}"}


def run_comprehensive_test():
    """Run comprehensive API tests"""
    print("🚀 Starting Qbitcoin HTTP API Tests\n")
    
    client = QbitcoinHTTPClient()
    
    # Test 1: Node Information APIs (should work)
    print("=" * 60)
    print("1. TESTING NODE INFORMATION APIs")
    print("=" * 60)
    
    tests = [
        ("Node State", lambda: client.get_node_state()),
        ("Blockchain Height", lambda: client.get_height()),
        ("Chain Statistics", lambda: client.get_chain_stats()),
        ("Known Peers", lambda: client.get_known_peers()),
        ("Peer Statistics", lambda: client.get_peers_stat()),
        ("General Stats", lambda: client.get_stats(False)),
    ]
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing: {test_name}")
        print("-" * 40)
        result = test_func()
        if "error" in result:
            print(f"❌ {test_name} failed: {result}")
        else:
            print(f"✅ {test_name} successful!")
            # Print a few key fields if available
            if isinstance(result, dict):
                for key in list(result.keys())[:3]:
                    print(f"   {key}: {result[key]}")
        print()

    # Test 2: Block APIs
    print("=" * 60)
    print("2. TESTING BLOCK APIs")
    print("=" * 60)
    
    print(f"\n🔍 Testing: Get Block by Number")
    print("-" * 40)
    result = client.get_block_by_number(1)
    if "error" in result:
        print(f"❌ Get Block by Number failed: {result}")
    else:
        print(f"✅ Get Block by Number successful!")
        if 'block' in result and 'header' in result['block']:
            header = result['block']['header']
            print(f"   Block Number: {header.get('blockNumber', 'N/A')}")
            print(f"   Timestamp: {header.get('timestampSeconds', 'N/A')}")
    print()

    # Test 3: Address and Balance APIs (with proper hex formatting)
    print("=" * 60)
    print("3. TESTING ADDRESS & BALANCE APIs")
    print("=" * 60)
    
    # Use a valid Qbitcoin address format (provided by user)
    # This address follows the correct Qbitcoin format: Q + 50 hex characters
    qtest_address = "Q015b13be3928eb6a419184eecfd4c3b967a03cb44ed821836c"
    
    address_tests = [
        ("Get Balance", lambda: client.get_balance(qtest_address)),
        ("Get Address State", lambda: client.get_address_state(qtest_address)),
        ("Get Optimized Address State", lambda: client.get_optimized_address_state(qtest_address)),
        ("Get Transactions by Address", lambda: client.get_transactions_by_address(qtest_address, 5, 1)),
        ("Get Mini Transactions by Address", lambda: client.get_mini_transactions_by_address(qtest_address, 5, 1)),
    ]
    
    print(f"Testing with address: {qtest_address[:20]}...")
    
    for test_name, test_func in address_tests:
        print(f"\n🔍 Testing: {test_name}")
        print("-" * 40)
        result = test_func()
        if "error" in result:
            print(f"⚠️  {test_name}: {result}")
        else:
            print(f"✅ {test_name} successful!")
            if isinstance(result, dict):
                for key in list(result.keys())[:2]:
                    print(f"   {key}: {result[key]}")
        print()

    # Test 4: JSON-RPC APIs
    print("=" * 60)
    print("4. TESTING JSON-RPC APIs")
    print("=" * 60)
    
    json_rpc_tests = [
        ("Get Height (JSON-RPC)", lambda: client.get_height_rpc()),
        ("Get Last Block Header (JSON-RPC)", lambda: client.get_last_block_header_rpc()),
    ]
    
    for test_name, test_func in json_rpc_tests:
        print(f"\n🔍 Testing: {test_name}")
        print("-" * 40)
        result = test_func()
        if "error" in result:
            print(f"⚠️  {test_name}: {result}")
        else:
            print(f"✅ {test_name} successful!")
            if isinstance(result, dict):
                # Print result or error info
                if "result" in result:
                    print(f"   Result: {result['result']}")
                elif "error" in result:
                    print(f"   Error: {result['error']}")
        print()

    

def test_transaction_creation_demo():
    """Create and submit real transaction using genesis wallet"""
    print("\n" + "=" * 60)
    print("TRANSACTION CREATION & SUBMISSION")
    print("=" * 60)
    
    client = QbitcoinHTTPClient()
    
    # Load genesis keys
    try:
        with open('genesis_keys.json', 'r') as f:
            genesis_keys = json.load(f)
        
        genesis_address = genesis_keys['address']
        private_key_hex = genesis_keys['private_key_hex']
        public_key_hex = genesis_keys['public_key_hex']
        
        print(f"📋 Using Genesis Wallet:")
        print(f"   Address: {genesis_address}")
        print(f"   Balance: {genesis_keys['genesis_balance']}")
        
    except Exception as e:
        print(f"❌ Failed to load genesis keys: {e}")
        return
    
    # Get current balance
    print(f"\n🔍 Checking current balance...")
    balance_result = client.get_balance(genesis_address)
    if 'balance' in balance_result:
        current_balance = int(balance_result['balance'])
        balance_qrl = current_balance / 1000000000  # Convert from shor to QRL
        print(f"✅ Current Balance: {current_balance} shor ({balance_qrl} QRL)")
    else:
        print(f"❌ Could not get balance: {balance_result}")
        return
    
    # Create a new recipient address for testing
    print(f"\n🔨 Creating new recipient address...")
    try:
        wallet_creator = WalletCreator()
        # Generate new Falcon key pair for recipient
        recipient_private, recipient_public = FalconSignature.generate_keypair()
        recipient_address = wallet_creator.generate_address(recipient_public)
        
        print(f"✅ Generated recipient address: {recipient_address}")
    except Exception as e:
        print(f"❌ Failed to create recipient address: {e}")
        return
    
    # Create and submit transaction
    print(f"\n💸 Creating transfer transaction...")
    transfer_amount = 1000000000  # 1 QRL in shor
    
    try:
        transaction_hex = client.create_transfer_transaction(
            from_address=genesis_address,
            to_address=recipient_address,
            amount=transfer_amount,
            private_key_hex=private_key_hex,
            public_key_hex=public_key_hex,
            fee=1000000  # 0.001 QRL fee
        )
        
        if transaction_hex:
            print(f"✅ Transaction created successfully!")
            print(f"   Transaction hex length: {len(transaction_hex)} characters")
            print(f"   Transaction preview: {transaction_hex[:64]}...")
            
            # Submit transaction
            print(f"\n🚀 Submitting transaction to network...")
            result = client.push_transaction(transaction_hex)
            
            if 'error' in result:
                print(f"❌ Transaction submission failed: {result['error']}")
            else:
                print(f"✅ Transaction submitted successfully!")
                print(f"   Result: {json.dumps(result, indent=2)}")
                
                # Wait a moment and check balances
                print(f"\n⏳ Waiting 3 seconds for transaction processing...")
                time.sleep(3)
                
                print(f"\n🔍 Checking updated balances...")
                
                # Check sender balance
                sender_balance = client.get_balance(genesis_address)
                if 'balance' in sender_balance:
                    new_balance = int(sender_balance['balance'])
                    balance_qrl = new_balance / 1000000000
                    print(f"   Sender ({genesis_address[:20]}...): {new_balance} shor ({balance_qrl} QRL)")
                
                # Check recipient balance
                recipient_balance = client.get_balance(recipient_address)
                if 'balance' in recipient_balance:
                    recv_balance = int(recipient_balance['balance'])
                    recv_balance_qrl = recv_balance / 1000000000
                    print(f"   Recipient ({recipient_address[:20]}...): {recv_balance} shor ({recv_balance_qrl} QRL)")
                else:
                    print(f"   Recipient balance: 0 (transaction may still be processing)")
        else:
            print(f"❌ Failed to create transaction")
            
    except Exception as e:
        print(f"❌ Transaction creation/submission error: {e}")
    
    print(f"\n💡 Transaction creation and submission demo completed!")
    print(f"📝 Note: This creates real transactions on the Qbitcoin network using HTTP API")
    
    


if __name__ == "__main__":
    try:
        run_comprehensive_test()
        test_transaction_creation_demo()
        
        print(f"\n🎉 HTTP API testing completed!")
         
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")