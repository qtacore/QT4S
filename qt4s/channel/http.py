# -*- coding: utf-8 -*-
"""http channel of qt4s
"""

import json
import os
import traceback

from qt4s.addressing.direct import DirectAddressing
from qt4s.channel.base import ChannelBase, IRequest, IResponse
from qt4s.channel.httpbody import HttpBody, MIMEAutoDecoderMgr, Binary, Json, MultiPart, \
    UrlEncoded
from qt4s.connections.http import HttpConn
from six.moves.urllib import parse


class HttpResponse(IResponse):
    """http response base
    """

    def __init__(self):
        self._request = None
        self._headers = None
        self._body = None
        self._status_code = None
        self._reason = None

    @property
    def headers(self):
        return self._headers

    @property
    def body(self):
        return self._body

    @property
    def status_code(self):
        return self._status_code

    @property
    def reason(self):
        return self._reason

    def post_process(self, chan):
        if self.status_code not in range(200, 400):
            raise HttpResponseError(self)

    def loads(self, value, deserializer=None):
        headers, body, status_code, reason = value
        self._headers = headers
        self._status_code = status_code
        self._reason = reason

        try:
            content_type = headers.get("Content-Type", "")
            content_disposition = headers.get("Content-Disposition", "")
            self._body = MIMEAutoDecoderMgr().decode(body, content_type, content_disposition)
        except:
            stack = traceback.format_exc()
            raise ValueError("load body failed: headers=%s\nbody=%s\nstack=%s" % (headers, body, stack))

    def set_request(self, request):
        self._request = request


class HttpRequest(IRequest):
    """http request base
    """
    response_class = HttpResponse

    def __init__(self, url_path, method="GET", params={}, body=None, headers={}, timeout=10):
        self._url_path = url_path
        self._method = method
        self._params = params
        self._headers = headers.copy()
        if self._params:
            self._url_path += "?" + parse.urlencode(self._params)
        self._timeout = timeout
        if body and not isinstance(body, HttpBody):
            raise ValueError("body must be None or HttpBody instance")
        self._body = body

    @property
    def url_path(self):
        return self._url_path

    @property
    def method(self):
        return self._method

    @property
    def params(self):
        return self._params

    @property
    def body(self):
        return self._body

    @property
    def headers(self):
        return self._headers

    def get_timeout(self):
        return self._timeout

    def dumps(self, serializer=None):
        if self.body is not None:
            body = self.body.dumps(serializer)
            if self.body.content_type:
                self.headers["Content-Type"] = self.body.content_type
        else:
            body = None
        return self.url_path, self.method, body, self.headers, self.get_timeout()

    def pre_process(self, chan):
        pass


class HttpResponseError(Exception):
    """http response error
    """

    def __init__(self, response):
        self.response = response

    def __str__(self):
        headers = json.dumps(dict(self.response.headers), indent=4)
        return "[%s][%s]headers=\n%s\nbody=\n%s" % (self.response.status_code,
                                                    self.response.reason,
                                                    headers,
                                                    self.response.body)


class HttpChannel(ChannelBase):
    """http channel
    """
    request_class = HttpRequest
    authentication = None

    def get_connection(self):
        address = DirectAddressing(self.kwargs).get_address()
        server_name = self.kwargs.get("server_name", None) or self.kwargs["host"]
        use_ssl = self.kwargs.get("use_ssl", False)
        return HttpConn(address, server_name, use_ssl)

    def get_response(self, request):
        url_path, method, body, headers, timeout = request.dumps()
        rsp_data = self._conn.request(url_path, method, body, headers, timeout)
        response = request.response_class()
        response.loads(rsp_data)
        return response

    def create_request(self, *args, **kwargs):
        if isinstance(kwargs.get("body", None), bytes):
            kwargs["body"] = Binary(kwargs["body"])
        if isinstance(kwargs.get("body", None), dict):
            if "files" in kwargs:
                multi_part = MultiPart()
                for key, value in kwargs.pop("body", {}).items():
                    multi_part.add_field(key, value)
                for field_name, fd in kwargs.pop("files", {}).items():
                    multi_part.add_file(field_name, os.path.basename(fd.name), fd)
                kwargs["body"] = multi_part
            else:
                urlencoded = UrlEncoded(kwargs["body"])
                kwargs["body"] = urlencoded

        if "json" in kwargs:
            if kwargs["body"] is not None:
                raise ValueError("json and body cannot specified at the same time")
            kwargs["body"] = Json(kwargs.pop("json"))

        req = HttpRequest(*args, **kwargs)
        return req

    def add_cookie_from_dict(self, key_values):
        for key, value in key_values.items():
            self._conn.add_cookie(key, value)

    def get(self, url_path, params={}, headers={}, timeout=10):
        return self.request(url_path, method="GET", params=params, body=None, headers=headers, timeout=timeout)

    def post(self, url_path, params={}, body=None, headers={}, timeout=10, **kwargs):
        return self.request(url_path, method="POST", params=params, body=body, headers=headers, timeout=timeout, **kwargs)

    def head(self, url_path, params={}, headers={}, timeout=10):
        return self.request(url_path, method="HEAD", params=params, body=None, headers=headers, timeout=timeout)

    def options(self, url_path, params={}, headers={}, timeout=10):
        return self.request(url_path, method="OPTIONS", params=params, body=None, headers=headers, timeout=timeout)

    def put(self, url_path, params={}, body=None, headers={}, timeout=10, **kwargs):
        return self.request(url_path, method="PUT", params=params, body=body, headers=headers, timeout=timeout, **kwargs)

    def delete(self, url_path, params={}, headers={}, timeout=10):
        return self.request(url_path, method="DELETE", params=params, body=None, headers=headers, timeout=timeout)

    def patch(self, url_path, params={}, body=None, headers={}, timeout=10, **kwargs):
        return self.request(url_path, method="PATCH", params=params, body=body, headers=headers, timeout=timeout, **kwargs)

