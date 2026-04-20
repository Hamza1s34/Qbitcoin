# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
from concurrent.futures import ThreadPoolExecutor

import argparse
import os
import logging
import grpc
from typing import Optional
from time import sleep
from daemonize import Daemonize

from pyqrllib.pyqrllib import hstr2bin, mnemonic2bin, bin2hstr

from qbitcoin.core import config
from qbitcoin.core.AddressState import AddressState
from qbitcoin.core.FalconHelper import falcon_pk_to_address
from qbitcoin.daemon.helper import logger
from qbitcoin.daemon.helper.DaemonHelper import WalletDecryptionError, Wallet
from qbitcoin.services.WalletAPIService import WalletAPIService
from qbitcoin.generated import qbit_pb2, qbit_pb2_grpc, qbitwallet_pb2
from qbitcoin.generated.qbitwallet_pb2_grpc import add_WalletAPIServicer_to_server
from qbitcoin.core.txs.TransferTransaction import TransferTransaction
from qbitcoin.core.txs.MessageTransaction import MessageTransaction
from qbitcoin.core.txs.SlaveTransaction import SlaveTransaction
from qbitcoin.core.txs.TokenTransaction import TokenTransaction
from qbitcoin.core.txs.TransferTokenTransaction import TransferTokenTransaction

CONNECTION_TIMEOUT = 30
config.create_path(config.user.wallet_dir)
pid = os.path.join(config.user.wallet_dir, 'qrl_walletd.pid')


