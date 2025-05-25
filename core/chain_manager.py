"""
Chain Manager for Qbitcoin

This file implements the ChainManager class which handles the low-level
storage and retrieval of blocks in the blockchain, using a file format
similar to Bitcoin's blk*.dat files.
"""

import os
import struct
import time
import hashlib
from pathlib import Path
from typing import Dict, Optional,  BinaryIO, Set
import threading

# Import local modules
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import config 
from core.block import Block
from utils.logger import get_logger
from utils.serializer import serialize_block, deserialize_block

# Initialize logger
logger = get_logger("chain_manager")

# Constants
MAGIC_BYTES = b'\xF9\xBE\xB4\xD9'  # Network magic bytes  
MAX_BLOCK_FILE_SIZE = 128 * 1024 * 1024  # 128 MB per file
BLOCK_INDEX_VERSION = 1

class ChainManager:
    """
    Manages the storage and retrieval of blockchain data using a file-based approach.
    
    This class handles:
    - Block storage in binary files (similar to Bitcoin's blk*.dat files)
    - Block index for quick lookups
    - File management and rotation
    """
    
    def __init__(self, chain_id: Optional[str] = None):
        """
        Initialize the chain manager
        
        Args:
            chain_id: Optional chain ID (for testnet or regtest)
        """
        self.chain_id = chain_id or config.BLOCKCHAIN_ID
        self.chain_dir = config.get_chain_dir(self.chain_id)
        self.blocks_dir = self.chain_dir / "blocks"
        self.blocks_dir.mkdir(exist_ok=True)
        
        # Block file handling
        self.current_file_number = 0
        self.current_file_size = 0
        self.current_file = None
        
        # Block index - maps block hash to file location
        self.block_index = {}  # hash -> (file_num, offset, size)
        self.height_index = {}  # height -> hash
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Initialize
        self._initialize_chain_files()
    
    def _initialize_chain_files(self):
        """Initialize the chain files and indexes"""
        with self.lock:
            # Create directories if they don't exist
            self.blocks_dir.mkdir(exist_ok=True)
            
            # Load block index if it exists
            index_file = self.chain_dir / "blockindex.dat"
            if index_file.exists():
                self._load_block_index()
            
            # Find the next file number to use
            max_file_num = -1
            for file_path in self.blocks_dir.glob("blk*.dat"):
                try:
                    file_num = int(file_path.name[3:-4])  # Extract number from blk<num>.dat
                    max_file_num = max(max_file_num, file_num)
                except (ValueError, IndexError):
                    pass
            
            if max_file_num >= 0:
                self.current_file_number = max_file_num
                # Open current file to get size, then close it
                try:
                    self._open_current_file(for_write=False)
                    self.current_file_size = self.current_file.tell() if self.current_file else 0
                    if self.current_file:
                        self.current_file.close()
                        self.current_file = None
                except Exception as e:
                    logger.error(f"Error opening block file: {e}")
                    self.current_file_size = 0
            
            # If no files exist yet, start with file 0
            if max_file_num < 0:
                self.current_file_number = 0
                self.current_file_size = 0
                
            logger.info(f"Initialized block files, using block file {self.current_file_number} with size {self.current_file_size} bytes")

    def _open_current_file(self, for_write=True) -> Optional[BinaryIO]:
        """
        Open the current block file
        
        Args:
            for_write: Open for writing if True, reading if False
            
        Returns:
            File handle or None if error
        """
        try:
            file_path = self._get_block_file_path(self.current_file_number)
            mode = 'ab' if for_write else 'rb'
            
            if self.current_file:
                self.current_file.close()
                
            self.current_file = open(file_path, mode)
            
            # If opening for append, move to end to get current size
            if for_write:
                self.current_file.seek(0, 2)  # Seek to end
                self.current_file_size = self.current_file.tell()
                
            return self.current_file
            
        except Exception as e:
            logger.error(f"Error opening block file: {e}")
            return None
    
    def _get_block_file_path(self, file_number: int) -> Path:
        """
        Get the path for a block file
        
        Args:
            file_number: The file number
            
        Returns:
            Path object for the block file
        """
        return self.blocks_dir / f"blk{file_number:05d}.dat"
    
    def _load_block_index(self):
        """Load the block index from disk"""
        index_file = self.chain_dir / "blockindex.dat"
        try:
            with open(index_file, 'rb') as f:
                # Read version
                version = struct.unpack('<I', f.read(4))[0]
                if version != BLOCK_INDEX_VERSION:
                    logger.warning(f"Block index version mismatch: {version}")
                
                # Read index count
                count = struct.unpack('<I', f.read(4))[0]
                
                # Read index entries
                for _ in range(count):
                    # Read hash (32 bytes)
                    block_hash_bytes = f.read(32)
                    block_hash = block_hash_bytes.hex()
                    
                    # Read file info (file_num, offset, size)
                    file_num, offset, size = struct.unpack('<III', f.read(12))
                    
                    # Read height separately
                    height = struct.unpack('<i', f.read(4))[0]
                    
                    # Store in indexes
                    self.block_index[block_hash] = (file_num, offset, size)
                    if height >= 0:  # -1 means no height information
                        self.height_index[height] = block_hash
                
                logger.info(f"Loaded block index with {count} entries")
                
        except Exception as e:
            logger.error(f"Error loading block index: {e}")
            # Reset indexes
            self.block_index = {}
            self.height_index = {}
    
    def _save_block_index(self):
        """Save the block index to disk"""
        index_file = self.chain_dir / "blockindex.dat"
        try:
            with open(index_file, 'wb') as f:
                # Write version
                f.write(struct.pack('<I', BLOCK_INDEX_VERSION))
                
                # Write index count
                f.write(struct.pack('<I', len(self.block_index)))
                
                # Write index entries
                for block_hash, (file_num, offset, size) in self.block_index.items():
                    # Get height
                    height = -1
                    for h, h_hash in self.height_index.items():
                        if h_hash == block_hash:
                            height = h
                            break
                    
                    # Write hash (32 bytes)
                    f.write(bytes.fromhex(block_hash))
                    
                    # Write file info (file_num, offset, size)
                    f.write(struct.pack('<III', file_num, offset, size))
                    
                    # Write height separately
                    f.write(struct.pack('<i', height))
                
                logger.info(f"Saved block index with {len(self.block_index)} entries")
                
        except Exception as e:
            logger.error(f"Error saving block index: {e}")
    
    def store_block(self, block: Block) -> bool:
        """
        Store a block in the block files
        
        Args:
            block: The Block object to store
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                # First, check if the block already exists by hash
                if block.hash in self.block_index:
                    logger.info(f"Block {block.hash} already exists in the index")
                    return True
                
                # Next, check if a block at this height already exists and has a different hash
                # This could indicate a chain reorg, but for now we'll just log a warning
                if block.height in self.height_index and self.height_index[block.height] != block.hash:
                    existing_hash = self.height_index[block.height]
                    logger.warning(f"Block at height {block.height} already exists with hash {existing_hash}, " +
                                 f"but new block has hash {block.hash}")
                
                # Make sure all fields in the block are properly set
                # This ensures we have a complete block structure before serializing
                if not block.merkle_root:
                    block.calculate_merkle_root()
                    
                if not block.hash:
                    block.hash = block.calculate_hash()
                
                logger.info(f"Storing block: height={block.height}, hash={block.hash}, " + 
                           f"prev_hash={block.prev_hash}, merkle_root={block.merkle_root}, " +
                           f"timestamp={block.timestamp}, nonce={block.nonce}")
                
                # Serialize the block with our improved format
                block_data = serialize_block(block)
                
                # Debug log size
                logger.debug(f"Serialized block size: {len(block_data)} bytes")
                
                # Check if we need to rotate to a new file
                data_size = len(block_data) + 8  # data + magic + size
                
                if (self.current_file_size + data_size > MAX_BLOCK_FILE_SIZE) or not self._open_current_file(for_write=True):
                    if self.current_file:
                        self.current_file.close()
                        self.current_file = None
                    
                    # Rotate to next file
                    self.current_file_number += 1
                    self.current_file_size = 0
                    logger.info(f"Rotating to new block file: blk{self.current_file_number:05d}.dat")
                    
                    # Open new file
                    if not self._open_current_file(for_write=True):
                        return False
                
                # Get current position
                offset = self.current_file_size
                
                # Write magic bytes
                self.current_file.write(MAGIC_BYTES)
                
                # Write block size
                self.current_file.write(struct.pack('<I', len(block_data)))
                
                # Write block data
                self.current_file.write(block_data)
                self.current_file.flush()
                
                # Ensure data is written to disk
                os.fsync(self.current_file.fileno())
                
                # Update file size
                self.current_file_size += 8 + len(block_data)
                
                # Update index
                self.block_index[block.hash] = (self.current_file_number, offset, 8 + len(block_data))
                self.height_index[block.height] = block.hash
                
                # Save index
                self._save_block_index()
                
                logger.info(f"Successfully stored block {block.hash} at height {block.height} in file {self.current_file_number}")
                return True
                
            except Exception as e:
                logger.error(f"Error storing block: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return False
    
    def get_block(self, block_hash: str) -> Optional[Block]:
        """
        Retrieve a block by its hash
        
        Args:
            block_hash: The hash of the block to retrieve
            
        Returns:
            Block object or None if not found
        """
        with self.lock:
            # Check if block exists in index
            if block_hash not in self.block_index:
                logger.warning(f"Block {block_hash} not found in index")
                return None
            
            try:
                file_num, offset, size = self.block_index[block_hash]
                file_path = self._get_block_file_path(file_num)
                
                with open(file_path, 'rb') as f:
                    f.seek(offset)
                    
                    # Read magic bytes
                    magic = f.read(4)
                    if magic != MAGIC_BYTES:
                        logger.error(f"Invalid magic bytes at {file_path}:{offset}")
                        return None
                    
                    # Read block size
                    block_size = struct.unpack('<I', f.read(4))[0]
                    
                    # Read block data
                    block_data = f.read(block_size)
                    
                    # Deserialize block
                    block = deserialize_block(block_data)
                    return block
                    
            except Exception as e:
                logger.error(f"Error retrieving block {block_hash}: {e}")
                return None
    
    def get_block_by_height(self, height: int) -> Optional[Block]:
        """
        Retrieve a block by its height
        
        Args:
            height: The height of the block to retrieve
            
        Returns:
            Block object or None if not found
        """
        with self.lock:
            if height in self.height_index:
                block_hash = self.height_index[height]
                return self.get_block(block_hash)
            logger.warning(f"Block at height {height} not found in index")
            return None
    
    def has_block(self, block_hash: str) -> bool:
        """
        Check if a block exists in the chain
        
        Args:
            block_hash: The hash of the block to check
            
        Returns:
            True if the block exists, False otherwise
        """
        return block_hash in self.block_index
    
    def get_block_hash_by_height(self, height: int) -> Optional[str]:
        """
        Get the hash of a block at a specific height
        
        Args:
            height: The height to check
            
        Returns:
            Block hash or None if not found
        """
        return self.height_index.get(height)
    
    def scan_blocks(self, start_height: int = 0) -> Dict[int, str]:
        """
        Scan all blocks starting from a height
        
        Args:
            start_height: The height to start scanning from
            
        Returns:
            Dictionary mapping heights to block hashes
        """
        result = {}
        for height, block_hash in self.height_index.items():
            if height >= start_height:
                result[height] = block_hash
        return dict(sorted(result.items()))
    
    def rebuild_index(self) -> bool:
        """
        Rebuild the block index by scanning all block files
        
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                # Reset indexes
                self.block_index = {}
                self.height_index = {}
                
                # Scan all block files
                for file_path in sorted(self.blocks_dir.glob("blk*.dat")):
                    try:
                        file_num = int(file_path.name[3:-4])
                    except (ValueError, IndexError):
                        continue
                    
                    logger.info(f"Scanning block file: {file_path}")
                    
                    offset = 0
                    with open(file_path, 'rb') as f:
                        while True:
                            # Record current position
                            pos = f.tell()
                            
                            # Read magic bytes
                            magic = f.read(4)
                            if not magic or len(magic) < 4:
                                break  # End of file
                            
                            if magic != MAGIC_BYTES:
                                # Not a valid block, skip ahead and search for magic
                                f.seek(pos + 1)
                                continue
                            
                            # Read block size
                            size_bytes = f.read(4)
                            if not size_bytes or len(size_bytes) < 4:
                                break
                                
                            block_size = struct.unpack('<I', size_bytes)[0]
                            
                            # Read block data
                            block_data = f.read(block_size)
                            if len(block_data) < block_size:
                                break  # Incomplete block
                            
                            try:
                                # Deserialize to get block info
                                block = deserialize_block(block_data)
                                
                                # Add to index
                                self.block_index[block.hash] = (file_num, pos, 8 + block_size)
                                self.height_index[block.height] = block.hash
                                
                            except Exception as e:
                                logger.error(f"Error deserializing block at {file_path}:{pos}: {e}")
                                
                            # Move to the next potential block
                            offset = f.tell()
                
                # Save rebuilt index
                self._save_block_index()
                
                logger.info(f"Index rebuilt with {len(self.block_index)} blocks")
                return True
                
            except Exception as e:
                logger.error(f"Error rebuilding index: {e}")
                return False
    
    def get_chain_stats(self) -> Dict:
        """
        Get statistics about the blockchain storage
        
        Returns:
            Dictionary with chain stats
        """
        stats = {
            "block_count": len(self.block_index),
            "file_count": 0,
            "total_size": 0,
            "files": []
        }
        
        try:
            # Get file stats
            for file_path in sorted(self.blocks_dir.glob("blk*.dat")):
                file_size = file_path.stat().st_size
                stats["files"].append({
                    "name": file_path.name,
                    "size": file_size
                })
                stats["total_size"] += file_size
                stats["file_count"] += 1
        
        except Exception as e:
            logger.error(f"Error getting chain stats: {e}")
        
        return stats
    
    def prune_orphaned_blocks(self, best_chain_blocks: Set[str]) -> int:
        """
        Remove blocks that are not part of the best chain
        
        Args:
            best_chain_blocks: Set of block hashes in the best chain
            
        Returns:
            Number of pruned blocks
        """
        # This is a placeholder - full implementation would require:
        # 1. Finding blocks not in the best chain
        # 2. Removing them from indexes
        # 3. Keeping track of which files have been modified
        # 4. Rewriting those files without the orphaned blocks
        # This is complex and would require careful handling
        logger.warning("Block pruning not fully implemented")
        return 0
    
    def close(self):
        """Close open files and save indexes"""
        with self.lock:
            if self.current_file:
                self.current_file.close()
                self.current_file = None
            self._save_block_index()