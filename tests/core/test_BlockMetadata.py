# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from unittest import TestCase

from tests.misc.helper import get_slave_xmss
from qbitcoin.core.misc import logger
from qbitcoin.core.BlockMetadata import BlockMetadata
from qbitcoin.core.State import State

from tests.misc.helper import set_qrl_dir, get_alice_xmss

logger.initialize_default()

alice = get_alice_xmss()
slave = get_slave_xmss()


class TestTokenMetadata(TestCase):
    def setUp(self):
        with set_qrl_dir('no_data'):
            self.state = State()

    def test_put_block_metadata(self):
        block_metadata = BlockMetadata.create()
        block_metadata.update_last_headerhashes([b'test1', b'test2'], b'test3')

        BlockMetadata.put_block_metadata(self.state, b'block_headerhash', block_metadata, None)
        BlockMetadata.put_block_metadata(self.state, b'block_headerhash2', BlockMetadata.create(), None)

        self.assertEqual(BlockMetadata.get_block_metadata(self.state, b'block_headerhash').to_json(),
                         block_metadata.to_json())

        expected_json = b'{\n  "blockDifficulty": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",\n  ' \
                        b'"cumulativeDifficulty": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="\n}'

        self.assertEqual(BlockMetadata.get_block_metadata(self.state, b'block_headerhash2').to_json(),
                         expected_json)

    def test_get_block_metadata(self):
        self.assertIsNone(BlockMetadata.get_block_metadata(self.state, b'test1'))
        BlockMetadata.put_block_metadata(self.state, b'block_headerhash2', BlockMetadata.create(), None)

        tmp_json = BlockMetadata.get_block_metadata(self.state, b'block_headerhash2').to_json()

        expected_json = b'{\n  "blockDifficulty": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",\n  ' \
                        b'"cumulativeDifficulty": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="\n}'

        self.assertEqual(tmp_json, expected_json)

def main():
    import unittest
    unittest.main()
if __name__ == '__main__':
    main()