class WalletD:
    def __init__(self):
        self._wallet_path = os.path.join(config.user.wallet_dir, 'walletd.json')
        self._public_stub = qbit_pb2_grpc.PublicAPIStub(grpc.insecure_channel(config.user.public_api_server))
        self._wallet = None
        self._passphrase = None
        self.load_wallet()

    def to_plain_blocks(self, block):
        pheader = qbitwallet_pb2.PlainBlockHeader()
        pheader.hash_header = bin2hstr(block.header.hash_header)
        pheader.block_number = block.header.block_number
        pheader.timestamp_seconds = block.header.timestamp_seconds
        pheader.hash_header_prev = bin2hstr(block.header.hash_header_prev)
        pheader.reward_block = block.header.reward_block
        pheader.reward_fee = block.header.reward_fee
        pheader.merkle_root = bin2hstr(block.header.merkle_root)

        pheader.mining_nonce = block.header.mining_nonce
        pheader.extra_nonce = block.header.extra_nonce

        pblock = qbitwallet_pb2.PlainBlock()
        pblock.header.MergeFrom(pheader)

        for tx in block.transactions:
            pblock.transactions.extend([self.to_plain_transaction(tx)])

        for genesis_balance in block.genesis_balance:
            pgb = qbitwallet_pb2.PlainGenesisBalance()
            pgb.address = self.address_to_qaddress(genesis_balance.address)
            pgb.balance = genesis_balance.balance
            pblock.genesis_balance.extend([pgb])

        return pblock

    @staticmethod
    def to_plain_address_amount(address_amount):
        am = qbitwallet_pb2.PlainAddressAmount()
        am.address = bin2hstr(address_amount.address)
        am.amount = address_amount.amount
        return am

    def to_plain_transaction(self, tx):
        ptx = qbitwallet_pb2.PlainTransaction()
        if not tx.WhichOneof('transactionType'):
            return ptx
        if tx.master_addr:
            ptx.master_addr = self.address_to_qaddress(tx.master_addr)
        ptx.fee = tx.fee
        ptx.public_key = bin2hstr(tx.public_key)
        ptx.signature = bin2hstr(tx.signature)
        ptx.nonce = tx.nonce
        ptx.transaction_hash = bin2hstr(tx.transaction_hash)
        if tx.WhichOneof('transactionType') != 'coinbase':
            ptx.signer_addr = self.get_address_from_pk(ptx.public_key)

        if tx.WhichOneof('transactionType') == "transfer":
            ptx.transfer.amounts.extend(tx.transfer.amounts)
            for addr in tx.transfer.addrs_to:
                ptx.transfer.addrs_to.extend([self.address_to_qaddress(addr)])

        elif tx.WhichOneof('transactionType') == 'coinbase':
            ptx.coinbase.addr_to = self.address_to_qaddress(tx.coinbase.addr_to)
            ptx.coinbase.amount = tx.coinbase.amount

        elif tx.WhichOneof('transactionType') == 'lattice_public_key':
            ptx.lattice_public_key.MergeFrom(ptx.lattice_public_key())
            ptx.lattice_public_key.kyber_pk = bin2hstr(tx.lattice_public_key.kyber_pk)
            ptx.lattice_public_key.dilithium_pk = bin2hstr(tx.lattice_public_key.dilithium_pk)

        elif tx.WhichOneof('transactionType') == 'message':
            ptx.message.message_hash = bin2hstr(tx.message.message_hash)

        elif tx.WhichOneof('transactionType') == 'token':
            try:
                ptx.token.symbol = tx.token.symbol.decode()
            except UnicodeDecodeError:
                ptx.token.symbol = bin2hstr(tx.token.symbol)
            except Exception:
                ptx.token.symbol = str(tx.token.symbol)
            try:
                ptx.token.name = tx.token.name.decode()
            except UnicodeDecodeError:
                ptx.token.name = bin2hstr(tx.token.name)
            except Exception:
                ptx.token.name = str(tx.token.name)

            ptx.token.owner = self.address_to_qaddress(tx.token.owner)
            ptx.token.decimals = tx.token.decimals
            for initial_balance in tx.token.initial_balances:
                ptx.token.initial_balances.extend([self.to_plain_address_amount(initial_balance)])

        elif tx.WhichOneof('transactionType') == 'transfer_token':
            ptx.transfer_token.token_txhash = bin2hstr(tx.transfer_token.token_txhash)
            ptx.transfer_token.addrs_to.extend(self.addresses_to_qaddress(tx.transfer_token.addrs_to))
            ptx.transfer_token.amounts.extend(tx.transfer_token.amounts)

        elif tx.WhichOneof('transactionType') == 'slave':
            for slave_pk in tx.slave.slave_pks:
                ptx.slave.slave_pks.extend([bin2hstr(slave_pk)])
            ptx.slave.access_types.extend(tx.slave.access_types)

        return ptx

    def generate_slave_tx(self, signer_pk: bytes, slave_pk_list: list, master_addr=None):
        return SlaveTransaction.create(slave_pks=slave_pk_list,
                                       access_types=[0] * len(slave_pk_list),
                                       fee=0,
                                       xmss_pk=signer_pk,
                                       master_addr=master_addr)

    def load_wallet(self):
        self._wallet = Wallet(self._wallet_path)

    @staticmethod
    def address_to_qaddress(address: bytes):
        return 'Q' + bin2hstr(address)

    @staticmethod
    def addresses_to_qaddress(addresses: list):
        qaddresses = []
        for address in addresses:
            qaddresses.append(WalletD.address_to_qaddress(address))
        return qaddresses

    @staticmethod
    def qaddress_to_address(qaddress: str) -> bytes:
        if not qaddress:
            return qaddress
        return bytes(hstr2bin(qaddress[1:]))

    @staticmethod
    def qaddresses_to_address(qaddresses: list) -> list:
        if not qaddresses:
            return qaddresses
        addresses = []
        for qaddress in qaddresses:
            addresses.append(WalletD.qaddress_to_address(qaddress))
        return addresses

    def authenticate(self):
        if not self._passphrase:
            if self._wallet.is_encrypted():
                raise ValueError('Failed: Passphrase Missing')

    def _encrypt_last_item(self):
        if not self._passphrase:
            return
        self._wallet.encrypt_item(len(self._wallet.address_items) - 1, self._passphrase)

    def _get_wallet_index_falcon(self, signer_address: str):
        index, _ = self._wallet.get_address_item(signer_address)
        if index is None:
            raise Exception("Signer Address Not Found ", signer_address)
        falcon_data = self._wallet.get_falcon_by_index(index, self._passphrase)
        return index, falcon_data

    def get_pk_list_from_falcon_list(self, slave_falcon_list):
        return [falcon_data['public_key'] for falcon_data in slave_falcon_list]

    def add_new_address(self, force=False) -> str:
        self.authenticate()

        falcon_data = self._wallet.add_new_address(force)
        self._encrypt_last_item()
        self._wallet.save()
        logger.info("Added New Address")
        return self._wallet.address_items[-1].qaddress

    def add_new_address_with_slaves(self,
                                    number_of_slaves=config.user.number_of_slaves) -> str:
        self.authenticate()

        if not number_of_slaves:
            number_of_slaves = config.user.number_of_slaves

        if number_of_slaves > 100:
            raise Exception("Number of slaves cannot be more than 100")

        falcon_data = self._wallet.add_new_address(True)
        slave_falcon_list = self._wallet.add_slave(index=-1,
                                                   number_of_slaves=number_of_slaves,
                                                   force=True)
        self._encrypt_last_item()

        slave_pk_list = self.get_pk_list_from_falcon_list(slave_falcon_list)
        slave_tx = self.generate_slave_tx(falcon_data['public_key'], slave_pk_list)
        self.sign_and_push_transaction(slave_tx, falcon_data, -1)

        self._wallet.save()
        logger.info("Added New Address With Slaves")
        return self._wallet.address_items[-1].qaddress

    def add_address_from_keys(self, private_key_hex: str, public_key_hex: str) -> str:
        self.authenticate()

        try:
            private_key_bytes = bytes.fromhex(private_key_hex)
            public_key_bytes = bytes.fromhex(public_key_hex)
        except ValueError:
            raise ValueError("Invalid key format")

        # Verify the keys are valid Falcon-512 keys
        if len(private_key_bytes) != 1281 or len(public_key_bytes) != 897:
            raise ValueError("Invalid Falcon-512 key sizes")

        address = falcon_pk_to_address(public_key_bytes)
        qaddress = 'Q' + address.hex()
        
        if self._wallet.get_falcon_by_qaddress(qaddress, self._passphrase):
            raise Exception("Address is already in the wallet")
        
        self._wallet.append_falcon(private_key_bytes, public_key_bytes)
        self._encrypt_last_item()
        self._wallet.save()

        return qaddress

    def list_address(self) -> list:
        self.authenticate()

        addresses = []
        for item in self._wallet.address_items:
            addresses.append(item.qaddress)

        return addresses

    def remove_address(self, qaddress: str) -> bool:
        self.authenticate()
        if self._wallet.remove(qaddress):
            logger.info("Removed Address %s", qaddress)
            return True

        return False

    def validate_address(self, qaddress: str) -> bool:
        try:
            return AddressState.address_is_valid(bytes(hstr2bin(qaddress[1:])))
        except Exception:
            return False

    def get_recovery_seeds(self, qaddress: str):
        self.authenticate()

        falcon_data = self._wallet.get_falcon_by_qaddress(qaddress, self._passphrase)
        if falcon_data:
            logger.info("Recovery seeds requested for %s", qaddress)
            return falcon_data['private_key'].hex(), falcon_data['public_key'].hex()

        raise ValueError("No such address found in wallet")

    def get_wallet_info(self):
        self.authenticate()

        return self._wallet.wallet_info()

    def get_address_state(self, qaddress: str) -> AddressState:
        request = qbit_pb2.GetAddressStateReq(address=bytes(hstr2bin(qaddress[1:])))

        resp = self._public_stub.GetAddressState(request=request)
        return AddressState(resp.state)

    def sign_and_push_transaction(self,
                                  tx,
                                  falcon_data,
                                  index,
                                  group_index=None,
                                  slave_index=None,
                                  enable_save=True):
        logger.info("Signing %s transaction by %s", tx.type, falcon_data['address'])
        # Use Falcon signature for signing
        from qbitcoin.crypto.falcon import FalconSignature
        signature = FalconSignature.sign_message(tx.get_hashable_bytes(), falcon_data['private_key'])
        tx.signature = signature
        tx.public_key = falcon_data['public_key']
        
        if not tx.validate(True):
            raise Exception("Invalid Transaction")

        # Falcon-512 doesn't use OTS indices, so we don't need to update them

        push_transaction_req = qbit_pb2.PushTransactionReq(transaction_signed=tx.pbdata)
        push_transaction_resp = self._public_stub.PushTransaction(push_transaction_req, timeout=CONNECTION_TIMEOUT)
        if push_transaction_resp.error_code != qbit_pb2.PushTransactionResp.SUBMITTED:
            raise Exception(push_transaction_resp.error_description)

    def try_txn_with_last_slave(self, item, index, group_index, falcon_data=None):
        slave = item.slaves[group_index][-1]

        # Falcon-512 doesn't use OTS indices or height
        slave_index = len(item.slaves[group_index]) - 1
        if not falcon_data:
            target_address_item = slave
            if self._passphrase:
                target_address_item = self._wallet.decrypt_address_item(slave, self._passphrase)
            falcon_data = self._wallet.get_falcon_by_item(target_address_item)
        # Falcon-512 doesn't use OTS indices

        return falcon_data

    def is_slave(self, master_address: bytes, slave_pk: bytes) -> bool:
        request = qbit_pb2.IsSlaveReq(master_address=master_address,
                                     slave_pk=slave_pk)

        resp = self._public_stub.IsSlave(request=request)
        return resp.result

    def get_unused_ots_index(self, address: bytes, unused_ots_index_from: int) -> Optional[int]:
        request = qbit_pb2.GetOTSReq(address=address,
                                    unused_ots_index_from=unused_ots_index_from)
        resp = self._public_stub.GetOTS(request=request)
        if not resp.unused_ots_index_found:
            return None
        return resp.next_unused_ots_index

    def get_slave(self, master_qaddress):
        index, item = self._wallet.get_address_item(master_qaddress)
        if index is None:
            raise Exception("Signer Address Not Found ", master_qaddress)

        # Should we check available OTS for master
        # Get slave list using address state
        address_state = self.get_address_state(master_qaddress)

        slave = item.slaves[-1][0]
        if not address_state.validate_slave_with_access_type(str(bytes.fromhex(slave.public_key)), [0]):
            if len(item.slaves) == 1:
                qaddress = item.qaddress
                target_address_item = item
                group_index = None
            else:
                qaddress = item.slaves[-2][-1].qaddress
                target_address_item = item.slaves[-2][-1]
                group_index = -2

            # Falcon-512 doesn't use OTS indices, so we don't need to check this
            pass

            if self._passphrase:
                target_address_item = self._wallet.decrypt_address_item(target_address_item, self._passphrase)

            falcon_data = self._wallet.get_falcon_by_item(target_address_item)

            slaves_pk = [bytes.fromhex(slave_item.public_key) for slave_item in item.slaves[-1]]
            tx = self.generate_slave_tx(falcon_data['public_key'],
                                        slaves_pk,
                                        self.qaddress_to_address(master_qaddress))

            self.sign_and_push_transaction(tx,
                                           falcon_data,
                                           index,
                                           enable_save=False)

            if len(item.slaves) > 1:
                if self.try_txn_with_last_slave(item, index, group_index, falcon_data):
                    return index, len(item.slaves) - 2, len(item.slaves[group_index]) - 1, falcon_data

        else:
            if len(item.slaves) > 1:
                group_index = len(item.slaves) - 2
                falcon_data = self.try_txn_with_last_slave(item, index, group_index)
                if falcon_data:
                    return index, group_index, len(item.slaves[group_index]) - 1, falcon_data
            group_index = len(item.slaves) - 1
            last_slaves = item.slaves[-1]
            for slave_index, slave in enumerate(last_slaves):
                # Falcon-512 doesn't use OTS indices or height, so we can use any slave
                if self._passphrase:
                    slave = self._wallet.decrypt_address_item(slave, self._passphrase)

                slave_falcon = self._wallet.get_falcon_by_item(slave)

                return index, group_index, slave_index, slave_falcon

        return index, -1, -1, None

    def get_slave_xmss(self, master_qaddress):
        """
        Get slave XMSS for a given master address
        """
        return self.get_slave(master_qaddress)

    # def get_slave(self, master_qaddress):
    #     index, item = self._wallet.get_address_item(master_qaddress)
    #     if index is None:
    #         raise Exception("Signer Address Not Found ", master_qaddress)
    #
    #     # Should we check available OTS for master
    #     # Get slave list using address state
    #     address_state = self.get_address_state(master_qaddress)
    #
    #     slave = item.slaves[-1][0]
    #     if not address_state.validate_slave_with_access_type(str(bytes(hstr2bin(slave.pk))), [0]):
    #         if len(item.slaves) == 1:
    #             qaddress = item.qaddress
    #             target_address_item = item
    #             group_index = None
    #         else:
    #             qaddress = item.slaves[-2][-1].qaddress
    #             target_address_item = item.slaves[-2][-1]
    #             group_index = -2
    #
    #         address_state = self.get_address_state(qaddress)
    #         ots_index = address_state.get_unused_ots_index()
    #
    #         if ots_index >= UNRESERVED_OTS_INDEX_START:
    #             raise Exception('Fatal Error!!! No reserved OTS index found')
    #
    #         if self._passphrase:
    #             target_address_item = self._wallet.decrypt_address_item(target_address_item, self._passphrase)
    #
    #         xmss = self._wallet.get_xmss_by_item(target_address_item, ots_index)
    #
    #         slaves_pk = [bytes(hstr2bin(slave_item.pk)) for slave_item in item.slaves[-1]]
    #         tx = self.generate_slave_tx(xmss.pk,
    #                                     slaves_pk,
    #                                     self.qaddress_to_address(master_qaddress))
    #
    #         self.sign_and_push_transaction(tx,
    #                                        xmss,
    #                                        index,
    #                                        enable_save=False)
    #
    #         if len(item.slaves) > 1:
    #             if self.try_txn_with_last_slave(item, index, group_index, xmss):
    #                 return index, len(item.slaves) - 2, len(item.slaves[group_index]) - 1, xmss
    #
    #     else:
    #         if len(item.slaves) > 1:
    #             group_index = len(item.slaves) - 2
    #             xmss = self.try_txn_with_last_slave(item, index, group_index)
    #             if xmss:
    #                 return index, group_index, len(item.slaves[group_index]) - 1, xmss
    #         group_index = len(item.slaves) - 1
    #         last_slaves = item.slaves[-1]
    #         for slave_index in range(len(last_slaves)):
    #             slave = last_slaves[slave_index]
    #
    #             # Check if all ots index has been marked as used
    #             if slave.index > 2 ** slave.height - 1:
    #                 continue
    #
    #             # Ignore usage of last 5 ots indexes for the last slave in slave group
    #             if slave_index + 1 == len(last_slaves) and slave.index >= 2 ** slave.height - 5:
    #                 continue
    #
    #             if self._passphrase:
    #                 slave = self._wallet.decrypt_address_item(slave, self._passphrase)
    #
    #             slave_address_state = self.get_address_state(slave.qaddress)
    #
    #             if slave_index + 1 == len(last_slaves) and slave.index > 2 ** slave.height - 100:
    #
    #                 ots_index = slave_address_state.get_unused_ots_index(0)
    #                 if ots_index >= UNRESERVED_OTS_INDEX_START:
    #                     raise Exception("Fatal Error, no unused reserved OTS index")
    #
    #                 curr_slave_xmss = self._wallet.get_xmss_by_item(slave, ots_index)
    #
    #                 slave_xmss_list = self._wallet.add_slave(index=index,
    #                                                          height=slave.height,
    #                                                          number_of_slaves=config.user.number_of_slaves,
    #                                                          passphrase=self._passphrase,
    #                                                          force=True)
    #                 slave_pk_list = self.get_pk_list_from_xmss_list(slave_xmss_list)
    #
    #                 tx = self.generate_slave_tx(bytes(hstr2bin(slave.pk)),
    #                                             slave_pk_list,
    #                                             self.qaddress_to_address(item.qaddress))
    #
    #                 self.sign_and_push_transaction(tx,
    #                                                curr_slave_xmss,
    #                                                index,
    #                                                enable_save=False)
    #
    #             ots_index = slave_address_state.get_unused_ots_index(slave.index)
    #
    #             if ots_index == None:  # noqa
    #                 self._wallet.set_slave_ots_index(index,
    #                                                  group_index,
    #                                                  slave_index,
    #                                                  2 ** slave.height)
    #                 continue
    #
    #             slave_xmss = self._wallet.get_xmss_by_item(slave, ots_index)
    #
    #             return index, group_index, slave_index, slave_xmss
    #
    #     return index, -1, -1, None

    def get_slave_xmss(self, master_qaddress):
        index, group_index, slave_index, slave_falcon = self.get_slave(master_qaddress)

        return index, group_index, slave_index, slave_falcon

    def get_slave_list(self, qaddress) -> list:
        self.authenticate()
        _, addr_item = self._wallet.get_address_item(qaddress)
        if addr_item is None:
            raise Exception("Address Not Found ", qaddress)
        return addr_item.slaves

    def verify_ots(self, signer_address, falcon_data, user_ots_index):
        """
        Falcon-512 doesn't use OTS indices, so this is a no-op for compatibility
        """
        # Falcon-512 doesn't use OTS indices, so we don't need to verify them
        pass

    def relay_transfer_txn(self,
                           qaddresses_to: list,
                           amounts: list,
                           fee: int,
                           master_qaddress,
                           signer_address: str,
                           ots_index: int):
        self.authenticate()
        index, falcon_data = self._get_wallet_index_falcon(signer_address)
        self.verify_ots(signer_address, falcon_data, user_ots_index=ots_index)

        tx = TransferTransaction.create(addrs_to=self.qaddresses_to_address(qaddresses_to),
                                        amounts=amounts,
                                        message_data=None,
                                        fee=fee,
                                        xmss_pk=falcon_data['public_key'],
                                        master_addr=self.qaddress_to_address(master_qaddress))

        self.sign_and_push_transaction(tx, falcon_data, index)

        return self.to_plain_transaction(tx.pbdata)

    def relay_transfer_txn_by_slave(self,
                                    qaddresses_to: list,
                                    amounts: list,
                                    fee: int,
                                    master_qaddress):
        self.authenticate()
        index, group_index, slave_index, slave_falcon = self.get_slave_xmss(master_qaddress)
        if slave_index == -1:
            raise Exception("No Slave Found")

        tx = TransferTransaction.create(addrs_to=self.qaddresses_to_address(qaddresses_to),
                                        amounts=amounts,
                                        message_data=None,
                                        fee=fee,
                                        xmss_pk=slave_falcon['public_key'],
                                        master_addr=self.qaddress_to_address(master_qaddress))

        self.sign_and_push_transaction(tx, slave_falcon, index, group_index, slave_index)

        return self.to_plain_transaction(tx.pbdata)

    def relay_message_txn(self,
                          message: str,
                          fee: int,
                          master_qaddress,
                          signer_address: str,
                          ots_index: int):
        self.authenticate()
        index, falcon_data = self._get_wallet_index_falcon(signer_address)
        self.verify_ots(signer_address, falcon_data, user_ots_index=ots_index)

        tx = MessageTransaction.create(message_hash=message.encode(),
                                       addr_to=None,
                                       fee=fee,
                                       xmss_pk=falcon_data['public_key'],
                                       master_addr=self.qaddress_to_address(master_qaddress))

        self.sign_and_push_transaction(tx, falcon_data, index)

        return self.to_plain_transaction(tx.pbdata)

    def relay_message_txn_by_slave(self,
                                   message: str,
                                   fee: int,
                                   master_qaddress):
        self.authenticate()
        index, group_index, slave_index, slave_falcon = self.get_slave_xmss(master_qaddress)
        if slave_index == -1:
            raise Exception("No Slave Found")

        tx = MessageTransaction.create(message_hash=message.encode(),
                                       addr_to=None,
                                       fee=fee,
                                       xmss_pk=slave_falcon['public_key'],
                                       master_addr=self.qaddress_to_address(master_qaddress))

        self.sign_and_push_transaction(tx, slave_falcon, index, group_index, slave_index)

        return self.to_plain_transaction(tx.pbdata)

    def relay_token_txn(self,
                        symbol: str,
                        name: str,
                        owner_qaddress: str,
                        decimals: int,
                        qaddresses: list,
                        amounts: list,
                        fee: int,
                        master_qaddress,
                        signer_address: str,
                        ots_index: int):
        self.authenticate()

        if len(qaddresses) != len(amounts):
            raise Exception("Number of Addresses & Amounts Mismatch")

        index, falcon_data = self._get_wallet_index_falcon(signer_address)
        self.verify_ots(signer_address, falcon_data, user_ots_index=ots_index)

        initial_balances = []
        for idx, qaddress in enumerate(qaddresses):
            initial_balances.append(qbit_pb2.AddressAmount(address=self.qaddress_to_address(qaddress),
                                                          amount=amounts[idx]))
        tx = TokenTransaction.create(symbol=symbol.encode(),
                                     name=name.encode(),
                                     owner=self.qaddress_to_address(owner_qaddress),
                                     decimals=decimals,
                                     initial_balances=initial_balances,
                                     fee=fee,
                                     xmss_pk=falcon_data['public_key'],
                                     master_addr=self.qaddress_to_address(master_qaddress))

        self.sign_and_push_transaction(tx, falcon_data, index)

        return self.to_plain_transaction(tx.pbdata)

    def relay_token_txn_by_slave(self,
                                 symbol: str,
                                 name: str,
                                 owner_qaddress: str,
                                 decimals: int,
                                 qaddresses: list,
                                 amounts: list,
                                 fee: int,
                                 master_qaddress):
        self.authenticate()

        if len(qaddresses) != len(amounts):
            raise Exception("Number of Addresses & Amounts Mismatch")

        index, group_index, slave_index, slave_falcon = self.get_slave_xmss(master_qaddress)
        if slave_index == -1:
            raise Exception("No Slave Found")

        initial_balances = []
        for idx, qaddress in enumerate(qaddresses):
            initial_balances.append(qbit_pb2.AddressAmount(address=self.qaddress_to_address(qaddress),
                                                          amount=amounts[idx]))
        tx = TokenTransaction.create(symbol=symbol.encode(),
                                     name=name.encode(),
                                     owner=self.qaddress_to_address(owner_qaddress),
                                     decimals=decimals,
                                     initial_balances=initial_balances,
                                     fee=fee,
                                     xmss_pk=slave_falcon['public_key'],
                                     master_addr=self.qaddress_to_address(master_qaddress))

        self.sign_and_push_transaction(tx, slave_falcon, index, group_index, slave_index)

        return self.to_plain_transaction(tx.pbdata)

    def relay_transfer_token_txn(self,
                                 qaddresses_to: list,
                                 amounts: list,
                                 token_txhash: str,
                                 fee: int,
                                 master_qaddress,
                                 signer_address: str,
                                 ots_index: int):
        self.authenticate()
        index, falcon_data = self._get_wallet_index_falcon(signer_address)
        self.verify_ots(signer_address, falcon_data, user_ots_index=ots_index)

        tx = TransferTokenTransaction.create(token_txhash=bytes(hstr2bin(token_txhash)),
                                             addrs_to=self.qaddresses_to_address(qaddresses_to),
                                             amounts=amounts,
                                             fee=fee,
                                             xmss_pk=falcon_data['public_key'],
                                             master_addr=self.qaddress_to_address(master_qaddress))

        self.sign_and_push_transaction(tx, falcon_data, index)

        return self.to_plain_transaction(tx.pbdata)

    def relay_transfer_token_txn_by_slave(self,
                                          qaddresses_to: list,
                                          amounts: list,
                                          token_txhash: str,
                                          fee: int,
                                          master_qaddress):
        self.authenticate()
        index, group_index, slave_index, slave_falcon = self.get_slave_xmss(master_qaddress)
        if slave_index == -1:
            raise Exception("No Slave Found")

        tx = TransferTokenTransaction.create(token_txhash=bytes(hstr2bin(token_txhash)),
                                             addrs_to=self.qaddresses_to_address(qaddresses_to),
                                             amounts=amounts,
                                             fee=fee,
                                             xmss_pk=slave_falcon['public_key'],
                                             master_addr=self.qaddress_to_address(master_qaddress))

        self.sign_and_push_transaction(tx, slave_falcon, index, group_index, slave_index)

        return self.to_plain_transaction(tx.pbdata)

    def relay_slave_txn(self,
                        slave_pks: list,
                        access_types: list,
                        fee: int,
                        master_qaddress,
                        signer_address: str,
                        ots_index: int):
        self.authenticate()
        index, falcon_data = self._get_wallet_index_falcon(signer_address)
        self.verify_ots(signer_address, falcon_data, user_ots_index=ots_index)

        tx = SlaveTransaction.create(slave_pks=slave_pks,
                                     access_types=access_types,
                                     fee=fee,
                                     xmss_pk=falcon_data['public_key'],
                                     master_addr=self.qaddress_to_address(master_qaddress))

        self.sign_and_push_transaction(tx, falcon_data, index)

        return self.to_plain_transaction(tx.pbdata)

    def relay_slave_txn_by_slave(self,
                                 slave_pks: list,
                                 access_types: list,
                                 fee: int,
                                 master_qaddress):
        self.authenticate()
        index, group_index, slave_index, slave_falcon = self.get_slave_xmss(master_qaddress)
        if slave_index == -1:
            raise Exception("No Slave Found")

        tx = SlaveTransaction.create(slave_pks=slave_pks,
                                     access_types=access_types,
                                     fee=fee,
                                     xmss_pk=slave_falcon['public_key'],
                                     master_addr=self.qaddress_to_address(master_qaddress))

        self.sign_and_push_transaction(tx, slave_falcon, index, group_index, slave_index)

        return self.to_plain_transaction(tx.pbdata)

    def encrypt_wallet(self, passphrase: str):
        if self._wallet.is_encrypted():
            raise Exception('Wallet Already Encrypted')
        if not passphrase:
            raise Exception("Missing Passphrase")
        if len(self._wallet.address_items) == 0:
            raise ValueError('Cannot be encrypted as wallet does not have any address.')
        self._wallet.encrypt(passphrase)
        self._wallet.save()
        logger.info("Wallet Encrypted")

    def lock_wallet(self):
        if not self._wallet.is_encrypted():
            raise Exception('You cannot lock an unencrypted Wallet')

        self._passphrase = None
        logger.info("Wallet Locked")

    def unlock_wallet(self, passphrase: str):
        if not self._wallet.is_encrypted():
            raise Exception('You cannot unlock an unencrypted Wallet')

        self._passphrase = passphrase
        self._wallet.decrypt(passphrase, first_address_only=True)  # Check if Password Correct
        self._wallet.encrypt_item(0, passphrase)  # Re-Encrypt first address item
        logger.info("Wallet Unlocked")

    def change_passphrase(self, old_passphrase: str, new_passphrase: str):
        if len(old_passphrase) == 0:
            raise Exception('Missing Old Passphrase')

        if len(new_passphrase) == 0:
            raise Exception('Missing New Passphrase')

        if old_passphrase == new_passphrase:
            raise Exception('Old Passphrase and New Passphrase cannot be same')

        self._passphrase = old_passphrase

        if not self._wallet:
            self.unlock_wallet(old_passphrase)
        try:
            self._wallet.decrypt(old_passphrase)
        except WalletDecryptionError:
            raise ValueError('Invalid Old Passphrase')

        self._wallet.encrypt(new_passphrase)
        self._wallet.save()
        self.lock_wallet()
        logger.info("Passphrase Changed")

    def get_mini_transactions_by_address(self, qaddress: str, item_per_page: int, page_number: int) -> tuple:
        address = self.qaddress_to_address(qaddress)
        response = self._public_stub.GetMiniTransactionsByAddress(
            qbit_pb2.GetMiniTransactionsByAddressReq(address=address,
                                                    item_per_page=item_per_page,
                                                    page_number=page_number))
        return response.mini_transactions, response.balance

    def get_transaction(self, tx_hash: str):
        txhash = bytes(hstr2bin(tx_hash))
        response = self._public_stub.GetTransaction(qbit_pb2.GetTransactionReq(tx_hash=txhash))
        block_header_hash = None
        if response.block_header_hash:
            block_header_hash = bin2hstr(response.block_header_hash)
        return self.to_plain_transaction(response.tx), str(response.confirmations), response.block_number, block_header_hash

    def get_balance(self, qaddress: str) -> int:
        address = self.qaddress_to_address(qaddress)
        response = self._public_stub.GetBalance(qbit_pb2.GetBalanceReq(address=address))
        return response.balance

    def get_total_balance(self) -> int:
        self.authenticate()

        addresses = []
        for item in self._wallet.address_items:
            addresses.append(bytes(hstr2bin(item.qaddress[1:])))

        response = self._public_stub.GetTotalBalance(qbit_pb2.GetTotalBalanceReq(addresses=addresses))
        return response.balance
 
    def get_height(self) -> int:
        response = self._public_stub.GetHeight(qbit_pb2.GetHeightReq())
        return response.height

    def get_block(self, header_hash: str):
        headerhash = bytes(hstr2bin(header_hash))
        response = self._public_stub.GetBlock(qbit_pb2.GetBlockReq(header_hash=headerhash))
        return self.to_plain_blocks(response.block)

    def get_block_by_number(self, block_number: int):
        response = self._public_stub.GetBlockByNumber(qbit_pb2.GetBlockByNumberReq(block_number=block_number))
        return self.to_plain_blocks(response.block)

    def get_address_from_pk(self, pk: str) -> str:
        # Only handle Falcon-512 public keys (1793 bytes)
        pk_bytes = bytes(hstr2bin(pk))
        if len(pk_bytes) == 1793:
            address = falcon_pk_to_address(pk_bytes)
            return self.address_to_qaddress(address)
        else:
            # Invalid key size for Falcon-512
            return ""

    def get_node_info(self):
        return self._public_stub.GetNodeState(qbit_pb2.GetNodeStateReq())


