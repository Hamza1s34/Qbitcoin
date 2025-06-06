# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from decimal import Decimal
from unittest import TestCase

from qbitcoin.core import config
from qbitcoin.core.misc import logger
from qbitcoin.core.formulas import remaining_emission

logger.initialize_default()


class TestFormulas(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestFormulas, self).__init__(*args, **kwargs)

    def test_remaining_emission(self):
        logger.info(remaining_emission(100, config.dev))
        self.assertEqual(remaining_emission(100, config.dev), Decimal('9999750000000000'))  # 10M - (100 * 2.5 QRL)
        # TODO: Test more values

def main():
    import unittest
    unittest.main()
if __name__ == '__main__':
    main()