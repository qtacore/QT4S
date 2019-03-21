# -*- coding: utf-8 -*-
"""ioloop for underlayer socket connection
"""

import os
import select
import socket
import sys
import threading
import traceback
import errno

DEFAULT_BUFF_SIZE = 8192


class EnumSocketEvnet(object):
    E_READ = 0
    E_WRITE = 1
    E_ACCEPT = 1 << 2
    E_RESET = 1 << 3
    E_TIMEOUT = 1 << 4
    E_CLOSE = 1 << 5

    E_ERROR = E_RESET | E_TIMEOUT

    _event_map = {}

    @classmethod
    def displasy(cls, event):
        if not cls._event_map:
            for key in dir(cls):
                if not key.startswith("_") and key.isupper():
                    cls._event_map[getattr(cls, key)] = key

        return cls._event_map.get(event, "unknown")


class IOLoopBase(object):
    """base io loop
    """
    _instance_lock = threading.Lock()

    def __init__(self):
        self._lock = threading.Lock()
        self._fd_map = {}
        self._writing_fds = []

    def register_fd(self, fd, read_handler, connect_handler, err_handler):
        with self._lock:
            if fd in self._fd_map:
                raise RuntimeError("fd=%r is already registered")
            self._fd_map[fd] = {}
            self._writing_fds.append(fd)

            for event, handler in [(EnumSocketEvnet.E_READ, read_handler),
                          (EnumSocketEvnet.E_WRITE, connect_handler),
                          (EnumSocketEvnet.E_ERROR, err_handler)]:
                if not hasattr(handler, "__call__"):
                    raise ValueError("handler=%r must be callable object" % handler)
                self._fd_map[fd][event] = handler

    def remove_fd(self, fd):
        raise NotImplementedError

    def _check_valid_fd(self, fd):
        if fd not in self._fd_map:
            raise RuntimeError("fd=%r is not registered in current ioloop" % fd)

    def _handle_read(self, fd):
        self._check_valid_fd(fd)
        handler = self._fd_map[fd].get(EnumSocketEvnet.E_READ)
        handler()

    def _handle_connect(self, fd):
        self._check_valid_fd(fd)
        with self._lock:
            self._writing_fds.remove(fd)  # we should trigger E_WRITE only once
        handler = self._fd_map[fd].get(EnumSocketEvnet.E_WRITE)
        if not handler:
            raise RuntimeError("WRITE event of %s is not registered" % fd)
        handler()

    def _handle_error(self, fd, e, stack):
        self._check_valid_fd(fd)
        handler = self._fd_map[fd].get(EnumSocketEvnet.E_ERROR)
        self.remove_fd(fd)
        if not handler:
            raise RuntimeError("error event of %s is not registered" % fd)
        try:
            handler(e, stack)
        except:
            stack = traceback.format_exc()
            print("handle error socket failed: %s" % stack)

    def start(self):
        raise NotImplementedError

    def stop(self):
        cls = type(self)
        attr = "_instance_%s" % cls.__name__
        with self._instance_lock:
            setattr(cls, attr, None)

    @classmethod
    def instance(cls):
        attr = "_instance_%s" % cls.__name__
        if not hasattr(cls, attr):
            with cls._instance_lock:
                if not hasattr(cls, attr):
                    setattr(cls, attr, cls())
        return getattr(cls, attr)


class EnumSocketPairCmd:
    WAKEUP = "wakup\n"
    REGISTER = "register\n"
    REMOVE = "remove\n"

    @staticmethod
    def get_cmd_set():
        cmd_set = set()
        for key in dir(EnumSocketPairCmd):
            if key.isupper():
                cmd_set.add(getattr(EnumSocketPairCmd, key).strip())
        return cmd_set


socket_pair_cmd_set = EnumSocketPairCmd.get_cmd_set()


