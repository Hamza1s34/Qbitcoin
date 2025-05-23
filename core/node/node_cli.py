
"""
Command Line Interface for Qbitcoin Node

This file implements a CLI for interacting with a running Qbitcoin node,
allowing users to control mining, send transactions, and perform other
node operations from the command line.
"""

import os
import sys
import argparse
import cmd
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import config

# Import node and other components
from core.node.node import Node 
from core.block import Block
from utils.logger import get_logger
from utils.wallet_creator import WalletCreator

# Initialize logger
logger = get_logger("node_cli")

class QbitcoinCLI(cmd.Cmd):
    """
    Interactive CLI for Qbitcoin blockchain node
    
    This class provides an interactive command-line interface for the Qbitcoin node,
    allowing users to manage the node, wallet operations, mining, and more.
    """
    intro = f"""
======================================================
Welcome to Qbitcoin CLI v{config.VERSION}
A quantum-resistant cryptocurrency
======================================================
Type help or ? to list commands.
"""
    prompt = 'qbitcoin> '
    
    def __init__(self, node: Optional[Node] = None, data_dir: Optional[Path] = None):
        """
        Initialize the CLI with an optional Node instance
        
        Args:
            node: Optional Node instance to use
            data_dir: Optional data directory
        """
        super().__init__()
        self.node = node
        self.data_dir = data_dir
        self.wallet_path = None
        self.wallet = None
        
        # Auto-start if no node is provided
        if self.node is None:
            self._connect_to_node()
    
    def _connect_to_node(self) -> bool:
        """
        Start or connect to a node
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create and start a node instance
            self.node = Node(
                chain_id=None,  # Use default chain ID (mainnet)
                p2p_port=config.P2P_PORT,
                api_port=config.API_PORT,
                enable_api=True,
                enable_p2p=True,
                data_dir=self.data_dir,
                disable_signals=True  # CLI will handle signals
            )
            
            if not self.node.start():
                print("Failed to start node.")
                return False
                
            print(f"Qbitcoin node started successfully.")
            return True
            
        except Exception as e:
            print(f"Error starting node: {str(e)}")
            return False

    def _check_node_running(self) -> bool:
        """
        Check if the node is running
        
        Returns:
            True if running, False otherwise
        """
        if not self.node or not self.node.running:
            print("Node is not running. Use 'start' to start the node.")
            return False
        return True
    
    def _check_wallet_loaded(self) -> bool:
        """
        Check if a wallet is loaded
        
        Returns:
            True if wallet is loaded, False otherwise
        """
        if not self.wallet:
            print("No wallet loaded. Use 'wallet open <path>' or 'wallet create <path>' to load a wallet.")
            return False
        return True
    
    def _format_qbc(self, amount: float) -> str:
        """Format amount as QBC with proper precision"""
        return f"{amount:.6f} QBC"
    
    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """
        Parse an amount string into a float
        
        Args:
            amount_str: String representation of amount
            
        Returns:
            Float amount or None if invalid
        """
        try:
            amount = float(amount_str)
            if amount < 0:
                print("Amount cannot be negative.")
                return None
            return amount
        except ValueError:
            print(f"Invalid amount: {amount_str}")
            return None

    # Node commands
    def do_start(self, arg: str) -> None:
        """Start the Qbitcoin node if not already running."""
        if self.node and self.node.running:
            print("Node is already running.")
            return
            
        if self._connect_to_node():
            print("Node started successfully.")
        else:
            print("Failed to start node.")
    
    def do_stop(self, arg: str) -> None:
        """Stop the running Qbitcoin node."""
        if not self._check_node_running():
            return
            
        self.node.shutdown()
        print("Node stopped successfully.")
    
    def do_status(self, arg: str) -> None:
        """Show the current status of the Qbitcoin node."""
        if not self._check_node_running():
            return
            
        status = self.node.get_status()
        
        print("\n=== Node Status ===")
        print(f"Version: {status['version']}")
        print(f"Chain ID: {status['chain_id']}")
        print(f"Running: {'Yes' if status['running'] else 'No'}")
        
        # Format uptime
        uptime = status['uptime']
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f"Uptime: {hours:02}:{minutes:02}:{seconds:02}")
        
        print(f"Blockchain Height: {status.get('blockchain_height', 0)}")
        print(f"Best Block: {status.get('best_block_hash', 'unknown')}")
        print(f"Sync Complete: {'Yes' if status.get('sync_complete', False) else 'No'}")
        print(f"Connected Peers: {status.get('connected_peers', 0)}")
        print(f"Mempool Transactions: {status.get('mempool_transactions', 0)}")
        print(f"Listen Address: {status.get('listen_address', 'N/A')}")
        print(f"API Enabled: {'Yes' if status.get('api_enabled', False) else 'No'}")
        print(f"P2P Enabled: {'Yes' if status.get('p2p_enabled', False) else 'No'}")
        
        # Mining status
        if self.node.mining_running:
            mining_stats = self.node.get_mining_stats()
            print("\n=== Mining Status ===")
            print(f"Mining: {'Running' if mining_stats['mining'] else 'Stopped'}")
            print(f"Algorithm: {mining_stats['algorithm']}")
            print(f"Mining Address: {mining_stats['address']}")
            print(f"Blocks Mined: {mining_stats.get('blocks_found', 0)}")
            print(f"Current Difficulty: {mining_stats['current_difficulty']}")
            print(f"Hash Rate: {mining_stats.get('last_hash_rate', 0):.2f} H/s")
        else:
            print("\nMining: Not Running")
    
    # Wallet commands
    def do_wallet(self, arg: str) -> None:
        """
        Wallet operations: create, open, info, balance
        
        Usage:
            wallet create <path>    - Create a new wallet
            wallet open <path>      - Open an existing wallet
            wallet info             - Show wallet information
            wallet balance          - Show wallet balance
            wallet address          - Show wallet address
        """
        args = arg.split()
        if not args:
            print("Missing wallet command. Use 'help wallet' for usage.")
            return
            
        command = args[0].lower()
        
        if command == "create" and len(args) >= 2:
            wallet_path = " ".join(args[1:])
            self._create_wallet(wallet_path)
        
        elif command == "open" and len(args) >= 2:
            wallet_path = " ".join(args[1:])
            self._open_wallet(wallet_path)
        
        elif command == "info":
            if not self._check_wallet_loaded():
                return
            self._show_wallet_info()
        
        elif command == "balance":
            if not self._check_wallet_loaded():
                return
            self._show_wallet_balance()
        
        elif command == "address":
            if not self._check_wallet_loaded():
                return
            print(f"Wallet Address: {self.wallet.get_address()}")
        
        else:
            print("Invalid wallet command. Use 'help wallet' for usage.")
    
    def _create_wallet(self, wallet_path: str) -> None:
        """Create a new wallet"""
        try:
            # Make sure directory exists
            wallet_dir = os.path.dirname(wallet_path)
            if wallet_dir and not os.path.exists(wallet_dir):
                os.makedirs(wallet_dir)
            
            # Ask for password
            import getpass
            password = getpass.getpass("Enter password for new wallet: ")
            confirm = getpass.getpass("Confirm password: ")
            
            if password != confirm:
                print("Passwords do not match.")
                return
                
            # Create wallet
            creator = WalletCreator()
            self.wallet = creator.create_wallet(password)
            
            # Save wallet to file
            self.wallet.save_to_file(wallet_path)
            self.wallet_path = wallet_path
            
            print(f"New wallet created successfully at {wallet_path}")
            print(f"Address: {self.wallet.get_address()}")
            
        except Exception as e:
            print(f"Error creating wallet: {str(e)}")
    
    def _open_wallet(self, wallet_path: str) -> None:
        """Open an existing wallet"""
        try:
            if not os.path.exists(wallet_path):
                print(f"Wallet file not found: {wallet_path}")
                return
                
            # Ask for password
            import getpass
            password = getpass.getpass("Enter wallet password: ")
            
            # Open wallet
            from utils.wallet_creator import Wallet
            self.wallet = Wallet.load_from_file(wallet_path, password)
            self.wallet_path = wallet_path
            
            print(f"Wallet opened successfully from {wallet_path}")
            print(f"Address: {self.wallet.get_address()}")
            
        except Exception as e:
            print(f"Error opening wallet: {str(e)}")
    
    def _show_wallet_info(self) -> None:
        """Show wallet information"""
        print("\n=== Wallet Information ===")
        print(f"Path: {self.wallet_path}")
        print(f"Address: {self.wallet.get_address()}")
        print(f"Public Key: {self.wallet.get_public_key()}")
        
        # Show balance if node is running
        if self._check_node_running():
            self._show_wallet_balance()
    
    def _show_wallet_balance(self) -> None:
        """Show wallet balance"""
        if not self._check_node_running():
            return
            
        address = self.wallet.get_address()
        balance = self.node.blockchain.get_balance(address)
        
        print("\n=== Wallet Balance ===")
        print(f"Address: {address}")
        print(f"Total Balance: {self._format_qbc(balance)}")
        
        # Get pending transactions if any
        pending_balance = 0.0
        if self.node.mempool:
            # Fixed: Using the correct method name get_transactions_by_address instead of get_transactions_for_address
            transactions = self.node.mempool.get_transactions_by_address(address)
            if transactions:
                for tx in transactions:
                    # Calculate net effect on wallet
                    outgoing = sum(output["amount"] for output in tx.outputs 
                                  if "address" in output and output["address"] != address)
                    incoming = sum(output["amount"] for output in tx.outputs 
                                  if "address" in output and output["address"] == address)
                    pending_balance += (incoming - outgoing)
        
        if pending_balance != 0:
            print(f"Pending Balance: {self._format_qbc(pending_balance)}")
            print(f"Available Balance: {self._format_qbc(balance + pending_balance)}")
    
    def do_balance(self, arg: str) -> None:
        """
        Check the balance of any address
        
        Usage: balance <address>
        """
        if not self._check_node_running():
            return
            
        address = arg.strip()
        if not address:
            print("Usage: balance <address>")
            return
            
        try:
            # Get balance from blockchain
            balance = self.node.blockchain.get_balance(address)
            
            print(f"\n=== Address Balance ===")
            print(f"Address: {address}")
            print(f"Balance: {self._format_qbc(balance)}")
            
            # Get pending transactions if any
            pending_balance = 0.0
            if self.node.mempool:
                # Fixed: Using the correct method name get_transactions_by_address instead of get_transactions_for_address
                transactions = self.node.mempool.get_transactions_by_address(address)
                if transactions:
                    for tx in transactions:
                        # Calculate net effect on wallet
                        outgoing = sum(output["amount"] for output in tx.outputs 
                                      if "address" in output and output["address"] != address)
                        incoming = sum(output["amount"] for output in tx.outputs 
                                      if "address" in output and output["address"] == address)
                        pending_balance += (incoming - outgoing)
            
            if pending_balance != 0:
                print(f"Pending Balance: {self._format_qbc(pending_balance)}")
                print(f"Available Balance: {self._format_qbc(balance + pending_balance)}")
        
        except Exception as e:
            print(f"Error getting balance: {str(e)}")
    
    # Mining commands
    def do_startmining(self, arg: str) -> None:
        """
        Start mining blocks
        
        Usage: startmining [address]
        If address is not provided, the address from the loaded wallet will be used.
        """
        if not self._check_node_running():
            return
            
        # Get mining address
        mining_address = arg.strip()
        if not mining_address:
            if not self._check_wallet_loaded():
                return
            mining_address = self.wallet.get_address()
        
        # Start mining
        if self.node.start_mining(mining_address):
            print(f"Mining started to address {mining_address}")
        else:
            print("Failed to start mining.")
    
    def do_stopmining(self, arg: str) -> None:
        """Stop the mining process."""
        if not self._check_node_running():
            return
            
        if self.node.stop_mining():
            print("Mining stopped.")
        else:
            print("Mining is not running.")
    
    def do_mininginfo(self, arg: str) -> None:
        """Show mining information and statistics."""
        if not self._check_node_running():
            return
            
        mining_stats = self.node.get_mining_stats()
        
        print("\n=== Mining Status ===")
        print(f"Mining: {'Running' if mining_stats['mining'] else 'Stopped'}")
        print(f"Algorithm: {mining_stats['algorithm']}")
        print(f"Mining Address: {mining_stats['address'] or 'Not set'}")
        print(f"Current Difficulty: {mining_stats['current_difficulty']}")
        print(f"Blocks Mined: {mining_stats.get('blocks_found', 0)}")
        
        if mining_stats['mining']:
            print(f"Hash Rate: {mining_stats.get('last_hash_rate', 0):.2f} H/s")
            print(f"Total Hashes: {mining_stats.get('total_hashes', 0)}")
    
    # Transaction commands
    def do_send(self, arg: str) -> None:
        """
        Send a transaction
        
        Usage: send <address> <amount> [fee]
        If fee is not provided, the minimum fee will be used.
        """
        if not self._check_node_running() or not self._check_wallet_loaded():
            return
            
        args = arg.split()
        if len(args) < 2:
            print("Usage: send <address> <amount> [fee]")
            return
            
        recipient = args[0]
        amount = self._parse_amount(args[1])
        if amount is None:
            return
            
        # Parse optional fee
        fee = config.MIN_RELAY_FEE
        if len(args) > 2:
            parsed_fee = self._parse_amount(args[2])
            if parsed_fee is None:
                return
            fee = parsed_fee
        
        try:
            # Create transaction
            tx = self.wallet.create_transaction(recipient, amount, fee)
            
            # Send transaction
            response = self.node.submit_transaction(tx.to_dict())
            
            if response["success"]:
                print(f"Transaction sent successfully!")
                print(f"Transaction ID: {response['tx_hash']}")
                print(f"Amount: {self._format_qbc(amount)}")
                print(f"Fee: {self._format_qbc(fee)}")
                print(f"Recipient: {recipient}")
            else:
                print(f"Failed to send transaction: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"Error sending transaction: {str(e)}")
    
    def do_txstatus(self, arg: str) -> None:
        """
        Get transaction status
        
        Usage: txstatus <transaction_id>
        """
        if not self._check_node_running():
            return
            
        tx_id = arg.strip()
        if not tx_id:
            print("Usage: txstatus <transaction_id>")
            return
        

        try:    
            # Check mempool first
            mempool_tx = None
            if self.node.mempool:
                mempool_tx = self.node.mempool.get_transaction(tx_id)
            
            if mempool_tx:
                print(f"\nTransaction {tx_id} is in the mempool (pending)")
                if hasattr(mempool_tx, 'to_dict'):
                    self._print_transaction_details(mempool_tx.to_dict())
                else:
                    self._print_transaction_details(mempool_tx)
                return
                
            # Check blockchain - we need to search through blocks to find the transaction
            # since there's no direct method to get a transaction by hash
            found = False
            
            # First try searching in the most recent blocks (more efficient)
            current_height = self.node.blockchain.current_height
            search_range = min(100, current_height + 1)  # Limit to last 100 blocks
            
            for height in range(current_height, current_height - search_range, -1):
                block = self.node.blockchain.get_block_by_height(height)
                if not block:
                    continue
                    
                for tx in block.transactions:
                    tx_hash = None
                    if hasattr(tx, 'hash'):
                        tx_hash = tx.hash
                    elif isinstance(tx, dict) and 'hash' in tx:
                        tx_hash = tx['hash']
                    
                    if tx_hash == tx_id:
                        print(f"\nTransaction {tx_id} is confirmed in the blockchain")
                        print(f"Included in block at height: {height}")
                        
                        # Convert to dict if needed
                        tx_dict = tx if isinstance(tx, dict) else (tx.to_dict() if hasattr(tx, 'to_dict') else tx)
                        self._print_transaction_details(tx_dict)
                        found = True
                        break
                
                if found:
                    break
            
            if not found:
                print(f"Transaction {tx_id} not found in mempool or recent blockchain history.")
        
        except Exception as e:
            print(f"Error checking transaction status: {str(e)}")
    
    def _print_transaction_details(self, tx: Dict[str, Any]) -> None:
        """Print transaction details"""
        print(f"Hash: {tx.get('hash', 'unknown')}")
        print(f"Timestamp: {tx.get('timestamp', 0)}")
        
        # Print inputs
        print("\nInputs:")
        for idx, tx_input in enumerate(tx.get("inputs", [])):
            print(f"  {idx+1}. {tx_input.get('prev_tx', '')}:{tx_input.get('prev_index', 0)} "
                  f"- {self._format_qbc(tx_input.get('amount', 0))}")
        
        # Print outputs
        print("\nOutputs:")
        for idx, output in enumerate(tx.get("outputs", [])):
            print(f"  {idx+1}. {output.get('address', 'unknown')} "
                  f"- {self._format_qbc(output.get('amount', 0))}")
        
        # Print total
        total_out = sum(output.get("amount", 0) for output in tx.get("outputs", []))
        print(f"\nTotal: {self._format_qbc(total_out)}")
    
    def do_txhistory(self, arg: str) -> None:
        """
        Get transaction history for a wallet address
        
        Usage: txhistory <address>
        """
        if not self._check_node_running():
            return
            
        address = arg.strip()
        if not address:
            print("Usage: txhistory <address>")
            return
            
        try:
            # Get transaction history from blockchain
            history = self.node.blockchain.get_transaction_history(address)
            
            if not history:
                print(f"No transaction history found for address: {address}")
                return
            
            print(f"\n=== Transaction History for {address} ===")
            for idx, tx in enumerate(history, 1):
                print(f"\nTransaction {idx}:")
                self._print_transaction_details(tx)
        
        except Exception as e:
            print(f"Error getting transaction history: {str(e)}")
    
    # Blockchain commands
    def do_getblock(self, arg: str) -> None:
        """
        Get block information
        
        Usage: 
          getblock <height> - Get block by height
          getblock <hash>   - Get block by hash
        """
        if not self._check_node_running():
            return
            
        arg = arg.strip()
        if not arg:
            print("Usage: getblock <height|hash>")
            return
            
        block = None
        
        # Check if input is a number (height) or a hash
        try:
            height = int(arg)
            block = self.node.blockchain.get_block_by_height(height)
        except ValueError:
            # Not a number, try as hash
            block = self.node.blockchain.get_block_by_hash(arg)
            
        if block:
            self._print_block_details(block)
        else:
            print(f"Block not found: {arg}")
    
    def _print_block_details(self, block: Block) -> None:
        """Print block details"""
        print("\n=== Block Details ===")
        print(f"Height: {block.height}")
        print(f"Hash: {block.hash}")
        print(f"Previous Hash: {block.prev_hash}")
        print(f"Merkle Root: {block.merkle_root}")
        print(f"Timestamp: {block.timestamp} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(block.timestamp))})")
        print(f"Difficulty: {block.difficulty}")
        print(f"Nonce: {block.nonce}")
        print(f"Version: {block.version}")
        # Fixed: Use json serialization instead of non-existent serialize method
        print(f"Size: {len(json.dumps(block.to_dict()).encode())} bytes")
        print(f"Transaction Count: {len(block.transactions)}")
        
        # Display transaction IDs
        if block.transactions:
            print("\nTransactions:")
            for idx, tx in enumerate(block.transactions):
                # Handle both Transaction objects and dictionaries
                if hasattr(tx, 'hash'):
                    # It's a Transaction object
                    tx_hash = tx.hash
                elif isinstance(tx, dict):
                    # It's a dictionary
                    tx_hash = tx.get("hash", "unknown")
                else:
                    # Try to convert to dict if it has to_dict method
                    if hasattr(tx, 'to_dict'):
                        tx_dict = tx.to_dict()
                        tx_hash = tx_dict.get("hash", "unknown")
                    else:
                        tx_hash = "unknown"
                        
                print(f"  {idx+1}. {tx_hash}")
    
    def do_getdifficulty(self, arg: str) -> None:
        """Get the current blockchain difficulty."""
        if not self._check_node_running():
            return
            
        current_difficulty = self.node.blockchain.get_next_block_difficulty(log_info=True)
        
        print(f"Current Difficulty: {current_difficulty}")
        
        # Get difficulty adjustment info
        from core.consensus.difficulty_adjuster import get_difficulty_info
        diff_info = get_difficulty_info(self.node.blockchain, log_info=True)
        
        print(f"Next Adjustment: {diff_info['next_adjustment_height']} blocks "
              f"({diff_info['blocks_until_adjustment']} blocks remaining)")
        
        if diff_info['estimated_adjustment_percent'] != 0:
            direction = "increase" if diff_info['estimated_adjustment_percent'] > 0 else "decrease"
            print(f"Estimated adjustment: {abs(diff_info['estimated_adjustment_percent']):.2f}% {direction}")
            print(f"Estimated next difficulty: {diff_info['next_difficulty']}")
    
    # Network commands
    def do_peers(self, arg: str) -> None:
        """Show information about connected peers."""
        if not self._check_node_running() or not self.node.p2p_network:
            print("P2P networking is not enabled.")
            return
            
        peers = self.node.p2p_network.get_connected_peers()
        
        if not peers:
            print("No connected peers.")
            return
            
        print(f"\n=== Connected Peers: {len(peers)} ===")
        for idx, peer in enumerate(peers, 1):
            print(f"{idx}. {peer['host']}:{peer['port']} - Height: {peer.get('height', 'unknown')}, "
                  f"Version: {peer.get('version', 'unknown')}")
    
    def do_addpeer(self, arg: str) -> None:
        """
        Add a peer to the network
        
        Usage: addpeer <host> [port]
        If port is not specified, the default P2P port will be used.
        """
        if not self._check_node_running() or not self.node.p2p_network:
            print("P2P networking is not enabled.")
            return
            
        args = arg.split()
        if not args:
            print("Usage: addpeer <host> [port]")
            return
            
        host = args[0]
        port = config.P2P_PORT
        
        if len(args) > 1:
            try:
                port = int(args[1])
            except ValueError:
                print(f"Invalid port: {args[1]}")
                return
                
        success = self.node.p2p_network.connect_to_peer(host, port)
        if success:
            print(f"Successfully connected to {host}:{port}")
        else:
            print(f"Failed to connect to {host}:{port}")
    
    # Exit command
    def do_exit(self, arg: str) -> bool:
        """Exit the CLI."""
        if self.node and self.node.running:
            print("Shutting down node...")
            self.node.shutdown()
            
        print("Goodbye!")
        return True
    
    def do_quit(self, arg: str) -> bool:
        """Exit the CLI."""
        return self.do_exit(arg)
    
    def do_getpublickey(self, arg: str) -> None:
        """
        Get the public key associated with an address from the blockchain
        
        Usage: getpublickey <address>
        """
        if not self._check_node_running():
            return
            
        address = arg.strip()
        if not address:
            print("Usage: getpublickey <address>")
            return
            
        try:
            # First get account info from the database to find the block containing the public key
            account_info = self.node.blockchain.get_account_info(address)
            
            if not account_info:
                print(f"Address {address} not found in the blockchain.")
                return
                
            # Get the block number that contains the public key
            pubkey_block = account_info.get('pubkey_block')
            
            if not pubkey_block:
                print(f"No public key reference found for address {address}.")
                print("This address may not have sent any transactions yet.")
                return
                
            # Directly access the specific block that contains the public key
            print(f"Retrieving public key from block #{pubkey_block}...")
            block = self.node.blockchain.get_block_by_height(pubkey_block)
            
            if not block:
                print(f"Error: Block #{pubkey_block} not found in the blockchain.")
                return
                
            # Find the transaction in this block that contains the public key for this address
            public_key = None
            for tx in block.transactions:
                # Convert to dict if needed
                tx_dict = tx if isinstance(tx, dict) else (tx.to_dict() if hasattr(tx, 'to_dict') else tx)
                
                # Check if this transaction has inputs from the address (sender)
                address_is_sender = False
                for tx_input in tx_dict.get('inputs', []):
                    if tx_input.get('address') == address:
                        address_is_sender = True
                        break
                        
                # If this is a transaction from this address and it has a public key
                if address_is_sender and 'public_key' in tx_dict and tx_dict['public_key']:
                    public_key = tx_dict['public_key']
                    tx_hash = tx_dict.get('hash', 'unknown')
                    print(f"Found public key in transaction: {tx_hash}")
                    break
            
            # Display the result
            if public_key:
                print(f"\n=== Public Key for {address} ===")
                print(f"Public Key (hex): {public_key}")
                
                # Also show the length of the public key
                try:
                    # Try to treat it as hex
                    try:
                        public_key_bytes = bytes.fromhex(public_key)
                        print(f"Public Key Length: {len(public_key_bytes)} bytes (hex format)")
                    except ValueError:
                        # If not valid hex, try base64
                        try:
                            import base64
                            # Try with different padding adjustments
                            padded_key = public_key
                            # Add padding if needed
                            while len(padded_key) % 4 != 0:
                                padded_key += '='
                            public_key_bytes = base64.b64decode(padded_key)
                            print(f"Public Key Length: {len(public_key_bytes)} bytes (base64 format)")
                        except Exception:
                            # If not valid base64 either
                            print(f"Public Key Length: {len(public_key)} characters (unknown format)")
                except Exception as e:
                    print(f"Public Key Length: {len(public_key)} characters")
                    print(f"Note: Could not determine format: {str(e)}")
            else:
                print(f"Public key for address {address} not found in block #{pubkey_block}.")
                print("This might be due to a database reference error.")
        
        except Exception as e:
            print(f"Error retrieving public key: {str(e)}")
            import traceback
            traceback.print_exc()

    # Mempool command
    def do_mempool(self, arg: str) -> None:
        """
        Show detailed information about transactions in the mempool
        
        Usage:
            mempool                 - Show summary statistics
            mempool list            - List all transactions in the mempool
            mempool tx <txid>       - Show detailed info for a specific transaction
            mempool address <addr>  - Show mempool transactions for a specific address
        """
        if not self._check_node_running():
            return
            
        if not self.node.mempool:
            print("Mempool is not available.")
            return
        
        args = arg.split()
        command = args[0].lower() if args else ""
        
        # Mempool summary (default)
        if not command:
            stats = self.node.mempool.get_stats()
            print("\n=== Mempool Summary ===")
            print(f"Transactions: {stats['tx_count']}")
            print(f"Total Size: {stats['size_bytes']} bytes ({stats['size_mb']:.2f} MB)")
            print(f"Total Fees: {self._format_qbc(stats['total_fees'])}")
            print(f"Average Fee per KB: {self._format_qbc(stats['avg_fee_per_kb']/1000)} per KB")
            print(f"Orphan Transactions: {stats['orphan_tx_count']}")
            
            # Show fee distribution if there are transactions
            if stats['tx_count'] > 0:
                transactions = self.node.mempool.get_transactions(limit=1000)  # Get up to 1000 transactions
                if transactions:
                    # Calculate fee ranges
                    fee_ranges = {
                        "0-1 sat/byte": 0,
                        "1-10 sat/byte": 0,
                        "10-50 sat/byte": 0,
                        "50-100 sat/byte": 0,
                        "100+ sat/byte": 0
                    }
                    
                    for tx in transactions:
                        # Convert dict to Transaction object if needed
                        if isinstance(tx, dict):
                            from core.transaction import Transaction
                            tx_obj = Transaction.from_dict(tx)
                        else:
                            tx_obj = tx
                            
                        size = len(json.dumps(tx_obj.to_dict()).encode())
                        if size > 0:
                            fee_rate = (tx_obj.fee * 100000000) / size  # satoshis per byte
                            
                            if fee_rate < 1:
                                fee_ranges["0-1 sat/byte"] += 1
                            elif fee_rate < 10:
                                fee_ranges["1-10 sat/byte"] += 1
                            elif fee_rate < 50:
                                fee_ranges["10-50 sat/byte"] += 1
                            elif fee_rate < 100:
                                fee_ranges["50-100 sat/byte"] += 1
                            else:
                                fee_ranges["100+ sat/byte"] += 1
                    
                    print("\n=== Fee Distribution ===")
                    for range_name, count in fee_ranges.items():
                        if count > 0:
                            percent = (count / len(transactions)) * 100
                            print(f"{range_name}: {count} transactions ({percent:.1f}%)")
        
        # List all transactions
        elif command == "list":
            limit = 20  # Default limit
            if len(args) > 1:
                try:
                    limit = int(args[1])
                except ValueError:
                    pass
                
            transactions = self.node.mempool.get_transactions(limit=limit)
            if not transactions:
                print("No transactions in mempool.")
                return
                
            print(f"\n=== Mempool Transactions (showing {len(transactions)}) ===")
            for idx, tx in enumerate(transactions, 1):
                if isinstance(tx, dict):
                    tx_hash = tx.get('hash', 'unknown')
                    tx_fee = tx.get('fee', 0)
                    tx_size = len(json.dumps(tx).encode())
                else:
                    tx_hash = tx.hash if hasattr(tx, 'hash') else 'unknown'
                    tx_fee = tx.fee if hasattr(tx, 'fee') else 0
                    tx_size = len(json.dumps(tx.to_dict() if hasattr(tx, 'to_dict') else {}).encode())
                
                # Calculate fee rate
                fee_rate = (tx_fee * 100000000) / tx_size if tx_size > 0 else 0  # satoshis per byte
                
                print(f"{idx}. {tx_hash[:16]}... | Size: {tx_size} bytes | " +
                      f"Fee: {self._format_qbc(tx_fee)} ({fee_rate:.2f} sat/byte)")
        
        # Show detailed information for a specific transaction
        elif command == "tx" and len(args) > 1:
            tx_id = args[1]
            tx = self.node.mempool.get_transaction(tx_id)
            
            if not tx:
                print(f"Transaction {tx_id} not found in mempool.")
                return
                
            self._print_mempool_tx_details(tx)
        
        # Show transactions for a specific address
        elif command == "address" and len(args) > 1:
            address = args[1]
            transactions = self.node.mempool.get_transactions_by_address(address)
            
            if not transactions:
                print(f"No mempool transactions found for address {address}.")
                return
                
            print(f"\n=== Mempool Transactions for {address} ===")
            print(f"Found {len(transactions)} transactions")
            
            for idx, tx in enumerate(transactions, 1):
                print(f"\nTransaction {idx}:")
                self._print_mempool_tx_details(tx)
        
        else:
            print("Usage:")
            print("  mempool                 - Show summary statistics")
            print("  mempool list [limit]    - List transactions in the mempool")
            print("  mempool tx <txid>       - Show detailed info for a transaction")
            print("  mempool address <addr>  - Show transactions for an address")
    
    def _print_mempool_tx_details(self, tx) -> None:
        """Print detailed information about a transaction in the mempool"""
        # Convert to dict if it's a Transaction object
        if not isinstance(tx, dict) and hasattr(tx, 'to_dict'):
            tx_dict = tx.to_dict()
        else:
            tx_dict = tx if isinstance(tx, dict) else {}
            
        # Get transaction in its original form for accurate size calculations
        tx_obj = tx if not isinstance(tx, dict) else None
        
        print("\n=== Transaction Details ===")
        tx_hash = tx_dict.get('hash', getattr(tx, 'hash', 'unknown'))
        print(f"Transaction ID: {tx_hash}")
        print(f"Timestamp: {tx_dict.get('timestamp', getattr(tx, 'timestamp', 0))}")
        
        # Calculate sizes
        if tx_obj:
            tx_json = json.dumps(tx_obj.to_dict())
        else:
            tx_json = json.dumps(tx_dict)
            
        tx_size = len(tx_json.encode())
        print(f"Total Size: {tx_size} bytes")
        
        # Try to calculate signature size
        signature = tx_dict.get('signature', getattr(tx, 'signature', None))
        if signature:
            if isinstance(signature, str):
                try:
                    # Try to decode hex
                    sig_bytes = bytes.fromhex(signature)
                    sig_size = len(sig_bytes)
                except ValueError:
                    # If not hex, just use string length
                    sig_size = len(signature)
            else:
                # If it's bytes or another format, get its string representation
                sig_size = len(str(signature))
                
            print(f"Signature Size: {sig_size} bytes ({(sig_size/tx_size)*100:.1f}% of tx)")
        
        # Fee information
        fee = tx_dict.get('fee', getattr(tx, 'fee', 0))
        print(f"Fee: {self._format_qbc(fee)}")
        
        if tx_size > 0:
            fee_rate = (fee * 100000000) / tx_size  # satoshis per byte
            print(f"Fee Rate: {fee_rate:.2f} satoshis/byte")
        
        # Public key information
        public_key = tx_dict.get('public_key', getattr(tx, 'public_key', None))
        if public_key:
            try:
                if isinstance(public_key, str):
                    # Try to decode hex
                    try:
                        pk_bytes = bytes.fromhex(public_key)
                        pk_size = len(pk_bytes)
                    except ValueError:
                        pk_size = len(public_key)
                else:
                    pk_size = len(str(public_key))
                    
                print(f"Public Key Size: {pk_size} bytes")
            except Exception:
                print(f"Public Key: Present (size unknown)")
        
        # Sender information
        sender_addresses = set()
        for tx_input in tx_dict.get('inputs', getattr(tx, 'inputs', [])):
            if isinstance(tx_input, dict) and 'address' in tx_input:
                sender_addresses.add(tx_input['address'])
        
        # For each sender address, try to find their public key block
        if sender_addresses and self.node.blockchain:
            print("\n=== Sender Information ===")
            for sender in sender_addresses:
                print(f"Sender Address: {sender}")
                
                # Try to get account info to find public key block
                try:
                    account_info = self.node.blockchain.get_account_info(sender)
                    if account_info:
                        if 'pubkey_block' in account_info:
                            pubkey_block = account_info['pubkey_block']
                            print(f"  Public Key Block: {pubkey_block}")
                            
                            # Try to get the actual public key from the block
                            pk_block = self.node.blockchain.get_block_by_height(pubkey_block)
                            if pk_block:
                                print(f"  Public Key First Seen: Block #{pubkey_block} " +
                                      f"({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(pk_block.timestamp))})")
                        
                        # Show balance
                        if 'balance' in account_info:
                            print(f"  Current Balance: {self._format_qbc(account_info['balance'])}")
                        
                        # Show transaction count
                        if 'tx_count' in account_info:
                            print(f"  Total Transactions: {account_info['tx_count']}")
                    else:
                        print(f"  No blockchain records found for this address")
                except Exception as e:
                    print(f"  Error retrieving sender info: {str(e)}")
        
        # Input details
        print("\n=== Inputs ===")
        total_in = 0
        for idx, tx_input in enumerate(tx_dict.get('inputs', getattr(tx, 'inputs', [])), 1):
            if isinstance(tx_input, dict):
                amount = tx_input.get('amount', 0)
                address = tx_input.get('address', 'unknown')
                prev_tx = tx_input.get('prev_tx', '')
                prev_index = tx_input.get('prev_index', 0)
                total_in += amount
                
                # Format the input line
                input_desc = f"  {idx}. {address}"
                if prev_tx:
                    input_desc += f" - {prev_tx[:8]}...:{prev_index}"
                input_desc += f" - {self._format_qbc(amount)}"
                print(input_desc)
        
        # Output details
        print("\n=== Outputs ===")
        total_out = 0
        for idx, output in enumerate(tx_dict.get('outputs', getattr(tx, 'outputs', [])), 1):
            if isinstance(output, dict):
                amount = output.get('amount', 0)
                address = output.get('address', 'unknown')
                total_out += amount
                print(f"  {idx}. {address} - {self._format_qbc(amount)}")
        
        # Data/message if present
        if 'data' in tx_dict or hasattr(tx, 'data'):
            data = tx_dict.get('data', getattr(tx, 'data', None))
            if data:
                print(f"\nTransaction Data: {data}")
        
        # Transaction totals
        print(f"\nTotal Input: {self._format_qbc(total_in)}")
        print(f"Total Output: {self._format_qbc(total_out)}")
        print(f"Fee: {self._format_qbc(fee)}")
        
        # Time in mempool
        received_time = 0
        if self.node.mempool and hasattr(self.node.mempool, 'tx_metadata'):
            metadata = self.node.mempool.tx_metadata.get(tx_hash, {})
            received_time = metadata.get('received_time', 0)
            
        if received_time > 0:
            current_time = int(time.time())
            time_in_pool = current_time - received_time
            if time_in_pool < 60:
                time_str = f"{time_in_pool} seconds"
            elif time_in_pool < 3600:
                time_str = f"{time_in_pool // 60} minutes, {time_in_pool % 60} seconds"
            else:
                hours = time_in_pool // 3600
                minutes = (time_in_pool % 3600) // 60
                time_str = f"{hours} hours, {minutes} minutes"
                
            print(f"\nTime in Mempool: {time_str}")
            print(f"Received: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(received_time))}")


def run_cli():
    """Run the Qbitcoin CLI"""
    parser = argparse.ArgumentParser(description="Qbitcoin Command Line Interface")
    parser.add_argument("--p2p-port", type=int, help=f"P2P port (default: {config.P2P_PORT})")
    parser.add_argument("--api-port", type=int, help=f"API port (default: {config.API_PORT})")
    parser.add_argument("--testnet", action="store_true", help="Use testnet instead of mainnet")
    parser.add_argument("--data-dir", type=str, help="Custom data directory")
    parser.add_argument("--wallet", type=str, help="Path to wallet file")
    
    args = parser.parse_args()
    
    # Set chain ID based on network selection
    chain_id = "qbitcoin-testnet-v1" if args.testnet else None
    
    # Create data directory path if specified
    data_dir = Path(args.data_dir) if args.data_dir else None
    
    try:
        # Create CLI
        cli = QbitcoinCLI(data_dir=data_dir)
        
        # Open wallet if specified
        if args.wallet:
            cli.do_wallet(f"open {args.wallet}")
        
        # Start the CLI
        cli.cmdloop()
        
    except KeyboardInterrupt:
        print("\nExiting...")
        if cli.node and cli.node.running:
            cli.node.shutdown()
    
    except Exception as e:
        logger.error(f"Error in CLI: {str(e)}")
        print(f"An error occurred: {str(e)}")
        if cli.node and cli.node.running:
            cli.node.shutdown()


if __name__ == "__main__":
    run_cli()

