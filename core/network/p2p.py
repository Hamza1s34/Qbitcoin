"""
P2P Network Implementation for Qbitcoin

This file implements the core peer-to-peer networking functionality for the Qbitcoin blockchain,
enabling secure and efficient communication between nodes in the network.
"""

import os
import sys
import socket
import threading
import time
import json
import hashlib
import base64
import struct
import random
import ipaddress
import queue
from typing import Dict, List, Set, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import traceback
# Import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import config
from core.blockchain import Blockchain
from core.block import Block
from core.transaction import Transaction
from core.mempool import Mempool
from utils.logger import get_logger

# Initialize logger
logger = get_logger("p2p")

# Message types
class MessageType(Enum):
    HANDSHAKE = "handshake"
    PING = "ping"
    PONG = "pong"
    GET_BLOCKS = "get_blocks"
    BLOCKS = "blocks"
    GET_HEADERS = "get_headers"
    HEADERS = "headers"
    GET_DATA = "get_data"
    DATA = "data"
    TRANSACTION = "transaction"
    INV = "inventory"
    GET_PEERS = "get_peers"
    PEERS = "peers"
    ALERT = "alert"
    REJECT = "reject"

# Inventory types
class InventoryType(Enum):
    ERROR = 0
    TRANSACTION = 1
    BLOCK = 2
    FILTERED_BLOCK = 3
    COMPACT_BLOCK = 4

@dataclass
class PeerInfo:
    """Class to store information about a peer"""
    address: str
    port: int
    last_seen: float = 0  # timestamp
    services: int = 0  # Bitfield of services
    version: str = ""
    user_agent: str = ""
    height: int = 0
    latency: float = 0  # in seconds
    connection_failures: int = 0
    banned_until: float = 0  # timestamp when ban expires
    is_outgoing: bool = False

    @property
    def endpoint(self) -> str:
        return f"{self.address}:{self.port}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'address': self.address,
            'port': self.port,
            'last_seen': self.last_seen,
            'services': self.services,
            'version': self.version,
            'user_agent': self.user_agent,
            'height': self.height,
            'latency': self.latency,
            'is_outgoing': self.is_outgoing
        }

