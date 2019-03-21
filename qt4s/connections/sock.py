# -*- coding: utf-8 -*-
"""socket connection implement
"""

from __future__ import print_function

import errno
import os
import socket
import threading

from qt4s.connections.base import ConnectionBase
from qt4s.connections.ioloop import DEFAULT_IOLOOP_CLS
from qt4s.network.proxy import NullProxy
from qt4s.network.rules import get_proxy

if hasattr(errno, "WSAEINPROGRESS"):
    E_INPROGRESS = (errno.EINPROGRESS, getattr(errno, "WSAEINPROGRESS"))
else:
    E_INPROGRESS = (errno.EINPROGRESS,)

if hasattr(errno, "WSAEWOULDBLOCK"):
    E_WOULDBLOCK = (getattr(errno, "WSAEWOULDBLOCK"),)
else:
    E_WOULDBLOCK = ()

DEFAULT_BUFF_SIZE = 8192


class EnumConnType(object):
    TCP = "TCP"
    UDP = "UDP"

    @staticmethod
    def get_socket_type(conn_type):
        conn_type = conn_type.upper()
        if conn_type == "TCP":
            return socket.SOCK_STREAM
        elif conn_type == "UDP":
            return socket.SOCK_DGRAM
        else:
            raise ValueError("unrecognized connection type: %s" % conn_type)


def get_errno(e):
    if hasattr(e, "errno"):
        return getattr(e, "errno")
    if e.args:
        return e.args[0]
    return None


class SocketCallback(object):
    """socket callback
    """

    def on_recv(self, data):
        pass

    def on_send(self, data):
        pass

    def on_connect(self):
        pass

    def on_closed(self):
        pass

    def on_error(self, e, stack):
        print("socket error %s:\n%s" % (e, stack))

    def on_push(self, response):
        print("receive unexpected response: %s" % response)


class SocketConn(ConnectionBase):
    """socket connection
    """
    ioloop_cls = None

    def __init__(self, address, callback):
        super(SocketConn, self).__init__(address)
        self.socket_type = address["proto"].upper()
        self._host = address["host"]
        self._port = address["port"]
        self._callback = callback
        self._sock = None
        self._ioloop = DEFAULT_IOLOOP_CLS.instance()
        self._closed = False
        self._buf = []
        self._lock = threading.Lock()

    @property
    def host(self):
        return self._host

    @property
    def orig_host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def fd(self):
        return self._sock

    def get_proxy(self):
        conditions = {
            "proto" : self.socket_type,
            "port" : self.port
        }
        return get_proxy(self.get_net_area(), conditions=conditions)

    def register(self):
        self._ioloop.register_fd(self._sock, self.on_recv, self.on_connected, self.on_error)
        self._ioloop.start()

    def connect(self):
        proxy = self.get_proxy()
        need_connect = self.socket_type == EnumConnType.TCP
        need_connect |= self.socket_type == EnumConnType.UDP and not isinstance(proxy, NullProxy)
        if need_connect:
            try:
                with proxy:
                    self._sock = socket.socket(socket.AF_INET, EnumConnType.get_socket_type(self.socket_type))
                    self._sock.setblocking(False)  # we use non-blocking socket
                    self._sock.connect((self._host, self._port))
            except socket.error as e:
                err_number = get_errno(e)
                if err_number not in E_INPROGRESS and err_number not in E_WOULDBLOCK:
                    raise
        else:
            self._sock = socket.socket(socket.AF_INET, EnumConnType.get_socket_type(self.socket_type))
            self._sock.setblocking(False)
        self.register()

    def send(self, data):
        self._callback.on_send(data)
        if self.socket_type == EnumConnType.TCP:
            sent_size = 0
            data_size = len(data)
            while sent_size < data_size:
                sent_size += self._sock.send(data[sent_size:])
        else:
            self._sock.sendto(data, 0, (self._host, self._port))

    def read(self):
        with self._lock:
            if self.socket_type == EnumConnType.TCP:
                data = "".join(self._buf)
                self._buf = []
            else:
                data = self._buf[0]
                self._buf = self._buf[1:]
        return data

    def close(self):
        if not self._closed:
            self._closed = True
            self._ioloop.remove_fd(self._sock)
            self._sock.close()
            self._callback.on_closed()

    def on_connected(self):
        self._callback.on_connected()

    def on_recv(self):
        if self.socket_type == EnumConnType.TCP:
            data = self.fd.recv(DEFAULT_BUFF_SIZE)
            if data:
                with self._lock:
                    self._buf.append(data)
                self._callback.on_recv()
            else:
                self._ioloop.remove_fd(self._sock)
                self._callback.on_closed()
        else:
            data, addr = self.fd.recvfrom(DEFAULT_BUFF_SIZE)
            with self._lock:
                self._buf.append((data, addr))
            self._callback.on_recv()

    def on_error(self, e, stack):
        if not e:
            err = self._sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            e = socket.error(err, os.strerror(err))
        self._callback.on_error(e, stack)
