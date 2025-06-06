# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

from qbitcoin.core import config
from qbitcoin.core.PaginatedData import PaginatedData
from qbitcoin.core.misc import logger
from qbitcoin.core.PaginatedFalconPK import PaginatedFalconPK
from qbitcoin.generated import qbit_pb2


class PaginatedBitfield(PaginatedData):
    """
    This class maintains backward compatibility with old OTS tracking,
    but delegates to the new PaginatedFalconPK for actual functionality.
    It's kept to minimize changes in the codebase during migration.
    """
    def __init__(self, write_access: bool, db):
        super(PaginatedBitfield, self).__init__(b'bitfield', write_access, db)
        # Create a new instance of PaginatedFalconPK for delegating calls
        self._falcon_pk_tracker = PaginatedFalconPK(write_access, db)

    def generate_bitfield_key(self, address, page):
        # Kept for backward compatibility
        return self.name + b'_' + address + b'_' + page.to_bytes(8, byteorder='big', signed=False)

    def load_bitfield_and_ots_key_reuse(self, address, ots_key_index) -> bool:
        # This is deprecated - we don't use OTS with Falcon
        logger.warning("load_bitfield_and_ots_key_reuse is deprecated - Falcon doesn't use OTS keys")
        return False

    @staticmethod
    def ots_key_reuse(ots_bitfield, ots_key_index) -> bool:
        # Deprecated - return False to avoid key reuse errors
        logger.warning("ots_key_reuse is deprecated - Falcon doesn't use OTS keys")
        return False

    def set_ots_key(self, addresses_state: dict, address, public_key):
        """
        Transition method - instead of tracking OTS keys, track Falcon public keys
        """
        # Simply delegate to the falcon public key tracker
        self._falcon_pk_tracker.add_used_key(addresses_state, address, public_key)

    def update_used_page_in_address_state(self, address, addresses_state: dict, page: int):
        # This no longer needs to be implemented for Falcon
        pass

    def unset_ots_key(self, addresses_state: dict, address, public_key):
        """
        Transition method - removes a public key from tracking
        Used during rollbacks
        """
        self._falcon_pk_tracker.remove_used_key(addresses_state, address, public_key)

    def load_bitfield(self, address, ots_key_index):
        # This is deprecated - kept for backward compatibility
        pass

    def get_paginated_data(self, key, page):
        """
        Maintained for backward compatibility
        """
        try:
            pbData = self.db.get_raw(self.name + b'_' + key + b'_' + page.to_bytes(8, byteorder='big', signed=False))
            data_list = qbit_pb2.DataList()
            data_list.ParseFromString(bytes(pbData))
            return list(data_list.values)
        except KeyError:
            return []
        except Exception as e:
            logger.error('[get_paginated_data] Exception for %s', self.name)
            logger.exception(e)
            raise

    def put_addresses_bitfield(self, batch):
        """
        Save all data to db
        """
        if not self.write_access:
            return
            
        # Save falcon public keys
        self._falcon_pk_tracker.put_used_keys(batch)
        
        # Also save traditional bitfields for backward compatibility
        for key in self.key_value:
            data_list = qbit_pb2.DataList(values=self.key_value[key])
            self.db.put_raw(key,
                            data_list.SerializeToString(),
                            batch)
