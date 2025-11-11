# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
import sys
import os

# Add the project root to Python path - fix for direct execution
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up one level from qbitcoin/ to project root
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Also add current directory to path for relative imports
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)



import argparse
import os
import grpc
from google.protobuf.json_format import MessageToJson
from qbitcoin.core import config
from pyqrllib.pyqrllib import hstr2bin, bin2hstr

from qbitcoin.generated import qbit_pb2_grpc, qbit_pb2, qbitmining_pb2, qbitmining_pb2_grpc
from flask import Flask, Response, request
from jsonrpc.backend.flask import api

app = Flask(__name__)


@app.route('/api/<api_method_name>')
def api_proxy(api_method_name):
    """
    Proxy JSON RPC requests to the gRPC server as well as converts back gRPC response
    to JSON.
    :param api_method_name:
    :return:
    """
    stub = qbit_pb2_grpc.PublicAPIStub(grpc.insecure_channel('{}:{}'.format(config.user.public_api_host,
                                                                           config.user.public_api_port),
                                                            options=[('grpc.max_receive_message_length', 10485760)]))
    public_api = qbit_pb2.DESCRIPTOR.services_by_name['PublicAPI']
    api_method = public_api.FindMethodByName(api_method_name)
    api_request = getattr(qbit_pb2, api_method.input_type.name)()

    for arg in request.args:
        if arg not in api_method.input_type.fields_by_name:
            raise Exception('Invalid args %s', arg)
        field = api_method.input_type.fields_by_name[arg]
        data_type = type(getattr(api_request, arg))
        
        if data_type == bool and request.args[arg].lower() == 'false':
            continue
        
        arg_value = request.args.get(arg)
        if arg_value is None or arg_value == '':
            continue
            
        # Special handling for transaction_signed field - it expects a Transaction protobuf object
        if arg == 'transaction_signed':
            try:
                print(f"DEBUG: Parsing transaction_signed, hex length: {len(arg_value)}")
                # Convert hex string to bytes
                transaction_bytes = bytes.fromhex(arg_value)
                print(f"DEBUG: Transaction bytes length: {len(transaction_bytes)}")
                # Parse the bytes as a Transaction protobuf
                transaction_obj = qbit_pb2.Transaction()
                transaction_obj.ParseFromString(transaction_bytes)
                print(f"DEBUG: Successfully parsed transaction protobuf")
                
                # Use CopyFrom to copy the transaction into the request
                api_request.transaction_signed.CopyFrom(transaction_obj)
                print(f"DEBUG: Successfully copied transaction to request")
                continue  # Skip normal setattr
            except Exception as e:
                print(f"DEBUG: Failed to parse transaction protobuf: {e}")
                raise Exception(f'Invalid transaction format for {arg}: {str(e)}')
            
        # Handle bytes fields specially - expect hex string input or Q-address format
        elif data_type == bytes:
            try:
                # Handle Q-address format (Qbitcoin address)
                if arg_value.startswith('Q'):
                    # Validate Q-address format
                    if len(arg_value) != 51:  # Q + 50 hex chars
                        raise ValueError(f'Invalid Q-address length: {len(arg_value)}, expected 51')
                    # Remove 'Q' prefix and convert hex to bytes using pyqrllib
                    from pyqrllib.pyqrllib import hstr2bin
                    value = bytes(hstr2bin(arg_value[1:]))
                else:
                    # Handle raw hex input (backwards compatibility)
                    if len(arg_value) == 70:  # Old test format, reject it
                        raise ValueError(f'Invalid address format. Use Q-prefixed addresses (e.g., Q015b13be...). Length: {len(arg_value)}')
                    # For other hex fields, convert normally
                    value = bytes.fromhex(arg_value)
            except ValueError as e:
                raise Exception(f'Invalid address format for {arg}: {arg_value}. Use Q-prefixed addresses (e.g., Q015b13be...). Error: {str(e)}')
        else:
            value = data_type(arg_value)
        
        setattr(api_request, arg, value)

    resp = getattr(stub, api_method_name)(api_request, timeout=10)
    return Response(response=MessageToJson(resp, sort_keys=True), status=200, mimetype='application/json')


def get_mining_stub():
    global mining_stub
    return mining_stub


def get_public_stub():
    global public_stub
    return public_stub


@api.dispatcher.add_method
def getlastblockheader(height=0):
    try:
        stub = get_mining_stub()
        # If no height specified or height is 0, get the latest block
        # Otherwise get the specific height
        if height is None:
            height = 0  # This will get latest block
        request = qbitmining_pb2.GetLastBlockHeaderReq(height=height)
        grpc_response = stub.GetLastBlockHeader(request=request, timeout=10)
    except Exception as e:
        return {
            "error": "Mining API not available",
            "details": str(e),
            "status": "ERROR"
        }

    block_header = {
        'difficulty': grpc_response.difficulty,
        'height': grpc_response.height,
        'timestamp': grpc_response.timestamp,
        'reward': grpc_response.reward,
        'hash': grpc_response.hash,
        'depth': grpc_response.depth
    }

    resp = {
        "block_header": block_header,
        "status": "OK"
    }
    return resp


