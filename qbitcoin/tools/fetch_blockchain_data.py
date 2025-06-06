#!/usr/bin/env python3
"""
QRL Blockchain Data Fetcher

This script directly accesses the QRL blockchain database to fetch blocks
and print them in human-readable JSON format.

Usage:
    python fetch_blockchain_data.py [options]

Options:
    --start-block N     Start from block number N (default: 0)
    --end-block N       End at block number N (default: latest)
    --block-count N     Fetch N blocks starting from start-block
    --output-file FILE  Save output to file instead of stdout
    --pretty            Pretty print JSON with indentation
    --include-txs       Include full transaction details
    --data-dir PATH     Path to blockchain data directory
"""

import sys
import os
import json
import argparse
from typing import Optional, Dict, Any, List

# Add the parent directory to Python path to import QRL modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from qbitcoin.core.State import State
    from qbitcoin.core.ChainManager import ChainManager
    from qbitcoin.core import config
    from qbitcoin.core.Block import Block
    from qbitcoin.core.GenesisBlock import GenesisBlock
    from qbitcoin.generated.qbit_pb2 import Block as PBBlock
    from google.protobuf.json_format import MessageToJson
except ImportError as e:
    print(f"Error importing QRL modules: {e}")
    print("Make sure you're running this script from the QRL project directory")
    sys.exit(1)


