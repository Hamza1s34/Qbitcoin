# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
import traceback
import os
from statistics import variance, mean

from pyqrllib.pyqrllib import hstr2bin

from qbitcoin.core import config
from qbitcoin.core.AddressState import AddressState
from qbitcoin.core.misc import logger
from qbitcoin.core.qbitnode import QbitcoinNode
from qbitcoin.core.txs.Transaction import Transaction, CODEMAP
from qbitcoin.core.FalconHelper import falcon_pk_to_address
from qbitcoin.core.OptimizedAddressState import OptimizedAddressState
from qbitcoin.generated import qbit_pb2
from qbitcoin.generated.qbit_pb2_grpc import PublicAPIServicer
from qbitcoin.services.grpcHelper import GrpcExceptionWrapper


class PublicAPIService(PublicAPIServicer):
    MAX_REQUEST_QUANTITY = 100

    # TODO: Separate the Service from the node model
    def __init__(self, qbitnode: QbitcoinNode):
        self.qbitnode = qbitnode

    @GrpcExceptionWrapper(qbit_pb2.GetAddressFromPKResp)
    def GetAddressFromPK(self, request: qbit_pb2.GetAddressFromPKReq, context) -> qbit_pb2.GetAddressFromPKResp:
        # Only handle Falcon-512 public keys (1793 bytes)
        if len(request.pk) == 1793:
            address = falcon_pk_to_address(request.pk)
            return qbit_pb2.GetAddressFromPKResp(address=address)
        else:
            # Invalid key size for Falcon-512
            return qbit_pb2.GetAddressFromPKResp(address=b'')

    @GrpcExceptionWrapper(qbit_pb2.GetPeersStatResp)
    def GetPeersStat(self, request: qbit_pb2.GetPeersStatReq, context) -> qbit_pb2.GetPeersStatResp:
        peers_stat_resp = qbit_pb2.GetPeersStatResp()
        peers_stat = self.qbitnode.get_peers_stat()

        for stat in peers_stat:
            peers_stat_resp.peers_stat.extend([stat])

        return peers_stat_resp

    @GrpcExceptionWrapper(qbit_pb2.IsSlaveResp)
    def IsSlave(self, request: qbit_pb2.IsSlaveReq, context) -> qbit_pb2.IsSlaveResp:
        return qbit_pb2.IsSlaveResp(result=self.qbitnode.is_slave(request.master_address, request.slave_pk))

    @GrpcExceptionWrapper(qbit_pb2.GetNodeStateResp)
    def GetNodeState(self, request: qbit_pb2.GetNodeStateReq, context) -> qbit_pb2.GetNodeStateResp:
        return qbit_pb2.GetNodeStateResp(info=self.qbitnode.get_node_info())

    @GrpcExceptionWrapper(qbit_pb2.GetKnownPeersResp)
    def GetKnownPeers(self, request: qbit_pb2.GetKnownPeersReq, context) -> qbit_pb2.GetKnownPeersResp:
        response = qbit_pb2.GetKnownPeersResp()
        response.node_info.CopyFrom(self.qbitnode.get_node_info())
        response.known_peers.extend([qbit_pb2.Peer(ip=p) for p in self.qbitnode.peer_manager.known_peer_addresses])

        return response

    @GrpcExceptionWrapper(qbit_pb2.GetStatsResp)
    def GetStats(self, request: qbit_pb2.GetStatsReq, context) -> qbit_pb2.GetStatsResp:
        response = qbit_pb2.GetStatsResp()
        response.node_info.CopyFrom(self.qbitnode.get_node_info())

        response.epoch = self.qbitnode.epoch
        response.uptime_network = self.qbitnode.uptime_network
        response.block_last_reward = self.qbitnode.block_last_reward
        response.coins_total_supply = int(self.qbitnode.coin_supply_max)
        response.coins_emitted = int(self.qbitnode.coin_supply)

        response.block_time_mean = 0
        response.block_time_sd = 0

        if request.include_timeseries:
            tmp = list(self.qbitnode.get_block_timeseries(config.dev.block_timeseries_size))
            response.block_timeseries.extend(tmp)
            if len(tmp) > 2:
                vals = [v.time_last for v in tmp[1:]]
                response.block_time_mean = int(mean(vals))
                response.block_time_sd = int(variance(vals) ** 0.5)
        return response

    @GrpcExceptionWrapper(qbit_pb2.GetChainStatsResp)
    def GetChainStats(self, request: qbit_pb2.GetChainStatsReq, context) -> qbit_pb2.GetChainStatsResp:
        response = qbit_pb2.GetChainStatsResp()
        for (path, dirs, files) in os.walk(config.user.data_dir + "/state"):
            for f in files:
                filename = os.path.join(path, f)
                response.state_size += os.path.getsize(filename)

        response.state_size_mb = str(response.state_size / (1024 * 1024))
        response.state_size_gb = str(response.state_size / (1024 * 1024 * 1024))
        return response

    @GrpcExceptionWrapper(qbit_pb2.ParseAddressResp)
    def ParseAddress(self, request: qbit_pb2.ParseAddressReq, context) -> qbit_pb2.ParseAddressResp:
        response = qbit_pb2.ParseAddressResp()
        
        # Use OptimizedAddressState validation for Falcon addresses only
        response.is_valid = OptimizedAddressState.address_is_valid(request.address)
        
        # Only handle Falcon addresses (25 bytes starting with 0x01)
        if len(request.address) == 25 and request.address[0:1] == b'\x01':
            # This is a Falcon address
            response.desc.hash_function = 'FALCON-512'
            response.desc.signature_scheme = 'FALCON'
            response.desc.address_format = 'FALCON'
            response.desc.tree_height = 0  # Falcon doesn't use tree structure
            response.desc.signatures = 1  # Falcon allows unlimited signatures with key management
        else:
            # Invalid address format - only Falcon addresses are supported
            response.is_valid = False
            response.desc.hash_function = 'UNKNOWN'
            response.desc.signature_scheme = 'UNKNOWN'
            response.desc.address_format = 'UNKNOWN'
        
        return response

    @GrpcExceptionWrapper(qbit_pb2.GetAddressStateResp)
    def GetAddressState(self, request: qbit_pb2.GetAddressStateReq, context) -> qbit_pb2.GetAddressStateResp:
        address_state = self.qbitnode.get_address_state(request.address,
                                                       request.exclude_ots_bitfield,
                                                       request.exclude_transaction_hashes)
        return qbit_pb2.GetAddressStateResp(state=address_state.pbdata)

    @GrpcExceptionWrapper(qbit_pb2.GetOptimizedAddressStateResp)
    def GetOptimizedAddressState(self,
                                 request: qbit_pb2.GetAddressStateReq,
                                 context) -> qbit_pb2.GetOptimizedAddressStateResp:
        address_state = self.qbitnode.get_optimized_address_state(request.address)
        return qbit_pb2.GetOptimizedAddressStateResp(state=address_state.pbdata)

    @GrpcExceptionWrapper(qbit_pb2.GetMultiSigAddressStateResp)
    def GetMultiSigAddressState(self,
                                request: qbit_pb2.GetMultiSigAddressStateReq,
                                context) -> qbit_pb2.GetMultiSigAddressStateResp:
        multi_sig_address_state = self.qbitnode.get_multi_sig_address_state(request.address)
        if multi_sig_address_state is None:
            return qbit_pb2.GetMultiSigAddressStateResp()
        return qbit_pb2.GetMultiSigAddressStateResp(state=multi_sig_address_state.pbdata)

    @GrpcExceptionWrapper(qbit_pb2.TransferCoinsResp)
    def TransferCoins(self, request: qbit_pb2.TransferCoinsReq, context) -> qbit_pb2.TransferCoinsResp:
        logger.debug("[PublicAPI] TransferCoins")
        tx = self.qbitnode.create_send_tx(addrs_to=request.addresses_to,
                                         amounts=request.amounts,
                                         message_data=request.message_data,
                                         fee=request.fee,
                                         xmss_pk=request.xmss_pk,
                                         master_addr=request.master_addr)

        extended_transaction_unsigned = qbit_pb2.TransactionExtended(tx=tx.pbdata,
                                                                    addr_from=tx.addr_from,
                                                                    size=tx.size)
        return qbit_pb2.TransferCoinsResp(extended_transaction_unsigned=extended_transaction_unsigned)

    @GrpcExceptionWrapper(qbit_pb2.PushTransactionResp)
    def PushTransaction(self, request: qbit_pb2.PushTransactionReq, context) -> qbit_pb2.PushTransactionResp:
        logger.debug("[PublicAPI] PushTransaction")
        answer = qbit_pb2.PushTransactionResp()

        try:
            tx = Transaction.from_pbdata(request.transaction_signed)
            tx.update_txhash()

            # FIXME: Full validation takes too much time. At least verify there is a signature
            # the validation happens later in the tx pool
            # For Falcon-512 signatures, the length is variable but typically around 650-700 bytes
            # Check for a reasonable minimum length instead of a fixed value
            if len(tx.signature) > 600:  # Minimum length for a valid Falcon signature
                self.qbitnode.submit_send_tx(tx)
                answer.error_code = qbit_pb2.PushTransactionResp.SUBMITTED
                answer.tx_hash = tx.txhash
            else:
                answer.error_description = 'Signature too short'
                answer.error_code = qbit_pb2.PushTransactionResp.VALIDATION_FAILED

        except Exception as e:
            error_str = traceback.format_exception(None, e, e.__traceback__)
            answer.error_description = str(''.join(error_str))
            answer.error_code = qbit_pb2.PushTransactionResp.ERROR

        return answer

    @GrpcExceptionWrapper(qbit_pb2.TransferCoinsResp)
    def GetMultiSigCreateTxn(self, request: qbit_pb2.MultiSigCreateTxnReq, context) -> qbit_pb2.TransferCoinsResp:
        logger.debug("[PublicAPI] GetMultiSigCreateTxnReq")
        tx = self.qbitnode.create_multi_sig_txn(signatories=request.signatories,
                                               weights=request.weights,
                                               threshold=request.threshold,
                                               fee=request.fee,
                                               xmss_pk=request.xmss_pk,
                                               master_addr=request.master_addr)

        extended_transaction_unsigned = qbit_pb2.TransactionExtended(tx=tx.pbdata,
                                                                    addr_from=tx.addr_from,
                                                                    size=tx.size)
        return qbit_pb2.TransferCoinsResp(extended_transaction_unsigned=extended_transaction_unsigned)

    @GrpcExceptionWrapper(qbit_pb2.TransferCoinsResp)
    def GetMultiSigSpendTxn(self, request: qbit_pb2.MultiSigSpendTxnReq, context) -> qbit_pb2.TransferCoinsResp:
        logger.debug("[PublicAPI] GetMultiSigSpendTxnReq")
        tx = self.qbitnode.create_multi_sig_spend_txn(multi_sig_address=request.multi_sig_address,
                                                     addrs_to=request.addrs_to,
                                                     amounts=request.amounts,
                                                     expiry_block_number=request.expiry_block_number,
                                                     fee=request.fee,
                                                     xmss_pk=request.xmss_pk,
                                                     master_addr=request.master_addr)

        extended_transaction_unsigned = qbit_pb2.TransactionExtended(tx=tx.pbdata,
                                                                    addr_from=tx.addr_from,
                                                                    size=tx.size)
        return qbit_pb2.TransferCoinsResp(extended_transaction_unsigned=extended_transaction_unsigned)

    @GrpcExceptionWrapper(qbit_pb2.TransferCoinsResp)
    def GetMultiSigVoteTxn(self, request: qbit_pb2.MultiSigVoteTxnReq, context) -> qbit_pb2.TransferCoinsResp:
        logger.debug("[PublicAPI] GetMultiSigSpendTxnReq")
        tx = self.qbitnode.create_multi_sig_vote_txn(shared_key=request.shared_key,
                                                    unvote=request.unvote,
                                                    fee=request.fee,
                                                    xmss_pk=request.xmss_pk,
                                                    master_addr=request.master_addr)

        extended_transaction_unsigned = qbit_pb2.TransactionExtended(tx=tx.pbdata,
                                                                    addr_from=tx.addr_from,
                                                                    size=tx.size)
        return qbit_pb2.TransferCoinsResp(extended_transaction_unsigned=extended_transaction_unsigned)

    @GrpcExceptionWrapper(qbit_pb2.TransferCoinsResp)
    def GetMessageTxn(self, request: qbit_pb2.MessageTxnReq, context) -> qbit_pb2.TransferCoinsResp:
        logger.debug("[PublicAPI] GetMessageTxn")
        tx = self.qbitnode.create_message_txn(message_hash=request.message,
                                             addr_to=request.addr_to,
                                             fee=request.fee,
                                             xmss_pk=request.xmss_pk,
                                             master_addr=request.master_addr)

        extended_transaction_unsigned = qbit_pb2.TransactionExtended(tx=tx.pbdata,
                                                                    addr_from=tx.addr_from,
                                                                    size=tx.size)
        return qbit_pb2.TransferCoinsResp(extended_transaction_unsigned=extended_transaction_unsigned)

    @GrpcExceptionWrapper(qbit_pb2.TransferCoinsResp)
    def GetTokenTxn(self, request: qbit_pb2.TokenTxnReq, context) -> qbit_pb2.TransferCoinsResp:
        logger.debug("[PublicAPI] GetTokenTxn")
        tx = self.qbitnode.create_token_txn(symbol=request.symbol,
                                           name=request.name,
                                           owner=request.owner,
                                           decimals=request.decimals,
                                           initial_balances=request.initial_balances,
                                           fee=request.fee,
                                           xmss_pk=request.xmss_pk,
                                           master_addr=request.master_addr)

        extended_transaction_unsigned = qbit_pb2.TransactionExtended(tx=tx.pbdata,
                                                                    addr_from=tx.addr_from,
                                                                    size=tx.size)
        return qbit_pb2.TransferCoinsResp(extended_transaction_unsigned=extended_transaction_unsigned)

    @GrpcExceptionWrapper(qbit_pb2.TransferCoinsResp)
    def GetTransferTokenTxn(self, request: qbit_pb2.TransferTokenTxnReq, context) -> qbit_pb2.TransferCoinsResp:
        logger.debug("[PublicAPI] GetTransferTokenTxn")
        bin_token_txhash = bytes(hstr2bin(request.token_txhash.decode()))
        tx = self.qbitnode.create_transfer_token_txn(addrs_to=request.addresses_to,
                                                    token_txhash=bin_token_txhash,
                                                    amounts=request.amounts,
                                                    fee=request.fee,
                                                    xmss_pk=request.xmss_pk,
                                                    master_addr=request.master_addr)

        extended_transaction_unsigned = qbit_pb2.TransactionExtended(tx=tx.pbdata,
                                                                    addr_from=tx.addr_from,
                                                                    size=tx.size)
        return qbit_pb2.TransferCoinsResp(extended_transaction_unsigned=extended_transaction_unsigned)

    @GrpcExceptionWrapper(qbit_pb2.TransferCoinsResp)
    def GetSlaveTxn(self, request: qbit_pb2.SlaveTxnReq, context) -> qbit_pb2.TransferCoinsResp:
        logger.debug("[PublicAPI] GetSlaveTxn")
        tx = self.qbitnode.create_slave_tx(slave_pks=request.slave_pks,
                                          access_types=request.access_types,
                                          fee=request.fee,
                                          xmss_pk=request.xmss_pk,
                                          master_addr=request.master_addr)

        extended_transaction_unsigned = qbit_pb2.TransactionExtended(tx=tx.pbdata,
                                                                    addr_from=tx.addr_from,
                                                                    size=tx.size)
        return qbit_pb2.TransferCoinsResp(extended_transaction_unsigned=extended_transaction_unsigned)

    @GrpcExceptionWrapper(qbit_pb2.TransferCoinsResp)
    def GetLatticeTxn(self, request: qbit_pb2.LatticeTxnReq, context) -> qbit_pb2.TransferCoinsResp:
        logger.debug("[PublicAPI] GetLatticeTxn")
        tx = self.qbitnode.create_lattice_tx(pk1=request.pk1,
                                            pk2=request.pk2,
                                            pk3=request.pk3,
                                            fee=request.fee,
                                            xmss_pk=request.xmss_pk,
                                            master_addr=request.master_addr)

        extended_transaction_unsigned = qbit_pb2.TransactionExtended(tx=tx.pbdata,
                                                                    addr_from=tx.addr_from,
                                                                    size=tx.size)
        return qbit_pb2.TransferCoinsResp(extended_transaction_unsigned=extended_transaction_unsigned)

    @GrpcExceptionWrapper(qbit_pb2.GetObjectResp)
    def GetObject(self, request: qbit_pb2.GetObjectReq, context) -> qbit_pb2.GetObjectResp:
        logger.debug("[PublicAPI] GetObject")
        answer = qbit_pb2.GetObjectResp()
        answer.found = False

        # FIXME: We need a unified way to access and validate data.
        query = bytes(request.query)  # query will be as a string, if Q is detected convert, etc.

        try:
            if AddressState.address_is_valid(query):
                if self.qbitnode.get_address_is_used(query):
                    address_state = self.qbitnode.get_optimized_address_state(query)
                    if address_state is not None:
                        answer.found = True
                        answer.address_state.CopyFrom(address_state.pbdata)
                        return answer
        except ValueError:
            pass

        transaction_block_number = self.qbitnode.get_transaction(query)
        transaction = None
        blockheader = None
        if transaction_block_number:
            transaction, block_number = transaction_block_number
            answer.found = True
            block = self.qbitnode.get_block_from_index(block_number)
            blockheader = block.blockheader.pbdata
            timestamp = block.blockheader.timestamp
        else:
            transaction_timestamp = self.qbitnode.get_unconfirmed_transaction(query)
            if transaction_timestamp:
                transaction, timestamp = transaction_timestamp
                answer.found = True

        if transaction:
            txextended = qbit_pb2.TransactionExtended(header=blockheader,
                                                     tx=transaction.pbdata,
                                                     addr_from=transaction.addr_from,
                                                     size=transaction.size,
                                                     timestamp_seconds=timestamp)
            answer.transaction.CopyFrom(txextended)
            return answer

        # NOTE: This is temporary, indexes are accepted for blocks
        try:
            block = self.qbitnode.get_block_from_hash(query)
            if block is None or (block.block_number == 0 and block.prev_headerhash != config.user.genesis_prev_headerhash):
                query_str = query.decode()
                query_index = int(query_str)
                block = self.qbitnode.get_block_from_index(query_index)
                if not block:
                    return answer

            answer.found = True
            block_extended = qbit_pb2.BlockExtended()
            block_extended.header.CopyFrom(block.blockheader.pbdata)
            block_extended.size = block.size
            for transaction in block.transactions:
                tx = Transaction.from_pbdata(transaction)
                extended_tx = qbit_pb2.TransactionExtended(tx=transaction,
                                                          addr_from=tx.addr_from,
                                                          size=tx.size,
                                                          timestamp_seconds=block.blockheader.timestamp)
                block_extended.extended_transactions.extend([extended_tx])
            answer.block_extended.CopyFrom(block_extended)
            return answer
        except Exception:
            pass

        return answer

    @GrpcExceptionWrapper(qbit_pb2.GetLatestDataResp)
    def GetLatestData(self, request: qbit_pb2.GetLatestDataReq, context) -> qbit_pb2.GetLatestDataResp:
        logger.debug("[PublicAPI] GetLatestData")
        response = qbit_pb2.GetLatestDataResp()

        all_requested = request.filter == qbit_pb2.GetLatestDataReq.ALL
        quantity = min(request.quantity, self.MAX_REQUEST_QUANTITY)

        if all_requested or request.filter == qbit_pb2.GetLatestDataReq.BLOCKHEADERS:
            result = []
            for blk in self.qbitnode.get_latest_blocks(offset=request.offset, count=quantity):
                transaction_count = qbit_pb2.TransactionCount()
                for tx in blk.transactions:
                    transaction_count.count[CODEMAP[tx.WhichOneof('transactionType')]] += 1

                result.append(qbit_pb2.BlockHeaderExtended(header=blk.blockheader.pbdata,
                                                          transaction_count=transaction_count))
            response.blockheaders.extend(result)

        if all_requested or request.filter == qbit_pb2.GetLatestDataReq.TRANSACTIONS:
            result = []
            for tx in self.qbitnode.get_latest_transactions(offset=request.offset, count=quantity):
                # FIXME: Improve this once we have a proper database schema
                block_index = self.qbitnode.get_blockidx_from_txhash(tx.txhash)
                block = self.qbitnode.get_block_from_index(block_index)
                header = None
                if block:
                    header = block.blockheader.pbdata
                txextended = qbit_pb2.TransactionExtended(header=header,
                                                         tx=tx.pbdata,
                                                         addr_from=tx.addr_from,
                                                         size=tx.size)
                result.append(txextended)

            response.transactions.extend(result)

        if all_requested or request.filter == qbit_pb2.GetLatestDataReq.TRANSACTIONS_UNCONFIRMED:
            result = []
            for tx_info in self.qbitnode.get_latest_transactions_unconfirmed(offset=request.offset, count=quantity):
                tx = tx_info.transaction
                txextended = qbit_pb2.TransactionExtended(header=None,
                                                         tx=tx.pbdata,
                                                         addr_from=tx.addr_from,
                                                         size=tx.size,
                                                         timestamp_seconds=tx_info.timestamp)
                result.append(txextended)
            response.transactions_unconfirmed.extend(result)

        return response

    # Obsolete
    # @GrpcExceptionWrapper(qbit_pb2.GetTransactionsByAddressResp)
    # def GetTransactionsByAddress(self,
    #                              request: qbit_pb2.GetTransactionsByAddressReq,
    #                              context) -> qbit_pb2.GetTransactionsByAddressResp:
    #     logger.debug("[PublicAPI] GetTransactionsByAddress")
    #     response = qbit_pb2.GetTransactionsByAddressResp()
    #     mini_transactions, balance = self.qbitnode.get_transactions_by_address(request.address)
    #     response.mini_transactions.extend(mini_transactions)
    #     response.balance = balance
    #     return response

    @GrpcExceptionWrapper(qbit_pb2.GetMiniTransactionsByAddressResp)
    def GetMiniTransactionsByAddress(self,
                                     request: qbit_pb2.GetMiniTransactionsByAddressReq,
                                     context) -> qbit_pb2.GetMiniTransactionsByAddressResp:
        logger.debug("[PublicAPI] GetTransactionsByAddress")
        return self.qbitnode.get_mini_transactions_by_address(request.address,
                                                             request.item_per_page,
                                                             request.page_number)

    @GrpcExceptionWrapper(qbit_pb2.GetTransactionsByAddressResp)
    def GetTransactionsByAddress(self,
                                 request: qbit_pb2.GetTransactionsByAddressReq,
                                 context) -> qbit_pb2.GetTransactionsByAddressResp:
        logger.debug("[PublicAPI] GetTransactionsByAddress")
        return self.qbitnode.get_transactions_by_address(request.address,
                                                        request.item_per_page,
                                                        request.page_number)

    @GrpcExceptionWrapper(qbit_pb2.GetTokensByAddressResp)
    def GetTokensByAddress(self,
                           request: qbit_pb2.GetTransactionsByAddressReq,
                           context) -> qbit_pb2.GetTokensByAddressResp:
        logger.debug("[PublicAPI] GetTokensByAddress")
        return self.qbitnode.get_tokens_by_address(request.address,
                                                  request.item_per_page,
                                                  request.page_number)

    @GrpcExceptionWrapper(qbit_pb2.GetSlavesByAddressResp)
    def GetSlavesByAddress(self,
                           request: qbit_pb2.GetTransactionsByAddressReq,
                           context) -> qbit_pb2.GetSlavesByAddressResp:
        logger.debug("[PublicAPI] GetSlavesByAddress")
        return self.qbitnode.get_slaves_by_address(request.address,
                                                  request.item_per_page,
                                                  request.page_number)

    @GrpcExceptionWrapper(qbit_pb2.GetLatticePKsByAddressResp)
    def GetLatticePKsByAddress(self,
                               request: qbit_pb2.GetTransactionsByAddressReq,
                               context) -> qbit_pb2.GetLatticePKsByAddressResp:
        logger.debug("[PublicAPI] GetLatticePKsByAddress")
        return self.qbitnode.get_lattice_pks_by_address(request.address,
                                                       request.item_per_page,
                                                       request.page_number)

    @GrpcExceptionWrapper(qbit_pb2.GetMultiSigAddressesByAddressResp)
    def GetMultiSigAddressesByAddress(self,
                                      request: qbit_pb2.GetTransactionsByAddressReq,
                                      context) -> qbit_pb2.GetMultiSigAddressesByAddressResp:
        logger.debug("[PublicAPI] GetMultiSigAddressesByAddress")
        return self.qbitnode.get_multi_sig_addresses_by_address(request.address,
                                                               request.item_per_page,
                                                               request.page_number)

    @GrpcExceptionWrapper(qbit_pb2.GetMultiSigSpendTxsByAddressResp)
    def GetMultiSigSpendTxsByAddress(self,
                                     request: qbit_pb2.GetMultiSigSpendTxsByAddressReq,
                                     context) -> qbit_pb2.GetMultiSigSpendTxsByAddressResp:
        logger.debug("[PublicAPI] GetMultiSigSpendTxsByAddress")
        return self.qbitnode.get_multi_sig_spend_txs_by_address(request.address,
                                                               request.item_per_page,
                                                               request.page_number,
                                                               request.filter_type)

    @GrpcExceptionWrapper(qbit_pb2.GetInboxMessagesByAddressResp)
    def GetInboxMessagesByAddress(self,
                                  request: qbit_pb2.GetTransactionsByAddressReq,
                                  context) -> qbit_pb2.GetInboxMessagesByAddressResp:
        logger.debug("[PublicAPI] GetInboxMessagesByAddress")
        return self.qbitnode.get_inbox_messages_by_address(request.address,
                                                          request.item_per_page,
                                                          request.page_number)

    @GrpcExceptionWrapper(qbit_pb2.GetVoteStatsResp)
    def GetVoteStats(self,
                     request: qbit_pb2.GetVoteStatsReq,
                     context) -> qbit_pb2.GetVoteStatsResp:
        logger.debug("[PublicAPI] GetVoteStats")
        return self.qbitnode.get_vote_stats(request.multi_sig_spend_tx_hash)

    @GrpcExceptionWrapper(qbit_pb2.GetTransactionResp)
    def GetTransaction(self, request: qbit_pb2.GetTransactionReq, context) -> qbit_pb2.GetTransactionResp:
        logger.debug("[PublicAPI] GetTransaction")
        response = qbit_pb2.GetTransactionResp()
        tx_blocknumber = self.qbitnode.get_transaction(request.tx_hash)
        if tx_blocknumber:
            response.tx.MergeFrom(tx_blocknumber[0].pbdata)
            response.confirmations = self.qbitnode.block_height - tx_blocknumber[1] + 1
            response.block_number = tx_blocknumber[1]
            response.block_header_hash = self.qbitnode.get_block_header_hash_by_number(tx_blocknumber[1])
        else:
            tx_timestamp = self.qbitnode.get_unconfirmed_transaction(request.tx_hash)
            if tx_timestamp:
                response.tx.MergeFrom(tx_timestamp[0].pbdata)
                response.confirmations = 0

        return response

    @GrpcExceptionWrapper(qbit_pb2.GetBalanceResp)
    def GetBalance(self, request: qbit_pb2.GetBalanceReq, context) -> qbit_pb2.GetBalanceResp:
        logger.debug("[PublicAPI] GetBalance")
        address_state = self.qbitnode.get_optimized_address_state(request.address)
        response = qbit_pb2.GetBalanceResp(balance=address_state.balance)
        return response

    @GrpcExceptionWrapper(qbit_pb2.GetTotalBalanceResp)
    def GetTotalBalance(self, request: qbit_pb2.GetTotalBalanceReq, context) -> qbit_pb2.GetTotalBalanceResp:
        logger.debug("[PublicAPI] GetTotalBalance")
        response = qbit_pb2.GetBalanceResp(balance=0)

        for address in request.addresses:
            address_state = self.qbitnode.get_optimized_address_state(address)
            response.balance += address_state.balance

        return response

     
    @GrpcExceptionWrapper(qbit_pb2.GetHeightResp)
    def GetHeight(self, request: qbit_pb2.GetHeightReq, context) -> qbit_pb2.GetHeightResp:
        logger.debug("[PublicAPI] GetHeight")
        return qbit_pb2.GetHeightResp(height=self.qbitnode.block_height)

    @GrpcExceptionWrapper(qbit_pb2.GetBlockResp)
    def GetBlock(self, request: qbit_pb2.GetBlockReq, context) -> qbit_pb2.GetBlockResp:
        logger.debug("[PublicAPI] GetBlock")
        block = self.qbitnode.get_block_from_hash(request.header_hash)
        if block:
            return qbit_pb2.GetBlockResp(block=block.pbdata)
        return qbit_pb2.GetBlockResp()

    @GrpcExceptionWrapper(qbit_pb2.GetBlockByNumberResp)
    def GetBlockByNumber(self, request: qbit_pb2.GetBlockByNumberReq, context) -> qbit_pb2.GetBlockByNumberResp:
        logger.debug("[PublicAPI] GetBlockFromNumber")
        block = self.qbitnode.get_block_from_index(request.block_number)
        if block:
            return qbit_pb2.GetBlockByNumberResp(block=block.pbdata)
        return qbit_pb2.GetBlockByNumberResp()
