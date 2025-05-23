#!/usr/bin/env python3
"""
Full Node Implementation for Qbitcoin

This file implements the Node class which orchestrates all components of the Qbitcoin blockchain:
- Blockchain data management
- Memory pool for pending transactions
- P2P network communication
- API server for external interactions
- Wallet management
"""

import os
import sys
import time
import threading
import signal
import socket
import struct
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import config

# Import blockchain components
from core.blockchain import Blockchain
from core.transaction import Transaction
from core.mempool import Mempool
from core.network.p2p import P2PNetwork
from core.network.api import  create_api_server
from core.network.sync import BlockchainSynchronizer
from utils.logger import get_logger

# Initialize logger
logger = get_logger("node")

class Node:
    """
    Qbitcoin Full Node Implementation
    
    This class orchestrates all components of the Qbitcoin blockchain node,
    providing a complete, standalone blockchain node implementation.
    """
    
    def __init__(self, chain_id: Optional[str] = None, 
                 listen_address: str = "0.0.0.0",
                 p2p_port: Optional[int] = None,
                 api_port: Optional[int] = None,
                 max_peers: Optional[int] = None,
                 external_ip: Optional[str] = None,
                 enable_api: bool = True,
                 enable_p2p: bool = True,
                 data_dir: Optional[Path] = None,
                 disable_signals: bool = False):
        """
        Initialize the full node
        
        Args:
            chain_id: Optional chain ID (for testnet or regtest)
            listen_address: IP address to listen on (0.0.0.0 for all interfaces)
            p2p_port: Port for P2P communication
            api_port: Port for API server
            max_peers: Maximum number of peers to connect to
            external_ip: External IP address of this node
            enable_api: Whether to enable the API server
            enable_p2p: Whether to enable P2P networking
            data_dir: Optional custom data directory
            disable_signals: Whether to disable signal handlers (for use in non-main threads)
        """
        self.chain_id = chain_id or config.BLOCKCHAIN_ID
        self.listen_address = listen_address
        self.p2p_port = p2p_port or config.P2P_PORT
        self.api_port = api_port or config.API_PORT
        self.max_peers = max_peers or config.MAX_PEERS
        self.external_ip = external_ip
        self.enable_api = enable_api
        self.enable_p2p = enable_p2p
        self.disable_signals = disable_signals
        
        # Override data directory if specified
        if data_dir:
            config.DATA_DIR = data_dir
            config.CHAIN_DATA_DIR = data_dir / "chain"
        
        # Node state
        self.running = False
        self.sync_complete = False
        self.startup_time = 0
        
        # Components (initialized in start method)
        self.blockchain = None
        self.mempool = None
        self.p2p_network = None
        self.api_server = None
        self.synchronizer = None
        self.miner = None
        self.mining_running = False
        self.mining_thread = None
        self.mining_address = None
        
        # Threading and synchronization
        self.lock = threading.RLock()
        self.shutdown_event = threading.Event()
        
        logger.info(f"Qbitcoin node initialized with chain ID: {self.chain_id}")
        logger.info(f"Data directory: {config.DATA_DIR}")
        
    def _initialize_components(self):
        """Initialize all node components"""
        logger.info("Initializing blockchain components...")
        
        # Create blockchain instance
        self.blockchain = Blockchain(self.chain_id)
        logger.info(f"Blockchain initialized at height {self.blockchain.current_height}")
        
        # Add a reference to this node in the blockchain
        # This is critical for P2P broadcasting of mined blocks
        self.blockchain.node = self
        logger.info("Added node reference to blockchain for P2P operations")
        
        # Create mempool for pending transactions
        self.mempool = Mempool(self.chain_id)
        logger.info("Memory pool initialized")
        
        # Add a direct reference to the mempool in the blockchain
        # This ensures transactions can be removed when blocks are added
        self.blockchain.mempool = self.mempool
        logger.info("Connected mempool to blockchain for transaction management")
        
        # Initialize P2P network if enabled
        if self.enable_p2p:
            self.p2p_network = P2PNetwork(
                self.blockchain, 
                self.mempool,
                listen_port=self.p2p_port,
                max_peers=self.max_peers,
                external_ip=self.external_ip
            )
            logger.info(f"P2P network initialized on port {self.p2p_port}")
            
            # Initialize blockchain synchronizer
            self.synchronizer = BlockchainSynchronizer(self.p2p_network, self.blockchain)
            logger.info("Blockchain synchronizer initialized")
        
        # Initialize API server if enabled
        if self.enable_api:
            self.api_server = create_api_server(
                self.blockchain,
                self.mempool,
                self.p2p_network,
                host=self.listen_address,
                port=self.api_port
            )
            logger.info(f"API server initialized on {self.listen_address}:{self.api_port}")
    
    def start(self):
        """Start the full node and all its components"""
        if self.running:
            logger.warning("Node is already running")
            return
        
        logger.info(f"Starting Qbitcoin full node {config.VERSION}")
        self.startup_time = time.time()
        
        try:
            # Initialize components
            self._initialize_components()
            
            # Mark as running before starting threads
            self.running = True
            
            # Start P2P network if enabled
            if self.enable_p2p and self.p2p_network:
                self.p2p_network.start()
                
                # Start initial blockchain sync
                threading.Thread(target=self._sync_blockchain, daemon=True).start()
            
            # Start API server if enabled
            if self.enable_api and self.api_server:
                threading.Thread(target=self.api_server.start, daemon=True).start()
            
            # Start maintenance thread
            threading.Thread(target=self._maintenance_loop, daemon=True).start()
            
            logger.info("Qbitcoin node started successfully")
            
            # Set up signal handlers for graceful shutdown
            if not self.disable_signals:
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting node: {e}")
            self.running = False
            self.shutdown()
            return False
    
    def _sync_blockchain(self):
        """Initial blockchain synchronization"""
        if not self.enable_p2p or not self.p2p_network:
            self.sync_complete = True
            return
        
        try:
            logger.info("Starting initial blockchain synchronization...")
            time.sleep(5)  # Give P2P network time to establish connections
            
            if self.synchronizer:
                # Start blockchain sync
                self.synchronizer.start_sync()
                
                # Wait for sync to complete or node to shut down
                while self.running and self.synchronizer.is_syncing():
                    time.sleep(5)
                    status = self.synchronizer.get_sync_status()
                    logger.info(f"Sync progress: {status['progress']}% - {status['status_message']}")
                
                if self.running:
                    logger.info("Initial blockchain synchronization complete")
                    self.sync_complete = True
        
        except Exception as e:
            logger.error(f"Error during blockchain sync: {e}")
            if self.running:
                self.sync_complete = True  # Mark as complete even on error to prevent retrying
    
    def _maintenance_loop(self):
        """Regular maintenance tasks"""
        while self.running and not self.shutdown_event.is_set():
            try:
                # Perform routine maintenance tasks
                self._clean_mempool()
                self._check_peer_connections()
                
                # Log node status periodically
                self._log_node_status()
                
                # Wait before next maintenance cycle
                self.shutdown_event.wait(60)  # Run maintenance every minute
                
            except Exception as e:
                logger.error(f"Error in maintenance loop: {e}")
                self.shutdown_event.wait(30)  # On error, wait less before retrying
    
    def _clean_mempool(self):
        """Clean expired transactions from mempool"""
        if self.mempool:
            try:
                # Call remove_expired and don't expect a return value
                # (it's now an alias for expire_old_transactions which doesn't return anything)
                self.mempool.remove_expired()
                # We won't try to log how many were removed since that info isn't returned
            except Exception as e:
                logger.error(f"Error cleaning mempool: {e}")
    
    def _check_peer_connections(self):
        """Check and maintain peer connections"""
        if self.p2p_network:
            # Nothing to do here - P2P network maintains connections automatically
            try:
                connected_peers = len(self.p2p_network.active_connections)
                if connected_peers < config.OUTBOUND_PEER_TARGET:
                    logger.info(f"Low peer count ({connected_peers}), seeking more peers...")
            except Exception as e:
                logger.error(f"Error checking peer connections: {e}")
    
    def _log_node_status(self):
        """Log the current node status"""
        uptime = int(time.time() - self.startup_time)
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        status = {
            "uptime": f"{hours:02}:{minutes:02}:{seconds:02}",
            "height": self.blockchain.current_height if self.blockchain else 0,
            "mempool_tx": self.mempool.get_transaction_count() if self.mempool else 0,
            "peers": len(self.p2p_network.active_connections) if self.p2p_network else 0,
            "synced": "Yes" if self.sync_complete else "No"
        }
        
        logger.info(f"Node status: Height={status['height']}, " +
                  f"Mempool={status['mempool_tx']} txs, " +
                  f"Peers={status['peers']}, " +
                  f"Uptime={status['uptime']}, " +
                  f"Synced={status['synced']}")
    
    def _signal_handler(self, sig, frame):
        """Handle termination signals"""
        logger.info(f"Received signal {sig}, shutting down...")
        self.shutdown()
    
    def shutdown(self):
        """Shut down the node gracefully"""
        if not self.running:
            return
        
        logger.info("Shutting down Qbitcoin node...")
        self.running = False
        self.shutdown_event.set()
        
        # Stop P2P network
        if self.p2p_network:
            logger.info("Stopping P2P network...")
            self.p2p_network.stop()
        
        # No explicit stop method for API server - it runs in its own thread
        # that will be terminated when the main process exits
        
        # Close blockchain and database connections
        if self.blockchain:
            logger.info("Closing blockchain...")
            self.blockchain.close()
        
        if self.mempool:
            logger.info("Closing mempool...")
            self.mempool.close()
        
        logger.info("Qbitcoin node shutdown complete")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current node status"""
        status = {
            "version": config.VERSION,
            "chain_id": self.chain_id,
            "running": self.running,
            "uptime": int(time.time() - self.startup_time) if self.startup_time > 0 else 0,
            "sync_complete": self.sync_complete,
            "listen_address": f"{self.listen_address}:{self.p2p_port}",
            "api_enabled": self.enable_api,
            "p2p_enabled": self.enable_p2p
        }
        
        # Add blockchain status
        if self.blockchain:
            status.update({
                "blockchain_height": self.blockchain.current_height,
                "best_block_hash": self.blockchain.best_hash,
                "accounts_count": self.blockchain.get_account_count()
            })
        
        # Add mempool status
        if self.mempool:
            status.update({
                "mempool_transactions": self.mempool.get_transaction_count(),
                "mempool_size": self.mempool.get_size_bytes()
            })
        
        # Add P2P network status
        if self.p2p_network:
            status.update({
                "connected_peers": len(self.p2p_network.active_connections),
                "total_known_peers": len(self.p2p_network.peers)
            })
        
        return status
    
    def submit_transaction(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit a transaction to the node
        
        Args:
            tx_data: Transaction data as dictionary
            
        Returns:
            Response dictionary with success status and info
        """
        if not self.mempool:
            return {"success": False, "error": "Node not initialized"}
            
        try:
            # Create transaction object from data
            tx = Transaction.from_dict(tx_data)
            tx_hash = tx.hash  # Store the hash before converting to dict
            
            # Add to mempool
            if self.mempool.add_transaction(tx, self.blockchain):  # Pass tx object directly, not dict
                # Broadcast transaction if P2P network is enabled
                if self.p2p_network:
                    self.p2p_network.broadcast_transaction(tx.to_dict())
                    
                return {
                    "success": True,
                    "tx_hash": tx_hash,  # Use the stored hash
                    "message": "Transaction submitted successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Transaction rejected by mempool"
                }
        except Exception as e:
            logger.error(f"Error submitting transaction: {e}")
            return {
                "success": False,
                "error": f"Error submitting transaction: {str(e)}"
            }
    
    def get_local_ip_addresses(self) -> List[str]:
        """
        Get all local IP addresses of this node
        
        Returns:
            List of IP addresses
        """
        ip_addresses = []
        
        # Try to get all network interfaces
        try:
            # Get hostname and local IP
            hostname = socket.gethostname()
            ip_addresses.append(socket.gethostbyname(hostname))
            
            # Try to get all addresses
            for if_name in socket.if_nameindex():
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    ip = socket.inet_ntoa(
                        socket.ioctl(
                            s.fileno(),
                            0x8915,  # SIOCGIFADDR
                            struct.pack('256s', if_name[1][:15].encode())
                        )[20:24]
                    )
                    if ip not in ip_addresses:
                        ip_addresses.append(ip)
                except:
                    pass
        except:
            pass
        
        # Add external IP if provided
        if self.external_ip and self.external_ip not in ip_addresses:
            ip_addresses.append(self.external_ip)
        
        return ip_addresses

    def start_mining(self, mining_address: str) -> bool:
        """
        Start mining blocks with SHA3-256 PoW algorithm
        
        Args:
            mining_address: Address to receive mining rewards
            
        Returns:
            True if mining started, False otherwise
        """
        if not self.running:
            logger.error("Cannot start mining - node is not running")
            return False
        
        if self.mining_running:
            logger.warning("Mining is already running")
            return True
        
        try:
            logger.info(f"Starting SHA3-256 mining to address {mining_address}")
            
            # Import mining components
            from core.consensus.pow import BlockMiner
            
            # Ensure blockchain has reference to this node before starting the miner
            if not hasattr(self.blockchain, 'node') or self.blockchain.node is None:
                logger.info("Setting node reference in blockchain for mining operations")
                self.blockchain.node = self
            
            # Initialize miner if not already done
            self.miner = BlockMiner(self.blockchain, self.mempool)
            self.mining_address = mining_address
            
            # Set mining flag and start thread
            self.mining_running = True
            self.mining_thread = threading.Thread(
                target=self._mining_thread_func,
                daemon=True
            )
            self.mining_thread.start()
            
            logger.info(f"Mining started successfully using {config.MINING_ALGORITHM}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start mining: {e}")
            self.mining_running = False
            return False
    
    def stop_mining(self) -> bool:
        """
        Stop the mining operation
        
        Returns:
            True if stopped, False if wasn't running
        """
        if not self.mining_running:
            return False
            
        logger.info("Stopping mining operation")
        self.mining_running = False
        
        if self.miner:
            self.miner.stop_mining()
        
        if self.mining_thread:
            self.mining_thread.join(timeout=2.0)
            self.mining_thread = None
        
        logger.info("Mining stopped")
        return True
    
    def get_mining_stats(self) -> Dict[str, Any]:
        """
        Get mining statistics
        
        Returns:
            Dictionary with mining statistics
        """
        stats = {
            "mining": self.mining_running,
            "algorithm": config.MINING_ALGORITHM,
            "address": self.mining_address,
            "blocks_mined": 0,
            "current_difficulty": self.blockchain.get_next_block_difficulty(log_info=False) if self.blockchain else 0
        }
        
        if self.miner:
            stats.update(self.miner.get_mining_stats())
            
        return stats
        
    def _mining_thread_func(self):
        """Mining thread function that monitors the mining process"""
        try:
            # Start mining using the miner instance
            self.miner.start_mining(self.mining_address)
            
            # Monitor mining status
            while self.mining_running and self.running:
                # Sleep to avoid high CPU usage in the loop
                time.sleep(1)
                
                # Get mining stats periodically for logging
                if self.mining_running and self.miner:
                    stats = self.miner.get_mining_stats()
                    if stats.get('last_hash_rate', 0) > 0:
                        logger.debug(f"Mining: {stats.get('last_hash_rate', 0):.1f} H/s, " + 
                                    f"found {stats.get('blocks_found', 0)} blocks")
            
        except Exception as e:
            logger.error(f"Error in mining thread: {e}")
            self.mining_running = False