class P2PNetwork:
    """
    Core implementation of P2P networking for Qbitcoin blockchain
    
    This class manages peer discovery, connection handling, and message passing
    for the blockchain network.
    """
    
    def __init__(self, blockchain: Blockchain, mempool: Mempool, 
                 listen_port: int = None, max_peers: int = None,
                 external_ip: str = None):
        """
        Initialize the P2P network
        
        Args:
            blockchain: Reference to the blockchain
            mempool: Reference to the transaction memory pool
            listen_port: Port to listen on (defaults to config.P2P_PORT)
            max_peers: Maximum number of peers to connect to
            external_ip: External IP address of this node
        """
        self.blockchain = blockchain
        self.mempool = mempool
        self.listen_port = listen_port or config.P2P_PORT
        self.max_peers = max_peers or config.MAX_PEERS
        self.external_ip = external_ip
        
        # Peer management
        self.peers: Dict[str, PeerInfo] = {}
        self.active_connections: Dict[str, 'PeerConnection'] = {}
        self.peer_addresses: Set[str] = set()
        self.banned_ips: Dict[str, float] = {}  # IP -> ban expiration time
        
        # Network state
        self.running = False
        self.node_id = random.getrandbits(64)
        self.server_socket = None
        self.lock = threading.RLock()  # For thread safety
        
        # Message handlers
        self.message_handlers: Dict[MessageType, Callable] = {
            MessageType.HANDSHAKE: self._handle_handshake,
            MessageType.PING: self._handle_ping,
            MessageType.PONG: self._handle_pong,
            MessageType.GET_BLOCKS: self._handle_get_blocks,
            MessageType.BLOCKS: self._handle_blocks,
            MessageType.GET_HEADERS: self._handle_get_headers,
            MessageType.HEADERS: self._handle_headers,
            MessageType.GET_DATA: self._handle_get_data,
            MessageType.DATA: self._handle_data,
            MessageType.TRANSACTION: self._handle_transaction,
            MessageType.INV: self._handle_inventory,
            MessageType.GET_PEERS: self._handle_get_peers,
            MessageType.PEERS: self._handle_peers,
            MessageType.ALERT: self._handle_alert,
            MessageType.REJECT: self._handle_reject
        }
        
        # Synchronization state
        self.sync_state: Dict[str, Any] = {
            'syncing': False,
            'sync_peer': None,
            'sync_height': 0,
            'last_progress': 0,
            'requested_blocks': set(),
            'requested_headers': set()
        }
        
        # Stats
        self.stats = {
            'bytes_sent': 0,
            'bytes_received': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'connections_accepted': 0,
            'connections_rejected': 0,
            'start_time': time.time()
        }
        
        # Schedule regular tasks
        self._schedule_tasks()
    
    def _schedule_tasks(self):
        """Schedule regular maintenance tasks"""
        # We'll run these tasks on separate threads once the network is started
        self.tasks = [
            # (function, interval in seconds)
            (self._discover_peers, 300),  # Every 5 minutes
            (self._ping_peers, config.PEER_PING_INTERVAL),
            (self._cleanup_peers, 600),  # Every 10 minutes
            (self._maintain_connections, 60),  # Every minute
        ]
    
    def start(self):
        """Start the P2P network server"""
        if self.running:
            logger.warning("P2P network already running")
            return
        
        logger.info(f"Starting P2P network on port {self.listen_port}")
        
        try:
            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.listen_port))
            self.server_socket.listen(5)
            
            # Set running flag
            self.running = True
            
            # Start server thread
            server_thread = threading.Thread(target=self._accept_connections)
            server_thread.daemon = True
            server_thread.start()
            
            # Start task threads
            for task, interval in self.tasks:
                t = threading.Thread(target=self._run_task, args=(task, interval))
                t.daemon = True
                t.start()
            
            # Bootstrap with initial peers
            self._bootstrap()
            
            logger.info("P2P network started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start P2P network: {e}")
            self.running = False
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            return False
    
    def stop(self):
        """Stop the P2P network server"""
        if not self.running:
            return
        
        logger.info("Stopping P2P network...")
        self.running = False
        
        # Close server socket
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        
        # Disconnect from all peers
        with self.lock:
            for peer_id, conn in list(self.active_connections.items()):
                try:
                    conn.close()
                except:
                    pass
            self.active_connections.clear()
        
        logger.info("P2P network stopped")
    
    def _run_task(self, task_func, interval):
        """Run a scheduled task at regular intervals"""
        while self.running:
            try:
                task_func()
            except Exception as e:
                logger.error(f"Error in {task_func.__name__}: {e}")
            
            # Sleep for interval seconds
            time.sleep(interval)
    
    def _bootstrap(self):
        """Bootstrap the P2P network with initial peers"""
        logger.info("Bootstrapping P2P network with initial peers")
        
        # Add bootstrap nodes from config
        bootstrap_nodes_count = 0
        for node in config.BOOTSTRAP_NODES:
            try:
                if ':' in node:
                    host, port_str = node.split(':')
                    port = int(port_str)
                else:
                    host = node
                    port = config.P2P_PORT
                
                self._add_peer_address(host, port)
                bootstrap_nodes_count += 1
                logger.info(f"Added bootstrap node: {host}:{port}")
            except Exception as e:
                logger.error(f"Invalid bootstrap node {node}: {e}")
        
        # Start connections to bootstrap nodes
        self._maintain_connections()
        
        # If we have bootstrap nodes and blockchain is empty, initiate blockchain sync
        if bootstrap_nodes_count > 0 and self.blockchain.current_height < 0:
            logger.info("Blockchain is empty and bootstrap nodes are defined. Will sync blockchain including genesis block.")
            # Wait a bit for connections to establish before starting sync
            time.sleep(5)
            
            # At this point, if connections were established, the handshake handler
            # will have already requested the genesis block
    
    def _accept_connections(self):
        """Accept incoming connections"""
        logger.info(f"Accepting connections on port {self.listen_port}")
        
        while self.running:
            try:
                # Accept connection
                client_socket, address = self.server_socket.accept()
                
                # Remove socket timeout - we'll use ping/pong for keepalive instead
                # client_socket.settimeout(config.PEER_CONNECTION_TIMEOUT)
                
                # Check if banned
                ip = address[0]
                if self._is_banned(ip):
                    logger.warning(f"Rejected connection from banned IP: {ip}")
                    client_socket.close()
                    self.stats['connections_rejected'] += 1
                    continue
                
                # Check connection limit
                with self.lock:
                    if len(self.active_connections) >= self.max_peers:
                        logger.warning("Max peer connections reached, rejecting new connection")
                        client_socket.close()
                        self.stats['connections_rejected'] += 1
                        continue
                
                # Create peer connection
                peer_conn = PeerConnection(
                    self, client_socket, address[0], address[1], False)
                
                # Start connection threads
                peer_conn.start()
                
                # Update stats
                self.stats['connections_accepted'] += 1
                logger.info(f"Accepted connection from {address[0]}:{address[1]}")
                
            except socket.timeout:
                continue
                
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")
                time.sleep(1)
    
    def connect_to_peer(self, host: str, port: int) -> bool:
        """
        Establish outbound connection to a peer
        
        Args:
            host: Peer hostname or IP address
            port: Peer port number
            
        Returns:
            True if connection successful, False otherwise
        """
        peer_id = f"{host}:{port}"
        
        # Check if already connected
        with self.lock:
            if peer_id in self.active_connections:
                logger.debug(f"Already connected to {peer_id}")
                return True
            
            # Check if banned
            if self._is_banned(host):
                logger.warning(f"Cannot connect to banned peer: {host}")
                return False
            
            # Check connection limit
            if len(self.active_connections) >= self.max_peers:
                logger.warning("Max peer connections reached, cannot connect to more peers")
                return False
        
        # Connect
        try:
            logger.info(f"Connecting to peer {host}:{port}")
            
            # Create socket and set timeout only for initial connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(config.PEER_CONNECTION_TIMEOUT)
            
            # Connect
            sock.connect((host, port))
            
            # Remove timeout for regular operations
            sock.settimeout(None)
            
            # Create peer connection
            peer_conn = PeerConnection(self, sock, host, port, True)
            
            # Start connection threads
            peer_conn.start()
            
            # Send handshake
            handshake_msg = self._create_handshake_message()
            peer_conn.send_message(MessageType.HANDSHAKE, handshake_msg)
            
            logger.info(f"Connected to peer {host}:{port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to peer {host}:{port}: {e}")
            
            # Update peer info with connection failure
            self._record_connection_failure(host, port)
            return False
    
    def _record_connection_failure(self, host: str, port: int):
        """Record connection failure for a peer"""
        peer_id = f"{host}:{port}"
        
        with self.lock:
            # Update or create peer info
            if peer_id in self.peers:
                self.peers[peer_id].connection_failures += 1
                
                # Ban peer temporarily if too many failures
                if self.peers[peer_id].connection_failures >= 3:
                    # Ban for 1 hour (can be adjusted)
                    ban_duration = 3600  
                    self._ban_peer(host, ban_duration)
            else:
                # Create new peer info entry
                peer_info = PeerInfo(host, port)
                peer_info.connection_failures = 1
                self.peers[peer_id] = peer_info
    
    def _ban_peer(self, ip: str, duration: int):
        """
        Ban a peer for a specified duration
        
        Args:
            ip: IP address to ban
            duration: Ban duration in seconds
        """
        with self.lock:
            expiration = time.time() + duration
            self.banned_ips[ip] = expiration
            logger.info(f"Banned IP {ip} for {duration} seconds")
            
            # Disconnect if currently connected
            for peer_id, conn in list(self.active_connections.items()):
                if conn.host == ip:
                    conn.close(reason="Banned")
    
    def _is_banned(self, ip: str) -> bool:
        """Check if an IP is banned"""
        with self.lock:
            if ip in self.banned_ips:
                # Check if ban has expired
                if time.time() > self.banned_ips[ip]:
                    # Ban expired, remove from list
                    del self.banned_ips[ip]
                    return False
                return True
            return False
    
    def _add_peer_address(self, host: str, port: int):
        """Add a peer address to the known peers list"""
        peer_id = f"{host}:{port}"
        
        with self.lock:
            # Don't add if already known
            if peer_id in self.peer_addresses:
                return
            
            # Add to known addresses
            self.peer_addresses.add(peer_id)
            
            # Update or create peer info
            if peer_id not in self.peers:
                self.peers[peer_id] = PeerInfo(host, port)
    
    def _discover_peers(self):
        """Discover new peers"""
        logger.debug("Discovering new peers...")
        
        # Request peers from connected nodes
        with self.lock:
            connected_peers = list(self.active_connections.values())
        
        for peer in connected_peers:
            try:
                peer.send_message(MessageType.GET_PEERS, {})
            except:
                pass
    
    def _ping_peers(self):
        """Send ping messages to all connected peers"""
        with self.lock:
            connected_peers = list(self.active_connections.values())
        
        for peer in connected_peers:
            try:
                # Send ping with current timestamp
                ping_data = {"timestamp": time.time(), "height": self.blockchain.current_height}
                peer.send_message(MessageType.PING, ping_data)
            except:
                pass
    
    def _cleanup_peers(self):
        """Clean up disconnected and inactive peers"""
        logger.debug("Cleaning up peer list...")
        
        with self.lock:
            # Remove expired bans
            now = time.time()
            for ip in list(self.banned_ips.keys()):
                if now > self.banned_ips[ip]:
                    del self.banned_ips[ip]
            
            # Clean up inactive peers
            inactive_threshold = now - 3600  # 1 hour
            for peer_id in list(self.peers.keys()):
                peer = self.peers[peer_id]
                
                # If not connected and last seen too long ago
                if (peer_id not in self.active_connections and 
                    peer.last_seen < inactive_threshold):
                    del self.peers[peer_id]
    
    def _maintain_connections(self):
        """Maintain target number of outbound connections"""
        logger.debug("Maintaining peer connections...")
        
        with self.lock:
            # Count current outbound connections
            outbound_count = sum(1 for conn in self.active_connections.values() 
                                 if conn.is_outbound)
            
            # If below target, establish more connections
            if outbound_count < config.OUTBOUND_PEER_TARGET:
                # Calculate how many new connections needed
                needed = config.OUTBOUND_PEER_TARGET - outbound_count
                
                # Get candidate peers that we're not connected to yet
                candidates = []
                for peer_id in self.peer_addresses:
                    if (peer_id not in self.active_connections and
                        not self._is_banned(peer_id.split(':')[0])):
                        host, port_str = peer_id.split(':')
                        port = int(port_str)
                        candidates.append((host, port))
                
                # Sort by fewest connection failures (more reliable first)
                candidates.sort(key=lambda x: self.peers.get(f"{x[0]}:{x[1]}", 
                                             PeerInfo(x[0], x[1])).connection_failures)
                
                # Try to establish connections
                for host, port in candidates[:needed]:
                    # Start connection in a separate thread to not block
                    threading.Thread(target=self.connect_to_peer, 
                                     args=(host, port)).start()
    
    def broadcast_transaction(self, transaction) -> bool:
        """
        Broadcast a transaction to the network
        
        Args:
            transaction: Transaction object to broadcast
            
        Returns:
            True if broadcast to at least one peer, False otherwise
        """
        # Convert transaction to dict if it's an object
        if not isinstance(transaction, dict):
            tx_data = transaction.to_dict()
        else:
            tx_data = transaction
        
        # Create inventory message
        inv_data = {
            'type': InventoryType.TRANSACTION.value,
            'hash': tx_data.get('hash'),
            'data': tx_data
        }
        
        # Broadcast to all peers
        return self._broadcast_message(MessageType.TRANSACTION, tx_data)
    
    def broadcast_block(self, block) -> bool:
        """
        Broadcast a block to the network
        
        Args:
            block: Block object to broadcast
            
        Returns:
            True if broadcast to at least one peer, False otherwise
        """
        # Convert block to dict if it's an object
        if not isinstance(block, dict):
            block_data = block.to_dict()
        else:
            block_data = block
        
        # Check if we have any connected peers first
        with self.lock:
            peer_count = len(self.active_connections)
            peer_info = [f"{peer_id} (height: {peer.height})" for peer_id, peer in self.peers.items() 
                        if peer_id in self.active_connections]
        
        if peer_count == 0:
            logger.warning(f"Cannot broadcast block {block_data.get('height')} - no connected peers")
            return False
            
        # Log broadcasting attempt with detailed peer information
        logger.info(f"Broadcasting block {block_data.get('height')} with hash {block_data.get('hash')[:10]}... to {peer_count} peers: {', '.join(peer_info)}")
        
        # Create inventory message for the block
        inv_data = {
            'type': InventoryType.BLOCK.value,
            'hash': block_data.get('hash'),
            'height': block_data.get('height'),
            'header': {
                'version': block_data.get('version'),
                'prev_hash': block_data.get('prev_hash'),
                'merkle_root': block_data.get('merkle_root'),
                'timestamp': block_data.get('timestamp'),
                'height': block_data.get('height'),
                'difficulty': block_data.get('difficulty'),
                'nonce': block_data.get('nonce')
            }
        }
        
        # First broadcast inventory notification
        logger.info(f"Broadcasting inventory notification for block {block_data.get('height')}")
        inv_result = self._broadcast_message(MessageType.INV, inv_data)
        
        # Then broadcast full block
        logger.info(f"Broadcasting full block data for block {block_data.get('height')}")
        block_result = self._broadcast_message(MessageType.BLOCKS, [block_data])
        
        # Log the results
        if inv_result or block_result:
            logger.info(f"Successfully broadcast block {block_data.get('height')} to at least one peer")
            return True
        else:
            logger.warning(f"Failed to broadcast block {block_data.get('height')} to any peers")
            return False
    
    def _broadcast_message(self, message_type: MessageType, data) -> bool:
        """Broadcast a message to all connected peers"""
        sent_count = 0
        
        with self.lock:
            connected_peers = list(self.active_connections.values())
        
        # If we have no peers, try to bootstrap
        if not connected_peers and self.running:
            logger.warning(f"No connected peers for broadcasting {message_type.value}, attempting to bootstrap")
            self._bootstrap()
            
            # Check again after bootstrap attempt
            with self.lock:
                connected_peers = list(self.active_connections.values())
        
        # Debug log peer count and their connection status
        peer_count = len(connected_peers)
        logger.info(f"Attempting to broadcast {message_type.value} to {peer_count} peers")
        
        for peer in connected_peers:
            try:
                # Check if peer is still connected before sending
                if hasattr(peer, 'connected') and peer.connected:
                    peer.send_message(message_type, data)
                    sent_count += 1
                    logger.info(f"Successfully sent {message_type.value} to peer {peer.peer_id}")
                else:
                    logger.warning(f"Peer {peer.peer_id} is not connected, skipping broadcast")
            except Exception as e:
                logger.error(f"Failed to send {message_type.value} to {peer.peer_id}: {str(e)}")
                # Log the traceback for more detailed error information
                import traceback
                logger.debug(f"Broadcast error details: {traceback.format_exc()}")
        
        if sent_count > 0:
            logger.info(f"Broadcast {message_type.value} to {sent_count} peers")
            return True
        else:
            logger.warning(f"Failed to broadcast {message_type.value} - no connected peers")
            return False
    
    def _create_handshake_message(self) -> Dict[str, Any]:
        """Create handshake message with node information"""
        return {
            'version': config.VERSION,
            'chain_id': self.blockchain.chain_id,
            'height': self.blockchain.current_height,
            'best_hash': self.blockchain.best_hash,
            'node_id': self.node_id,
            'user_agent': f"Qbitcoin/{config.VERSION}",
            'timestamp': int(time.time()),
            'services': 1,  # Node type flags
            'relay': True  # Whether node requests tx relay
        }
    
    def _register_connection(self, connection: 'PeerConnection'):
        """Register a new active connection"""
        with self.lock:
            peer_id = connection.peer_id
            self.active_connections[peer_id] = connection
            
            # Update peer info
            if peer_id in self.peers:
                self.peers[peer_id].last_seen = time.time()
            else:
                peer_info = PeerInfo(connection.host, connection.port)
                peer_info.last_seen = time.time()
                peer_info.is_outgoing = connection.is_outbound
                self.peers[peer_id] = peer_info
    
    def _unregister_connection(self, connection: 'PeerConnection'):
        """Unregister a closed connection"""
        with self.lock:
            peer_id = connection.peer_id
            if peer_id in self.active_connections:
                del self.active_connections[peer_id]
    
    def get_connected_peers(self) -> List[Dict[str, Any]]:
        """Get a list of connected peer information"""
        with self.lock:
            peers = []
            for peer_id, conn in self.active_connections.items():
                peer = self.peers.get(peer_id)
                if peer:
                    peers.append(peer.to_dict())
            return peers
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics"""
        with self.lock:
            stats = self.stats.copy()
            stats['peers'] = len(self.active_connections)
            stats['known_addresses'] = len(self.peer_addresses)
            stats['banned'] = len(self.banned_ips)
            stats['uptime'] = time.time() - stats['start_time']
            return stats
    
    def start_blockchain_sync(self):
        """Start synchronizing blockchain with peers"""
        if self.sync_state['syncing']:
            logger.debug("Blockchain sync already in progress")
            return
        
        logger.info("Starting blockchain synchronization...")
        
        with self.lock:
            # Find the peer with highest reported block height
            best_height = self.blockchain.current_height
            sync_peer = None
            
            for peer_id, peer in self.peers.items():
                if (peer_id in self.active_connections and 
                    peer.height > best_height + 3):  # Only sync if significantly behind
                    best_height = peer.height
                    sync_peer = peer_id
            
            if not sync_peer:
                logger.info("No peers available for sync or blockchain is up to date")
                return
            
            # Set sync state
            self.sync_state['syncing'] = True
            self.sync_state['sync_peer'] = sync_peer
            self.sync_state['sync_height'] = best_height
            self.sync_state['last_progress'] = time.time()
            self.sync_state['requested_blocks'].clear()
            self.sync_state['requested_headers'].clear()
            
            # Start sync in a new thread
            threading.Thread(target=self._sync_blockchain).start()
    
    def _sync_blockchain(self):
        """Synchronize blockchain with network"""
        try:
            # First get headers to validate the chain
            self._sync_headers()
            
            # Then download blocks
            self._sync_blocks()
            
        except Exception as e:
            logger.error(f"Error during blockchain sync: {e}")
        finally:
            # Reset sync state
            self.sync_state['syncing'] = False
            self.sync_state['sync_peer'] = None
            self.sync_state['requested_blocks'].clear()
            self.sync_state['requested_headers'].clear()
    
    def _sync_headers(self):
        """Synchronize block headers first"""
        # Implementation details here
        pass
    
    def _sync_blocks(self):
        """Synchronize full blocks"""
        # Implementation details here
        pass
    
    # Message handler methods
    def _handle_handshake(self, connection: 'PeerConnection', data: Dict[str, Any]):
        """Handle handshake message from peer"""
        peer_id = connection.peer_id
        
        # Validate chain ID
        if data.get('chain_id') != self.blockchain.chain_id:
            logger.warning(f"Peer {peer_id} is on a different chain: {data.get('chain_id')}")
            connection.close(reason="Different chain")
            return
        
        logger.info(f"Handshake from {peer_id}: v{data.get('version')}, height {data.get('height')}")
        
        # Update peer information
        with self.lock:
            if peer_id in self.peers:
                peer = self.peers[peer_id]
                peer.version = data.get('version', '')
                peer.user_agent = data.get('user_agent', '')
                peer.height = data.get('height', 0)
                peer.services = data.get('services', 0)
                peer.last_seen = time.time()
            
            # Add to active connections if it's an incoming connection (outgoing already registered)
            if not connection.is_outbound:
                self._register_connection(connection)
                
                # Send our handshake in response
                handshake_msg = self._create_handshake_message()
                connection.send_message(MessageType.HANDSHAKE, handshake_msg)
        
        # Special case: If we are waiting for the genesis block (blockchain height is -1)
        # and the peer has blocks, immediately request the genesis block
        if self.blockchain.current_height < 0 and data.get('height', 0) >= 0:
            logger.info(f"Requesting genesis block from peer {peer_id} at height {data.get('height')}")
            
            # Request the genesis block
            connection.send_message(MessageType.GET_BLOCKS, {
                'start_height': 0,
                'end_height': 0
            })
        # Regular case: Check if we need to sync with this peer
        elif data.get('height', 0) > self.blockchain.current_height + 3:
            self.start_blockchain_sync()
    
    def _handle_ping(self, connection: 'PeerConnection', data: Dict[str, Any]):
        """Handle ping message from peer"""
        # Send pong response with the same timestamp
        pong_data = {
            'timestamp': data.get('timestamp', time.time()),
            'height': self.blockchain.current_height
        }
        connection.send_message(MessageType.PONG, pong_data)
        
        # Update peer height if included
        if 'height' in data and connection.peer_id in self.peers:
            with self.lock:
                self.peers[connection.peer_id].height = data['height']
    
    def _handle_pong(self, connection: 'PeerConnection', data: Dict[str, Any]):
        """Handle pong message from peer"""
        # Calculate latency
        if 'timestamp' in data:
            latency = time.time() - data['timestamp']
            
            with self.lock:
                if connection.peer_id in self.peers:
                    self.peers[connection.peer_id].latency = latency
                    
                    # Also update height if included
                    if 'height' in data:
                        self.peers[connection.peer_id].height = data['height']
            
            logger.debug(f"Peer {connection.peer_id} latency: {latency:.3f}s, height: {data.get('height')}")
    
    def _handle_get_blocks(self, connection: 'PeerConnection', data: Dict[str, Any]):
        """Handle request for blocks from peer"""
        if 'start_height' not in data:
            return
            
        start_height = data['start_height']
        end_height = data.get('end_height', start_height + 500)  # Limit to 500 blocks
        
        # Cap to our current height
        end_height = min(end_height, self.blockchain.current_height)
        
        if start_height > end_height:
            return
            
        # Fetch blocks
        blocks = []
        for height in range(start_height, end_height + 1):
            block = self.blockchain.get_block_by_height(height)
            if block:
                blocks.append(block.to_dict())
            
            # Limit response size
            if len(blocks) >= 50:  # Maximum 50 blocks per response
                break
        
        # Send blocks
        if blocks:
            connection.send_message(MessageType.BLOCKS, blocks)
    
    def _handle_blocks(self, connection: 'PeerConnection', data: List[Dict[str, Any]]):
        """Handle received blocks from peer"""
        if not isinstance(data, list):
            logger.warning(f"Invalid blocks data from peer {connection.peer_id}")
            return
        
        for block_data in data:
            try:
                # Convert to Block object
                block = Block.from_dict(block_data)
                
                # Validate
                if not block.validate():
                    logger.warning(f"Received invalid block from {connection.peer_id}: {block.hash}")
                    continue
                
                # Special case for genesis block
                if block.height == 0 and self.blockchain.current_height < 0:
                    logger.info(f"Received genesis block from peer {connection.peer_id}")
                    logger.info(f"Genesis block hash: {block.hash}")
                    logger.info(f"Genesis merkle root: {block.merkle_root}")
                    logger.info(f"Genesis timestamp: {block.timestamp}")
                    logger.info(f"Genesis nonce: {block.nonce}")
                
                # Check if we already have this block
                if self.blockchain.chain_manager.has_block(block.hash):
                    logger.info(f"Block {block.height} ({block.hash[:8]}) already exists")
                    continue
                
                # Check if parent block exists
                if block.height > 0 and not self.blockchain.chain_manager.has_block(block.prev_hash):
                    logger.error(f"Parent block {block.prev_hash} not found")
                    
                    # Request the parent block instead
                    parent_height = block.height - 1
                    self._request_specific_blocks(connection, parent_height, parent_height)
                    continue
                
                # Process block
                if self.blockchain.add_block(block):
                    logger.info(f"Added block {block.height} ({block.hash[:8]}) from peer {connection.peer_id}")
                    
                    # Update block height in database and account database
                    self.blockchain._save_blockchain_state()
                    
                    # Process transactions to update account balances
                    self.blockchain._process_block_transactions(block)
                    
                    # If this was the genesis block we were waiting for, trigger sync for more blocks
                    if block.height == 0 and self.blockchain.current_height == 0:
                        # We've successfully added the genesis block, now continue syncing
                        logger.info("Genesis block successfully added, triggering blockchain sync")
                        self.start_blockchain_sync()
                
            except Exception as e:
                logger.error(f"Error processing block from peer {connection.peer_id}: {e}")
                logger.error(traceback.format_exc())
    
    def _request_specific_blocks(self, connection: 'PeerConnection', start_height: int, end_height: int):
        """Request specific blocks from a peer"""
        get_blocks_msg = {
            'start_height': start_height,
            'end_height': end_height
        }
        try:
            connection.send_message(MessageType.GET_BLOCKS, get_blocks_msg)
            logger.info(f"Requested blocks {start_height}-{end_height} from peer {connection.peer_id}")
            return True
        except Exception as e:
            logger.error(f"Error requesting blocks from peer {connection.peer_id}: {e}")
            return False
    
    def _handle_get_headers(self, connection: 'PeerConnection', data: Dict[str, Any]):
        """Handle request for block headers from peer"""
        # Similar to _handle_get_blocks but only sending headers
        pass
        
    def _handle_headers(self, connection: 'PeerConnection', data: List[Dict[str, Any]]):
        """Handle received block headers from peer"""
        # Process block headers for efficient sync
        pass
    
    def _handle_get_data(self, connection: 'PeerConnection', data: Dict[str, Any]):
        """Handle request for specific data items from peer"""
        if 'items' not in data or not isinstance(data['items'], list):
            return
            
        for item in data['items']:
            try:
                item_type = item.get('type')
                item_hash = item.get('hash')
                
                if not item_type or not item_hash:
                    continue
                
                # Handle based on inventory type
                if item_type == InventoryType.BLOCK.value:
                    # Send requested block
                    block = self.blockchain.get_block_by_hash(item_hash)
                    if block:
                        connection.send_message(MessageType.BLOCKS, [block.to_dict()])
                        
                elif item_type == InventoryType.TRANSACTION.value:
                    # Send requested transaction
                    tx = self.mempool.get_transaction(item_hash)
                    if tx:
                        connection.send_message(MessageType.TRANSACTION, tx.to_dict())
                        
            except Exception as e:
                logger.error(f"Error handling get_data for {item_hash}: {e}")
    
    def _handle_data(self, connection: 'PeerConnection', data: Dict[str, Any]):
        """Handle data items from peer"""
        # Generic data handler - dispatch to specific handlers based on type
        pass
    
    def _handle_transaction(self, connection: 'PeerConnection', data: Dict[str, Any]):
        """Handle transaction received from peer"""
        try:
            # Validate and add to mempool
            tx_hash = data.get('hash', '')
            
            # Check if we already have this transaction
            if self.mempool.has_transaction(tx_hash):
                return
            
            # Add to mempool
            if self.mempool.add_transaction(data, self.blockchain):
                logger.debug(f"Added transaction {tx_hash[:8]} from peer {connection.peer_id} to mempool")
                
                # Relay to other peers (if relay is enabled)
                # This will broadcast to all peers except the originating peer
                peers_to_relay = [p for p in self.active_connections.values() 
                                if p.peer_id != connection.peer_id]
                                
                for peer in peers_to_relay:
                    try:
                        peer.send_message(MessageType.TRANSACTION, data)
                    except:
                        pass
            
        except Exception as e:
            logger.error(f"Error processing transaction from peer {connection.peer_id}: {e}")
    
    def _handle_inventory(self, connection: 'PeerConnection', data: Dict[str, Any]):
        """Handle inventory message from peer"""
        try:
            item_type = data.get('type')
            item_hash = data.get('hash')
            
            if not item_type or not item_hash:
                return
                
            # Handle based on inventory type
            if item_type == InventoryType.BLOCK.value:
                # Check if we have this block already
                if self.blockchain.get_block_by_hash(item_hash):
                    return
                    
                # Request the block
                get_data = {
                    'items': [{'type': item_type, 'hash': item_hash}]
                }
                connection.send_message(MessageType.GET_DATA, get_data)
                
            elif item_type == InventoryType.TRANSACTION.value:
                # Check if we have this transaction already
                if self.mempool.has_transaction(item_hash):
                    return
                    
                # Request the transaction
                get_data = {
                    'items': [{'type': item_type, 'hash': item_hash}]
                }
                connection.send_message(MessageType.GET_DATA, get_data)
                
        except Exception as e:
            logger.error(f"Error handling inventory from peer {connection.peer_id}: {e}")
    
    def _handle_get_peers(self, connection: 'PeerConnection', data: Dict[str, Any]):
        """Handle request for known peers"""
        # Get a subset of our known peers
        with self.lock:
            peer_list = []
            for peer_id, peer_info in self.peers.items():
                # Don't share banned peers or the requesting peer itself
                if (not self._is_banned(peer_info.address) and 
                    peer_id != connection.peer_id):
                    peer_list.append({
                        'address': peer_info.address,
                        'port': peer_info.port
                    })
                    
                # Limit to 100 peers
                if len(peer_list) >= 100:
                    break
        
        # Send peers
        connection.send_message(MessageType.PEERS, {'peers': peer_list})
    
    def _handle_peers(self, connection: 'PeerConnection', data: Dict[str, Any]):
        """Handle received peer addresses from peer"""
        if 'peers' not in data or not isinstance(data['peers'], list):
            return
            
        for peer in data['peers']:
            try:
                host = peer.get('address')
                port = peer.get('port', config.P2P_PORT)
                
                if not host:
                    continue
                    
                # Validate IP address
                try:
                    ipaddress.ip_address(host)
                    
                    # Add to our known peers
                    self._add_peer_address(host, port)
                    
                except ValueError:
                    # Not a valid IP address
                    pass
                    
            except Exception as e:
                logger.error(f"Error processing peer address: {e}")
    
    def _handle_alert(self, connection: 'PeerConnection', data: Dict[str, Any]):
        """Handle network alert message from peer"""
        alert_type = data.get('type', '')
        message = data.get('message', '')
        signature = data.get('signature', '')
        
        # In a real implementation, we would verify the signature against trusted keys
        
        logger.warning(f"Network alert from {connection.peer_id}: [{alert_type}] {message}")
    
    def _handle_reject(self, connection: 'PeerConnection', data: Dict[str, Any]):
        """Handle rejection message from peer"""
        message_type = data.get('message_type', '')
        reason = data.get('reason', '')
        hash_value = data.get('hash', '')
        
        logger.warning(f"Peer {connection.peer_id} rejected {message_type}: {reason}, hash: {hash_value}")


class PeerConnection:
    """
    Handles a connection to a single peer
    
    This class manages the communication with a specific peer, including
    message serialization, encryption, and handling.
    """
    
    def __init__(self, network: P2PNetwork, sock: socket.socket, 
                 host: str, port: int, is_outbound: bool):
        """
        Initialize peer connection
        
        Args:
            network: Reference to the P2P network
            sock: Connected socket
            host: Peer host IP address
            port: Peer port
            is_outbound: Whether this is an outbound connection
        """
        self.network = network
        self.socket = sock
        self.host = host
        self.port = port
        self.peer_id = f"{host}:{port}"
        self.is_outbound = is_outbound
        self.connected = True
        self.last_received = time.time()
        
        # Message handling
        self.send_lock = threading.Lock()
        self.receive_queue = queue.Queue()
        
        # Register with network
        if is_outbound:
            self.network._register_connection(self)
    
    def start(self):
        """Start connection threads"""
        # Start receive thread
        self.receive_thread = threading.Thread(target=self._receive_loop)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def close(self, reason: str = ""):
        """Close the connection"""
        if not self.connected:
            return
            
        self.connected = False
        logger.info(f"Closing connection to {self.peer_id}" + (f": {reason}" if reason else ""))
        
        try:
            self.socket.close()
        except:
            pass
        
        # Unregister from network
        self.network._unregister_connection(self)
    
    def send_message(self, message_type: MessageType, data):
        """
        Send a message to the peer
        
        Args:
            message_type: Type of message
            data: Message data (will be serialized)
        """
        if not self.connected:
            logger.warning(f"Cannot send to disconnected peer {self.peer_id}")
            raise Exception(f"Cannot send to disconnected peer {self.peer_id}")
        
        # Serialize message
        message = {
            'type': message_type.value,
            'timestamp': time.time(),
            'data': data
        }
        
        try:
            # Convert to JSON and encode
            message_json = json.dumps(message)
            message_bytes = message_json.encode('utf-8')
            
            # Add length prefix (4 bytes)
            length_prefix = struct.pack('!I', len(message_bytes))
            
            # Log the message size for debugging
            message_size = len(message_bytes)
            logger.debug(f"Sending {message_type.value} message of {message_size} bytes to {self.peer_id}")
            
            # Acquire lock to ensure message is sent as a whole
            with self.send_lock:
                try:
                    # Send length prefix followed by message
                    self.socket.sendall(length_prefix)
                    self.socket.sendall(message_bytes)
                    
                    # Update stats
                    self.network.stats['bytes_sent'] += len(length_prefix) + len(message_bytes)
                    self.network.stats['messages_sent'] += 1
                    
                    logger.debug(f"Successfully sent {message_type.value} message to {self.peer_id}")
                    return True
                    
                except (ConnectionError, socket.error) as e:
                    logger.error(f"Socket error sending message to {self.peer_id}: {str(e)}")
                    self.close(reason=f"Send error: {str(e)}")
                    raise
                    
                except Exception as e:
                    logger.error(f"Unexpected error sending message to {self.peer_id}: {str(e)}")
                    self.close(reason=f"Send error: {str(e)}")
                    raise
                    
        except json.JSONEncodeError as e:
            logger.error(f"JSON encoding error for message to {self.peer_id}: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Error preparing message for {self.peer_id}: {str(e)}")
            raise
    
    def _receive_loop(self):
        """Background thread for receiving messages"""
        try:
            while self.connected:
                try:
                    # Read message length (4 bytes)
                    length_data = self._recv_all(4)
                    if not length_data:
                        break
                        
                    # Unpack length
                    message_length = struct.unpack('!I', length_data)[0]
                    
                    # Sanity check - prevent DoS
                    if message_length > 10 * 1024 * 1024:  # 10MB max
                        raise Exception(f"Message too large: {message_length} bytes")
                    
                    # Read the message
                    message_data = self._recv_all(message_length)
                    if not message_data:
                        break
                    
                    # Update stats
                    self.network.stats['bytes_received'] += len(length_data) + len(message_data)
                    self.network.stats['messages_received'] += 1
                    
                    # Parse the message
                    message_json = message_data.decode('utf-8')
                    message = json.loads(message_json)
                    
                    # Update last received timestamp
                    self.last_received = time.time()
                    
                    # Add to processing queue
                    self.receive_queue.put(message)
                    
                except Exception as e:
                    if self.connected:
                        logger.error(f"Error receiving from {self.peer_id}: {e}")
                    break
            
        finally:
            self.close(reason="Receive loop ended")
    
    def _recv_all(self, length: int) -> bytes:
        """
        Receive exactly 'length' bytes from socket
        
        Args:
            length: Number of bytes to receive
            
        Returns:
            Bytes received
        """
        data = b''
        remaining = length
        
        # Set socket back to blocking mode to prevent timeouts
        self.socket.setblocking(True)
        
        try:
            while remaining > 0:
                chunk = self.socket.recv(remaining)
                if not chunk:  # Connection closed by peer
                    return None
                data += chunk
                remaining -= len(chunk)
                
            return data
            
        except Exception as e:
            logger.debug(f"Error in _recv_all: {e}")
            return None
    
    def _processing_loop(self):
        """Background thread for processing received messages"""
        try:
            while self.connected:
                try:
                    # Get message from queue with timeout
                    message = self.receive_queue.get(timeout=1)
                    
                    # Process message
                    self._process_message(message)
                    
                    # Mark task as done
                    self.receive_queue.task_done()
                    
                except queue.Empty:
                    continue
                    
                except Exception as e:
                    if self.connected:
                        logger.error(f"Error processing message from {self.peer_id}: {e}")
        
        finally:
            # Ensure connection is closed when thread exits
            self.close(reason="Processing loop ended")
    
    def _process_message(self, message):
        """
        Process a message received from peer
        
        Args:
            message: Parsed message object
        """
        try:
            message_type_str = message.get('type')
            data = message.get('data')
            
            # Find message type
            try:
                message_type = MessageType(message_type_str)
            except ValueError:
                logger.warning(f"Unknown message type from {self.peer_id}: {message_type_str}")
                return
            
            # Find handler for this message type
            handler = self.network.message_handlers.get(message_type)
            if handler:
                handler(self, data)
            else:
                logger.warning(f"No handler for message type: {message_type_str}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            
    def __str__(self) -> str:
        """String representation"""
        direction = "outbound" if self.is_outbound else "inbound"
        return f"PeerConnection({self.peer_id}, {direction})"