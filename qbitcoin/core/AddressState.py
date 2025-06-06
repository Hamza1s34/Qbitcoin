# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

from pyqrllib.pyqrllib import bin2hstr

from qbitcoin.core import config
from qbitcoin.core.State import State
from qbitcoin.core.OptimizedAddressState import OptimizedAddressState
from qbitcoin.generated import qbit_pb2


class AddressState(object):
    def __init__(self, protobuf_block=None):
        self._data = protobuf_block
        if protobuf_block is None:
            self._data = qbit_pb2.AddressState()

    @property
    def pbdata(self):
        """
        Returns a protobuf object that contains persistable data representing this object
        :return: A protobuf AddressState object
        :rtype: qbit_pb2.AddressState
        """
        return self._data

    @property
    def address(self):
        return self._data.address

    @property
    def nonce(self):
        return self._data.nonce

    @property
    def balance(self):
        return self._data.balance

    @balance.setter
    def balance(self, new_balance: int):
        self._data.balance = new_balance

    @property
    def transaction_hashes(self):
        return self._data.transaction_hashes

    @property
    def latticePK_list(self):
        return self._data.latticePK_list

    @property
    def slave_pks_access_type(self):
        return self._data.slave_pks_access_type

    @staticmethod
    def create(address: bytes,
               nonce: int,
               balance: int,
               falcon_pk_list: list,
               tokens: dict,
               slave_pks_access_type: dict):
        address_state = AddressState()

        address_state._data.address = address
        address_state._data.nonce = nonce
        address_state._data.balance = balance
        
        if falcon_pk_list:
            address_state._data.falcon_pk_list.extend(falcon_pk_list)

        for token_txhash in tokens:
            address_state.update_token_balance(token_txhash, tokens[token_txhash])

        for slave_pk in slave_pks_access_type:
            address_state.add_slave_pks_access_type(slave_pk, slave_pks_access_type[slave_pk])

        return address_state

    def validate_slave_with_access_type(self, slave_pk: str, access_types: list):
        if slave_pk not in self.slave_pks_access_type:
            return False

        access_type = self.slave_pks_access_type[slave_pk]
        if access_type not in access_types:
            return False

        return True

    def update_token_balance(self, token_tx_hash: bytes, balance: int):
        str_token_tx_hash = bin2hstr(token_tx_hash)
        self._data.tokens[str_token_tx_hash] += balance
        if self._data.tokens[str_token_tx_hash] == 0:
            del self._data.tokens[str_token_tx_hash]

    def get_token_balance(self, token_tx_hash: bytes) -> int:
        str_token_tx_hash = bin2hstr(token_tx_hash)
        if str_token_tx_hash in self._data.tokens:
            return self._data.tokens[str_token_tx_hash]
        return 0

    def is_token_exists(self, token_tx_hash: bytes) -> bool:
        str_token_tx_hash = bin2hstr(token_tx_hash)
        if str_token_tx_hash in self._data.tokens:
            return True
        return False

    def add_slave_pks_access_type(self, slave_pk: bytes, access_type: int):
        self._data.slave_pks_access_type[str(slave_pk)] = access_type

    def remove_slave_pks_access_type(self, slave_pk: bytes):
        del self._data.slave_pks_access_type[str(slave_pk)]

    def add_lattice_pk(self, lattice_txn):
        lattice_pk = qbit_pb2.LatticePK(txhash=lattice_txn.txhash,
                                       dilithium_pk=lattice_txn.dilithium_pk,
                                       kyber_pk=lattice_txn.kyber_pk)

        self._data.latticePK_list.extend([lattice_pk])

    def remove_lattice_pk(self, lattice_txn):
        for i, lattice_pk in enumerate(self._data.latticePK_list):
            if lattice_pk.txhash == lattice_txn.txhash:
                del self._data.latticePK_list[i]
                break

    def add_falcon_pk(self, public_key: bytes):
        """
        Add a Falcon 512 public key to the address state
        This is used to track used keys for preventing key reuse
        
        Args:
            public_key (bytes): A Falcon 512 public key to add
        """
        self._data.falcon_pk_list.append(public_key)

    def remove_falcon_pk(self, public_key: bytes):
        """
        Remove a Falcon 512 public key from the address state
        Used during rollbacks to undo transactions
        
        Args:
            public_key (bytes): Public key to remove
        """
        if public_key in self._data.falcon_pk_list:
            self._data.falcon_pk_list.remove(public_key)

    def is_falcon_pk_used(self, public_key: bytes) -> bool:
        """
        Check if a Falcon 512 public key has been used before
        
        Args:
            public_key (bytes): Public key to check
            
        Returns:
            bool: True if the key has been used previously
        """
        return public_key in self._data.falcon_pk_list

    def increase_nonce(self):
        self._data.nonce += 1

    def decrease_nonce(self):
        self._data.nonce -= 1

    def get_slave_permission(self, slave_pk) -> int:
        slave_pk_str = str(slave_pk)
        if slave_pk_str in self._data.slave_pks_access_type:
            return self._data.slave_pks_access_type[slave_pk_str]

        return -1

    @staticmethod
    def get_default(address):
        address_state = AddressState.create(address=address,                                            nonce=config.dev.default_nonce,
                                            balance=config.dev.default_account_balance,
                                            falcon_pk_list=[],
                                            tokens=dict(),
                                            slave_pks_access_type=dict())
        if address == config.dev.coinbase_address:
            address_state.balance = int(config.dev.max_coin_supply * config.dev.shor_per_quanta)
        return address_state
    
    @staticmethod
    def address_is_valid(address: bytes) -> bool:
        """
        Validate Falcon address format only
        """
        return OptimizedAddressState.address_is_valid(address)

    def serialize(self):
        return self._data.SerializeToString()

    @staticmethod
    def put_addresses_state(state: State, addresses_state: dict, batch=None):
        """
        :param addresses_state:
        :param batch:
        :return:
        """
        for address in addresses_state:
            address_state = addresses_state[address]
            AddressState.put_address_state(state, address_state, batch)

    @staticmethod
    def put_address_state(state: State, address_state, batch=None):
        data = address_state.pbdata.SerializeToString()
        state._db.put_raw(address_state.address, data, batch)

    @staticmethod
    def get_address_state(state: State, address: bytes):
        try:
            data = state._db.get_raw(address)
            pbdata = qbit_pb2.AddressState()
            pbdata.ParseFromString(bytes(data))
            address_state = AddressState(pbdata)
            return address_state
        except KeyError:
            return AddressState.get_default(address)

    @staticmethod
    def return_all_addresses(state: State) -> list:
        addresses = []
        for key, data in state._db.db:
            if key[0] != b'Q':
                continue
            pbdata = qbit_pb2.AddressState()
            pbdata.ParseFromString(bytes(data))
            address_state = AddressState(pbdata)
            addresses.append(address_state)
        return addresses
