# -*- coding: utf-8 -*-
"""base channel of qt4s
"""

from qt4s.auth import UserBase


class IRequest(object):

    def dumps(self, serializer=None):
        """dump to other format
        """
        raise NotImplementedError

    def loads(self, value, serializer=None):
        """dump to other format
        """
        raise NotImplementedError

    def pre_process(self, chan):
        raise NotImplementedError

    def get_timeout(self):
        raise NotImplementedError


class IResponse(object):

    def dumps(self, serializer=None):
        """dump to other format
        """
        raise NotImplementedError

    def loads(self, value, serializer=None):
        """load from other value
        """
        raise NotImplementedError

    def post_process(self, chan):
        """post process after response is loaded
        """
        raise NotImplementedError

    def set_request(self, request):
        """explicitly set request of current repsonse
        """
        raise NotImplementedError


class ChannelBase(object):
    """base channel for all channels
    """
    request_class = None
    authentication = None

    def __init__(self, account_or_user=None, **kwargs):
        self.kwargs = kwargs
        self._user = self.do_auth(account_or_user)
        self._conn = self.get_connection()

    def do_auth(self, account_or_user):
        if isinstance(account_or_user, UserBase):
            return account_or_user
        authentication = self.get_authentication()
        if authentication is not None:
            user = authentication().auth(account_or_user)
            return user

    def get_user(self):
        return self._user

    def get_connection(self):
        raise NotImplementedError

    def get_address(self):
        raise NotImplementedError

    def get_authentication(self):
        return self.authentication

    def send(self, request):
        """send a request to server
        """
        if not isinstance(request, self.request_class):
            raise TypeError("request=%r does not match %r" % (request, self.request_class))
        request.pre_process(self)
        response = self.get_response(request)
        response.set_request(request)
        response.post_process(self)
        return response

    def get_response(self, request):
        raise NotImplementedError

    def request(self, *args, **kwargs):
        """a simplified method to invoke send
        """
        rsp = self.send(self.create_request(*args, **kwargs))
        return rsp

    def create_request(self, *args, **kwargs):
        """create a request, user should can override this method
        """
        req = self.request_class(*args, **kwargs)
        return req

    def close(self):
        self._conn.close()

