# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import server_pb2 as server__pb2


class RaftServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.RequestVote = channel.unary_unary(
                '/RaftService/RequestVote',
                request_serializer=server__pb2.RequestVoteMessage.SerializeToString,
                response_deserializer=server__pb2.RequestVoteResponse.FromString,
                )
        self.AppendEntries = channel.unary_unary(
                '/RaftService/AppendEntries',
                request_serializer=server__pb2.AppendEntriesMessage.SerializeToString,
                response_deserializer=server__pb2.AppendEntriesResponse.FromString,
                )
        self.GetLeader = channel.unary_unary(
                '/RaftService/GetLeader',
                request_serializer=server__pb2.GetLeaderMessage.SerializeToString,
                response_deserializer=server__pb2.GetLeaderResponse.FromString,
                )
        self.Suspend = channel.unary_unary(
                '/RaftService/Suspend',
                request_serializer=server__pb2.SuspendMessage.SerializeToString,
                response_deserializer=server__pb2.SuspendResponse.FromString,
                )
        self.GetVal = channel.unary_unary(
                '/RaftService/GetVal',
                request_serializer=server__pb2.GetValMessage.SerializeToString,
                response_deserializer=server__pb2.GetValResponse.FromString,
                )
        self.SetVal = channel.unary_unary(
                '/RaftService/SetVal',
                request_serializer=server__pb2.SetValMessage.SerializeToString,
                response_deserializer=server__pb2.SetValResponse.FromString,
                )
        self.RenewLeaderLease = channel.unary_unary(
                '/RaftService/RenewLeaderLease',
                request_serializer=server__pb2.RenewLeaderLeaseRequest.SerializeToString,
                response_deserializer=server__pb2.RenewLeaderLeaseResponse.FromString,
                )


class RaftServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def RequestVote(self, request, context):
        """Functions called by the servers.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def AppendEntries(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetLeader(self, request, context):
        """Functions called by the client.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Suspend(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetVal(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SetVal(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def RenewLeaderLease(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_RaftServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'RequestVote': grpc.unary_unary_rpc_method_handler(
                    servicer.RequestVote,
                    request_deserializer=server__pb2.RequestVoteMessage.FromString,
                    response_serializer=server__pb2.RequestVoteResponse.SerializeToString,
            ),
            'AppendEntries': grpc.unary_unary_rpc_method_handler(
                    servicer.AppendEntries,
                    request_deserializer=server__pb2.AppendEntriesMessage.FromString,
                    response_serializer=server__pb2.AppendEntriesResponse.SerializeToString,
            ),
            'GetLeader': grpc.unary_unary_rpc_method_handler(
                    servicer.GetLeader,
                    request_deserializer=server__pb2.GetLeaderMessage.FromString,
                    response_serializer=server__pb2.GetLeaderResponse.SerializeToString,
            ),
            'Suspend': grpc.unary_unary_rpc_method_handler(
                    servicer.Suspend,
                    request_deserializer=server__pb2.SuspendMessage.FromString,
                    response_serializer=server__pb2.SuspendResponse.SerializeToString,
            ),
            'GetVal': grpc.unary_unary_rpc_method_handler(
                    servicer.GetVal,
                    request_deserializer=server__pb2.GetValMessage.FromString,
                    response_serializer=server__pb2.GetValResponse.SerializeToString,
            ),
            'SetVal': grpc.unary_unary_rpc_method_handler(
                    servicer.SetVal,
                    request_deserializer=server__pb2.SetValMessage.FromString,
                    response_serializer=server__pb2.SetValResponse.SerializeToString,
            ),
            'RenewLeaderLease': grpc.unary_unary_rpc_method_handler(
                    servicer.RenewLeaderLease,
                    request_deserializer=server__pb2.RenewLeaderLeaseRequest.FromString,
                    response_serializer=server__pb2.RenewLeaderLeaseResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'RaftService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class RaftService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def RequestVote(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/RaftService/RequestVote',
            server__pb2.RequestVoteMessage.SerializeToString,
            server__pb2.RequestVoteResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def AppendEntries(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/RaftService/AppendEntries',
            server__pb2.AppendEntriesMessage.SerializeToString,
            server__pb2.AppendEntriesResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def GetLeader(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/RaftService/GetLeader',
            server__pb2.GetLeaderMessage.SerializeToString,
            server__pb2.GetLeaderResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def Suspend(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/RaftService/Suspend',
            server__pb2.SuspendMessage.SerializeToString,
            server__pb2.SuspendResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def GetVal(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/RaftService/GetVal',
            server__pb2.GetValMessage.SerializeToString,
            server__pb2.GetValResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def SetVal(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/RaftService/SetVal',
            server__pb2.SetValMessage.SerializeToString,
            server__pb2.SetValResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def RenewLeaderLease(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/RaftService/RenewLeaderLease',
            server__pb2.RenewLeaderLeaseRequest.SerializeToString,
            server__pb2.RenewLeaderLeaseResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
