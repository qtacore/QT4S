# -*- coding: utf-8 -*-
"""test proxy
"""

import os
import sys
import unittest

from qt4s.network.areas import LAN
from qt4s.network.proxy import ProxyBase, NullProxy
from qt4s.network.rules import NetworkRuleManager, NoRuleException, get_proxy
from testbase.test import modify_settings
from qt4s.network.base import NetworkArea
from qt4s.network.detectors import CURRENT, detect
import shutil

FOO = NetworkArea("foo")
BAR = NetworkArea("bar")


class FooProxy(ProxyBase):
    pass


class FooClibProxy(ProxyBase):
    clib_support = True


QT4S_NETWORK_RULES = [
    {
        "rule_type" : "direct",
        "dst" : "wan",
        "src" : "lan"
    },
    {
        "rule_type" : "direct",
        "dst" : "foo",
        "src" : "lan",
        "conditions" : {
            "protocols" : ["http", "https"],
            "ports" : [80, 443, 8080, 8081],
            "hosts" : ["172.16.1.1"]
        }
    },
    {
        "rule_type" : "proxy",
        "dst" : "foo",
        "src" : "lan",
        "conditions" : {
            "protocols" : ["http", "https"],
        },
        "proxy" : {
            "type" : "tests.test_network.FooProxy",
            "kwargs" : {}
        }
    },
    {
        "rule_type" : "proxy",
        "dst" : "bar",
        "src" : "lan",
        "proxy" : {
            "type" : "tests.test_network.FooClibProxy",
            "kwargs" : {}
        }
    }
]


class DetectorTest(unittest.TestCase):

    def test_dectector(self):
        if sys.version_info[0] == 3:
            raise RuntimeError("this case will conflict in parallel with python 2 and 3")

        self.assertEqual(CURRENT, LAN)

        qt4s_dir = os.path.join(os.path.expanduser("~"), ".qt4s")

        os.makedirs(qt4s_dir)
        with open(os.path.join(qt4s_dir, "netarea"), "w") as fd:
            fd.write("tests.test_network.FOO\nqt4s.network.areas.WAN")
        self.addCleanup(shutil.rmtree, qt4s_dir)
        current_area = detect()
        self.assertEqual(current_area, NetworkArea("foo", "wan", "lan"))
        self.assertTrue(current_area & LAN)
        self.assertTrue(current_area & FOO)


class NetworkRuleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        instances = getattr(NetworkRuleManager, "_instances")
        instances.pop(NetworkRuleManager, None)
        cls.ctx = modify_settings(QT4S_NETWORK_RULES=QT4S_NETWORK_RULES)
        cls.ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.__exit__()
        instances = getattr(NetworkRuleManager, "_instances")
        instances.pop(NetworkRuleManager, None)

    def test_network_rule(self):
        rules = NetworkRuleManager().get_rules()
        self.assertEqual(len(rules["wan"]["lan"]), 1)
        self.assertEqual(len(rules["foo"]["lan"]), 2)
        self.assertEqual(len(rules["bar"]["lan"]), 1)

        rule_item = {"dst": "bar",
                     "src": "lan",
                     "conditions" :{"ports" : [443, 80]},
                     "rule_type" : "direct"}
        NetworkRuleManager().insert_rule(rule_item)
        self.assertEqual(len(rules["bar"]["lan"]), 2)
        self.assertEqual(rules["bar"]["lan"][0]["conditions"], rule_item["conditions"])

    def test_match_rule(self):
        rule_manager = NetworkRuleManager()

        proxy = get_proxy(FOO, FOO)
        self.assertEqual(type(proxy), NullProxy)

        rule_manager.insert_rule({"rule_type" : "proxy",
                                  "dst" : "lan",
                                  "src" : "lan",
                                  "conditions" : {
                                      "hosts" : ["127.0.0.2"]
                                  },
                                  "proxy" : {
                                      "type" : "tests.test_network.FooProxy",
                                      "kwargs" : {}
                                  }})
        conditions = {"host" : "127.0.0.2", "port" : 80, "protocol" : "https"}
        proxy = rule_manager.get_proxy(LAN, conditions=conditions)
        self.assertEqual(type(proxy).__name__, FooProxy.__name__)

        conditions = {"host" : "172.16.1.1", "port" : 80, "protocol" : "https"}
        proxy = rule_manager.get_proxy(LAN, conditions=conditions)
        self.assertEqual(type(proxy), NullProxy)

        proxy = rule_manager.get_proxy(FOO, conditions=conditions)
        self.assertEqual(type(proxy), NullProxy)

        conditions = {"host" : "172.16.1.2", "protocol" : "https"}
        proxy = rule_manager.get_proxy(FOO, conditions=conditions)
        self.assertEqual(type(proxy).__name__, FooProxy.__name__)

        conditions = {"protocol" : "tcp"}
        self.assertRaises(NoRuleException, rule_manager.get_proxy, FOO, conditions=conditions)

        conditions = {"protocol" : "http", "clib" : True}
        self.assertRaises(NoRuleException, rule_manager.get_proxy, FOO, conditions=conditions)

        conditions = {"protocol" : "http", "clib" : True}
        proxy = rule_manager.get_proxy(BAR, conditions=conditions)
        self.assertEqual(type(proxy).__name__, FooClibProxy.__name__)


if __name__ == "__main__":
#     unittest.main(defaultTest="NetworkRuleTest.test_match_rule")
    unittest.main()
