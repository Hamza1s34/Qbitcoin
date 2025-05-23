#!/usr/bin/env python3
"""
Qbitcoin API Client

A standalone client to interact with a Qbitcoin node's API endpoints.
This client can retrieve blockchain information, transaction history, 
account information, and submit transactions to the network.
"""

import sys
import json
import time
import base64
import argparse
import requests
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

class QbitcoinAPIClient:
    """
    Client to interact with a Qbitcoin node's API endpoints
    
    This client provides methods to:
    - Get blockchain status and information
    - Retrieve block data
    - Get transaction information
    - Submit new transactions
    - Query account balances and history
    - Create and manage wallets
    - Get network and mining information
    """
    
    def __init__(self, host: str = "localhost", port: int = 9568, api_key: Optional[str] = None):
        """
        Initialize the API client
        
        Args:
            host: The hostname or IP address of the Qbitcoin node (default: localhost)
            port: The API port on the Qbitcoin node (default: 8000)
            api_key: Optional API key for authenticated endpoints
        """
        self.base_url = f"http://{host}:{port}"
        self.api_key = api_key
        # We'll use a session to maintain headers and connection pooling
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"X-API-Key": api_key})
        self.session.headers.update({"Content-Type": "application/json"})
        
    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make a GET request to the API
        
        Args:
            endpoint: The API endpoint to call (without base URL)
            params: Optional query parameters
            
        Returns:
            Response JSON as a dictionary
        """
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()  # Raise exception on HTTP error
        return response.json()
        
    def _post(self, endpoint: str, data: Dict) -> Dict:
        """
        Make a POST request to the API
        
        Args:
            endpoint: The API endpoint to call (without base URL)
            data: The JSON data to send in the request body
            
        Returns:
            Response JSON as a dictionary
        """
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, json=data)
        response.raise_for_status()  # Raise exception on HTTP error
        return response.json()
        
    def _delete(self, endpoint: str) -> Dict:
        """
        Make a DELETE request to the API
        
        Args:
            endpoint: The API endpoint to call (without base URL)
            
        Returns:
            Response JSON as a dictionary
        """
        url = f"{self.base_url}{endpoint}"
        response = self.session.delete(url)
        response.raise_for_status()  # Raise exception on HTTP error
        return response.json()
        
    # General Information Methods
    
    def get_node_info(self) -> Dict:
        """
        Get basic information about the node
        
        Returns:
            Dictionary with basic node information
        """
        return self._get("/")
        
    def get_blockchain_status(self) -> Dict:
        """
        Get comprehensive blockchain status
        
        Returns:
            Dictionary with detailed blockchain status information
        """
        return self._get("/status")
        
    # Block Methods
    
    def get_latest_blocks(self, limit: int = 10) -> Dict:
        """
        Get the latest blocks from the blockchain
        
        Args:
            limit: Number of blocks to retrieve (1-100)
            
        Returns:
            Dictionary containing list of blocks and count
        """
        return self._get("/blockchain/blocks/latest", params={"limit": limit})
        
    def get_block_by_height(self, height: int) -> Dict:
        """
        Get a block by its height
        
        Args:
            height: The block height to retrieve
            
        Returns:
            Dictionary with block details
        """
        return self._get(f"/blockchain/blocks/height/{height}")
        
    def get_block_by_hash(self, block_hash: str) -> Dict:
        """
        Get a block by its hash
        
        Args:
            block_hash: The block hash to retrieve
            
        Returns:
            Dictionary with block details
        """
        return self._get(f"/blockchain/blocks/hash/{block_hash}")
        
    def get_blocks_in_range(self, start: int, end: int) -> Dict:
        """
        Get blocks within a height range
        
        Args:
            start: Starting height (inclusive)
            end: Ending height (inclusive)
            
        Returns:
            Dictionary with blocks in the range and count
        """
        return self._get("/blockchain/blocks/range", params={"start": start, "end": end})
        
    # Transaction Methods
    
    def get_transaction(self, tx_hash: str) -> Dict:
        """
        Get transaction details by hash
        
        Args:
            tx_hash: The transaction hash to retrieve
            
        Returns:
            Dictionary with transaction details
        """
        return self._get(f"/transactions/{tx_hash}")
        
    def send_transaction(self, sender_address: str, recipient_address: str, 
                        amount: float, private_key: str, fee: Optional[float] = None, 
                        data: Optional[str] = None) -> Dict:
        """
        Submit a transaction to the network
        
        Args:
            sender_address: The sender's wallet address
            recipient_address: The recipient's wallet address
            amount: Amount to send
            private_key: The sender's private key to sign the transaction
            fee: Optional transaction fee
            data: Optional data to include in the transaction
            
        Returns:
            Dictionary with transaction details and status
        """
        tx_data = {
            "sender_address": sender_address,
            "recipient_address": recipient_address,
            "amount": amount,
            "private_key": private_key
        }
        
        if fee is not None:
            tx_data["fee"] = fee
            
        if data is not None:
            tx_data["data"] = data
            
        return self._post("/transactions/send", tx_data)
        
    def get_mempool_transactions(self, limit: int = 100) -> Dict:
        """
        Get pending transactions in the mempool
        
        Args:
            limit: Maximum number of transactions to retrieve
            
        Returns:
            Dictionary with transaction list and count
        """
        return self._get("/transactions/mempool", params={"limit": limit})
        
    # Account/Address Methods
    
    def get_account_info(self, address: str) -> Dict:
        """
        Get account information and balance
        
        Args:
            address: The wallet address to query
            
        Returns:
            Dictionary with account details and balance
        """
        return self._get(f"/accounts/{address}")
        
    def get_account_transactions(self, address: str, limit: int = 50, offset: int = 0) -> Dict:
        """
        Get transaction history for an account
        
        Args:
            address: The wallet address to query
            limit: Maximum number of transactions to retrieve
            offset: Offset for pagination
            
        Returns:
            Dictionary with transaction list and count
        """
        params = {
            "limit": limit,
            "offset": offset
        }
        return self._get(f"/accounts/{address}/transactions", params=params)
        
    def get_top_accounts(self, limit: int = 100) -> Dict:
        """
        Get top accounts by balance
        
        Args:
            limit: Maximum number of accounts to retrieve
            
        Returns:
            Dictionary with account list and count
        """
        return self._get("/accounts/top", params={"limit": limit})
        
    # Wallet Management Methods (requires API key)
    
    def create_wallet(self, name: str, passphrase: Optional[str] = None) -> Dict:
        """
        Create a new wallet
        
        Args:
            name: The name for the new wallet
            passphrase: Optional passphrase to secure the wallet
            
        Returns:
            Dictionary with new wallet details
        """
        wallet_data = {
            "name": name
        }
        
        if passphrase is not None:
            wallet_data["passphrase"] = passphrase
            
        return self._post("/wallet/create", wallet_data)
        
    def import_wallet(self) -> Dict:
        """
        Import an existing wallet from private key
        
        Returns:
            Dictionary with imported wallet details
        """
        return self._post("/wallet/import", {})
        
    # Network Status Methods
    
    def get_peers(self) -> Dict:
        """
        Get information about connected peers
        
        Returns:
            Dictionary with peer list and count
        """
        return self._get("/network/peers")
        
    def get_network_stats(self) -> Dict:
        """
        Get network statistics
        
        Returns:
            Dictionary with network statistics
        """
        return self._get("/network/stats")
        
    # Mining Methods
    
    def get_mining_info(self) -> Dict:
        """
        Get current mining information
        
        Returns:
            Dictionary with mining details
        """
        return self._get("/mining/info")
        
    def submit_block(self) -> Dict:
        """
        Submit a mined block
        
        Returns:
            Dictionary with submission result
        """
        return self._post("/mining/submit", {})
        
    # Utility Methods
    
    def validate_address(self, address: str) -> Dict:
        """
        Validate a wallet address
        
        Args:
            address: The address to validate
            
        Returns:
            Dictionary with validation result
        """
        return self._get(f"/utils/validate-address/{address}")
        
    def verify_signature(self, message: str, signature: str, public_key: str) -> Dict:
        """
        Verify a cryptographic signature
        
        Args:
            message: The message that was signed
            signature: The signature to verify
            public_key: The public key to use for verification
            
        Returns:
            Dictionary with verification result
        """
        data = {
            "message": message,
            "signature": signature,
            "public_key": public_key
        }
        return self._post("/utils/verify-signature", data)
        
    # API Key Management Methods (admin only)
    
    def create_api_key(self, admin_key: str) -> Dict:
        """
        Create a new API key (admin only)
        
        Args:
            admin_key: The admin master key
            
        Returns:
            Dictionary with new API key details
        """
        headers = {"X-Admin-Key": admin_key}
        response = self.session.post(f"{self.base_url}/admin/api-keys/create", headers=headers)
        response.raise_for_status()
        return response.json()
        
    def delete_api_key(self, api_key: str, admin_key: str) -> Dict:
        """
        Delete an API key (admin only)
        
        Args:
            api_key: The API key to delete
            admin_key: The admin master key
            
        Returns:
            Dictionary with deletion result
        """
        headers = {"X-Admin-Key": admin_key}
        response = self.session.delete(f"{self.base_url}/admin/api-keys/{api_key}", headers=headers)
        response.raise_for_status()
        return response.json()


def print_json(data: Dict) -> None:
    """Helper function to pretty print JSON data"""
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Qbitcoin API Client')
    parser.add_argument('-H', '--host', default='localhost', help='Host address (default: localhost)')
    parser.add_argument('-p', '--port', type=int, default=9568, help='Port number (default: 8000)')
    parser.add_argument('-k', '--api-key', help='API key for authenticated endpoints')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # General info commands
    subparsers.add_parser('info', help='Get basic node information')
    subparsers.add_parser('status', help='Get blockchain status')
    
    # Block commands
    latest_blocks_parser = subparsers.add_parser('latest-blocks', help='Get latest blocks')
    latest_blocks_parser.add_argument('-l', '--limit', type=int, default=10, help='Number of blocks (default: 10)')
    
    block_height_parser = subparsers.add_parser('block-height', help='Get block by height')
    block_height_parser.add_argument('height', type=int, help='Block height')
    
    block_hash_parser = subparsers.add_parser('block-hash', help='Get block by hash')
    block_hash_parser.add_argument('hash', help='Block hash')
    
    block_range_parser = subparsers.add_parser('block-range', help='Get blocks in range')
    block_range_parser.add_argument('start', type=int, help='Start height')
    block_range_parser.add_argument('end', type=int, help='End height')
    
    # Transaction commands
    tx_parser = subparsers.add_parser('transaction', help='Get transaction details')
    tx_parser.add_argument('hash', help='Transaction hash')
    
    send_tx_parser = subparsers.add_parser('send-transaction', help='Send a transaction')
    send_tx_parser.add_argument('--sender', required=True, help='Sender address')
    send_tx_parser.add_argument('--recipient', required=True, help='Recipient address')
    send_tx_parser.add_argument('--amount', type=float, required=True, help='Amount to send')
    send_tx_parser.add_argument('--private-key', required=True, help='Private key to sign transaction')
    send_tx_parser.add_argument('--fee', type=float, help='Transaction fee')
    send_tx_parser.add_argument('--data', help='Optional transaction data')
    
    mempool_parser = subparsers.add_parser('mempool', help='Get pending transactions')
    mempool_parser.add_argument('-l', '--limit', type=int, default=100, help='Number of transactions (default: 100)')
    
    # Account commands
    account_parser = subparsers.add_parser('account', help='Get account info')
    account_parser.add_argument('address', help='Wallet address')
    
    account_tx_parser = subparsers.add_parser('account-transactions', help='Get account transactions')
    account_tx_parser.add_argument('address', help='Wallet address')
    account_tx_parser.add_argument('-l', '--limit', type=int, default=50, help='Number of transactions (default: 50)')
    account_tx_parser.add_argument('-o', '--offset', type=int, default=0, help='Offset for pagination')
    
    top_accounts_parser = subparsers.add_parser('top-accounts', help='Get top accounts by balance')
    top_accounts_parser.add_argument('-l', '--limit', type=int, default=100, help='Number of accounts (default: 100)')
    
    # Wallet commands
    create_wallet_parser = subparsers.add_parser('create-wallet', help='Create a new wallet')
    create_wallet_parser.add_argument('name', help='Wallet name')
    create_wallet_parser.add_argument('--passphrase', help='Optional passphrase')
    
    # Network commands
    subparsers.add_parser('peers', help='Get connected peers')
    subparsers.add_parser('network-stats', help='Get network statistics')
    
    # Mining commands
    subparsers.add_parser('mining-info', help='Get mining information')
    
    # Utility commands
    validate_address_parser = subparsers.add_parser('validate-address', help='Validate an address')
    validate_address_parser.add_argument('address', help='Address to validate')
    
    verify_signature_parser = subparsers.add_parser('verify-signature', help='Verify a signature')
    verify_signature_parser.add_argument('message', help='Message that was signed')
    verify_signature_parser.add_argument('signature', help='Signature to verify')
    verify_signature_parser.add_argument('public_key', help='Public key for verification')
    
    args = parser.parse_args()
    
    # Initialize the client
    client = QbitcoinAPIClient(host=args.host, port=args.port, api_key=args.api_key)
    
    try:
        # Handle commands
        if args.command == 'info':
            print_json(client.get_node_info())
            
        elif args.command == 'status':
            print_json(client.get_blockchain_status())
            
        elif args.command == 'latest-blocks':
            print_json(client.get_latest_blocks(limit=args.limit))
            
        elif args.command == 'block-height':
            print_json(client.get_block_by_height(args.height))
            
        elif args.command == 'block-hash':
            print_json(client.get_block_by_hash(args.hash))
            
        elif args.command == 'block-range':
            print_json(client.get_blocks_in_range(args.start, args.end))
            
        elif args.command == 'transaction':
            print_json(client.get_transaction(args.hash))
            
        elif args.command == 'send-transaction':
            print_json(client.send_transaction(
                sender_address=args.sender,
                recipient_address=args.recipient,
                amount=args.amount,
                private_key=args.private_key,
                fee=args.fee,
                data=args.data
            ))
            
        elif args.command == 'mempool':
            print_json(client.get_mempool_transactions(limit=args.limit))
            
        elif args.command == 'account':
            print_json(client.get_account_info(args.address))
            
        elif args.command == 'account-transactions':
            print_json(client.get_account_transactions(
                address=args.address,
                limit=args.limit,
                offset=args.offset
            ))
            
        elif args.command == 'top-accounts':
            print_json(client.get_top_accounts(limit=args.limit))
            
        elif args.command == 'create-wallet':
            print_json(client.create_wallet(
                name=args.name,
                passphrase=args.passphrase
            ))
            
        elif args.command == 'peers':
            print_json(client.get_peers())
            
        elif args.command == 'network-stats':
            print_json(client.get_network_stats())
            
        elif args.command == 'mining-info':
            print_json(client.get_mining_info())
            
        elif args.command == 'validate-address':
            print_json(client.validate_address(args.address))
            
        elif args.command == 'verify-signature':
            print_json(client.verify_signature(
                message=args.message,
                signature=args.signature,
                public_key=args.public_key
            ))
            
        else:
            if not args.command:
                parser.print_help()
            else:
                print(f"Unknown command: {args.command}")
                
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to the Qbitcoin node: {e}")
    except json.JSONDecodeError:
        print("Error parsing response from server")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")