def run():
    logger.initialize_default(force_console_output=True).setLevel(logging.INFO)
    file_handler = logger.log_to_file()
    file_handler.setLevel(logging.INFO)

    LOG_FORMAT_CUSTOM = '%(asctime)s| %(levelname)s : %(message)s'  # noqa

    logger.set_colors(False, LOG_FORMAT_CUSTOM)
    logger.set_unhandled_exception_handler()

    walletd = WalletD()  # noqa
    wallet_server = grpc.server(ThreadPoolExecutor(max_workers=config.user.wallet_api_threads),
                                maximum_concurrent_rpcs=config.user.wallet_api_max_concurrent_rpc)
    add_WalletAPIServicer_to_server(WalletAPIService(walletd), wallet_server)

    wallet_server.add_insecure_port("{0}:{1}".format(config.user.wallet_api_host,
                                                     config.user.wallet_api_port))
    wallet_server.start()

    logger.info("WalletAPIService Started")

    try:
        while True:
            sleep(60)
    except Exception:  # noqa
        wallet_server.stop(0)


def parse_arguments():
    parser = argparse.ArgumentParser(description='QRL node')
    parser.add_argument('--qrldir', '-d', dest='qrl_dir', default=config.user.qrl_dir,
                        help="Use a different directory for node data/configuration")
    parser.add_argument('--network-type', dest='network_type', choices=['mainnet', 'testnet'],
                        default='mainnet', required=False, help="Runs QRL Testnet Node")
    return parser.parse_args()


def main():
    args = parse_arguments()

    qrl_dir_post_fix = ''
    copy_files = []
    if args.network_type == 'testnet':
        qrl_dir_post_fix = '-testnet'
        package_directory = os.path.dirname(os.path.abspath(__file__))
        copy_files.append(os.path.join(package_directory, '../network/testnet/genesis.yml'))
        copy_files.append(os.path.join(package_directory, '../network/testnet/config.yml'))

    config.user.qrl_dir = os.path.expanduser(os.path.normpath(args.qrl_dir) + qrl_dir_post_fix)
    config.create_path(config.user.qrl_dir, copy_files)
    config.user.load_yaml(config.user.config_path)

    daemon = Daemonize(app="qrl_walletd", pid=pid, action=run)
    daemon.start()


if __name__ == '__main__':
    main()
