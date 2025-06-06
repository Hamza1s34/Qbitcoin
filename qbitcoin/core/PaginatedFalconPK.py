# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

from qbitcoin.core import config
from qbitcoin.core.PaginatedData import PaginatedData
from qbitcoin.core.misc import logger
from qbitcoin.generated import qbit_pb2


class PaginatedFalconPK(PaginatedData):
    """
    Tracks Falcon512 public keys used in transactions.
    This replaces the previous OTS tracking mechanism that was specific to XMSS.
    """
    def __init__(self, write_access: bool, db):
        super().__init__(b'falconpk', write_access, db)

    def generate_pkey_key(self, address, page):
        """
        Generate a key for storing falcon public keys in the database
        """
        return self.name + b'_' + address + b'_' + page.to_bytes(8, byteorder='big', signed=False)

    def is_key_used(self, address: bytes, public_key: bytes) -> bool:
        """
        Check if a public key has been used before
        
        Args:
            address: The address that used the key
            public_key: The falcon public key to check
            
        Returns:
            bool: True if key has been used, False otherwise
        """
        # Get the list of used keys for this address
        used_keys = self.get_used_keys(address)
        
        # Check if the public key is in the used keys list
        return public_key in used_keys

    def get_used_keys(self, address: bytes) -> list:
        """
        Get all used public keys for an address
        
        Args:
            address: Address to check
            
        Returns:
            list: List of used public keys for this address
        """
        # Start with page 1
        page = 1
        all_used_keys = []
        
        # Keep checking pages until we find an empty one
        while True:
            key = self.generate_pkey_key(address, page)
            if key not in self.key_value:
                self.key_value[key] = self.get_paginated_data(address, page)
            
            keys_list = self.key_value[key]
            
            # If this page is empty and it's not the first page, we're done
            if not keys_list and page > 1:
                break
                
            # Add all keys from this page to our list
            all_used_keys.extend(keys_list)
            
            # Move to the next page
            page += 1
        
        return all_used_keys

    def add_used_key(self, addresses_state: dict, address: bytes, public_key: bytes):
        """
        Add a public key to the used keys list
        
        Args:
            addresses_state: Dict of address states to update
            address: Address that used the key
            public_key: Public key that was used
        """
        # Find the last page or create a new one
        page = 1
        last_page_key = None
        last_page_data = None
        
        while True:
            key = self.generate_pkey_key(address, page)
            if key not in self.key_value:
                self.key_value[key] = self.get_paginated_data(address, page)
            
            keys_list = self.key_value[key]
            
            # If this page has space or it's the last page, use it
            if len(keys_list) < config.dev.data_per_page:
                last_page_key = key
                last_page_data = keys_list
                break
                
            # Move to the next page
            page += 1
        
        # Add the public key to the page
        last_page_data.append(public_key)
        self.key_value[last_page_key] = last_page_data
        
        # Update the address state to track used keys
        address_state = addresses_state[address]
        address_state.used_falcon_pk_count += 1
        address_state.update_falcon_pk_count()

    def remove_used_key(self, addresses_state: dict, address: bytes, public_key: bytes):
        """
        Remove a public key from the used keys list (for rollbacks)
        
        Args:
            addresses_state: Dict of address states to update
            address: Address to update
            public_key: Public key to remove
        """
        # Find the page containing this key
        page = 1
        found = False
        
        while True:
            key = self.generate_pkey_key(address, page)
            if key not in self.key_value:
                self.key_value[key] = self.get_paginated_data(address, page)
            
            keys_list = self.key_value[key]
            
            # If this page is empty and it's not the first page, we're done
            if not keys_list and page > 1:
                break
                
            # If the key is in this page, remove it
            if public_key in keys_list:
                keys_list.remove(public_key)
                self.key_value[key] = keys_list
                found = True
                break
                
            # Move to the next page
            page += 1
        
        if found:
            # Update the address state
            address_state = addresses_state[address]
            address_state.used_falcon_pk_count -= 1
            address_state.update_falcon_pk_count(subtract=True)

    def get_paginated_data(self, address, page):
        """
        Get paginated data from the database
        
        Args:
            address: Address to get data for
            page: Page number
            
        Returns:
            List of public keys for this page
        """
        try:
            pbData = self.db.get_raw(self.name + b'_' + address + b'_' + page.to_bytes(8, byteorder='big', signed=False))
            data_list = qbit_pb2.DataList()
            data_list.ParseFromString(bytes(pbData))
            return list(data_list.values)
        except KeyError:
            return []
        except Exception as e:
            logger.error('[get_paginated_data] Exception for %s', self.name)
            logger.exception(e)
            raise

    def put_used_keys(self, batch):
        """
        Write all public keys to database
        
        Args:
            batch: Database batch to use for writing
        """
        if not self.write_access:
            return
        
        for key in self.key_value:
            data_list = qbit_pb2.DataList(values=self.key_value[key])
            self.db.put_raw(key,
                            data_list.SerializeToString(),
                            batch)
