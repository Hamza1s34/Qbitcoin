# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
import functools
import os
import base64
from collections import namedtuple
from typing import List, Optional

import simplejson

from qbitcoin.core import config
from qbitcoin.core.misc import logger
from qbitcoin.crypto.AESHelper import AESHelper
from qbitcoin.crypto.falcon import FalconSignature
from qbitcoin.tools.wallet_creator import WalletCreator
from qbitcoin.crypto.falcon import PUBLIC_KEY_SIZE, SECRET_KEY_SIZE

FalconAddressItem = namedtuple('FalconAddressItem',
                              'qaddress private_key public_key private_key_size public_key_size signature_type encrypted')


class WalletException(Exception):
    pass


class WalletEncryptionError(WalletException):
    pass


class WalletDecryptionError(WalletException):
    pass


class WalletVersionError(WalletException):
    pass


class Wallet:
    def __init__(self, wallet_path=None):
        if wallet_path is None:
            wallet_path = self.get_default_wallet_path()

        self.wallet_path = wallet_path
        self._address_items = []
        self.version = 1

        self.load()

    @staticmethod
    def get_default_wallet_path() -> str:
        config.create_path(config.user.wallet_dir)
        return os.path.join(config.user.wallet_dir,
                            config.dev.wallet_dat_filename)

    @property
    def address_items(self) -> List[FalconAddressItem]:
        """
        Returns all address items in the wallet
        :return:
        """
        return self._address_items

    @property
    def addresses(self) -> List[bytes]:
        """
        Returns all address items in the wallet
        :return:
        """
        result = []
        for item in self._address_items:
            try:
                if item.qaddress.startswith('Q'):
                    # Handle Q-address format (Q + hex)
                    addr_hex = item.qaddress[1:]
                    result.append(bytes.fromhex(addr_hex))
                else:
                    # Handle base64 encoded address
                    result.append(base64.b64decode(item.qaddress))
            except Exception as e:
                logger.warning(f"Error decoding address {item.qaddress}: {str(e)}")
                # Return empty bytes as a fallback
                result.append(b'')
        return result

    @property
    def encrypted(self) -> bool:
        if len(self.address_items) == 0:
            return False
        return all([item.encrypted for item in self.address_items])

    @property
    def encrypted_partially(self) -> bool:
        # FIXME: slow, makes 2 passes over address_items.
        return any([item.encrypted for item in self.address_items]) and not self.encrypted

    @functools.lru_cache(maxsize=20)
    def get_falcon_by_index(self, idx, passphrase=None) -> Optional[dict]:
        """
        Gets Falcon-512 key pair based on the information contained in the wallet
        :param idx: The index of the address item
        :param passphrase: passphrase to decrypt
        :return: A Falcon-512 key pair dictionary
        """
        if passphrase:
            self.decrypt_item(idx, passphrase)

        falcon_keypair = self._get_falcon_by_index_no_cache(idx)

        if passphrase:
            self.encrypt_item(idx, passphrase)

        return falcon_keypair

    def is_encrypted(self) -> bool:
        if len(self.address_items) == 0:
            return False

        return self.address_items[0].encrypted

    def wallet_info(self):
        """
        Provides Wallet Info
        :return:
        """

        return self.version, len(self._address_items), self.encrypted

    def _get_falcon_by_index_no_cache(self, idx) -> Optional[dict]:
        """
        Generates a Falcon-512 key pair based on the information contained in the wallet
        :param idx: The index of the address item
        :return: A Falcon-512 key pair dictionary
        """
        if idx >= len(self._address_items):
            return None

        item = self._address_items[idx]
        
        # For Falcon-512, we store the keys directly
        try:
            private_key_bytes = base64.b64decode(item.private_key)
            public_key_bytes = base64.b64decode(item.public_key)
            
            # Handle address - it's already in the correct Q format
            address = item.qaddress
            
            # Extract the hex part for address_bytes (remove Q prefix)
            if address.startswith('Q'):
                address_hex = address[1:]
                address_bytes = bytes.fromhex(address_hex)
            else:
                # Fallback for other formats
                address_bytes = base64.b64decode(address)
                
            falcon_keypair = {
                'private_key_bytes': private_key_bytes,
                'public_key_bytes': public_key_bytes,
                'address': address,
                'address_bytes': address_bytes,
                'private_key_size': item.private_key_size,
                'public_key_size': item.public_key_size
            }
            
            return falcon_keypair
        except Exception as e:
            logger.warning(f"Error decoding keys: {str(e)}")
            return None

    @staticmethod
    def _get_Qaddress(addr: bytes) -> str:
        """
        Gets an address in Q format from bytes
        :param addr:
        :return:
        """
        return 'Q' + addr.hex()

    @staticmethod
    def _get_address_item_from_falcon(private_key_bytes: bytes, public_key_bytes: bytes) -> FalconAddressItem:
        """
        Creates an address item from Falcon-512 key pair
        """
        # Generate address from public key
        address = WalletCreator.generate_address(public_key_bytes)
        
        return FalconAddressItem(
            qaddress=address,
            private_key=base64.b64encode(private_key_bytes).decode(),
            public_key=base64.b64encode(public_key_bytes).decode(),
            private_key_size=len(private_key_bytes),
            public_key_size=len(public_key_bytes),
            signature_type='FALCON',
            encrypted=False
        )

    def get_address_item(self, qaddress) -> tuple[int, Optional[FalconAddressItem]]:
        for idx, item in enumerate(self._address_items):
            if item.qaddress == qaddress:
                return idx, item
        return -1, None

    def get_falcon_by_address(self, search_addr) -> Optional[dict]:
        search_addr_str = self._get_Qaddress(search_addr)
        return self.get_falcon_by_qaddress(search_addr_str)

    def get_falcon_by_qaddress(self, search_addr_str, passphrase: str=None) -> Optional[dict]:
        idx, _ = self.get_address_item(search_addr_str)

        if idx == -1:
            return None

        return self.get_falcon_by_index(idx, passphrase)

    def set_nonce(self, index, nonce):
        """
        Set nonce for Falcon-512 address (equivalent to ots_index for XMSS)
        """
        item = self._address_items[index]
        # Falcon-512 doesn't use nonce in the same way as XMSS, but we keep it for compatibility
        self._address_items[index] = FalconAddressItem(
            qaddress=item.qaddress,
            private_key=item.private_key,
            public_key=item.public_key,
            private_key_size=item.private_key_size,
            public_key_size=item.public_key_size,
            signature_type=item.signature_type,
            encrypted=item.encrypted
        )
        self.save()

    def verify_wallet(self):
        """
        Confirms that json address data is correct and valid.
        For Falcon-512, we verify the key pairs and addresses
        :return: True if valid
        """
        num_items = len(self._address_items)
        if num_items == 0:
            return True  # Empty wallet is valid
            
        if not self.encrypted:
            try:
                for i in range(num_items):
                    # Get the falcon keypair
                    item = self._address_items[i]
                    
                    # Verify we can decode both keys
                    try:
                        private_key = base64.b64decode(item.private_key)
                        public_key = base64.b64decode(item.public_key)
                    except Exception as e:
                        logger.warning(f"Error decoding keys: {str(e)}")
                        return False
                    
                    # Verify the address format
                    if not item.qaddress.startswith('Q'):
                        logger.warning(f"Invalid address format: {item.qaddress}")
                        return False
                        
                    # Generate the address from the public key and compare
                    expected_address = WalletCreator.generate_address(public_key)
                    if item.qaddress != expected_address:
                        logger.warning(f"Address mismatch: {item.qaddress} != {expected_address}")
                        return False
                    
            except Exception as e:
                logger.warning(f"Wallet verification error: {str(e)}")
                return False

        return True

    def _read_wallet_ver0(self, filename) -> None:
        def get_address_item_from_json(addr_json: dict) -> FalconAddressItem:
            # address -> qaddress for webwallet compatibility
            if isinstance(addr_json, dict) and "address" in addr_json:
                addr_json["qaddress"] = addr_json.pop("address")
            return FalconAddressItem(**addr_json)

        try:
            with open(filename, "rb") as infile:
                data = simplejson.loads(infile.read())
                if isinstance(data, list):
                    answer = [get_address_item_from_json(d) for d in data if isinstance(d, dict)]
                else:
                    answer = []
            self._address_items = answer
            self.version = 0
        except FileNotFoundError:
            return

    def _read_wallet_ver1(self, filename) -> None:
        def get_address_item_from_json(addr_json: dict, encrypted: bool) -> FalconAddressItem:
            # address -> qaddress for webwallet compatibility
            addr_json["qaddress"] = addr_json.pop("address")
            # Make sure key sizes are included
            if "private_key_size" not in addr_json:
                # Try to determine size from the keys themselves
                try:
                    private_key_bytes = base64.b64decode(addr_json["private_key"])
                    addr_json["private_key_size"] = len(private_key_bytes)
                except:
                    addr_json["private_key_size"] = SECRET_KEY_SIZE
                    
            if "public_key_size" not in addr_json:
                try:
                    public_key_bytes = base64.b64decode(addr_json["public_key"])
                    addr_json["public_key_size"] = len(public_key_bytes)
                except:
                    addr_json["public_key_size"] = PUBLIC_KEY_SIZE
            
            # Remove encrypted if it already exists in addr_json to avoid duplicate
            if "encrypted" in addr_json:
                addr_json.pop("encrypted")
                    
            return FalconAddressItem(encrypted=encrypted, **addr_json)

        try:
            with open(filename, "rb") as infile:
                data = simplejson.loads(infile.read())
                answer = [get_address_item_from_json(d, data["encrypted"]) for d in data["addresses"]]
            self._address_items = answer
            self.version = data.get("version", 1)
        except FileNotFoundError:
            return

    def _read_wallet_ver2(self, filename) -> None:
        def get_address_item_from_json(addr_json: dict, encrypted: bool) -> FalconAddressItem:
            # address -> qaddress for webwallet compatibility
            addr_json["qaddress"] = addr_json.pop("address")
            
            # Ensure key sizes are available
            if "private_key_size" not in addr_json:
                try:
                    private_key_bytes = base64.b64decode(addr_json["private_key"])
                    addr_json["private_key_size"] = len(private_key_bytes)
                except:
                    addr_json["private_key_size"] = SECRET_KEY_SIZE
                    
            if "public_key_size" not in addr_json:
                try:
                    public_key_bytes = base64.b64decode(addr_json["public_key"])
                    addr_json["public_key_size"] = len(public_key_bytes)
                except:
                    addr_json["public_key_size"] = PUBLIC_KEY_SIZE
                    
            return FalconAddressItem(encrypted=encrypted, **addr_json)

        try:
            with open(filename, "rb") as infile:
                data = simplejson.loads(infile.read())
                answer = [get_address_item_from_json(d, data["encrypted"]) for d in data["addresses"]]
            self._address_items = answer
            self.version = 2
        except FileNotFoundError:
            return

    def save_wallet(self, filename):
        if not self.verify_wallet():
            raise WalletException("Could not be saved. Invalid wallet.")

        with open(filename, "wb") as outfile:
            address_items_asdict = [a._asdict() for a in self._address_items]
            for a in address_items_asdict:
                a["address"] = a.pop("qaddress")  # for backwards compatibility with webwallet
                # Keep encrypted field for new wallet format
                # Also ensure private_key_size and public_key_size are included

            output = {
                "addresses": address_items_asdict,
                "encrypted": self.encrypted,
                "version": 2  # New version for .wallet format
            }
            data_out = simplejson.dumps(output).encode('ascii')
            outfile.write(data_out)

    def decrypt_item(self, index: int, key: str):
        cipher = AESHelper(key)
        tmp = self._address_items[index]._asdict()  # noqa
        tmp['private_key'] = cipher.decrypt(tmp['private_key']).decode()
        tmp['public_key'] = cipher.decrypt(tmp['public_key']).decode()
        tmp['encrypted'] = False
        self._address_items[index] = FalconAddressItem(**tmp)

    def decrypt_item_ver0(self, index: int, key: str):
        cipher = AESHelper(key)
        tmp = self._address_items[index]._asdict()  # noqa
        tmp['qaddress'] = cipher.decrypt(tmp['qaddress']).decode()
        tmp['private_key'] = cipher.decrypt(tmp['private_key']).decode()
        tmp['public_key'] = cipher.decrypt(tmp['public_key']).decode()
        tmp['encrypted'] = False
        self._address_items[index] = FalconAddressItem(**tmp)

    def encrypt_item(self, index: int, key: str):
        cipher = AESHelper(key)
        tmp = self._address_items[index]._asdict()  # noqa
        tmp['private_key'] = cipher.encrypt(tmp['private_key'].encode())
        tmp['public_key'] = cipher.encrypt(tmp['public_key'].encode())
        tmp['encrypted'] = True
        self._address_items[index] = FalconAddressItem(**tmp)

    def decrypt(self, password: str, first_address_only: bool=False):
        if self.encrypted_partially:
            raise WalletEncryptionError("Some addresses are already decrypted. Please re-encrypt all addresses before"
                                        "running decrypt().")
        elif not self.encrypted:
            raise WalletEncryptionError("Wallet is already unencrypted.")

        if self.version == 0:
            decryptor = self.decrypt_item_ver0
        elif self.version in [1, 2]:
            decryptor = self.decrypt_item
        else:
            raise WalletVersionError("Wallet.decrypt() can only decrypt wallet files of version 0/1/2")

        try:
            for i in range(len(self._address_items)):
                decryptor(i, password)
                if first_address_only:
                    return
        except Exception as e:
            raise WalletDecryptionError("Error during decryption. Likely due to invalid password: {}".format(str(e)))

        if not self.verify_wallet():
            raise WalletDecryptionError("Decrypted wallet is not valid. Likely due to invalid password")

    def encrypt(self, key: str):
        if self.encrypted_partially:
            raise WalletEncryptionError("Please decrypt all addresses before adding a new one to the wallet."
                                        "This is to ensure they are all encrypted with the same key.")
        elif self.encrypted:
            raise WalletEncryptionError("Wallet is already encrypted.")

        for i in range(len(self._address_items)):
            self.encrypt_item(i, key)

    def save(self):
        if self.version == 0:
            raise WalletVersionError("Your wallet.json is version 0. Saving will transform it to version 1."
                                     "Please decrypt your wallet before proceeding.")

        if self.encrypted_partially:
            raise WalletEncryptionError("Not all addresses are encrypted! Please ensure everything is "
                                        "decrypted/encrypted before saving it.")

        self.save_wallet(self.wallet_path)

    def load(self):
        try:
            self._read_wallet_ver1(self.wallet_path)
        except TypeError:
            logger.info("ReadWallet: reading ver1 wallet failed, this must be an old wallet")
            self._read_wallet_ver0(self.wallet_path)

    def append_falcon(self, private_key_bytes: bytes, public_key_bytes: bytes):
        """
        Append a new Falcon-512 key pair to the wallet
        """
        tmp_item = self._get_address_item_from_falcon(private_key_bytes, public_key_bytes)
        self._address_items.append(tmp_item)

    def add_new_address(self, force=False):
        """
        Generate a new Falcon-512 address and add it to the wallet
        """
        if not force:
            if self.encrypted or self.encrypted_partially:
                raise WalletEncryptionError("Please decrypt all addresses in this wallet before adding a new address!")

        # Generate new Falcon-512 key pair
        private_key_bytes, public_key_bytes = FalconSignature.generate_keypair()
        
        self.append_falcon(private_key_bytes, public_key_bytes)
        
        # Return falcon keypair
        return {
            'private_key_bytes': private_key_bytes,
            'public_key_bytes': public_key_bytes,
            'address': self._address_items[-1].qaddress,
            'private_key_size': len(private_key_bytes),
            'public_key_size': len(public_key_bytes)
        }

    def add_address_from_keys(self, private_key_bytes: bytes, public_key_bytes: bytes):
        """
        Add an address to the wallet from existing Falcon-512 keys
        Used for wallet recovery
        """
        if self.encrypted or self.encrypted_partially:
            raise WalletEncryptionError("Please decrypt all addresses in this wallet before adding a new address!")
        
        self.append_falcon(private_key_bytes, public_key_bytes)
        
        return {
            'private_key_bytes': private_key_bytes,
            'public_key_bytes': public_key_bytes,
            'address': self._address_items[-1].qaddress,
            'private_key_size': len(private_key_bytes),
            'public_key_size': len(public_key_bytes)
        }

    def remove(self, addr) -> bool:
        for item in self._address_items:
            if item.qaddress == addr:
                try:
                    self._address_items.remove(item)
                    self.save_wallet(self.wallet_path)
                    return True
                except ValueError:
                    logger.warning("Could not remove address from wallet")
        return False
