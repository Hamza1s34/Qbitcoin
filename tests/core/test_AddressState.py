# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from random import shuffle
from unittest import TestCase
from mock import Mock, PropertyMock, patch

from tests.misc.helper import get_alice_xmss, get_slave_xmss, get_random_xmss, set_qrl_dir
from qbitcoin.core.misc import logger
from qbitcoin.core import config
from qbitcoin.core.State import State
from qbitcoin.core.AddressState import AddressState
from qbitcoin.core.OptimizedAddressState import OptimizedAddressState

logger.initialize_default()

alice = get_alice_xmss()
slave = get_slave_xmss()


class TestAddressState(TestCase):
    def setUp(self):
        self.addr_state = AddressState.get_default(alice.address)

    def test_create_and_properties(self):
        a = AddressState.create(address=alice.address, nonce=0, balance=10,
                                falcon_pk_list=[alice.pk],
                                tokens={b'010101': 100, b'020202': 200},
                                slave_pks_access_type={slave.pk: 1}
                                )
        self.assertEqual(a.pbdata.address, a.address)
        self.assertEqual(a.pbdata.balance, a.balance)
        a.balance = 3
        self.assertEqual(a.balance, 3)
        self.assertEqual(a.pbdata.nonce, a.nonce)
        self.assertEqual(a.pbdata.falcon_pk_list, a._data.falcon_pk_list)
        self.assertEqual(a.pbdata.transaction_hashes, a.transaction_hashes)
        self.assertEqual(a.pbdata.latticePK_list, a.latticePK_list)
        self.assertEqual(a.pbdata.slave_pks_access_type, a.slave_pks_access_type)

    def test_token_balance_functionality(self):
        # If I update an AddressState's token balance, it should do what the function name says.
        self.addr_state.update_token_balance(b'010101', 10)
        self.assertEqual(self.addr_state.get_token_balance(b'010101'), 10)
        self.assertTrue(self.addr_state.is_token_exists(b'010101'))

        # I can call update_token_balance with a negative number to decrease the balance.
        self.addr_state.update_token_balance(b'010101', -2)
        self.assertEqual(self.addr_state.get_token_balance(b'010101'), 8)

        # If the token balance hits 0, the token_txhash should have been pruned from the AddressState.
        # And when I ask for its balance, it should return 0.
        self.addr_state.update_token_balance(b'010101', -8)
        self.assertFalse(self.addr_state.is_token_exists(b'010101'))
        self.assertEqual(self.addr_state.get_token_balance(b'010101'), 0)

    def test_nonce(self):
        self.addr_state.increase_nonce()
        self.assertEqual(self.addr_state.nonce, 1)

        self.addr_state.increase_nonce()
        self.addr_state.increase_nonce()
        self.assertEqual(self.addr_state.nonce, 3)

        self.addr_state.decrease_nonce()
        self.addr_state.decrease_nonce()
        self.assertEqual(self.addr_state.nonce, 1)

    def test_nonce_negative(self):
        with self.assertRaises(ValueError):
            self.addr_state.decrease_nonce()

    def test_slave_pks_access_type(self):
        # slave_pks_access_type could take 2 values: 0 (all permission granted to slaves), 1 (only mining)
        # There is no validation for the values of slave_pks_access_type.
        # For now only 0 is used.
        # By default all slave_pks get permission level 0
        self.addr_state.add_slave_pks_access_type(slave.pk, 1)
        self.assertEqual(self.addr_state.slave_pks_access_type[str(slave.pk)], 1)

    def test_get_slave_permission(self):
        # We haven't added slave.pk to the addr_state yet, so slave is not yet a slave of this AddressState.
        self.assertEqual(self.addr_state.get_slave_permission(slave.pk), -1)

        # Add slave permissions for slave.pk
        self.addr_state.add_slave_pks_access_type(slave.pk, 1)
        self.assertEqual(self.addr_state.get_slave_permission(slave.pk), 1)

        # Remove slave permissions for slave.pk
        self.addr_state.remove_slave_pks_access_type(slave.pk)
        self.assertEqual(self.addr_state.get_slave_permission(slave.pk), -1)

    def test_get_default_coinbase(self):
        # Make sure that Coinbase AddressState gets all the coins supply by default
        coinbase_addr_state = AddressState.get_default(config.dev.coinbase_address)
        self.assertEqual(coinbase_addr_state.balance, int(config.dev.max_coin_supply * config.dev.shor_per_quanta))

    def test_falcon_pk_tracking(self):
        # Test adding and checking Falcon public keys
        test_pk = b'test_falcon_pk_' + b'0' * 18  # Mock Falcon public key
        
        # Initially, the key should not be used
        self.assertFalse(self.addr_state.is_falcon_pk_used(test_pk))
        
        # Add the key and verify it's tracked
        self.addr_state.add_falcon_pk(test_pk)
        self.assertTrue(self.addr_state.is_falcon_pk_used(test_pk))
        
        # Test with another key
        test_pk2 = b'test_falcon_pk_' + b'1' * 18
        self.assertFalse(self.addr_state.is_falcon_pk_used(test_pk2))
        self.addr_state.add_falcon_pk(test_pk2)
        self.assertTrue(self.addr_state.is_falcon_pk_used(test_pk2))

    def test_falcon_pk_removal(self):
        # Test removing Falcon public keys (for transaction rollbacks)
        test_pk = b'test_falcon_pk_' + b'0' * 18
        
        # Add a key
        self.addr_state.add_falcon_pk(test_pk)
        self.assertTrue(self.addr_state.is_falcon_pk_used(test_pk))
        
        # Remove the key
        self.addr_state.remove_falcon_pk(test_pk)
        self.assertFalse(self.addr_state.is_falcon_pk_used(test_pk))

    def test_falcon_pk_tracking_multiple(self):
        # Test tracking multiple Falcon public keys
        test_keys = [
            b'falcon_pk_1_' + b'0' * 20,
            b'falcon_pk_2_' + b'1' * 20,
            b'falcon_pk_3_' + b'2' * 20
        ]
        
        # Add all keys
        for key in test_keys:
            self.assertFalse(self.addr_state.is_falcon_pk_used(key))
            self.addr_state.add_falcon_pk(key)
            self.assertTrue(self.addr_state.is_falcon_pk_used(key))
        
        # Remove some keys
        self.addr_state.remove_falcon_pk(test_keys[1])
        self.assertTrue(self.addr_state.is_falcon_pk_used(test_keys[0]))
        self.assertFalse(self.addr_state.is_falcon_pk_used(test_keys[1]))
        self.assertTrue(self.addr_state.is_falcon_pk_used(test_keys[2]))

    def test_falcon_key_validation(self):
        # Test that Falcon key reuse detection works correctly
        test_pk = alice.pk  # Use alice's actual public key
        
        # Initially should not be marked as used
        self.assertFalse(self.addr_state.is_falcon_pk_used(test_pk))
        
        # After adding, should be marked as used
        self.addr_state.add_falcon_pk(test_pk)
        self.assertTrue(self.addr_state.is_falcon_pk_used(test_pk))

    def test_serialize(self):
        # Simply test that serialize() works and you can deserialize from it.
        output = self.addr_state.serialize()
        another_addr_state = AddressState(protobuf_block=output)
        self.assertIsInstance(another_addr_state, AddressState)

    def test_address_format_validation(self):
        # Test that address validation works for Falcon addresses
        self.assertTrue(AddressState.address_is_valid(alice.address))
        self.assertFalse(AddressState.address_is_valid(b'fake address'))

    def test_return_all_addresses(self):
        with set_qrl_dir('no_data'):
            with State() as state:
                self.assertEqual(AddressState.return_all_addresses(state), [])

    def test_put_addresses_state(self):
        with set_qrl_dir('no_data'):
            with State() as state:
                alice_xmss = get_alice_xmss()
                alice_state = OptimizedAddressState.get_default(alice_xmss.address)
                addresses_state = {
                    alice_state.address: alice_state,
                    b'test1': OptimizedAddressState.get_default(b'test1')
                }
                AddressState.put_addresses_state(state, addresses_state, None)
                alice_state2 = OptimizedAddressState.get_optimized_address_state(state, alice_xmss.address)
                self.assertEqual(alice_state.serialize(), alice_state2.serialize())
                test_state = OptimizedAddressState.get_optimized_address_state(state, b'test1')
                self.assertEqual(test_state.serialize(), OptimizedAddressState.get_default(b'test1').serialize())

def main():
    import unittest
    unittest.main()
if __name__ == '__main__':
    main()