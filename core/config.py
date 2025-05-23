
"""
Qbitcoin Blockchain Configuration

This file contains all the configuration parameters for the Qbitcoin blockchain,
including consensus rules, network settings .
"""

import os
from pathlib import Path
from typing import  Optional

# Import logger for configuration-related logging
from utils.logger import get_logger

# Initialize logger
logger = get_logger("config")

#######################################
# BLOCKCHAIN IDENTITY & BASIC SETTINGS
#######################################

# Blockchain name and version
BLOCKCHAIN_NAME = "Qbitcoin"
BLOCKCHAIN_TICKER = "QBIT"
VERSION = "0.1.0"  # Semantic versioning
BLOCKCHAIN_ID = "qbitcoin-mainnet-v1"  # Unique blockchain identifier
#GENESIS_NONCE = 0
GENESIS_VERSION = 1
# Get current project directory
PROJECT_DIR = Path(os.path.abspath(os.path.dirname(__file__)))

# Home directory for blockchain data - changed to use project directory for testing
HOME_DIR = PROJECT_DIR / "data"
DATA_DIR = HOME_DIR / "blockchain"
CHAIN_DATA_DIR = DATA_DIR / "chain"
WALLET_DIR = HOME_DIR / "wallets"
TEMP_DIR = HOME_DIR / "temp"
LOG_DIR = HOME_DIR / "logs"

#######################################
# CONSENSUS PARAMETERS
#######################################

# Supply and emission controls
MAX_SUPPLY = 30_000_000  # Maximum supply in QBIT
INITIAL_SUPPLY = 20_000_000  # Initial supply in QBIT (pre-mined)
CIRCULATING_SUPPLY = INITIAL_SUPPLY  # Will be updated as blocks are mined

# Block parameters
BLOCK_TIME = 60  # Target time between blocks in seconds (1 minute)
DIFFICULTY_ADJUSTMENT_BLOCKS = 3  # Number of blocks for difficulty adjustment (~ 2 weeks)
DIFFICULTY_ADJUSTMENT_TIMESPAN = BLOCK_TIME * DIFFICULTY_ADJUSTMENT_BLOCKS  # Target timespan

# Initial mining difficulty (lower means easier)
INITIAL_DIFFICULTY = 0.001  # Starting difficulty
MINIMUM_DIFFICULTY = 0.001  # Never go below this difficulty
#TEST_MINING_DIFFICULTY = 0.001  # Very easy difficulty for testing
DIFFICULTY_PRECISION = 8  # Decimal precision for difficulty calculations

# Mining reward parameters
INITIAL_BLOCK_REWARD = 2.5  # Initial reward per block in QBIT
HALVING_INTERVAL = 1_051_200  # Blocks between halvings (~2 years)

# Maturity period (how many confirmations until rewards can be spent)
COINBASE_MATURITY = 10  # Number of blocks

 

#######################################
# NETWORK CONFIGURATION
#######################################

# Network ports
P2P_PORT = 9567  # Default port for peer-to-peer communication
API_PORT = 9568  # Default port for API server
RPC_PORT = 9569  # Default port for RPC server

# Bootstrap nodes (initial peers to connect to)
BOOTSTRAP_NODES = [
    
]

# Network magic bytes (to identify network messages)
NETWORK_MAGIC = b'QBIT'
TESTNET_MAGIC = b'QBTT'

# Maximum number of peers to maintain connections with
MAX_PEERS = 125
OUTBOUND_PEER_TARGET = 8  # Target number of outbound connections

# Peer connection parameters
PEER_CONNECTION_TIMEOUT = 10  # Connection timeout in seconds
PEER_HANDSHAKE_TIMEOUT = 30  # Handshake timeout in seconds
PEER_PING_INTERVAL = 120  # Ping interval in seconds

#######################################
# TRANSACTION PARAMETERS
#######################################

# Transaction fees
MIN_RELAY_FEE = 0.00001  # Minimum fee per KB to relay transactions
RECOMMENDED_FEE = 0.0001  # Recommended fee per KB

# Transaction size and field limits
MAX_BLOCK_SIZE = 2_000_000  # Maximum block size in bytes (2 MB)
MAX_TX_SIZE = 100_000  # Maximum transaction size in bytes
MAX_SIGNATURE_SIZE = 1024  # Maximum signature size (for Falcon-512)