class BlockchainDataFetcher:
    """Fetches and formats blockchain data from the QRL database."""
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize the blockchain data fetcher.
        
        Args:
            data_dir: Path to the blockchain data directory
        """
        # Set data directory if provided
        if data_dir:
            config.user.data_dir = data_dir
        
        # Initialize state and chain manager
        self.state = State()
        self.chain_manager = ChainManager(self.state)
        
        print(f"Initialized blockchain reader with data directory: {config.user.data_dir}")
        print(f"Current chain height: {self.state.get_mainchain_height()}")
    
    def get_block_data(self, block_number: int, include_transactions: bool = True) -> Optional[Dict[str, Any]]:
        """Fetch a single block and convert it to human-readable format.
        
        Args:
            block_number: The block number to fetch
            include_transactions: Whether to include full transaction details
            
        Returns:
            Dictionary containing block data or None if block not found
        """
        try:
            # Get block from chain manager
            block = self.chain_manager.get_block_by_number(block_number)
            
            if not block:
                return None
            
            # Convert block to JSON using protobuf's built-in JSON conversion
            block_json_str = MessageToJson(block.pbdata, sort_keys=True)
            
            # Parse JSON string to dictionary for manipulation
            block_data = json.loads(block_json_str)
            
            # Add human-readable fields
            block_data['human_readable'] = {
                'block_number': block_number,
                'timestamp_readable': self._format_timestamp(block.timestamp),
                'block_size_bytes': len(block.serialize()),
                'transaction_count': len(block.transactions),
                'block_hash': block.headerhash.hex(),
                'previous_hash': block.prev_headerhash.hex(),
                'merkle_root': block.blockheader.tx_merkle_root.hex(),
                'mining_nonce': str(block.mining_nonce),
                'extra_nonce': str(block.blockheader.extra_nonce),
                'block_reward': str(block.block_reward),
                'fee_reward': str(block.fee_reward),
                'total_reward': str(block.block_reward + block.fee_reward)
            }
            
            # Add transaction summaries if requested
            if include_transactions and block.transactions:
                block_data['human_readable']['transaction_summaries'] = []
                for i, tx_pbdata in enumerate(block.transactions):
                    # Convert protobuf transaction to Transaction object
                    from qbitcoin.core.txs.Transaction import Transaction
                    tx = Transaction.from_pbdata(tx_pbdata)
                    
                    tx_summary = {
                        'index': i,
                        'type': tx.type,
                        'txhash': tx.txhash.hex(),
                        'fee': str(tx.fee),
                        'nonce': str(tx.nonce),
                        'signature': tx.signature.hex()[:64] + '...' if len(tx.signature.hex()) > 64 else tx.signature.hex()
                    }
                    
                    # Add type-specific information
                    if hasattr(tx, 'pbdata') and hasattr(tx.pbdata, 'coinbase') and tx.pbdata.WhichOneof('transactionType') == 'coinbase':
                        tx_summary['coinbase_to'] = tx.pbdata.coinbase.addr_to.hex()
                        tx_summary['coinbase_amount'] = str(tx.pbdata.coinbase.amount)
                    elif hasattr(tx, 'pbdata') and hasattr(tx.pbdata, 'transfer') and tx.pbdata.WhichOneof('transactionType') == 'transfer':
                        tx_summary['transfer_from'] = tx.addr_from.hex()
                        tx_summary['transfer_to'] = [addr.hex() for addr in tx.pbdata.transfer.addrs_to]
                        tx_summary['transfer_amounts'] = [str(amount) for amount in tx.pbdata.transfer.amounts]
                    
                    block_data['human_readable']['transaction_summaries'].append(tx_summary)
            
            return block_data
            
        except Exception as e:
            print(f"Error fetching block {block_number}: {e}")
            return None
    
    def _format_timestamp(self, timestamp: int) -> str:
        """Convert timestamp to human-readable format."""
        import datetime
        try:
            dt = datetime.datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except (ValueError, OSError):
            return f"Invalid timestamp: {timestamp}"
    
    def fetch_blocks(self, 
                    start_block: int = 0, 
                    end_block: Optional[int] = None,
                    block_count: Optional[int] = None,
                    include_transactions: bool = True) -> List[Dict[str, Any]]:
        """Fetch multiple blocks from the blockchain.
        
        Args:
            start_block: Starting block number
            end_block: Ending block number (inclusive)
            block_count: Number of blocks to fetch (alternative to end_block)
            include_transactions: Whether to include transaction details
            
        Returns:
            List of block data dictionaries
        """
        chain_height = self.state.get_mainchain_height()
        
        # Determine the actual end block
        if end_block is None:
            if block_count is not None:
                end_block = min(start_block + block_count - 1, chain_height)
            else:
                end_block = chain_height
        else:
            end_block = min(end_block, chain_height)
        
        print(f"Fetching blocks {start_block} to {end_block} (chain height: {chain_height})")
        
        blocks = []
        for block_num in range(start_block, end_block + 1):
            print(f"Fetching block {block_num}...", end=' ')
            
            block_data = self.get_block_data(block_num, include_transactions)
            if block_data:
                blocks.append(block_data)
                print("✓")
            else:
                print("✗ (not found)")
        
        return blocks
    
    def close(self):
        """Clean up resources."""
        # State doesn't have a close method, so we just pass
        pass


def main():
    parser = argparse.ArgumentParser(
        description='Fetch blocks from QRL blockchain database and print as JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--start-block', type=int, default=0,
                       help='Start from block number N (default: 0)')
    parser.add_argument('--end-block', type=int, default=None,
                       help='End at block number N (default: latest)')
    parser.add_argument('--block-count', type=int, default=None,
                       help='Fetch N blocks starting from start-block')
    parser.add_argument('--output-file', type=str, default=None,
                       help='Save output to file instead of stdout')
    parser.add_argument('--pretty', action='store_true',
                       help='Pretty print JSON with indentation')
    parser.add_argument('--include-txs', action='store_true', default=True,
                       help='Include full transaction details (default: True)')
    parser.add_argument('--no-txs', action='store_true',
                       help='Exclude transaction details')
    parser.add_argument('--data-dir', type=str, default=None,
                       help='Path to blockchain data directory')
    
    args = parser.parse_args()
    
    # Handle transaction inclusion flag
    include_transactions = args.include_txs and not args.no_txs
    
    try:
        # Initialize the fetcher
        fetcher = BlockchainDataFetcher(args.data_dir)
        
        # Fetch the blocks
        blocks = fetcher.fetch_blocks(
            start_block=args.start_block,
            end_block=args.end_block,
            block_count=args.block_count,
            include_transactions=include_transactions
        )
        
        # Prepare output
        output_data = {
            'metadata': {
                'total_blocks_fetched': len(blocks),
                'start_block': args.start_block,
                'end_block': blocks[-1]['human_readable']['block_number'] if blocks else None,
                'include_transactions': include_transactions,
                'generated_at': str(datetime.datetime.now())
            },
            'blocks': blocks
        }
        
        # Format JSON
        if args.pretty:
            json_output = json.dumps(output_data, indent=2, ensure_ascii=False)
        else:
            json_output = json.dumps(output_data, ensure_ascii=False)
        
        # Output to file or stdout
        if args.output_file:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"\nOutput saved to: {args.output_file}")
        else:
            print("\n" + "="*80)
            print("BLOCKCHAIN DATA:")
            print("="*80)
            print(json_output)
        
        # Clean up
        fetcher.close()
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    import datetime
    main()


# Example usage:
# python qbitcoin/tools/fetch_blockchain_data.py --start-block 0 --pretty --include-txs
#cd /workspaces/QRL && python qbitcoin/tools/fetch_blockchain_data.py --start-block 0 --pretty --include-txs