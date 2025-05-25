
"""
Blockchain Synchronization Module for Qbitcoin

This module implements the blockchain synchronization functionality for the Qbitcoin network.
It handles efficient download and verification of blocks and headers from peers.
"""

import os
import sys
import time
import threading
import queue
import heapq
from typing import Dict, List, Set, Optional, Any, Tuple, Deque
from collections import deque

# Import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from core import config 
from core.blockchain import Blockchain
from core.block import Block
from core.transaction import Transaction
from core.network.p2p import P2PNetwork, MessageType
from utils.logger import get_logger

# Initialize logger
logger = get_logger("sync")

class SyncState:
    """
    Stores the state of blockchain synchronization
    """
    # Sync modes
    MODE_IDLE = 'idle'
    MODE_HEADERS = 'headers_sync'
    MODE_BLOCKS = 'blocks_sync'
    MODE_CATCHUP = 'catchup'
    
    def __init__(self, p2p_network: P2PNetwork, blockchain: Blockchain):
        """
        Initialize sync state
        
        Args:
            p2p_network: Reference to P2P network
            blockchain: Reference to blockchain
        """
        self.p2p_network = p2p_network
        self.blockchain = blockchain
        self.mode = self.MODE_IDLE
        
        # Sync status
        self.syncing = False
        self.sync_peer = None
        self.sync_height = 0
        self.current_height = 0
        self.initial_height = 0
        self.target_height = 0
        self.last_progress_time = 0
        self.progress_percentage = 0
        
        # Headers sync
        self.headers_queue = queue.Queue()
        self.headers_in_flight = set()  # Set of heights requested but not received
        self.headers_map = {}  # Map of height -> header data
        self.verified_headers = set()  # Set of heights with verified headers
        
        # Blocks sync
        self.blocks_queue = queue.PriorityQueue()  # Priority queue for blocks to download
        self.blocks_in_flight = set()  # Set of hashes requested but not received
        self.downloaded_blocks = set()  # Set of downloaded block hashes
        self.blocks_processing_queue = deque()  # Queue for processing downloaded blocks
        
        # Speed and stats
        self.download_start_time = 0
        self.blocks_downloaded = 0
        self.headers_downloaded = 0
        
        # Worker threads
        self.threads = []
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        
        # Status for UI/CLI
        self.status_message = "Idle"

    def start_sync(self, target_height: int):
        """
        Start synchronization to reach target height
        
        Args:
            target_height: Target blockchain height to reach
        """
        with self.lock:
            if self.syncing:
                logger.info("Sync already in progress")
                return False
                
            # Initialize sync state
            self.syncing = True
            self.mode = self.MODE_HEADERS
            self.target_height = target_height
            self.initial_height = self.blockchain.current_height
            self.current_height = self.initial_height
            self.progress_percentage = 0
            self.last_progress_time = time.time()
            self.download_start_time = time.time()
            self.blocks_downloaded = 0
            self.headers_downloaded = 0
            
            # Clear queues and sets
            self._reset_sync_state()
            
            # Start worker threads
            self._start_worker_threads()
            
            logger.info(f"Starting blockchain sync from height {self.initial_height} to {target_height}")
            self.status_message = f"Synchronizing headers ({self.initial_height}/{target_height})"
            return True
    
    def stop_sync(self):
        """Stop synchronization process"""
        if not self.syncing:
            return
            
        logger.info("Stopping blockchain synchronization")
        self.syncing = False
        self.stop_event.set()
        
        # Wait for threads to end
        for t in self.threads:
            if t.is_alive():
                t.join(timeout=2.0)
        
        # Reset sync state
        self._reset_sync_state()
        self.mode = self.MODE_IDLE
        self.status_message = "Sync stopped"
    
    def _reset_sync_state(self):
        """Reset all sync state data structures"""
        # Clear header sync state
        while not self.headers_queue.empty():
            try:
                self.headers_queue.get_nowait()
            except:
                pass
        self.headers_in_flight.clear()
        self.headers_map.clear()
        self.verified_headers.clear()
        
        # Clear block sync state
        while not self.blocks_queue.empty():
            try:
                self.blocks_queue.get_nowait()
            except:
                pass
        self.blocks_in_flight.clear()
        self.downloaded_blocks.clear()
        self.blocks_processing_queue.clear()
    
    def _start_worker_threads(self):
        """Start worker threads for sync operations"""
        self.stop_event.clear()
        self.threads = []
        
        # Create and start threads
        header_thread = threading.Thread(target=self._headers_sync_thread)
        header_thread.daemon = True
        self.threads.append(header_thread)
        header_thread.start()
        
        blocks_thread = threading.Thread(target=self._blocks_sync_thread)
        blocks_thread.daemon = True
        self.threads.append(blocks_thread)
        blocks_thread.start()
        
        processing_thread = threading.Thread(target=self._block_processing_thread)
        processing_thread.daemon = True
        self.threads.append(processing_thread)
        processing_thread.start()
        
        status_thread = threading.Thread(target=self._status_update_thread)
        status_thread.daemon = True
        self.threads.append(status_thread)
        status_thread.start()
    
    def _headers_sync_thread(self):
        """Thread for synchronizing block headers"""
        logger.info("Header synchronization thread started")
        
        # Initial request for headers
        self._request_next_headers(self.current_height + 1)
        
        while not self.stop_event.is_set() and self.syncing and self.mode == self.MODE_HEADERS:
            try:
                # Process headers if we have any
                if len(self.headers_map) > 0:
                    # Verify headers in sequential order
                    next_height = self.current_height + 1
                    while next_height in self.headers_map and next_height <= self.target_height:
                        header_data = self.headers_map[next_height]
                        
                        # Verify header (check difficulty, timestamps, etc.)
                        if self._verify_block_header(header_data, next_height):
                            self.verified_headers.add(next_height)
                            self.current_height = next_height
                            
                            # Add to blocks queue if verified
                            self.blocks_queue.put((next_height, {
                                'height': next_height,
                                'hash': header_data.get('hash'),
                                'header': header_data
                            }))
                            
                            # Update progress
                            self._update_progress()
                            
                        else:
                            logger.warning(f"Invalid header at height {next_height}, stopping sync")
                            self.stop_sync()
                            return
                        
                        # Remove from map to free memory
                        del self.headers_map[next_height]
                        next_height += 1
                    
                    # If we've verified all headers up to target, switch to block download
                    if self.current_height >= self.target_height:
                        logger.info(f"All headers verified up to height {self.target_height}")
                        self.mode = self.MODE_BLOCKS
                        self.status_message = f"Downloading blocks (0/{self.target_height - self.initial_height})"
                
                # Check for timed-out header requests
                now = time.time()
                timeout = 30  # 30 seconds timeout
                timed_out = [h for h in self.headers_in_flight if (now - self.last_progress_time) > timeout]
                
                for height in timed_out:
                    self.headers_in_flight.remove(height)
                    logger.debug(f"Header request for {height} timed out, retrying")
                
                # Request more headers if needed
                if len(self.headers_in_flight) < 5 and self.current_height < self.target_height:
                    next_request_height = self.current_height + 1
                    while next_request_height in self.headers_map:
                        next_request_height += 1
                    
                    if next_request_height <= self.target_height and next_request_height not in self.headers_in_flight:
                        self._request_next_headers(next_request_height)
                
                # Sleep to prevent CPU overuse
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in headers sync thread: {e}")
                time.sleep(1)
    
    def _blocks_sync_thread(self):
        """Thread for downloading blocks"""
        logger.info("Block download thread started")
        
        # Wait until we switch to block download mode
        while not self.stop_event.is_set() and self.syncing:
            if self.mode == self.MODE_BLOCKS:
                break
            time.sleep(0.5)
        
        # If we're not in block download mode, exit
        if not self.syncing or self.mode != self.MODE_BLOCKS:
            return
        
        logger.info("Starting block download phase")
        max_in_flight = 20  # Maximum number of simultaneous block requests
        
        while not self.stop_event.is_set() and self.syncing and self.mode == self.MODE_BLOCKS:
            try:
                # Check if we have blocks to download and still have capacity
                if not self.blocks_queue.empty() and len(self.blocks_in_flight) < max_in_flight:
                    # Get next block to download
                    _, block_data = self.blocks_queue.get()
                    height = block_data['height']
                    block_hash = block_data['hash']
                    
                    # Skip if already downloaded
                    if block_hash in self.downloaded_blocks or block_hash in self.blocks_in_flight:
                        continue
                    
                    # Request this block
                    self._request_block(height, block_hash)
                    self.blocks_in_flight.add(block_hash)
                
                # Check if all blocks are downloaded
                if self.blocks_queue.empty() and len(self.blocks_in_flight) == 0 and self.blocks_downloaded == (self.target_height - self.initial_height):
                    logger.info(f"All blocks downloaded up to height {self.target_height}")
                    
                    # Wait for processing to finish
                    if len(self.blocks_processing_queue) == 0:
                        logger.info("All blocks processed, sync complete")
                        self.mode = self.MODE_IDLE
                        self.syncing = False
                        self.status_message = "Sync complete"
                
                # Check for timed-out block requests
                now = time.time()
                timeout = 60  # 60 seconds timeout for block downloads
                
                timed_out_blocks = []
                for block_hash in self.blocks_in_flight:
                    # We'd need to store request time for each hash, simplified here
                    if now - self.last_progress_time > timeout:
                        timed_out_blocks.append(block_hash)
                
                for block_hash in timed_out_blocks:
                    self.blocks_in_flight.remove(block_hash)
                    # We'd need to re-queue the block, simplified here
                    logger.debug(f"Block request for {block_hash[:8]} timed out, retrying")
                
                # Sleep to prevent CPU overuse
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in blocks sync thread: {e}")
                time.sleep(1)
    
    def _block_processing_thread(self):
        """Thread for processing downloaded blocks"""
        logger.info("Block processing thread started")
        
        while not self.stop_event.is_set():
            try:
                # Process blocks if we have any
                if len(self.blocks_processing_queue) > 0:
                    # Get next block for processing
                    block_data = self.blocks_processing_queue.popleft()
                    
                    # Convert to Block object
                    block = Block.from_dict(block_data)
                    
                    # Add to blockchain
                    if self.blockchain.add_block(block):
                        logger.debug(f"Successfully added block {block.height} to blockchain")
                        self.blocks_downloaded += 1
                        self._update_progress()
                    else:
                        logger.warning(f"Failed to add block {block.height} to blockchain")
                
                # Sleep if no blocks to process
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error in block processing thread: {e}")
                time.sleep(1)
    
    def _status_update_thread(self):
        """Thread for updating sync status"""
        while not self.stop_event.is_set() and self.syncing:
            try:
                # Update status message based on current state
                if self.mode == self.MODE_HEADERS:
                    progress = 0
                    if self.target_height > self.initial_height:
                        progress = min(100, int(100 * (self.current_height - self.initial_height) / (self.target_height - self.initial_height)))
                    self.status_message = f"Synchronizing headers: {self.current_height}/{self.target_height} ({progress}%)"
                    
                elif self.mode == self.MODE_BLOCKS:
                    total_blocks = self.target_height - self.initial_height
                    progress = min(100, int(100 * self.blocks_downloaded / total_blocks)) if total_blocks > 0 else 100
                    
                    # Calculate download speed
                    elapsed = time.time() - self.download_start_time
                    blocks_per_second = self.blocks_downloaded / elapsed if elapsed > 0 else 0
                    
                    self.status_message = (f"Downloading blocks: {self.blocks_downloaded}/{total_blocks} ({progress}%) "
                                         f"- {blocks_per_second:.1f} blocks/s")
                
                # Sleep for a bit
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in status update thread: {e}")
                time.sleep(5)
    
    def _request_next_headers(self, start_height: int):
        """
        Request headers starting from a specific height
        
        Args:
            start_height: Height to start requesting headers from
        """
        try:
            # Find a suitable peer to request from
            peer = self._select_sync_peer()
            if not peer:
                logger.warning("No suitable peers for header sync")
                return
                
            # Add to in-flight set
            end_height = min(start_height + 1999, self.target_height)
            for h in range(start_height, end_height + 1):
                self.headers_in_flight.add(h)
            
            # Create request message
            request = {
                'start_height': start_height,
                'end_height': end_height,
                'count': end_height - start_height + 1
            }
            
            # Send request
            self.p2p_network.active_connections[peer].send_message(
                MessageType.GET_HEADERS, request)
            
            logger.debug(f"Requested headers from {start_height} to {end_height} from {peer}")
            
        except Exception as e:
            logger.error(f"Error requesting headers: {e}")
    
    def _request_block(self, height: int, block_hash: str):
        """
        Request a specific block from peers
        
        Args:
            height: Block height
            block_hash: Block hash
        """
        try:
            # Find a suitable peer to request from
            peer = self._select_sync_peer()
            if not peer:
                logger.warning("No suitable peers for block download")
                return
                
            # Create request message
            request = {
                'items': [{
                    'type': 2,  # Block type
                    'hash': block_hash,
                    'height': height
                }]
            }
            
            # Send request
            self.p2p_network.active_connections[peer].send_message(
                MessageType.GET_DATA, request)
            
            logger.debug(f"Requested block {height} ({block_hash[:8]}) from {peer}")
            
        except Exception as e:
            logger.error(f"Error requesting block: {e}")
    
    def _select_sync_peer(self) -> Optional[str]:
        """
        Select the best peer for sync
        
        Returns:
            Peer ID or None if no suitable peer found
        """
        with self.p2p_network.lock:
            # Find peers with highest height
            best_peer = None
            best_height = self.blockchain.current_height
            
            for peer_id, peer in self.p2p_network.peers.items():
                # Only use connected peers that are ahead of us
                if (peer_id in self.p2p_network.active_connections and 
                    peer.height > best_height):
                    best_peer = peer_id
                    best_height = peer.height
            
            return best_peer
    
    def _verify_block_header(self, header_data: Dict[str, Any], height: int) -> bool:
        """
        Verify a block header
        
        Args:
            header_data: Header data to verify
            height: Expected height
            
        Returns:
            True if header is valid, False otherwise
        """
        try:
            # Verify height
            if header_data.get('height') != height:
                logger.warning(f"Header height mismatch: expected {height}, got {header_data.get('height')}")
                return False
            
            # Check difficulty adjustments (simplified)
            if height % config.DIFFICULTY_ADJUSTMENT_BLOCKS == 0:
                # TODO: Proper difficulty verification
                pass
            
            # More validation can be done here
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying header: {e}")
            return False
    
    def _update_progress(self):
        """Update sync progress statistics"""
        now = time.time()
        self.last_progress_time = now
        
        # Calculate progress percentage
        if self.mode == self.MODE_HEADERS:
            if self.target_height > self.initial_height:
                self.progress_percentage = min(50, int(50 * (self.current_height - self.initial_height) / 
                                            (self.target_height - self.initial_height)))
        elif self.mode == self.MODE_BLOCKS:
            total_blocks = self.target_height - self.initial_height
            if total_blocks > 0:
                block_progress = min(50, int(50 * self.blocks_downloaded / total_blocks))
                self.progress_percentage = 50 + block_progress  # 50% for headers, 50% for blocks
    
    def handle_headers_message(self, headers: List[Dict[str, Any]]):
        """
        Handle received block headers
        
        Args:
            headers: List of header data
        """
        if not self.syncing or self.mode != self.MODE_HEADERS:
            return
            
        count = len(headers)
        if count == 0:
            return
            
        logger.debug(f"Received {count} headers")
        processed = 0
        
        for header in headers:
            height = header.get('height')
            if height is not None and height not in self.headers_map:
                self.headers_map[height] = header
                if height in self.headers_in_flight:
                    self.headers_in_flight.remove(height)
                processed += 1
                self.headers_downloaded += 1
        
        logger.debug(f"Processed {processed} new headers")
    
    def handle_blocks_message(self, blocks: List[Dict[str, Any]]):
        """
        Handle received blocks
        
        Args:
            blocks: List of block data
        """
        if not self.syncing:
            return
            
        count = len(blocks)
        if count == 0:
            return
            
        logger.debug(f"Received {count} blocks")
        
        for block_data in blocks:
            block_hash = block_data.get('hash')
            if block_hash and block_hash in self.blocks_in_flight:
                # Remove from in-flight
                self.blocks_in_flight.remove(block_hash)
                
                # Add to downloaded set
                self.downloaded_blocks.add(block_hash)
                
                # Add to processing queue
                self.blocks_processing_queue.append(block_data)
                
                logger.debug(f"Queued block {block_data.get('height')} ({block_hash[:8]}) for processing")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        return {
            'syncing': self.syncing,
            'mode': self.mode,
            'current_height': self.current_height,
            'target_height': self.target_height,
            'progress': self.progress_percentage,
            'status_message': self.status_message,
            'headers_downloaded': self.headers_downloaded,
            'blocks_downloaded': self.blocks_downloaded
        }


