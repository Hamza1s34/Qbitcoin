# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
import contextlib
import os
import shutil
import tempfile
import time
from copy import deepcopy

import simplejson as json
from mock import mock
from pyqrllib.pyqrllib import bin2hstr, hstr2bin
from pyqryptonight.pyqryptonight import StringToUInt256

from qbitcoin.core import config
from qbitcoin.core.Block import Block
from qbitcoin.core.BlockMetadata import BlockMetadata
from qbitcoin.core.ChainManager import ChainManager
from qbitcoin.core.OptimizedAddressState import OptimizedAddressState
from qbitcoin.core.GenesisBlock import GenesisBlock
from qbitcoin.core.txs.Transaction import Transaction
from qbitcoin.core.txs.SlaveTransaction import SlaveTransaction
from qbitcoin.core.txs.TokenTransaction import TokenTransaction
from qbitcoin.core.FalconHelper import falcon_pk_to_address
from qbitcoin.crypto.falcon import FalconSignature
from qbitcoin.generated import qbit_pb2


def replacement_getTime():
    return int(time.time())


@contextlib.contextmanager
def set_default_balance_size(new_value=100 * int(config.dev.shor_per_quanta)):
    old_value = config.dev.default_account_balance
    try:
        config.dev.default_account_balance = new_value
        yield
    finally:
        config.dev.default_account_balance = old_value


@contextlib.contextmanager
def set_hard_fork_block_number(hard_fork_index=0, new_value=1):
    old_value = config.dev.hard_fork_heights[hard_fork_index]
    try:
        config.dev.hard_fork_heights[hard_fork_index] = new_value
        yield
    finally:
        config.dev.hard_fork_heights[hard_fork_index] = old_value


@contextlib.contextmanager
def set_wallet_dir(wallet_name):
    dst_dir = tempfile.mkdtemp()
    prev_val = config.user.wallet_dir
    try:
        test_path = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.join(test_path, "..", "data", wallet_name)
        shutil.rmtree(dst_dir)
        shutil.copytree(src_dir, dst_dir)
        config.user.wallet_dir = dst_dir
        yield dst_dir
    finally:
        shutil.rmtree(dst_dir)
        config.user.wallet_dir = prev_val


@contextlib.contextmanager
def set_qrl_dir(data_name):
    dst_dir = tempfile.mkdtemp()
    prev_val = config.user.qrl_dir
    try:
        test_path = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(test_path, "..", "data")
        src_dir = os.path.join(data_dir, data_name)
        shutil.rmtree(dst_dir)
        shutil.copytree(src_dir, dst_dir)
        shutil.copy(os.path.join(data_dir, 'core', 'genesis.yml'), dst_dir)
        shutil.copy(os.path.join(data_dir, 'core', 'config.yml'), dst_dir)
        config.user.qrl_dir = dst_dir
        yield dst_dir
    finally:
        shutil.rmtree(dst_dir)
        config.user.qrl_dir = prev_val


def get_genesis_with_only_coin_base_txn(coin_base_reward_addr, dev_config):
    g = GenesisBlock()

    coin_base_tx = Transaction.from_pbdata(g.transactions[0])
    coin_base_tx.update_mining_address(coin_base_reward_addr)

    # Remove all other transaction except CoinBase txn
    del g.transactions[:]

    g.pbdata.transactions.extend([coin_base_tx.pbdata])
    g.blockheader.generate_headerhash(dev_config)

    return g


def read_data_file(filename):
    test_path = os.path.dirname(os.path.abspath(__file__))
    src_file = os.path.join(test_path, "..", "data", filename)
    with open(src_file, 'r') as f:
        return f.read()


@contextlib.contextmanager
def mocked_genesis():
    custom_genesis_block = deepcopy(GenesisBlock())
    with mock.patch('qbitcoin.core.GenesisBlock.GenesisBlock.instance'):
        GenesisBlock.instance = custom_genesis_block
        yield custom_genesis_block


