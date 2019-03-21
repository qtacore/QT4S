# -*- coding: utf-8 -*-
"""direct addressing
"""

from qt4s.addressing.base import AddressingBase
from qt4s.domain import resolve
from qt4s.network.areas import LAN


class DirectAddressing(AddressingBase):
    """default direct addressing
    """
    keywords = ["host"]

    def get_address(self):
        port = self.kwargs.get("port", None)
        proto = self.kwargs.get("proto", "TCP")
        net_area = self.kwargs.get("net_area", LAN)
        new_host, new_area = resolve(self.kwargs["host"], net_area)
        address = {"host" : new_host,
                   "port" : port,
                   "proto" : proto,
                   "net_area" : new_area}
        return address