def run_node(chain_id=None, listen_address="0.0.0.0", p2p_port=None, 
            api_port=None, enable_api=True, enable_p2p=True, 
            data_dir=None):
    """
    Helper function to create and run a node
    
    Args:
        chain_id: Optional chain ID
        listen_address: IP address to listen on
        p2p_port: P2P port
        api_port: API port
        enable_api: Whether to enable API
        enable_p2p: Whether to enable P2P
        data_dir: Optional data directory
        
    Returns:
        Running Node instance
    """
    # Create node
    node = Node(
        chain_id=chain_id,
        listen_address=listen_address,
        p2p_port=p2p_port,
        api_port=api_port,
        enable_api=enable_api,
        enable_p2p=enable_p2p,
        data_dir=Path(data_dir) if data_dir else None
    )
    
    # Start node
    if node.start():
        return node
    return None


if __name__ == "__main__":
    # Run node with default settings when executed directly
    import argparse
    
    parser = argparse.ArgumentParser(description="Qbitcoin Full Node")
    parser.add_argument("--p2p-port", type=int, help=f"P2P port (default: {config.P2P_PORT})")
    parser.add_argument("--api-port", type=int, help=f"API port (default: {config.API_PORT})")
    parser.add_argument("--no-api", action="store_true", help="Disable API server")
    parser.add_argument("--no-p2p", action="store_true", help="Disable P2P networking")
    parser.add_argument("--testnet", action="store_true", help="Use testnet instead of mainnet")
    parser.add_argument("--data-dir", type=str, help="Custom data directory")
    parser.add_argument("--external-ip", type=str, help="External IP address for this node")
    
    args = parser.parse_args()
    
    # Set chain ID based on network selection
    chain_id = "qbitcoin-testnet-v1" if args.testnet else None
    
    # Create and run node
    node = Node(
        chain_id=chain_id,
        p2p_port=args.p2p_port,
        api_port=args.api_port,
        enable_api=not args.no_api,
        enable_p2p=not args.no_p2p,
        external_ip=args.external_ip,
        data_dir=Path(args.data_dir) if args.data_dir else None
    )
    
    try:
        # Start node
        node.start()
        
        # Keep main thread running
        while node.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        node.shutdown()