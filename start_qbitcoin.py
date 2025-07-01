#!/usr/bin/env python3
# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
import sys
import os

# Set Protocol Buffers implementation to Python for compatibility with newer protobuf versions
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

if sys.version_info < (3, 5):
    print("This application requires at least Python 3.5")
    quit(1)

from qbitcoin.core.misc.DependencyChecker import DependencyChecker  # noqa

DependencyChecker.check()

from qbitcoin.main import main  # noqa

def main_entry():
    """Entry point for qbitcoin-node command"""
    main()

if __name__ == "__main__":
    main_entry()
