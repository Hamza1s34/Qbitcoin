#!/usr/bin/env python3
"""
REST API Implementation for Qbitcoin

This file implements a comprehensive REST API for the Qbitcoin blockchain node,
allowing external systems to interact with the node for data retrieval,
transaction submission, and blockchain management.
"""

import os
import sys
import json
import time
import hashlib
import threading
from typing import Dict,  Any, Optional
 

# Import web server frameworks
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query, Path as PathParam, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, validator

# Import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from core import config 
from core.blockchain import Blockchain
from core.block import Block
from core.transaction import Transaction
from core.mempool import Mempool
from core.network.p2p import P2PNetwork
from crypto.falcon import generate_keys, create_signature, verify_signature
from utils.wallet_creator import create_new_wallet, address_from_public_key
from utils.logger import get_logger

# Initialize logger
logger = get_logger("api")

# API Models for request/response validation
class TransactionRequest(BaseModel):
    sender_address: str
    recipient_address: str
    amount: float
    fee: Optional[float] = None
    data: Optional[str] = None
    private_key: str  # Only used in requests, never stored
    public_key: Optional[str] = None  # Optional public key for first transactions
    
    @validator('amount')
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v
        
    @validator('fee')
    def fee_must_be_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError('Fee must be non-negative')
        return v

class WalletCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    passphrase: Optional[str] = None

class BlockchainStatusResponse(BaseModel):
    chain_id: str
    current_height: int
    best_hash: str
    difficulty: float
    total_supply: float
    account_count: int
    mempool_size: int
    sync_status: Dict[str, Any]
    version: str
    uptime: int  # in seconds

class AccountInfoResponse(BaseModel):
    address: str
    balance: float
    transaction_count: int
    first_seen_block: int
    nonce: int
    last_updated_block: int

class APIKeyModel(BaseModel):
    api_key: str = Field(..., min_length=32)

# API Security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