@api.dispatcher.add_method
def getblockheaderbyheight(height):
    # Ensure we pass the exact height requested
    stub = get_mining_stub()
    request = qbitmining_pb2.GetLastBlockHeaderReq(height=int(height))
    grpc_response = stub.GetLastBlockHeader(request=request, timeout=10)

    block_header = {
        'difficulty': grpc_response.difficulty,
        'height': grpc_response.height,
        'timestamp': grpc_response.timestamp,
        'reward': grpc_response.reward,
        'hash': grpc_response.hash,
        'depth': grpc_response.depth
    }

    resp = {
        "block_header": block_header,
        "status": "OK"
    }
    return resp


@api.dispatcher.add_method
def getblocktemplate(reserve_size, wallet_address):
    try:
        stub = get_mining_stub()
        # Convert wallet address from hex string to bytes, handling Q prefix
        if wallet_address.startswith('Q'):
            wallet_addr_bytes = bytes(hstr2bin(wallet_address[1:]))  # Skip 'Q' prefix
        else:
            wallet_addr_bytes = bytes(hstr2bin(wallet_address))
        
        request = qbitmining_pb2.GetBlockToMineReq(wallet_address=wallet_addr_bytes)
        grpc_response = stub.GetBlockToMine(request=request, timeout=10)
    except Exception as e:
        return {
            "error": "Mining API not available or template generation failed",
            "details": str(e),
            "status": "ERROR"
        }
    resp = {
        'blocktemplate_blob': grpc_response.blocktemplate_blob,
        'difficulty': grpc_response.difficulty,
        'height': grpc_response.height,
        'reserved_offset': grpc_response.reserved_offset,
        'seed_hash': grpc_response.seed_hash,
        'status': 'OK'
    }

    return resp


@api.dispatcher.add_method
def getheight():
    stub = get_public_stub()
    grpc_response = stub.GetHeight(request=qbit_pb2.GetHeightReq())

    resp = {'height': grpc_response.height}
    return resp


@api.dispatcher.add_method
def submitblock(blob):
    try:
        stub = get_mining_stub()
        request = qbitmining_pb2.SubmitMinedBlockReq(blob=bytes(hstr2bin(blob)))
        response = stub.SubmitMinedBlock(request=request, timeout=10)
        if response.error:
            return {'status': 'ERROR', 'error': 'Block submission rejected by node'}
        return {'status': 'OK', 'error': 0}
    except Exception as e:
        return {
            "error": "Mining API not available or block submission failed",
            "details": str(e),
            "status": "ERROR"
        }


@api.dispatcher.add_method
def getblockminingcompatible(height):
    stub = get_mining_stub()
    request = qbitmining_pb2.GetBlockMiningCompatibleReq(height=height)
    response = stub.GetBlockMiningCompatible(request=request, timeout=10)
    return MessageToJson(response, sort_keys=True)


app.add_url_rule('/json_rpc', 'api', api.as_view(), methods=['POST'])


def parse_arguments():
    parser = argparse.ArgumentParser(description='QBitcoin node')
    parser.add_argument('--qrldir', '-d', dest='qrl_dir', default=config.user.qrl_dir,
                        help="Use a different directory for node data/configuration")
    parser.add_argument('--network-type', dest='network_type', choices=['mainnet', 'testnet'],
                        default='mainnet', required=False, help="Runs QRL Testnet Node")
    return parser.parse_args()


def main():
    args = parse_arguments()

    qrl_dir_post_fix = ''
    copy_files = []
    if args.network_type == 'testnet':
        qrl_dir_post_fix = '-testnet'
        package_directory = os.path.dirname(os.path.abspath(__file__))
        copy_files.append(os.path.join(package_directory, 'network/testnet/genesis.yml'))
        copy_files.append(os.path.join(package_directory, 'network/testnet/config.yml'))

    config.user.qrl_dir = os.path.expanduser(os.path.normpath(args.qrl_dir) + qrl_dir_post_fix)
    config.create_path(config.user.qrl_dir, copy_files)
    config.user.load_yaml(config.user.config_path)

    global mining_stub, public_stub
    mining_stub = qbitmining_pb2_grpc.MiningAPIStub(grpc.insecure_channel('{0}:{1}'.format(config.user.mining_api_host,
                                                                                          config.user.mining_api_port)))
    public_stub = qbit_pb2_grpc.PublicAPIStub(grpc.insecure_channel('{0}:{1}'.format(config.user.public_api_host,
                                                                                    config.user.public_api_port),
                                                                   options=[('grpc.max_receive_message_length',
                                                                             10485760)]))
    app.run(host=config.user.grpc_proxy_host, port=config.user.grpc_proxy_port, threaded=False)


if __name__ == '__main__':
    main()
