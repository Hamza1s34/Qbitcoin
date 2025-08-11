# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

# FIXME: This is odd...
import sys

import os
from grpc._cython.cygrpc import StatusCode

from qbitcoin.core.qbitnode import QbitcoinNode
from qbitcoin.generated.qbitbase_pb2 import GetNodeInfoReq, GetNodeInfoResp
from qbitcoin.generated.qbitbase_pb2_grpc import BaseServicer


class BaseService(BaseServicer):
    def __init__(self, qrlnode: QbitcoinNode):
        self.qbitnode = qrlnode

    def GetNodeInfo(self, request: GetNodeInfoReq, context) -> GetNodeInfoResp:
        try:
            resp = GetNodeInfoResp()
            if self.qbitnode:
                resp.version = self.qbitnode.version

                pkgdir = os.path.dirname(sys.modules['qbitcoin'].__file__)
                grpcprotopath = os.path.join(pkgdir, "protos", "qbit.proto")
                with open(grpcprotopath, 'r') as infile:
                    resp.grpcProto = infile.read()

            return resp
        except Exception as e:
            context.set_code(StatusCode.UNKNOWN)
            context.set_details(str(e))
            return GetNodeInfoResp()
