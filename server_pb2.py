# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: server.proto
# Protobuf Python Version: 4.25.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0cserver.proto\x12\x06server\"\x1f\n\x0cValueRequest\x12\x0f\n\x07payload\x18\x01 \x01(\t\".\n\rValueResponse\x12\x0c\n\x04\x63ode\x18\x01 \x01(\t\x12\x0f\n\x07payload\x18\x02 \x01(\t\"E\n\x12VoteRequestMessage\x12\x0c\n\x04term\x18\x01 \x01(\x05\x12\x11\n\tcommitIdx\x18\x02 \x01(\x05\x12\x0e\n\x06staged\x18\x03 \x01(\x08\"3\n\x13VoteResponseMessage\x12\x0e\n\x06\x63hoice\x18\x01 \x01(\x08\x12\x0c\n\x04term\x18\x02 \x01(\x05\"3\n\x10HeartbeatRequest\x12\x0c\n\x04term\x18\x01 \x01(\x05\x12\x11\n\tcommitIdx\x18\x02 \x01(\x05\"4\n\x11HeartbeatResponse\x12\x0c\n\x04term\x18\x01 \x01(\x05\x12\x11\n\tcommitIdx\x18\x02 \x01(\x05\x32\x8b\x02\n\rKeyValueStore\x12\x37\n\x08GetValue\x12\x14.server.ValueRequest\x1a\x15.server.ValueResponse\x12\x37\n\x08PutValue\x12\x14.server.ValueRequest\x1a\x15.server.ValueResponse\x12\x46\n\x0bVoteRequest\x12\x1a.server.VoteRequestMessage\x1a\x1b.server.VoteResponseMessage\x12@\n\tHeartbeat\x12\x18.server.HeartbeatRequest\x1a\x19.server.HeartbeatResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'server_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_VALUEREQUEST']._serialized_start=24
  _globals['_VALUEREQUEST']._serialized_end=55
  _globals['_VALUERESPONSE']._serialized_start=57
  _globals['_VALUERESPONSE']._serialized_end=103
  _globals['_VOTEREQUESTMESSAGE']._serialized_start=105
  _globals['_VOTEREQUESTMESSAGE']._serialized_end=174
  _globals['_VOTERESPONSEMESSAGE']._serialized_start=176
  _globals['_VOTERESPONSEMESSAGE']._serialized_end=227
  _globals['_HEARTBEATREQUEST']._serialized_start=229
  _globals['_HEARTBEATREQUEST']._serialized_end=280
  _globals['_HEARTBEATRESPONSE']._serialized_start=282
  _globals['_HEARTBEATRESPONSE']._serialized_end=334
  _globals['_KEYVALUESTORE']._serialized_start=337
  _globals['_KEYVALUESTORE']._serialized_end=604
# @@protoc_insertion_point(module_scope)