class BlockchainSynchronizer:
    """
    Main blockchain synchronization controller
    
    This class coordinates blockchain synchronization between peers.
    """
    
    def __init__(self, p2p_network: P2PNetwork, blockchain: Blockchain):
        """
        Initialize blockchain synchronizer
        
        Args:
            p2p_network: Reference to P2P network
            blockchain: Reference to blockchain
        """
        self.p2p_network = p2p_network
        self.blockchain = blockchain
        self.sync_state = SyncState(p2p_network, blockchain)
        
        # Register message handlers on the P2P network
        self._register_message_handlers()
    
    def _register_message_handlers(self):
        """Register message handlers with the P2P network"""
        # Integration with the P2P network would require modifications to the P2P class
        # to support external message handler registration
        pass
    
    def start_sync(self) -> bool:
        """
        Start blockchain synchronization
        
        Returns:
            True if sync started successfully, False otherwise
        """
        logger.info("Starting blockchain synchronization")
        
        # Find the best peer to sync from
        best_height = self.blockchain.current_height
        for peer_id, peer in self.p2p_network.peers.items():
            if peer_id in self.p2p_network.active_connections and peer.height > best_height:
                best_height = peer.height
        
        # If no better peer, we're up to date
        if best_height <= self.blockchain.current_height:
            logger.info("Blockchain is up to date")
            return False
        
        # Start sync
        return self.sync_state.start_sync(best_height)
    
    def stop_sync(self):
        """Stop blockchain synchronization"""
        self.sync_state.stop_sync()
    
    def is_syncing(self) -> bool:
        """Check if synchronization is in progress"""
        return self.sync_state.syncing
    
    def handle_headers_message(self, sender: str, headers: List[Dict[str, Any]]):
        """
        Handle headers message from peer
        
        Args:
            sender: Peer ID of sender
            headers: List of header data
        """
        self.sync_state.handle_headers_message(headers)
    
    def handle_blocks_message(self, sender: str, blocks: List[Dict[str, Any]]):
        """
        Handle blocks message from peer
        
        Args:
            sender: Peer ID of sender
            blocks: List of block data
        """
        self.sync_state.handle_blocks_message(blocks)
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current synchronization status"""
        return self.sync_state.get_status()