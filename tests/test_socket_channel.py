# -*- coding: utf-8 -*-
"""test cases for ioloop
"""
import socket
import threading
import unittest

from qt4s.channel.sock import SocketChannel, SocketGetResponseTimeoutError, \
    SocketConnectionTimeoutError, RequestBase, ResponseBase
from qt4s.message.definition import Field, Buffer
from qt4s.message.serializers.binary import BinarySerializer
from tests.simple_servers import TcpEchoServer, UdpEchoServer


class FooResponse(ResponseBase):
    _struct_ = [
        Field("buffer", Buffer)
    ]
    _serializer_ = BinarySerializer()

    def get_sequence_id(self):
        return None


class FooRequest(RequestBase):
    _struct_ = [
        Field("buffer", Buffer)
    ]
    _serializer_ = BinarySerializer()
    response_class = FooResponse

    def get_sequence_id(self):
        return None


class FooChannel(SocketChannel):
    request_class = FooRequest


class SocketChannelTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tcp_server = TcpEchoServer()
        threading.Thread(name="tcp_server", target=cls.tcp_server.serve_forever, args=(0.1,)).start()
        cls.udp_server = UdpEchoServer()
        threading.Thread(name="udp_server", target=cls.udp_server.serve_forever, args=(0.1,)).start()
        cls.tcp_host , cls.tcp_port = cls.tcp_server.server_address
        cls.udp_host , cls.udp_port = cls.udp_server.server_address

    @classmethod
    def tearDownClass(cls):
        cls.tcp_server.shutdown()
        cls.udp_server.shutdown()

    def test_tcp_channel_send(self):
        chan = FooChannel(host=self.tcp_host, port=self.tcp_port)
        self.addCleanup(chan.close)
        data = "xxxx"
        req = FooRequest(timeout=1)
        req.buffer = data
        rsp = chan.send(req)
        self.assertEqual(type(rsp), FooResponse)
        self.assertEqual(data, rsp.buffer)
        self.assertEqual(rsp.request, req)

        rsp = chan.request(data)
        self.assertEqual(type(rsp), FooResponse)
        self.assertEqual(data, rsp.buffer)
        self.assertEqual(rsp.request, req)

    def test_tcp_channel_request(self):
        data = "xxxx"
        req = FooRequest(data, timeout=1)
        chan = FooChannel(host=self.tcp_host, port=self.tcp_port)
        self.addCleanup(chan.close)
        req.pre_process(chan)
        rsp = chan.get_response(req)
        rsp.post_process(chan)
        rsp.set_request(req)
        self.assertEqual(type(rsp), FooResponse)
        self.assertEqual(data, rsp.buffer)
        self.assertEqual(rsp.request, req)

    def test_tcp_on_push(self):

        class _PushRequest(FooRequest):

            def get_sequence_id(self):
                return 1

        chan = FooChannel(host=self.tcp_host, port=self.tcp_port)
        self.addCleanup(chan.close)
        self.assertRaises(SocketGetResponseTimeoutError, chan.send, _PushRequest("xxxx", timeout=1))

    def test_tcp_connect_timeout(self):
        host, port = ("255.255.255.254", 80)
        chan = FooChannel(host=host, port=port, connect_timeout=0.5)
        self.addCleanup(chan.close)
        self.assertRaises(SocketConnectionTimeoutError, chan.send, FooRequest("xxxx"))

    def test_tcp_response_timeout(self):

        def listening_thread(sock):
            s = sock.accept()[0]
            while True:
                buf = s.recv(8192)
                if buf == "":
                    break

        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        sock.listen(1)
        threading.Thread(target=listening_thread, args=(sock,)).start()

        chan = FooChannel(host=host, port=port)
        self.addCleanup(chan.close)
        self.assertRaises(SocketGetResponseTimeoutError, chan.send, FooRequest("xxxx", timeout=1))

    def test_udp_channel(self):
        chan = FooChannel(host=self.udp_host, port=self.udp_port, proto="UDP")
        self.addCleanup(chan.close)
        data = "xxxx"
        req_ctx = FooRequest(data, timeout=1)
        rsp = chan.send(req_ctx)
        self.assertEqual(data, rsp.buffer)

    def test_udp_response_timeout(self):
        host, port = ("10.255.255.1", 80)  # non-routable address
        chan = FooChannel(host=host, port=port, proto="UDP")
        self.addCleanup(chan.close)
        self.assertRaises(SocketGetResponseTimeoutError, chan.send, FooRequest("xxxx", timeout=1))


if __name__ == "__main__":
    unittest.main(defaultTest="SocketChannelTest.test_udp_response_timeout")
