# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
from pyqrllib.pyqrllib import hstr2bin

from qbitcoin.core.OptimizedAddressState import OptimizedAddressState
from qbitcoin.core.MultiSigAddressState import MultiSigAddressState


def parse_hexblob(blob: str) -> bytes:
    """
    Binary conversions from hexstring are handled by bytes(hstr2bin()).
    :param blob:
    :return:
    """
    return bytes(hstr2bin(blob))


def parse_qaddress(qaddress: str, check_multi_sig_address=False) -> bytes:
    """
    Converts from a Qaddress to an Address.
    qaddress: 'Q' + hexstring representation of an XMSS tree's address
    check_multi_sig_address: Flag if multi sig address should be checked
    :param qaddress:
    :return:
    """
    try:
        from qbitcoin.core import config
        
        qaddress = parse_hexblob(qaddress[1:])
        
        # Special case for coinbase address - allow it even if it doesn't pass normal validation
        if qaddress == config.dev.coinbase_address:
            return qaddress
            
        if not OptimizedAddressState.address_is_valid(qaddress):
            print("checking for multi_sig_address ", check_multi_sig_address)
            if check_multi_sig_address:
                print("checking for multi_sig_address")
                if not MultiSigAddressState.address_is_valid(qaddress):
                    raise ValueError("Invalid Addresss ", qaddress)
            else:
                raise ValueError("Invalid Addresss ", qaddress)
    except Exception as e:
        raise ValueError("Failed To Decode Address", e)

    return qaddress
