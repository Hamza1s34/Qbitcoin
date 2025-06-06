# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


from mock import PropertyMock, patch
from unittest import TestCase
from math import ceil

from qbitcoin.core import config
from qbitcoin.core.misc import logger
from qbitcoin.core.State import State
from qbitcoin.core.OptimizedAddressState import OptimizedAddressState
from qbitcoin.core.PaginatedBitfield import PaginatedBitfield
from qbitcoin.core.AddressState import AddressState
from tests.misc.helper import get_alice_xmss, get_slave_xmss, set_qrl_dir

logger.initialize_default()

alice = get_alice_xmss()
slave = get_slave_xmss()


class TestOptimizedAddressState(TestCase):
    def setUp(self):
        with set_qrl_dir('no_data'):
            self.state = State()

    # TODO: Move this test to Optimized Address State
    def test_get_optimized_address_state(self):
        alice_xmss = get_alice_xmss()

        alice_address = alice_xmss.address
        address_state = OptimizedAddressState.get_optimized_address_state(self.state, alice_address)
        self.assertTrue(isinstance(address_state.address, bytes))

        alice_address = bytearray(alice_xmss.address)
        with self.assertRaises(TypeError):
            OptimizedAddressState.get_optimized_address_state(self.state, alice_address)

        alice_address = alice_xmss.address
        address_state = OptimizedAddressState.get_optimized_address_state(self.state, alice_address)
        addresses_state = {
            alice_address: address_state
        }
        self.assertTrue(isinstance(address_state.address, bytes))
        AddressState.put_addresses_state(self.state, addresses_state)

        address_state = OptimizedAddressState.get_optimized_address_state(self.state, alice_address)
        self.assertTrue(isinstance(address_state.address, bytes))

    def test_get_optimized_address_state2(self):
        alice_xmss = get_alice_xmss()

        alice_address = alice_xmss.address
        address_state = OptimizedAddressState.get_optimized_address_state(self.state, alice_address)
        addresses_state = {
            alice_address: address_state
        }
        self.assertTrue(isinstance(address_state.address, bytes))
        OptimizedAddressState.put_optimized_addresses_state(self.state, addresses_state)
        address_state = OptimizedAddressState.get_optimized_address_state(self.state, alice_address)
        self.assertTrue(isinstance(address_state.address, bytes))

    def test_falcon_pk_count_functionality(self):
        """Test Falcon public key count tracking instead of OTS bitfield"""
        alice_xmss = get_alice_xmss()
        address = alice_xmss.address
        address_state = OptimizedAddressState.get_default(address)
        
        # Initially, falcon_pk_count should be 0
        self.assertEqual(address_state.falcon_pk_count(), 0)
        
        # Test updating falcon_pk_count
        address_state.update_falcon_pk_count(5)
        self.assertEqual(address_state.falcon_pk_count(), 5)
        
        # Test subtracting from falcon_pk_count
        address_state.update_falcon_pk_count(2, subtract=True)
        self.assertEqual(address_state.falcon_pk_count(), 3)

    def test_update_used_page_in_address_state2(self):
        """Test deprecated - OTS tracking replaced with Falcon-512 signature counting"""
        # This test is no longer relevant as OTS tracking has been replaced with Falcon-512
        # which doesn't use bitfields or paging mechanisms
        alice_xmss = get_alice_xmss(12)
        address = alice_xmss.address
        address_state = OptimizedAddressState.get_default(address)
        
        # Test Falcon PK count functionality instead
        initial_count = address_state.falcon_pk_count()
        address_state.update_falcon_pk_count(5)
        self.assertEqual(address_state.falcon_pk_count(), initial_count + 5)

    def test_update_used_page_in_address_state3(self):
        """Test deprecated - OTS tracking replaced with Falcon-512 signature counting"""
        # This test is no longer relevant as OTS tracking has been replaced with Falcon-512
        # which doesn't use bitfields or paging mechanisms
        alice_xmss = get_alice_xmss(12)
        address = alice_xmss.address
        address_state = OptimizedAddressState.get_default(address)
        
        # Test Falcon PK count with various operations
        address_state.update_falcon_pk_count(10)
        self.assertEqual(address_state.falcon_pk_count(), 10)
        
        address_state.update_falcon_pk_count(5, subtract=True)
        self.assertEqual(address_state.falcon_pk_count(), 5)

    def test_update_used_page_in_address_state4(self):
        """Test deprecated - OTS tracking replaced with Falcon-512 signature counting"""
        # This test is no longer relevant as OTS tracking has been replaced with Falcon-512
        # which doesn't use bitfields or paging mechanisms
        alice_xmss = get_alice_xmss(12)
        address = alice_xmss.address
        address_state = OptimizedAddressState.get_default(address)
        
        # Test Falcon PK count with large numbers to simulate real usage
        large_count = 2048
        address_state.update_falcon_pk_count(large_count)
        self.assertEqual(address_state.falcon_pk_count(), large_count)
        
        # Test boundary conditions
        address_state.update_falcon_pk_count(large_count, subtract=True)
        self.assertEqual(address_state.falcon_pk_count(), 0)
def main():
    import unittest
    unittest.main()
if __name__ == '__main__':
    main()