# Memory pool settings
MEMPOOL_MAX_SIZE = 300_000_000  # Maximum mempool size in bytes (300 MB)
MEMPOOL_EXPIRY = 48  # Hours before a transaction expires from mempool

#######################################
# CRYPTOGRAPHIC PARAMETERS
#######################################

# Signature algorithm settings
SIGNATURE_ALGORITHM = "falcon-512"  # Default signature algorithm
HASH_ALGORITHM = "sha3-256"  # Default hashing algorithm
MINING_ALGORITHM = "sha3-256"  # PoW mining algorithm

# Wallet encryption parameters
WALLET_KDF_ITERATIONS = 600_000  # Iterations for key derivation function
WALLET_KDF_ALGORITHM = "argon2id"  # Key derivation function for wallet encryption

#######################################
# GUI AND CLI PARAMETERS
#######################################

# User interface settings
GUI_DEFAULT_THEME = "dark"  # Default theme for GUI
GUI_REFRESH_INTERVAL = 10  # UI refresh interval in seconds
GUI_MAX_TRANSACTIONS = 100  # Maximum transactions to display in UI

# CLI parameters
CLI_HISTORY_FILE = HOME_DIR / "cli_history"
CLI_MAX_HISTORY = 1000

#######################################
# DEVELOPMENT AND TESTING
#######################################

# Feature flags
ENABLE_ZKPROOF = True  # Enable zero-knowledge proof features
ENABLE_SMART_CONTRACTS = False  # Smart contracts not implemented yet
ENABLE_MULTI_SIG = True  # Enable multi-signature transactions

# Testing parameters
TESTNET = False  # Whether running in testnet mode
REGTEST = False  # Whether running in regression test mode

# Debug settings
DEBUG = False  # Global debug flag
PROFILE = False  # Enable performance profiling


#######################################
# HELPER FUNCTIONS
#######################################

def calculate_block_reward(block_height: int) -> float:
    """
    Calculate the block reward at a given height.
    
    Args:
        block_height: The block height
        
    Returns:
        The block reward in QBIT
    """
    halvings = block_height // HALVING_INTERVAL
    
    # No more rewards after 64 halvings (effectively 0)
    if halvings >= 64:
        return 0
        
    return INITIAL_BLOCK_REWARD / (2 ** halvings)


def get_chain_dir(chain_id: Optional[str] = None) -> Path:
    """
    Get the directory for a specific chain.
    
    Args:
        chain_id: The chain ID (default is the main blockchain ID)
        
    Returns:
        Path to the chain directory
    """
    c_id = chain_id or BLOCKCHAIN_ID
    chain_path = CHAIN_DATA_DIR / c_id
    chain_path.mkdir(parents=True, exist_ok=True)
    return chain_path


def load_environment_overrides() -> None:
    """
    Load configuration overrides from environment variables.
    This allows for customization without changing the code.
    """
    # Example overrides (not comprehensive, expand as needed)
    global P2P_PORT, API_PORT, DATA_DIR, DEBUG, TESTNET
    
    if os.environ.get("QBIT_P2P_PORT"):
        P2P_PORT = int(os.environ["QBIT_P2P_PORT"])
        
    if os.environ.get("QBIT_API_PORT"):
        API_PORT = int(os.environ["QBIT_API_PORT"])
        
    if os.environ.get("QBIT_DATA_DIR"):
        DATA_DIR = Path(os.environ["QBIT_DATA_DIR"])
        
    if os.environ.get("QBIT_DEBUG") in ("1", "true", "yes"):
        DEBUG = True
        
    if os.environ.get("QBIT_TESTNET") in ("1", "true", "yes"):
        TESTNET = True
        BLOCKCHAIN_ID = "qbitcoin-testnet-v1"


# Load any environment variable overrides
load_environment_overrides()

# Create necessary directories
for directory in [DATA_DIR, CHAIN_DATA_DIR, WALLET_DIR, TEMP_DIR, LOG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Log configuration loading
if DEBUG:
    logger.info(f"Loaded {BLOCKCHAIN_NAME} configuration, version {VERSION}")
    if TESTNET:
        logger.info("Running in TESTNET mode")
    elif REGTEST:
        logger.info("Running in REGTEST mode")