class SelectIOLoop(IOLoopBase):
    """io loop via select.select
    """

    def __init__(self):
        super(SelectIOLoop, self).__init__()
        self._ioloop_thread = None
        self._running = False
        self._removing_fds = []
        self._socket_pair = socketpair()
        r = self._socket_pair[0]
        self.register_fd(r, self.on_socket_pair_read, lambda : None, self.on_socket_pair_error)

    def on_socket_pair_read(self):
        data = self._socket_pair[0].recv(DEFAULT_BUFF_SIZE)
        cmd_set = set(filter(lambda x: x != "", data.split("\n")))
        if not cmd_set.issubset(socket_pair_cmd_set):
            raise RuntimeError("socket pair receive unexpected data: %s" % data)

    def on_socket_pair_error(self, e, stack):
        err_msg = "wakup fd for read error: %s\n%s" % (e, stack)
        raise RuntimeError(err_msg)

    def register_fd(self, fd, read_handler, connect_handler, err_handler):
        IOLoopBase.register_fd(self, fd, read_handler, connect_handler, err_handler)
        self._socket_pair[1].send(EnumSocketPairCmd.REGISTER)  # wakeup select from pending

    def remove_fd(self, fd):
        with self._lock:
            self._removing_fds.append(fd)
            self._socket_pair[1].send(EnumSocketPairCmd.REMOVE)

    def start(self):
        if not self._running:  # avoiding lock acquire and release
            with self._lock:
                if not self._running:
                    self._running = True
                    self._ioloop_thread = threading.Thread(target=self._ioloop_thread_func)
                    self._ioloop_thread.daemon = True
                    self._ioloop_thread.start()

    def stop(self):
        if self._ioloop_thread:
            self._running = False
            self._socket_pair[1].send(EnumSocketPairCmd.WAKEUP)
            self._ioloop_thread.join(10)
            with self._lock:
                for fd in self._fd_map.keys():
                    fd.close()
                self._fd_map = {}
                self._writing_fds = []
            self._ioloop_thread = None
            super(SelectIOLoop, self).stop()

    def _ioloop_thread_func(self):
        try:
            while self._running:
                with self._lock:
                    for fd in self._removing_fds[:]:
                        if fd not in self._fd_map:
                            break
                        del self._fd_map[fd]
                        try:
                            self._writing_fds.remove(fd)
                        except ValueError:  # already removed
                            pass
                    self._removing_fds = []

                fds = self._fd_map.keys()
                if not fds:
                    self._running = False
                    print("select ioloop exit normally")
                    break
                r, w, x = select.select(fds, self._writing_fds, fds, None)
                self._handle_fd(r, w, x)
        except:
            stack = traceback.format_exc()
            print("select loop unexpectedly exited:\n%s" % stack)
            for fd in self._fd_map.copy():
                fd.close()
            self._fd_map = {}

    def _handle_fd(self, r, w, x):
        try:
            for active_fd in w:
                err = active_fd.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                if 0 != err:
                    e = socket.error(err, os.strerror(err))
                    self._handle_error(active_fd, e, "socket level error")
                else:
                    self._handle_connect(active_fd)

            for active_fd in r:
                self._handle_read(active_fd)
        except socket.error as e:
            if e.args[0] == errno.EBADF:
                pass  # socket unexpectedly closed
            else:
                stack = traceback.format_exc()
                self._handle_error(active_fd, e, stack)
        except Exception as e:
            stack = traceback.format_exc()
            self._handle_error(active_fd, e, stack)

        for active_fd in x:
            err = active_fd.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            e = socket.error(err, os.strerror(err))
            self._handle_error(active_fd, e, "socket exception from select")


if "win32" in sys.platform:

    def socketpair():
        server = socket.socket()
        server.bind(("localhost", 0))
        server.listen(1)
        w = socket.socket()
        w.connect(server.getsockname())
        r = server.accept()[0]
        return r, w

    DEFAULT_IOLOOP_CLS = SelectIOLoop
else:
    from socket import socketpair
    DEFAULT_IOLOOP_CLS = SelectIOLoop
