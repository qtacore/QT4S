# -*- coding: utf-8 -*-
"""test utilities for qt4s
"""
import base64
import re
import select
import struct
import sys

from six.moves import socketserver
from six.moves import BaseHTTPServer
from hashlib import sha1
from testbase.util import smart_binary

DEFAULT_ADDRESS = ("127.0.0.1", 0)


class EchoStreamHandler(socketserver.StreamRequestHandler):
    """handler implements an echo stream handler
    """

    def handle(self):
        while True:
            buff = self.connection.recv(8192)
            if buff:
                self.connection.send(buff)
            else:
                break


class TcpEchoServer(socketserver.ThreadingTCPServer):
    """server implements an echo server
    """
    allow_reuse_address = True

    def __init__(self, server_address=DEFAULT_ADDRESS):
        socketserver.ThreadingTCPServer.__init__(self, server_address, EchoStreamHandler)


class EchoDatagramHandler(socketserver.DatagramRequestHandler):
    """handler implements an echo datagram handler
    """

    def handle(self):
        self.wfile.write("xxxx")


class UdpEchoServer(socketserver.ThreadingUDPServer):
    """server implements an echo server
    """
    allow_reuse_address = True

    def __init__(self, server_address=DEFAULT_ADDRESS):
        socketserver.ThreadingUDPServer.__init__(self, server_address, EchoDatagramHandler)


class HttpHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """http echo handler
    """

    def do_GET(self):
        if self.path == "/404":
            self.send_error(404)
        elif self.path.startswith("/param"):
            params = self.path[len("/param") + 2:]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(params)
        elif self.path == "/attachment":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="qt4s.html"')
            body = "<HTML>qt4s</HTML>"
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/qt4s.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            body = "<HTML><head>qt4s</head></HTML>"
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/image"):
            self.send_response(200)
            self.send_header("Content-Type", "image/%s; charset=utf-8" % self.path[7:])
            body = "qt4s." + self.path[7:]
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(200)
            self.send_header("Host", self.headers["Host"])
            self.end_headers()
            self.wfile.write("http get")

    def do_POST(self):
        self.send_response(200)
        for header in ["Host", "Content-Length", "Content-Type"]:
            if header in self.headers:
                self.send_header(header, self.headers[header])
        content_len = int(self.headers.get("Content-Length", "0"))
        self.end_headers()

        body = self.rfile.read(content_len)
        self.wfile.write(body)

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Length", "100")
        self.end_headers()

    def do_PUT(self):
        self.send_response(200)
        self.end_headers()

        content_len = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_len)
        self.wfile.write(body)

    def do_DELETE(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write("http delete")

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write("http options")

    def do_PATCH(self):
        self.send_response(200)
        self.end_headers()

        content_len = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_len)
        self.wfile.write(body)


class HttpEchoServer(BaseHTTPServer.HTTPServer):
    """http echo server
    """
    allow_reuse_address = True

    def __init__(self, server_address=DEFAULT_ADDRESS):
        BaseHTTPServer.HTTPServer.__init__(self, server_address, HttpHandler)


FIN = 0x80
OPCODE = 0x0f
MASKED = 0x80
PAYLOAD_LEN = 0x7f
PAYLOAD_LEN_EXT16 = 0x7e
PAYLOAD_LEN_EXT64 = 0x7f

OPCODE_TEXT = 0x01
CLOSE_CONN = 0x8


