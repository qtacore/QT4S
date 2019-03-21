# -*- coding: utf-8 -*-
'''杂项
'''

import socket
import time
import random
import threading
import traceback

_orig_socket = socket.socket  # 防止多线程时，socket被hook


class RetryLimitError(Exception):
    '''超过重试错误
    '''
    pass


class Limit(object):
    '''限定次数的重试操作
    '''

    def __init__(self, max_count, interval):
        self._max = max_count
        self._interval = interval

    def retry(self,
        func,
        args,
        exceptions=(Exception),
        resultmatcher=None):
        '''重试
        '''
        count = 0
        while True:
            try:
                ret = func(*args)
                if resultmatcher is None:
                    return ret
                else:
                    if resultmatcher(ret) == True:
                        return ret
                count += 1
                if count >= self._max:
                    raise RetryLimitError('尝试了%d次，结果为%s' % (count, str(ret)))

            except exceptions:
                count += 1
                if count >= self._max:
                    raise RetryLimitError('尝试了%d次，异常为:\n%s' % (count, traceback.format_exc()))

            time.sleep(self._interval)
        return ret


class SequenceGenerator(object):
    '''序号生成器
    '''

    def __init__(self, min_val=0, max_val=0xffffffff):
        self._min = min_val
        self._max = max_val
        self._curr = random.randint(min_val, max_val)
        self._lock = threading.Lock()

    def create_seq(self):
        with self._lock:
            self._curr += 1
            if self._curr > self._max:
                self._curr = self._min
            return self._curr


class ServerList(object):
    '''解析出server列表，自动尝试端口是否可连，仅支持tcp
    '''

    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._ip_list = socket.gethostbyname_ex(host)[2]
        random.shuffle(self._ip_list)
        self._index = 0

    def addr(self):
        if len(self._ip_list) == 0:
            raise RuntimeError("[%s]无可用的服务器ip" % self._host)
        for i in range(len(self._ip_list)):
            host = self._ip_list[i]
            if self.test_connectivity(host):
                return (host, self._port)
        else:
            raise RuntimeError("[%s:%s]对应的服务器列表：%s均不可达" % (self._host, self._port, str(self._ip_list)))

    def test_connectivity(self, host, timeout=5):
        try:
            sock = _orig_socket()
            sock.settimeout(timeout)
            sock.connect((host, self._port))
        except socket.error:
            sock.close()
            return False
        else:
            sock.close()
            return True


class cached_method(object):
    """caching a method's result
    """
    _not_invoked = object()

    def __init__(self, func):
        self.__func = func
        self.__result = self._not_invoked
        self.__callee = None

    def __call__(self, *args, **kwargs):
        if self.__result == self._not_invoked:
            if self.__callee:
                self.__result = self.__func(self.__callee, *args, **kwargs)
            else:
                self.__result = self.__func(*args, **kwargs)
        else:
            return self.__result

    def __get__(self, instance, owner):
        if instance:
            self.__callee = instance
        else:
            self.__callee = owner
        return self