@contextlib.contextmanager
def clean_genesis():
    data_name = "no_data"
    dst_dir = tempfile.mkdtemp()
    prev_val = config.user.qrl_dir
    try:
        GenesisBlock.instance = None
        test_path = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.join(test_path, "..", "data", data_name)
        shutil.rmtree(dst_dir)
        shutil.copytree(src_dir, dst_dir)
        config.user.qrl_dir = dst_dir
        _ = GenesisBlock()  # noqa
        config.user.qrl_dir = prev_val
        config.user = config.UserConfig(True)
        yield
    finally:
        shutil.rmtree(dst_dir)
        GenesisBlock.instance = None
        config.user.qrl_dir = prev_val


def get_some_address(idx=0) -> bytes:
    """Get a deterministic address for testing"""
    # Generate a Falcon key pair with deterministic seed
    private_key, public_key = FalconSignature.generate_keypair()
    
    # Generate address from public key
    address = falcon_pk_to_address(public_key)
    return address


class FalconKeypair:
    """Simple wrapper class to provide attribute access to Falcon keypair data"""
    def __init__(self, private_key, public_key, address, address_str, pk=None):
        self.private_key = private_key
        self.public_key = public_key
        self.address = address
        self.address_str = address_str
        self.pk = pk if pk is not None else public_key

def get_alice_falcon(seed_modifier=0):
    """Get Alice's Falcon key pair for testing"""
    # Create a deterministic seed based on a pattern
    seed_bytes = bytes([(i + seed_modifier) % 256 for i in range(48)])
    
    # Generate Falcon key pair from seed (deterministic for testing)
    private_key, public_key = FalconSignature.generate_keypair()
    
    # Generate address from public key
    address = falcon_pk_to_address(public_key)
    
    return FalconKeypair(
        private_key=private_key,
        public_key=public_key,
        address=address,
        address_str='Q' + bin2hstr(address),
        pk=public_key
    )


def get_bob_falcon(seed_modifier=5):
    """Get Bob's Falcon key pair for testing"""
    # Create a deterministic seed based on a pattern  
    seed_bytes = bytes([(i + seed_modifier) % 256 for i in range(48)])
    
    # Generate Falcon key pair from seed (deterministic for testing)
    private_key, public_key = FalconSignature.generate_keypair()
    
    # Generate address from public key
    address = falcon_pk_to_address(public_key)
    
    return FalconKeypair(
        private_key=private_key,
        public_key=public_key,
        address=address,
        address_str='Q' + bin2hstr(address),
        pk=public_key
    )


def get_slave_falcon(seed_modifier=10):
    """Get a slave Falcon key pair for testing"""
    # Create a deterministic seed based on a pattern
    seed_bytes = bytes([(i + seed_modifier) % 256 for i in range(48)])
    
    # Generate Falcon key pair from seed (deterministic for testing)
    private_key, public_key = FalconSignature.generate_keypair()
    
    # Generate address from public key
    address = falcon_pk_to_address(public_key)
    
    return FalconKeypair(
        private_key=private_key,
        public_key=public_key,
        address=address,
        address_str='Q' + bin2hstr(address),
        pk=public_key
    )


def get_random_falcon():
    """Get a random Falcon key pair for testing"""
    # Generate random Falcon key pair
    private_key, public_key = FalconSignature.generate_keypair()
    
    # Generate address from public key
    address = falcon_pk_to_address(public_key)
    
    return FalconKeypair(
        private_key=private_key,
        public_key=public_key,
        address=address,
        address_str='Q' + bin2hstr(address),
        pk=public_key
    )


def get_token_transaction(falcon1, falcon2, amount1=400000000, amount2=200000000, fee=1) -> TokenTransaction:
    initial_balances = list()
    initial_balances.append(qbit_pb2.AddressAmount(address=falcon1['address'],
                                                  amount=amount1))
    initial_balances.append(qbit_pb2.AddressAmount(address=falcon2['address'],
                                                  amount=amount2))

    return TokenTransaction.create(symbol=b'QRL',
                                   name=b'Quantum Resistant Ledger',
                                   owner=falcon1['address'],
                                   decimals=4,
                                   initial_balances=initial_balances,
                                   fee=fee,
                                   xmss_pk=falcon1['public_key'])


