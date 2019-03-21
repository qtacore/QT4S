# -*- coding: utf-8 -*-
"""base class
"""


class NetworkArea(object):
    """network area
    """

    def __init__(self, *args):
        self.names = set(map(lambda x: x.upper(), args))

    def __eq__(self, other):
        if not isinstance(other, NetworkArea):
            return False
        else:
            return self.names == other.names

    def __str__(self):
        return "|".join(self.names)

    def __and__(self, other):
        return len(self.names & other.names) > 0


class INetworkAreaDetector(object):
    """network area detector interface definition
    """

    def detect(self):
        raise NotImplementedError


class IProxy(object):
    """proxy interface definition
    """

    def __enter__(self):
        raise NotImplementedError

    def __exit__(self, *args):
        raise NotImplementedError