class WebsocketHandler(socketserver.StreamRequestHandler):
    """a handler for websocket
    """
    _uuid = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

    def setup(self):
        socketserver.StreamRequestHandler.setup(self)
        self.ioloop_running = True
        self.handshake_done = False

    def handle(self):
        while self.ioloop_running:
            r, _, _ = select.select([self.connection], [], [], 60)
            if r:
                if not self.handshake_done:
                    self.do_handshake()
                else:
                    self.read_next_message()

    def send_all(self, data):
        sent_size = 0
        data_len = len(data)
        while sent_size < data_len:
            sent_size += self.connection.send(data[sent_size:])

    def do_handshake(self):
        buf = ""
        while buf[-4:] != "\r\n\r\n":
            buf += self.request.recv(1024)
        upgrade = re.search('\nupgrade[\s]*:[\s]*websocket', buf.lower())
        if not upgrade:
            self.ioloop_running = False
            return

        key = re.search('\n[sS]ec-[wW]eb[sS]ocket-[kK]ey[\s]*:[\s]*(.*)\r\n', buf)
        if key:
            key = key.group(1)
        else:
            print("Client tried to connect but was missing a key")
            self.ioloop_running = False
            return

        response = self.make_handshake_response(key)
        self.send_all(response)
        self.handshake_done = True
        self.server.on_new_client(self)

    @classmethod
    def make_handshake_response(cls, key):
        return \
          'HTTP/1.1 101 Switching Protocols\r\n'\
          'Upgrade: websocket\r\n'              \
          'Connection: Upgrade\r\n'             \
          'Sec-WebSocket-Accept: %s\r\n'        \
          '\r\n' % cls.calculate_response_key(key)

    @classmethod
    def calculate_response_key(cls, key):
        hash_val = sha1(key.encode() + cls._uuid)
        response_key = base64.encodestring(hash_val.digest()).strip()
        return response_key

    def finish(self):
        self.server.on_lost_client(self)

    def read_bytes(self, num):
        # python3 gives ordinal of byte directly
        data = self.rfile.read(num)
        if sys.version_info[0] < 3:
            return map(ord, data)
        else:
            return data

    def read_next_message(self):
        data = self.read_bytes(2)
        if not data:
            self.ioloop_running = False
            return ""
        else:
            b1, b2 = data[:2]

        opcode = b1 & OPCODE
        masked = b2 & MASKED
        payload_length = b2 & PAYLOAD_LEN

        if not b1:
            print("Client closed connection.")
            self.ioloop_running = False
            return
        if opcode == CLOSE_CONN:
            print("Client asked to close connection.")
            self.ioloop_running = False
            return
        if not masked:
            print("Client must always be masked.")
            self.ioloop_running = False
            return

        if payload_length == 126:
            payload_length = struct.unpack(">H", self.rfile.read(2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack(">Q", self.rfile.read(8))[0]

        masks = self.read_bytes(4)
        decoded = ""
        for char in self.read_bytes(payload_length):
            char ^= masks[len(decoded) % 4]
            decoded += chr(char)
        self.server.on_new_message(self, decoded)

    def send_message(self, message):
        self.send_text(message)

    def send_text(self, message):
        '''
        NOTES
        Fragmented(=continuation) messages are not being used since their usage
        is needed in very limited cases - when we don't know the payload length.
        '''

        # Validate message
        if isinstance(message, bytes):
            message = smart_binary(message)  # this is slower but assures we have UTF-8
            if not message:
                print("Can\'t send message, message is not valid UTF-8")
                return False
        elif isinstance(message, str) or isinstance(message, unicode):
            pass
        else:
            print('Can\'t send message, message has to be a string or bytes. Given type is %s' % type(message))
            return False

        header = bytearray()
        payload = smart_binary(message)
        payload_length = len(payload)

        # Normal payload
        if payload_length <= 125:
            header.append(FIN | OPCODE_TEXT)
            header.append(payload_length)

        # Extended payload
        elif payload_length >= 126 and payload_length <= 65535:
            header.append(FIN | OPCODE_TEXT)
            header.append(PAYLOAD_LEN_EXT16)
            header.extend(struct.pack(">H", payload_length))

        # Huge extended payload
        elif payload_length < 18446744073709551616:
            header.append(FIN | OPCODE_TEXT)
            header.append(PAYLOAD_LEN_EXT64)
            header.extend(struct.pack(">Q", payload_length))

        else:
            raise Exception("Message is too big. Consider breaking it into chunks.")
            return

        self.request.send(header + payload)


class WebSocketServer(socketserver.ThreadingTCPServer):
    """abstract websocket server
    """
    allow_reuse_address = True

    def __init__(self, port, host="127.0.0.1", bind_and_activate=True):
        socketserver.ThreadingTCPServer.__init__(self, (host, port), RequestHandlerClass=WebsocketHandler, bind_and_activate=bind_and_activate)

    def on_new_client(self, client):
        pass

    def on_lost_client(self, client):
        pass

    def on_new_message(self, handler, msg):
        raise NotImplementedError