def destroy_state():
    try:
        db_path = os.path.join(config.user.data_dir, config.dev.db_name)
        shutil.rmtree(db_path)
    except FileNotFoundError:
        pass


def get_slaves(alice_nonce, txn_nonce):
    # [master_address: bytes, slave_keys: list, slave_txn: json]

    slave_falcon = get_slave_falcon()
    alice_falcon = get_alice_falcon()

    # Create a slave transaction using Falcon keys
    slave_txn = SlaveTransaction.create([slave_falcon['public_key']],
                                        [1],
                                        0,
                                        alice_falcon['public_key'])
    slave_txn._data.nonce = txn_nonce
    
    # Sign with Alice's Falcon private key
    message = slave_txn.get_hashable_bytes()
    signature = FalconSignature.sign_message(message, alice_falcon['private_key'])
    slave_txn._data.signature = signature

    slave_data = json.loads(json.dumps([bin2hstr(alice_falcon['address']), [bin2hstr(slave_falcon['private_key'])], slave_txn.to_json()]))
    slave_data[0] = bytes(hstr2bin(slave_data[0]))
    return slave_data


def get_random_master():
    random_master = get_random_falcon()
    slave_data = json.loads(json.dumps([bin2hstr(random_master['address']), [bin2hstr(random_master['private_key'])], None]))
    slave_data[0] = bytes(hstr2bin(slave_data[0]))
    return slave_data


def gen_blocks(block_count, state, miner_address):
    blocks = []
    block = None
    with mock.patch('qbitcoin.core.misc.ntp.getTime') as time_mock:
        time_mock.return_value = 1615270948
        addresses_state = dict()
        for i in range(0, block_count):
            if i == 0:
                block = GenesisBlock()
                for genesis_balance in GenesisBlock().genesis_balance:
                    bytes_addr = genesis_balance.address
                    addresses_state[bytes_addr] = OptimizedAddressState.get_default(bytes_addr)
                    addresses_state[bytes_addr]._data.balance = genesis_balance.balance
            else:
                block = Block.create(dev_config=config.dev,
                                     block_number=i,
                                     prev_headerhash=block.headerhash,
                                     prev_timestamp=block.timestamp,
                                     transactions=[],
                                     miner_address=miner_address,
                                     seed_height=None,
                                     seed_hash=None)
                addresses_set = ChainManager.set_affected_address(block)
                coin_base_tx = Transaction.from_pbdata(block.transactions[0])
                coin_base_tx.set_affected_address(addresses_set)

                chain_manager = ChainManager(state)
                state_container = chain_manager.new_state_container(addresses_set,
                                                                    block.block_number,
                                                                    False,
                                                                    None)
                coin_base_tx.apply(state, state_container)

                for tx_idx in range(1, len(block.transactions)):
                    tx = Transaction.from_pbdata(block.transactions[tx_idx])
                    if not chain_manager.update_state_container(tx, state_container):
                        return False
                    tx.apply(state, state_container)

                block.set_nonces(dev_config=config.dev, mining_nonce=10, extra_nonce=0)
            blocks.append(block)

            metadata = BlockMetadata()
            metadata.set_block_difficulty(StringToUInt256('256'))
            BlockMetadata.put_block_metadata(state, block.headerhash, metadata, None)

            Block.put_block(state, block, None)
            bm = qbit_pb2.BlockNumberMapping(headerhash=block.headerhash,
                                            prev_headerhash=block.prev_headerhash)

            Block.put_block_number_mapping(state, block.block_number, bm, None)
            state.update_mainchain_height(block.block_number, None)
            OptimizedAddressState.put_optimized_addresses_state(state, addresses_state)

    return blocks


# Backward compatibility aliases for XMSS functions
def get_alice_xmss(xmss_height=6):
    """Backward compatibility alias for get_alice_falcon"""
    return get_alice_falcon()

def get_bob_xmss(xmss_height=6): 
    """Backward compatibility alias for get_bob_falcon"""
    return get_bob_falcon()

def get_slave_xmss():
    """Backward compatibility alias for get_slave_falcon"""
    return get_slave_falcon()

def get_random_xmss(xmss_height=6):
    """Backward compatibility alias for get_random_falcon"""
    return get_random_falcon()
