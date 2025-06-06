# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
from qbitcoin.core import config
from qbitcoin.core.qbitnode import QbitcoinNode
from qbitcoin.generated import qbitdebug_pb2
from qbitcoin.generated.qbitdebug_pb2_grpc import DebugAPIServicer
from qbitcoin.services.grpcHelper import GrpcExceptionWrapper


class DebugAPIService(DebugAPIServicer):
    MAX_REQUEST_QUANTITY = 100

    def __init__(self, qbitnode: QbitcoinNode):
        self.qbitnode = qbitnode

    @GrpcExceptionWrapper(qbitdebug_pb2.GetFullStateResp)
    def GetFullState(self, request: qbitdebug_pb2.GetFullStateReq, context) -> qbitdebug_pb2.GetFullStateResp:
        return qbitdebug_pb2.GetFullStateResp(
            coinbase_state=self.qrlnode.get_address_state(config.dev.coinbase_address).pbdata,
            addresses_state=self.qrlnode.get_all_address_state()
        )
