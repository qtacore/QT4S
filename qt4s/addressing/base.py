# -*- coding: utf-8 -*-
"""addressing base
"""


class IAddressing(object):
    """addressing interface class
    """

    def get_address(self):
        """get address with given keyword arguments
        
        :returns : a dict including host, port, proto and net_area
        :type    : dict
        """
        raise NotImplementedError


class AddressingBase(object):
    """base class of addressing
    """
    keywords = []

    def __init__(self, kwargs):
        self.kwargs = kwargs
        self.check_params(kwargs)

    def get_keywords(self):
        """return essential keyword arguments for addressing
        """
        return self.keywords

    def check_params(self, kwargs):
        not_found = []
        for keyword in self.get_keywords():
            if keyword not in kwargs:
                not_found.append(keyword)
        if not_found:
            err_msg = "essential keyword argument(s): %s not found" % ",".join(not_found)
            raise ValueError(err_msg)
