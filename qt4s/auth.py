# -*- coding: utf-8 -*-
"""qt4s authentication
"""


class AuthenticationBase(object):
    """base class of authentication
    """

    def auth(self, account):
        raise NotImplementedError


class AccountBase(object):
    """base class of account
    """
    pass


class UserBase(object):
    """base class of user
    """

    def __init__(self, account, tickets):
        self._account = account
        self._tickets = tickets

    @property
    def account(self):
        return self._account
