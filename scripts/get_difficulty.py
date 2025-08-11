#!/usr/bin/env python3
"""
Simple script to get Qbitcoin network difficulty using generated protobuf files
"""

import grpc
import sys
import os

# Add the qbitcoin package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from qbitcoin.generated import qbit_pb2, qbit_pb2_grpc

def get_difficulty():
    """Get current network difficulty"""
    
    # Connect to Qbitcoin node
    channel = grpc.insecure_channel('134.122.79.166:19009')
    stub = qbit_pb2_grpc.PublicAPIStub(channel)
    
    try:
        # Create request with timeseries enabled
        request = qbit_pb2.GetStatsReq(include_timeseries=True)
        
        # Get stats
        response = stub.GetStats(request)
        
        # Extract latest difficulty
        if response.block_timeseries:
            latest_block = response.block_timeseries[-1]
            difficulty = latest_block.difficulty
            
            print(f"Current Difficulty: {difficulty}")
            print(f"Block Number: {latest_block.number}")
            print(f"Timestamp: {latest_block.timestamp}")
            
            return difficulty
        else:
            print("No timeseries data available")
            return None
            
    except grpc.RpcError as e:
        print(f"gRPC Error: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        channel.close()

if __name__ == "__main__":
    difficulty = get_difficulty()
    if difficulty:
        print(f"\nDifficulty: {difficulty}")
    else:
        print("Failed to get difficulty")
