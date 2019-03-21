# -*- coding: utf-8 -*-
"""test case for service
"""

import unittest

from qt4s.service import Method, Service, Channel
from qt4s.message.definition import Uint32, Message


# 定义协议格式
class HelloRequest(Message):
    _struct_ = Uint32


class HelloResponse(Message):
    _struct_ = Uint32


# 定义通道
class HelloChannel(Channel):

    def call_method(self, methodid, request, response_class, timeout):
        return response_class()


# 定义服务
class Memory(Service):
    _name_ = 'memory'
    _methods_ = [
        Method("free", HelloRequest, HelloResponse),
        Method("alloc", HelloRequest, HelloResponse)
    ]


class OperatingSystem(Service):
    _name_ = 'os'
    _methods_ = [
        Method("boot", HelloRequest, HelloResponse),
        Method("shutdown", HelloRequest, HelloResponse),
        Method("user.logon", HelloRequest, HelloResponse),
        Method("user.logout", HelloRequest, HelloResponse)
    ]
    _services_ = [
        Memory,
        {
            '_name_': 'process',
            '_methods_':[
                Method("start", HelloRequest, HelloResponse),
                Method("kill", HelloRequest, HelloResponse),
            ],
            '_services_':[
                {
                    '_name_': 'manager',
                    '_methods_':[
                        Method("listall", HelloRequest, HelloResponse),
                    ]
                 }
            ]
         }
    ]


class ServiceTest(unittest.TestCase):
    """service test
    """

    def setUp(self):
        chan = HelloChannel()
        self.service = OperatingSystem(chan)

    def test_invoke(self):
        rsp = self.service.boot(HelloRequest())
        self.assertIsInstance(rsp, HelloResponse, "rsp is not HelloResponse type")

        rsp = self.service.shutdown(HelloRequest())
        self.assertIsInstance(rsp, HelloResponse, "rsp is not HelloResponse type")

    def test_cascade_invoke(self):
        rsp = self.service.user.logon(HelloRequest())
        self.assertIsInstance(rsp, HelloResponse, "rsp is not HelloResponse type")

        rsp = self.service.user.logout(HelloRequest())
        self.assertIsInstance(rsp, HelloResponse, "rsp is not HelloResponse type")

    def test_subservice_invoke(self):
        rsp = self.service.process.start(HelloRequest())
        self.assertIsInstance(rsp, HelloResponse, "rsp is not HelloResponse type")

        rsp = self.service.process.kill(HelloRequest())
        self.assertIsInstance(rsp, HelloResponse, "rsp is not HelloResponse type")

    def test_subservice_cascade_invoke(self):
        rsp = self.service.process.manager.listall(HelloRequest())
        self.assertIsInstance(rsp, HelloResponse, "rsp is not HelloResponse type")
