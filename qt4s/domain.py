# -*- coding: utf-8 -*-
"""host resolving
"""
from testbase import logger
from testbase.conf import settings
from testbase.util import get_attribute_from_string


class IDomainResolver(object):
    """domain resolver interface definition
    """

    def resolve(self, host, net_area=None):
        """if not resolved, return None, else return the actual host or ip
        """
        raise NotImplementedError


class DefaultDomainResolver(IDomainResolver):
    """default domain resolver whose scope is restricted in QT4S
    """

    def __init__(self):
        self._domain_dict = {}

    def resolve(self, host, net_area=None):
        '''resolve a host 
        '''
        new_host = self._domain_dict.get(host.lower(), host)
        return new_host, net_area

    def add_name(self, name, addr):
        '''add a host mapping
        '''
        logger.info("[Host]%s---->%s" % (name, addr))
        self._domain_dict[name.lower()] = addr

    def remove_name(self, name):
        '''remove a host mapping
        '''
        if self._domain_dict.has_key(name.lower()):
            self._domain_dict.pop(name.lower())

    def list_names(self):
        '''list all host mappings
        '''
        return self._domain_dict.copy()


default_domain_resolver = DefaultDomainResolver()
HostResolver = default_domain_resolver
HTTPResolver = HostResolver  # legacy code compatible

__qt4s_resolvers = []


def add_name(name, host):
    default_domain_resolver.add_name(name, host)


def resolve(host, net_area=None):
    if not __qt4s_resolvers:
        resolver_paths = settings.QT4S_DOMAIN_RESOLVERS
        for resolver_path in resolver_paths:
            resolver_cls = get_attribute_from_string(resolver_path)
            __qt4s_resolvers.append(resolver_cls())

        __qt4s_resolvers.append(default_domain_resolver)  # default resolver

    for resolver in __qt4s_resolvers:
        ret = resolver.resolve(host, net_area)
        if len(ret) != 2:
            raise ValueError("IDomainResolver.resolve must return two elements")
        if ret[0]:
            return ret
    else:
        raise RuntimeError("resolve host=%s failed" % host)
