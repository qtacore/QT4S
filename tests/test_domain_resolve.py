# -*- coding: utf-8 -*-
"""testing qt4s domain resolving
"""

import sys
import threading
import unittest

from qt4s.channel.http import HttpChannel
from qt4s.domain import add_name, resolve, IDomainResolver
from tests.simple_servers import HttpEchoServer, TcpEchoServer
from testbase.test import modify_settings
from tests.test_socket_channel import FooChannel


class FooDomainResolver(IDomainResolver):

    def resolve(self, host, net_area=None):
        if host == "unknown.com":
            return None, net_area
        return "192.168.1.1", net_area


class DomainResolveTest(unittest.TestCase):
    """domain resolving test
    """

    @classmethod
    def setUpClass(cls):
        cls.http_server = HttpEchoServer()
        cls.http_host, cls.http_port = cls.http_server.server_address
        threading.Thread(target=cls.http_server.serve_forever).start()

        cls.sock_server = TcpEchoServer()
        cls.sock_host, cls.sock_port = cls.sock_server.server_address
        threading.Thread(target=cls.sock_server.serve_forever).start()

    @classmethod
    def tearDownClass(cls):
        cls.http_server.shutdown()
        cls.sock_server.shutdown()

    def test_default_resovler(self):
        domain = "www.default-resolver.com"
        ip = "127.0.0.1"
        add_name(domain, ip)
        host, _ = resolve(domain)
        self.assertEqual(host, ip)

    def test_set_resolver(self):
        mod = sys.modules["qt4s.domain"]
        setattr(mod, "__qt4s_resolvers", [])  # reset resolvers
        with modify_settings(QT4S_DOMAIN_RESOLVERS=["tests.test_domain_resolve.FooDomainResolver"]):
            ip, _ = resolve("www.set-resolver.com")
            self.assertEqual(ip, "192.168.1.1")

            ip, _ = resolve("unknown.com")
            self.assertEqual(ip, "unknown.com")

            add_name("unknown.com", "172.16.1.1")
            ip, _ = resolve("unknown.com")
            self.assertEqual(ip, "172.16.1.1")
        setattr(mod, "__qt4s_resolvers", [])  # reset resolvers

    def test_resolve_http(self):
        domain = "www.resolve-http.com"
        add_name(domain, self.http_host)
        chan = HttpChannel(host=domain, port=self.http_port)
        rsp = chan.request("/", timeout=3)
        ret_host = rsp.headers["Host"].split(":")[0]
        self.assertEqual(ret_host, domain)
        self.assertEqual(rsp.body.data, "http get")

    def test_resolve_socket(self):
        domain = "www.resolve-socket.com"
        add_name(domain, self.sock_host)
        chan = FooChannel(host=self.sock_host, port=self.sock_port)
        rsp = chan.request("xxxx", timeout=2)
        chan.close()
        self.assertEqual(rsp.buffer, "xxxx")


if __name__ == "__main__":
    unittest.main(defaultTest="DomainResolveTest.test_set_resolver")
