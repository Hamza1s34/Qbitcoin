# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: qbitdebug.proto
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
    'qbitdebug.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


import qbitcoin.generated.qbit_pb2 as qbit__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0fqbitdebug.proto\x12\x03qrl\x1a\nqbit.proto\"\x11\n\x0fGetFullStateReq\"i\n\x10GetFullStateResp\x12)\n\x0e\x63oinbase_state\x18\x01 \x01(\x0b\x32\x11.qrl.AddressState\x12*\n\x0f\x61\x64\x64resses_state\x18\x02 \x03(\x0b\x32\x11.qrl.AddressState2G\n\x08\x44\x65\x62ugAPI\x12;\n\x0cGetFullState\x12\x14.qrl.GetFullStateReq\x1a\x15.qrl.GetFullStateRespb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'qbitdebug_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_GETFULLSTATEREQ']._serialized_start=36
  _globals['_GETFULLSTATEREQ']._serialized_end=53
  _globals['_GETFULLSTATERESP']._serialized_start=55
  _globals['_GETFULLSTATERESP']._serialized_end=160
  _globals['_DEBUGAPI']._serialized_start=162
  _globals['_DEBUGAPI']._serialized_end=233
# @@protoc_insertion_point(module_scope)
