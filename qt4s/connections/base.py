# -*- coding: utf-8 -*-
"""connections base
"""


class ConnectionBase(object):
    """base class of connection
    """

    def __init__(self, address):
        """construct a connection from addressing object
        
        :param address: address from addressing object
        :type  address: dict
        """
        self._address = address

    def get_net_area(self):
        return self._address.get("net_area")

    def get_proxy(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError
