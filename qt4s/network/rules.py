# -*- coding: utf-8 -*-
"""network rules
"""

import fnmatch

from qt4s.network.detectors import CURRENT
from qt4s.network.proxy import NullProxy
from testbase.conf import settings
from testbase.util import get_attribute_from_string, Singleton


class CaseInsensitiveDict(dict):

    def __getitem__(self, key):
        return super(CaseInsensitiveDict, self).__getitem__(key.lower())

    def __setitem__(self, key, value):
        return super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)

    def __contains__(self, key):
        return super(CaseInsensitiveDict, self).__contains__(key.lower())

    def get(self, key, *args):
        return super(CaseInsensitiveDict, self).get(key.lower(), *args)


class NoRuleException(Exception):
    """no rule exception
    """


class NetworkRuleManager(object):
    __metaclass__ = Singleton

    def __init__(self):
        self.__rules = CaseInsensitiveDict()
        for rule_item in settings.QT4S_NETWORK_RULES:
            self._add_rule(rule_item)

    def _add_rule(self, rule_item, append=True):
        dst = rule_item["dst"]
        src = rule_item["src"]
        conditions = rule_item.get("conditions", {})
        proxy = rule_item.get("proxy", {})
        self.__rules.setdefault(dst, CaseInsensitiveDict())
        self.__rules[dst].setdefault(src, [])
        item = {"rule_type" : rule_item["rule_type"],
                "conditions" : conditions,
                "proxy" : proxy}
        if append:
            self.__rules[dst][src].append(item)
        else:
            self.__rules[dst][src].insert(0, item)

    def insert_rule(self, rule_item):
        self._add_rule(rule_item, append=False)

    def get_rules(self):
        return self.__rules

    def get_proxy(self, dst_area, src_area=None, conditions={}):
        if src_area is None:
            src_area = CURRENT

        dst_area_name = str(dst_area)
        for src_area_name in src_area.names:
            proxy = self._get_proxy(dst_area_name, src_area_name, conditions)
            if proxy is not None:
                return proxy
        else:
            raise NoRuleException("no rule found from %s to %s with conditions=%s" % (src_area,
                                                                                   dst_area,
                                                                                   conditions))

    def _get_proxy(self, dst_area_name, src_area_name, conditions):
        rule_items = self.__rules.get(dst_area_name, {}).get(src_area_name, {})
        for rule_item in rule_items:
            rule_conditions = rule_item["conditions"]
            proxy_conf = rule_item["proxy"]
            if "protocols" in rule_conditions:
                if "protocol" not in conditions:
                    continue
                if conditions["protocol"] not in rule_conditions["protocols"]:
                    continue

            if "hosts" in rule_conditions:
                if "host" not in conditions:
                    continue
                for item in rule_conditions["hosts"]:
                    if fnmatch.fnmatch(conditions["host"], item):
                        break
                else:
                    continue

            if "ports" in rule_conditions:
                if "port" not in conditions:
                    continue
                for item in rule_conditions["ports"]:
                    if isinstance(item, list) and conditions["port"] in item:
                        break
                    elif conditions["port"] == item:
                        break
                else:
                    continue

            if rule_item["rule_type"] == "direct":
                return NullProxy()

            proxy_type = get_attribute_from_string(proxy_conf["type"])
            if conditions.get("clib", False) is True and proxy_type.clib_support is False:
                return None

            proxy = proxy_type(**proxy_conf["kwargs"])
            return proxy
        else:
            if dst_area_name == src_area_name:  # same area and no explicit rule
                return NullProxy()
            else:
                return None


def get_proxy(dst_area, src_area=None, conditions={}):
    return NetworkRuleManager().get_proxy(dst_area, src_area=src_area, conditions=conditions)