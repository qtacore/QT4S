# -*- coding: utf-8 -*-
"""network proxy
"""

import socket
import threading

from qt4s.network.base import IProxy


class ProxyBase(IProxy):
    """base class of proxy
    """
    clib_support = False

    def __enter__(self):
        threading.local()._orig_socket = socket.socket
        try:
            self.negotiate()
        except:
            socket.socket = threading.local()._orig_socket  # rollback
            raise

    def __exit__(self, *args):
        try:
            self.cleanup()
        finally:
            socket.socket = threading.local()._orig_socket

    def negotiate(self):
        raise NotImplementedError

    def cleanup(self):
        pass


class NullProxy(IProxy):
    """null proxy
    """

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass

