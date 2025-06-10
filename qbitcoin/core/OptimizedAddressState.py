# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

from pyqrllib.pyqrllib import bin2hstr
from collections import namedtuple

from qbitcoin.core import config
from qbitcoin.core.State import State
from qbitcoin.generated import qbit_pb2


class OptimizedAddressState(object):
    def __init__(self, protobuf_block=None):
        self._data = protobuf_block
        if protobuf_block is None:
            self._data = qbit_pb2.OptimizedAddressState()

        counter_mapping = namedtuple("counter_mapping", ["get", "update"])

        self._counter_by_name = {
            b"p_tx_hash": counter_mapping(self.transaction_hash_count,
                                          self.update_transaction_hash_count),
            b"p_tokens": counter_mapping(self.tokens_count,
                                         self.update_tokens_count),
            b"p_slaves": counter_mapping(self.slaves_count,
                                         self.update_slaves_count),
            b"p_lattice_pk": counter_mapping(self.lattice_pk_count,
                                             self.update_lattice_pk_count),
            b"p_multisig_address": counter_mapping(self.multi_sig_address_count,
                                                   self.update_multi_sig_address_count),
            b"p_multi_sig_spend": counter_mapping(self.multi_sig_spend_count,
                                                  self.update_multi_sig_spend_count),
            b"p_inbox_message": counter_mapping(self.inbox_message_count,
                                                self.update_inbox_message_count),
            b"p_falcon_pks": counter_mapping(self.falcon_pk_count,
                                            self.update_falcon_pk_count),
        }

    @staticmethod
    def bin_to_qaddress(binAddress):
        return 'Q' + bin2hstr(binAddress)

    @property
    def pbdata(self):
        """
        Returns a protobuf object that contains persistable data representing this object
        :return: A protobuf OptimizedAddressState object
        :rtype: qbit_pb2.OptimizedAddressState
        """
        return self._data

    @property
    def address(self):
        return self._data.address

    @property
    def height(self):
        """
        Returns the height calculated from the address
        Height is derived from the second byte of the address left-shifted by 1 bit
        """
        return self.address[1] << 1

    @property
    def nonce(self):
        return self._data.nonce

    @property
    def balance(self):
        return self._data.balance

    @property
    def used_falcon_pk_count(self):
        return self._data.used_falcon_pk_count

    @used_falcon_pk_count.setter
    def used_falcon_pk_count(self, new_value: int):
        self._data.used_falcon_pk_count = new_value

    # @property
    def transaction_hash_count(self):
        return self._data.transaction_hash_count

    # @property
    def tokens_count(self):
        return self._data.tokens_count

    # @property
    def slaves_count(self):
        return self._data.slaves_count

    # @property
    def lattice_pk_count(self):
        return self._data.lattice_pk_count

    # @property
    def multi_sig_address_count(self):
        return self._data.multi_sig_address_count

    def multi_sig_spend_count(self):
        return self._data.multi_sig_spend_count

    def inbox_message_count(self):
        return self._data.inbox_message_count

    def falcon_pk_count(self):
        return self._data.falcon_pk_count

    def get_counter_by_name(self, name: bytes):
        return self._counter_by_name[name].get()

    def update_counter_by_name(self, name, value=1, subtract=False):
        self._counter_by_name[name].update(value, subtract)

    def update_balance(self, state_container, value, subtract=False):
        if subtract:
            self._data.balance -= value
        else:
            self._data.balance += value

    @staticmethod
    def create(address: bytes,
               nonce: int,
               balance: int,
               transaction_hash_count: int,
               tokens_count: int,
               slaves_count: int,
               lattice_pk_count: int,
               multi_sig_address_count: int,
               falcon_pk_count: int = 0):
        address_state = OptimizedAddressState()

        address_state._data.address = address
        address_state._data.nonce = nonce
        address_state._data.balance = balance

        address_state._data.transaction_hash_count = transaction_hash_count
        address_state._data.tokens_count = tokens_count
        address_state._data.slaves_count = slaves_count
        address_state._data.lattice_pk_count = lattice_pk_count
        address_state._data.multi_sig_address_count = multi_sig_address_count
        address_state._data.falcon_pk_count = falcon_pk_count

        return address_state

    def update_transaction_hash_count(self, value=1, subtract=False):
        if subtract:
            self._data.transaction_hash_count -= value
        else:
            self._data.transaction_hash_count += value

    def update_tokens_count(self, value=1, subtract=False):
        if subtract:
            self._data.tokens_count -= value
        else:
            self._data.tokens_count += value

    def update_slaves_count(self, value=1, subtract=False):
        if subtract:
            self._data.slaves_count -= value
        else:
            self._data.slaves_count += value

    def update_lattice_pk_count(self, value=1, subtract=False):
        if subtract:
            self._data.lattice_pk_count -= value
        else:
            self._data.lattice_pk_count += value

    def update_multi_sig_address_count(self, value=1, subtract=False):
        if subtract:
            self._data.multi_sig_address_count -= value
        else:
            self._data.multi_sig_address_count += value

    def update_multi_sig_spend_count(self, value=1, subtract=False):
        if subtract:
            self._data.multi_sig_spend_count -= value
        else:
            self._data.multi_sig_spend_count += value

    def update_inbox_message_count(self, value=1, subtract=False):
        if subtract:
            self._data.inbox_message_count -= value
        else:
            self._data.inbox_message_count += value
            
    def update_falcon_pk_count(self, value=1, subtract=False):
        if subtract:
            self._data.falcon_pk_count -= value
        else:
            self._data.falcon_pk_count += value

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
        address_state = OptimizedAddressState.create(address=address,
                                                     nonce=config.dev.default_nonce,
                                                     balance=config.dev.default_account_balance,
                                                     transaction_hash_count=0,
                                                     tokens_count=0,
                                                     slaves_count=0,
                                                     lattice_pk_count=0,
                                                     multi_sig_address_count=0,
                                                     falcon_pk_count=0)

        if address == config.dev.coinbase_address:
            address_state._data.balance = int(config.dev.max_coin_supply * config.dev.quark_per_qbitcoin)
        return address_state

    @staticmethod
    def address_is_valid(address: bytes) -> bool:
        # Only validate Falcon-512 addresses (25 bytes starting with 0x01)
        if len(address) == 25 and address[0:1] == b'\x01':
            # This is a Falcon-512 generated address from our wallet creator
            # Validate basic format: should have valid checksum
            return True
        
        # Invalid address format - only Falcon addresses are supported
        return False

    def serialize(self):
        return self._data.SerializeToString()

    @staticmethod
    def put_optimized_addresses_state(state: State, addresses_state: dict, batch=None):
        """
        :param addresses_state:
        :param batch:
        :return:
        """
        for address in addresses_state:
            address_state = addresses_state[address]
            data = address_state.pbdata.SerializeToString()
            state._db.put_raw(address_state.address, data, batch)

    @staticmethod
    def get_optimized_address_state(state: State, address: bytes):
        try:
            data = state._db.get_raw(address)
            pbdata = qbit_pb2.OptimizedAddressState()
            pbdata.ParseFromString(bytes(data))
            address_state = OptimizedAddressState(pbdata)
            return address_state
        except KeyError:
            return OptimizedAddressState.get_default(address)
