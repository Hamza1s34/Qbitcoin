# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: qbitlegacy.proto
# Protobuf Python Version: 5.29.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    29,
    0,
    '',
    'qbitlegacy.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


import qbitcoin.generated.qbit_pb2 as qbit__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x10qbitlegacy.proto\x12\x03qrl\x1a\nqbit.proto\"\xf2\x08\n\rLegacyMessage\x12.\n\tfunc_name\x18\x01 \x01(\x0e\x32\x1b.qrl.LegacyMessage.FuncName\x12\x1d\n\x06noData\x18\x02 \x01(\x0b\x32\x0b.qrl.NoDataH\x00\x12\x1d\n\x06veData\x18\x03 \x01(\x0b\x32\x0b.qrl.VEDataH\x00\x12\x1d\n\x06plData\x18\x04 \x01(\x0b\x32\x0b.qrl.PLDataH\x00\x12!\n\x08pongData\x18\x05 \x01(\x0b\x32\r.qrl.PONGDataH\x00\x12\x1d\n\x06mrData\x18\x06 \x01(\x0b\x32\x0b.qrl.MRDataH\x00\x12\x1b\n\x05\x62lock\x18\x07 \x01(\x0b\x32\n.qrl.BlockH\x00\x12\x1d\n\x06\x66\x62\x44\x61ta\x18\x08 \x01(\x0b\x32\x0b.qrl.FBDataH\x00\x12\x1d\n\x06pbData\x18\t \x01(\x0b\x32\x0b.qrl.PBDataH\x00\x12&\n\x06\x62hData\x18\n \x01(\x0b\x32\x14.qrl.BlockHeightDataH\x00\x12\"\n\x06txData\x18\x0b \x01(\x0b\x32\x10.qrl.TransactionH\x00\x12\"\n\x06mtData\x18\x0c \x01(\x0b\x32\x10.qrl.TransactionH\x00\x12\"\n\x06tkData\x18\r \x01(\x0b\x32\x10.qrl.TransactionH\x00\x12\"\n\x06ttData\x18\x0e \x01(\x0b\x32\x10.qrl.TransactionH\x00\x12\"\n\x06ltData\x18\x0f \x01(\x0b\x32\x10.qrl.TransactionH\x00\x12\"\n\x06slData\x18\x10 \x01(\x0b\x32\x10.qrl.TransactionH\x00\x12\x31\n\x07\x65phData\x18\x11 \x01(\x0b\x32\x1e.qrl.EncryptedEphemeralMessageH\x00\x12!\n\x08syncData\x18\x12 \x01(\x0b\x32\r.qrl.SYNCDataH\x00\x12-\n\x0e\x63hainStateData\x18\x13 \x01(\x0b\x32\x13.qrl.NodeChainStateH\x00\x12-\n\x0enodeHeaderHash\x18\x14 \x01(\x0b\x32\x13.qrl.NodeHeaderHashH\x00\x12-\n\np2pAckData\x18\x15 \x01(\x0b\x32\x17.qrl.P2PAcknowledgementH\x00\x12\"\n\x06mcData\x18\x16 \x01(\x0b\x32\x10.qrl.TransactionH\x00\x12\"\n\x06msData\x18\x17 \x01(\x0b\x32\x10.qrl.TransactionH\x00\x12\"\n\x06mvData\x18\x18 \x01(\x0b\x32\x10.qrl.TransactionH\x00\"\xdf\x01\n\x08\x46uncName\x12\x06\n\x02VE\x10\x00\x12\x06\n\x02PL\x10\x01\x12\x08\n\x04PONG\x10\x02\x12\x06\n\x02MR\x10\x03\x12\x07\n\x03SFM\x10\x04\x12\x06\n\x02\x42K\x10\x05\x12\x06\n\x02\x46\x42\x10\x06\x12\x06\n\x02PB\x10\x07\x12\x06\n\x02\x42H\x10\x08\x12\x06\n\x02TX\x10\t\x12\x06\n\x02LT\x10\n\x12\x07\n\x03\x45PH\x10\x0b\x12\x06\n\x02MT\x10\x0c\x12\x06\n\x02TK\x10\r\x12\x06\n\x02TT\x10\x0e\x12\x06\n\x02SL\x10\x0f\x12\x08\n\x04SYNC\x10\x10\x12\x0e\n\nCHAINSTATE\x10\x11\x12\x10\n\x0cHEADERHASHES\x10\x12\x12\x0b\n\x07P2P_ACK\x10\x13\x12\x06\n\x02MC\x10\x14\x12\x06\n\x02MS\x10\x15\x12\x06\n\x02MV\x10\x16\x42\x06\n\x04\x64\x61ta\"\x08\n\x06NoData\"H\n\x06VEData\x12\x0f\n\x07version\x18\x01 \x01(\t\x12\x19\n\x11genesis_prev_hash\x18\x02 \x01(\x0c\x12\x12\n\nrate_limit\x18\x03 \x01(\x04\"/\n\x06PLData\x12\x10\n\x08peer_ips\x18\x01 \x03(\t\x12\x13\n\x0bpublic_port\x18\x02 \x01(\r\"\n\n\x08PONGData\"\x9d\x01\n\x06MRData\x12\x0c\n\x04hash\x18\x01 \x01(\x0c\x12)\n\x04type\x18\x02 \x01(\x0e\x32\x1b.qrl.LegacyMessage.FuncName\x12\x16\n\x0estake_selector\x18\x03 \x01(\x0c\x12\x14\n\x0c\x62lock_number\x18\x04 \x01(\x04\x12\x17\n\x0fprev_headerhash\x18\x05 \x01(\x0c\x12\x13\n\x0breveal_hash\x18\x06 \x01(\x0c\"@\n\x06\x42KData\x12\x1b\n\x06mrData\x18\x01 \x01(\x0b\x32\x0b.qrl.MRData\x12\x19\n\x05\x62lock\x18\x02 \x01(\x0b\x32\n.qrl.Block\"\x17\n\x06\x46\x42\x44\x61ta\x12\r\n\x05index\x18\x01 \x01(\x04\"#\n\x06PBData\x12\x19\n\x05\x62lock\x18\x01 \x01(\x0b\x32\n.qrl.Block\"\x19\n\x08SYNCData\x12\r\n\x05state\x18\x01 \x01(\tb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'qbitlegacy_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_LEGACYMESSAGE']._serialized_start=38
  _globals['_LEGACYMESSAGE']._serialized_end=1176
  _globals['_LEGACYMESSAGE_FUNCNAME']._serialized_start=945
  _globals['_LEGACYMESSAGE_FUNCNAME']._serialized_end=1168
  _globals['_NODATA']._serialized_start=1178
  _globals['_NODATA']._serialized_end=1186
  _globals['_VEDATA']._serialized_start=1188
  _globals['_VEDATA']._serialized_end=1260
  _globals['_PLDATA']._serialized_start=1262
  _globals['_PLDATA']._serialized_end=1309
  _globals['_PONGDATA']._serialized_start=1311
  _globals['_PONGDATA']._serialized_end=1321
  _globals['_MRDATA']._serialized_start=1324
  _globals['_MRDATA']._serialized_end=1481
  _globals['_BKDATA']._serialized_start=1483
  _globals['_BKDATA']._serialized_end=1547
  _globals['_FBDATA']._serialized_start=1549
  _globals['_FBDATA']._serialized_end=1572
  _globals['_PBDATA']._serialized_start=1574
  _globals['_PBDATA']._serialized_end=1609
  _globals['_SYNCDATA']._serialized_start=1611
  _globals['_SYNCDATA']._serialized_end=1636
# @@protoc_insertion_point(module_scope)