class QbitcoinAPI:
    """
    API interface for Qbitcoin blockchain node
    
    This class implements a comprehensive REST API that allows external systems
    to interact with the Qbitcoin blockchain, query data, manage wallets,
    submit transactions, and monitor the network.
    """
    
    def __init__(self, blockchain: Blockchain, mempool: Mempool, p2p: Optional[P2PNetwork] = None, 
                 host: str = "0.0.0.0", port: int = None):
        """
        Initialize the API server
        
        Args:
            blockchain: Reference to the blockchain
            mempool: Reference to the transaction memory pool
            p2p: Optional reference to the P2P network
            host: Host address to bind the API server to
            port: Port to listen on (defaults to config.API_PORT)
        """
        self.blockchain = blockchain
        self.mempool = mempool
        self.p2p = p2p
        self.host = host
        self.port = port or config.API_PORT
        
        # Initialize the API server
        self.app = FastAPI(
            title="Qbitcoin API",
            description="Comprehensive API for Qbitcoin blockchain node",
            version=config.VERSION,
        )
        
        # Authentication API Keys (in a production system, would use proper database)
        self._api_keys = {}
        self._load_api_keys()
        
        # State variables
        self.start_time = time.time()
        
        # Setup API routes
        self._setup_routes()
        
        # Configure CORS
        self._setup_cors()
        
        # Setup middleware
        self._setup_middleware()
        
    def _setup_cors(self):
        """Configure CORS settings for the API"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, restrict to specific origins
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
    def _setup_middleware(self):
        """Configure middleware for the API"""
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            # Log the request
            logger.debug(f"Request: {request.method} {request.url}")
            
            # Process the request
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log the response time
            response.headers["X-Process-Time"] = str(process_time)
            logger.debug(f"Response time: {process_time:.3f}s Status: {response.status_code}")
            
            return response
            
    def _setup_routes(self):
        """Set up API routes"""
        # Shorthand for route definitions
        app = self.app
        
        # Basic Info Endpoints
        @app.get("/", tags=["General"])
        async def root():
            """Get basic API information"""
            return {
                "name": config.BLOCKCHAIN_NAME,
                "version": config.VERSION,
                "chain_id": self.blockchain.chain_id,
                "height": self.blockchain.current_height,
                "api_version": "1.0"
            }
            
        @app.get("/status", response_model=BlockchainStatusResponse, tags=["General"])
        async def get_status():
            """Get comprehensive blockchain status"""
            best_block = self.blockchain.get_best_block()
            difficulty = best_block.difficulty if best_block else config.INITIAL_DIFFICULTY
            
            # Get sync status if p2p network is available
            sync_status = {}
            if self.p2p:
                if hasattr(self.p2p, 'sync_state'):
                    # Use the sync_state directly if available from P2P
                    sync_status = self.p2p.sync_state
                else:
                    # Basic sync info
                    sync_status = {
                        'syncing': False,
                        'current_height': self.blockchain.current_height
                    }
            
            return {
                "chain_id": self.blockchain.chain_id,
                "current_height": self.blockchain.current_height,
                "best_hash": self.blockchain.best_hash,
                "difficulty": difficulty,
                "total_supply": self.blockchain.get_total_supply(),
                "account_count": self.blockchain.get_account_count(),
                "mempool_size": self.mempool.get_transaction_count(),
                "sync_status": sync_status,
                "version": config.VERSION,
                "uptime": int(time.time() - self.start_time)
            }
            
        # Blockchain Data Endpoints
        @app.get("/blockchain/blocks/latest", tags=["Blockchain"])
        async def get_latest_blocks(limit: int = Query(10, ge=1, le=100)):
            """Get the latest blocks from the blockchain"""
            blocks = []
            current_height = self.blockchain.current_height
            
            # Fetch blocks in reverse order (newest first)
            for height in range(current_height, max(0, current_height - limit), -1):
                block = self.blockchain.get_block_by_height(height)
                if block:
                    blocks.append(block.to_dict())
            
            return {"blocks": blocks, "count": len(blocks)}
            
        @app.get("/blockchain/blocks/height/{height}", tags=["Blockchain"])
        async def get_block_by_height(height: int = PathParam(..., ge=0)):
            """Get a block by its height"""
            block = self.blockchain.get_block_by_height(height)
            if not block:
                raise HTTPException(status_code=404, detail=f"Block at height {height} not found")
            return block.to_dict()
            
        @app.get("/blockchain/blocks/hash/{block_hash}", tags=["Blockchain"])
        async def get_block_by_hash(block_hash: str = PathParam(..., min_length=64, max_length=64)):
            """Get a block by its hash"""
            block = self.blockchain.get_block_by_hash(block_hash)
            if not block:
                raise HTTPException(status_code=404, detail=f"Block with hash {block_hash} not found")
            return block.to_dict()
            
        @app.get("/blockchain/blocks/range", tags=["Blockchain"])
        async def get_blocks_in_range(
            start: int = Query(..., ge=0),
            end: int = Query(..., ge=0)
        ):
            """Get blocks within a height range (inclusive)"""
            # Validate range
            if end < start:
                raise HTTPException(status_code=400, detail="End height must be greater than or equal to start height")
                
            if end > self.blockchain.current_height:
                end = self.blockchain.current_height
                
            # Limit range to prevent excessive load
            if end - start > 100:
                raise HTTPException(status_code=400, detail="Maximum range is 100 blocks")
                
            blocks = self.blockchain.get_blocks_in_range(start, end)
            return {
                "blocks": [block.to_dict() for block in blocks],
                "count": len(blocks),
                "start_height": start,
                "end_height": end
            }
            
        # Transaction Endpoints
        @app.get("/transactions/{tx_hash}", tags=["Transactions"])
        async def get_transaction(tx_hash: str = PathParam(..., min_length=64, max_length=64)):
            """Get transaction details by hash"""
            # Check mempool first for pending transactions
            tx = self.mempool.get_transaction(tx_hash)
            if tx:
                tx_data = tx.to_dict() if hasattr(tx, 'to_dict') else tx
                return {
                    "transaction": tx_data,
                    "confirmations": 0,
                    "status": "pending"
                }
                
            # Search in blockchain
            # This would require a proper transaction index 
            # For now, we'll indicate that we need a proper index
            return {
                "error": "Transaction indexing not implemented yet",
                "message": "Coming soon in the next release"
            }
            
        @app.post("/transactions/send", tags=["Transactions"])
        async def send_transaction(request_data: dict):
            """Submit a transaction to the network"""
            try:
                # Get the signed transaction from the request
                # The transaction should already be signed by the wallet app
                if 'transaction' not in request_data:
                    raise HTTPException(status_code=400, detail="Missing transaction data")
                    
                tx_dict = request_data['transaction']
                
                # Create Transaction object from the received dictionary
                tx = Transaction.from_dict(tx_dict)
                
                # Check if public key is missing but we have a sender address
                sender_address = None
                for tx_input in tx.inputs:
                    if 'address' in tx_input:
                        sender_address = tx_input['address']
                        break
                        
                # If transaction doesn't have a public key but does have a sender address,
                # try to retrieve the public key from the blockchain
                if not tx.public_key and sender_address:
                    logger.info(f"Transaction doesn't include public key. Retrieving from blockchain for address: {sender_address}")
                    # Get the public key from the blockchain database
                    public_key = self.blockchain.get_account_public_key(sender_address)
                    
                    if public_key:
                        logger.info(f"Found public key in blockchain for {sender_address}")
                        # Set the public key in the transaction - just for verification
                        tx.public_key = public_key
                    else:
                        logger.error(f"No public key found in blockchain for address: {sender_address}")
                        raise HTTPException(status_code=400, detail="Cannot verify transaction: public key not found")
                
                # Verify the transaction signature
                if not tx.verify_signature():
                    logger.error("Transaction failed signature verification")
                    raise HTTPException(status_code=400, detail="Transaction failed signature verification")
                
                # If this is not the first transaction from this address, remove the public key
                # from the transaction before adding it to the mempool
                if sender_address and self.blockchain.get_account_public_key(sender_address) and tx.public_key:
                    logger.info(f"Public key already exists for {sender_address}, removing from transaction to save space")
                    # Clear the public key after verification since we already have it in the blockchain
                    tx.public_key = None
                
                # Add to mempool
                if not self.mempool.add_transaction(tx, self.blockchain):
                    raise HTTPException(status_code=400, detail="Transaction rejected by mempool")
                
                # Broadcast to network if P2P is available
                if self.p2p:
                    self.p2p.broadcast_transaction(tx.to_dict())
                    
                return {
                    "success": True,
                    "transaction_hash": tx.hash,
                    "status": "pending",
                    "timestamp": tx.timestamp
                }
                
            except Exception as e:
                logger.error(f"Error processing transaction: {e}")
                raise HTTPException(status_code=400, detail=f"Error processing transaction: {str(e)}")
                
        @app.get("/transactions/mempool", tags=["Transactions"])
        async def get_mempool_transactions(limit: int = Query(100, ge=1, le=1000)):
            """Get pending transactions in the mempool"""
            transactions = self.mempool.get_transactions(limit)
            return {
                "transactions": transactions,
                "count": len(transactions),
                "total_in_mempool": self.mempool.get_transaction_count()
            }
            
        # Account/Address Endpoints
        @app.get("/accounts/{address}", response_model=AccountInfoResponse, tags=["Accounts"])
        async def get_account_info(address: str = PathParam(..., min_length=32)):
            """Get account information and balance"""
            account_info = self.blockchain.get_account_info(address)
            if not account_info:
                # If not found, return zeroed account
                return {
                    "address": address,
                    "balance": 0.0,
                    "transaction_count": 0,
                    "first_seen_block": 0,
                    "nonce": 0,
                    "last_updated_block": 0
                }
                
            # Transform the account_info data to match the required response model
            return {
                "address": account_info["address"],
                "balance": account_info["balance"],
                "transaction_count": account_info.get("tx_count", 0),
                "first_seen_block": account_info.get("first_seen_block", 0),
                "nonce": account_info.get("nonce", 0),
                "last_updated_block": account_info.get("last_updated_block", 0)
            }
            
        @app.get("/accounts/{address}/transactions", tags=["Accounts"])
        async def get_account_transactions(
            address: str = PathParam(..., min_length=32),
            limit: int = Query(50, ge=1, le=100),
            offset: int = Query(0, ge=0)
        ):
            """Get transaction history for an account"""
            transactions = self.blockchain.get_transaction_history(address, limit, offset)
            return {
                "address": address,
                "transactions": transactions,
                "count": len(transactions)
            }
            
        @app.get("/accounts/top", tags=["Accounts"])
        async def get_top_accounts(limit: int = Query(100, ge=1, le=100)):
            """Get top accounts by balance"""
            # This would require a specialized index
            # For now, simulate with a placeholder
            return {
                "message": "Top accounts feature coming soon",
                "accounts": []
            }
            
        # Wallet Management Endpoints (protected by API key)
        @app.post("/wallet/create", tags=["Wallet"], dependencies=[Depends(self.verify_api_key)])
        async def create_wallet(wallet_request: WalletCreateRequest):
            """Create a new wallet"""
            try:
                # Create wallet with utility function
                wallet = create_new_wallet(wallet_request.name, wallet_request.passphrase)
                
                # Return wallet info (excluding private key for security)
                return {
                    "name": wallet_request.name,
                    "address": wallet["address"],
                    "public_key": wallet["public_key"],
                    "created_at": int(time.time()),
                    "success": True
                }
                
            except Exception as e:
                logger.error(f"Error creating wallet: {e}")
                raise HTTPException(status_code=500, detail=f"Error creating wallet: {str(e)}")
                
        @app.post("/wallet/import", tags=["Wallet"], dependencies=[Depends(self.verify_api_key)])
        async def import_wallet():
            """Import an existing wallet from private key"""
            # Implementation would be added here
            return {"message": "Wallet import functionality coming soon"}
            
        # Network Status Endpoints
        @app.get("/network/peers", tags=["Network"])
        async def get_peers():
            """Get information about connected peers"""
            if not self.p2p:
                return {"peers": [], "count": 0, "message": "P2P network not available"}
                
            peers = self.p2p.get_connected_peers()
            return {
                "peers": peers,
                "count": len(peers)
            }
            
        @app.get("/network/stats", tags=["Network"])
        async def get_network_stats():
            """Get network statistics"""
            if not self.p2p:
                return {"message": "P2P network not available"}
                
            stats = self.p2p.get_network_stats()
            return stats
            
        # Mining Endpoints
        @app.get("/mining/info", tags=["Mining"])
        async def get_mining_info():
            """Get current mining information"""
            best_block = self.blockchain.get_best_block()
            next_difficulty = self.blockchain.calculate_next_difficulty()
            
            return {
                "difficulty": best_block.difficulty if best_block else config.INITIAL_DIFFICULTY,
                "next_difficulty": next_difficulty,
                "algorithm": config.MINING_ALGORITHM,
                "current_height": self.blockchain.current_height,
                "next_height": self.blockchain.current_height + 1,
                "reward": config.calculate_block_reward(self.blockchain.current_height + 1),
                "mempool_size": self.mempool.get_transaction_count(),
                "mempool_bytes": self.mempool.get_size_bytes()
            }
            
        @app.post("/mining/submit", tags=["Mining"], dependencies=[Depends(self.verify_api_key)])
        async def submit_block():
            """Submit a mined block"""
            # Implementation would be added here
            return {"message": "Block submission functionality coming soon"}
            
        # Utility Endpoints
        @app.get("/utils/validate-address/{address}", tags=["Utilities"])
        async def validate_address(address: str = PathParam(...)):
            """Validate a wallet address"""
            # Basic address validation (would be more comprehensive in production)
            is_valid = len(address) >= 32 and address.startswith("Q")
            return {
                "address": address,
                "is_valid": is_valid
            }
            
        @app.post("/utils/verify-signature", tags=["Utilities"])
        async def verify_signature_endpoint(
            message: str = Body(...),
            signature: str = Body(...),
            public_key: str = Body(...)
        ):
            """Verify a cryptographic signature"""
            try:
                # Convert message to bytes
                message_bytes = message.encode() if isinstance(message, str) else message
                
                # Verify using Falcon
                is_valid = verify_signature(message_bytes, signature, public_key)
                
                return {
                    "is_valid": is_valid,
                    "message": message,
                    "signature_algorithm": config.SIGNATURE_ALGORITHM
                }
                
            except Exception as e:
                logger.error(f"Error verifying signature: {e}")
                return {
                    "is_valid": False,
                    "error": str(e)
                }
                
        # API Key Management (admin only)
        @app.post("/admin/api-keys/create", tags=["Admin"])
        async def create_api_key(request: Request):
            """Create a new API key (admin only)"""
            # In a real implementation, we would have proper admin authentication
            # This is simplified for demonstration
            
            # Check admin API key from header
            admin_key = request.headers.get("X-Admin-Key")
            if not admin_key or admin_key != "admin-master-key":  # Hardcoded for demo only
                raise HTTPException(status_code=403, detail="Admin authentication required")
                
            # Generate a new API key
            api_key = hashlib.sha256(os.urandom(32)).hexdigest()
            
            # Store API key
            self._api_keys[api_key] = {
                "created_at": int(time.time()),
                "last_used": None
            }
            
            # Save API keys
            self._save_api_keys()
            
            return {
                "api_key": api_key,
                "created_at": self._api_keys[api_key]["created_at"]
            }
            
        @app.delete("/admin/api-keys/{api_key}", tags=["Admin"])
        async def delete_api_key(
            api_key: str = PathParam(...),
            request: Request = None
        ):
            """Delete an API key (admin only)"""
            # Check admin API key from header
            admin_key = request.headers.get("X-Admin-Key")
            if not admin_key or admin_key != "admin-master-key":
                raise HTTPException(status_code=403, detail="Admin authentication required")
                
            # Delete API key
            if api_key in self._api_keys:
                del self._api_keys[api_key]
                self._save_api_keys()
                return {"deleted": True, "api_key": api_key}
            else:
                raise HTTPException(status_code=404, detail="API key not found")
    
    async def verify_api_key(self, api_key: str = Depends(api_key_header)):
        """Verify API key for protected endpoints"""
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="API key is required",
                headers={"WWW-Authenticate": "API-Key"},
            )
            
        if api_key not in self._api_keys:
            raise HTTPException(
                status_code=403,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "API-Key"},
            )
            
        # Update last used timestamp
        self._api_keys[api_key]["last_used"] = int(time.time())
        return api_key
        
    def _load_api_keys(self):
        """Load API keys from file"""
        api_keys_file = config.DATA_DIR / "api_keys.json"
        if api_keys_file.exists():
            try:
                with open(api_keys_file, "r") as f:
                    self._api_keys = json.load(f)
            except Exception as e:
                logger.error(f"Error loading API keys: {e}")
                self._api_keys = {}
        else:
            self._api_keys = {}
            
    def _save_api_keys(self):
        """Save API keys to file"""
        api_keys_file = config.DATA_DIR / "api_keys.json"
        try:
            api_keys_file.parent.mkdir(parents=True, exist_ok=True)
            with open(api_keys_file, "w") as f:
                json.dump(self._api_keys, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving API keys: {e}")
            
    def start(self):
        """Start the API server"""
        logger.info(f"Starting API server on {self.host}:{self.port}")
        
        # Run the API server
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        
    def start_in_thread(self):
        """Start the API server in a background thread"""
        thread = threading.Thread(target=self.start)
        thread.daemon = True
        thread.start()
        return thread
        

# Helper function to create an API instance
def create_api_server(blockchain: Blockchain, mempool: Mempool, p2p: Optional[P2PNetwork] = None, 
                      host: str = "0.0.0.0", port: int = None) -> QbitcoinAPI:
    """
    Create and initialize an API server
    
    Args:
        blockchain: Reference to the blockchain
        mempool: Reference to the transaction memory pool
        p2p: Optional reference to the P2P network
        host: Host address to bind the API server to
        port: Port to listen on (defaults to config.API_PORT)
        
    Returns:
        Initialized API server instance
    """
    return QbitcoinAPI(blockchain, mempool, p2p, host, port)