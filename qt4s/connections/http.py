# -*- coding: utf-8 -*-
"""http connection
"""

from qt4s.connections.base import ConnectionBase
from qt4s.network.rules import get_proxy
from six.moves.http_cookiejar import CookieJar, Cookie
from testbase.util import smart_text

try:
    import requests
    has_requests = True
except ImportError:
    has_requests = False


class HttpConn(ConnectionBase):
    """http connection
    """

    def __init__(self, address, server_name=None, use_ssl=False,
                 ssl_verify=False, ssl_cert=None):
        super(HttpConn, self).__init__(address)
        self.use_requests = has_requests
        if server_name is None:
            self._server_name = self._address["host"]
        else:
            self._server_name = server_name
        if use_ssl:
            scheme = "https://"
            port = self._address["port"] or 443
        else:
            scheme = "http://"
            port = self._address["port"] or 80
        self._use_ssl = use_ssl
        self._host = self._address["host"]
        self._port = port
        self._ssl_verify = ssl_verify
        self._ssl_cert = ssl_cert
        netloc = "%s:%s" % (self._host, self._port)
        self._url_base = scheme + netloc
        self._session, self._cookie_jar = self.create_session()

    def create_session(self):
        if self.use_requests:
            session = requests.Session()
            session.verify = self._ssl_verify
            session.cert = self._ssl_cert
            session.trust_env = False  # let qt4s handle proxying
            cookie_jar = session.cookies
        else:
            from six.moves.urllib import request
            cookie_jar = CookieJar()
            cookie_processor = request.HTTPCookieProcessor(cookie_jar)
            session = request.build_opener(request.ProxyHandler({}),
                                           cookie_processor)
        return session, cookie_jar

    def get_proxy(self):
        conditions = {"port" : self._port}
        if self._use_ssl:
            conditions["proto"] = "https"
        else:
            conditions["proto"] = "http"
        return get_proxy(self.get_net_area(), conditions=conditions)

    def add_cookie(self, key, value):
        value = smart_text(value)
        cookie = Cookie(None, key, value,
                        None, False,
                        '', False, None,
                        '', False,
                        None, None, None, None, None, None)
        self._cookie_jar.set_cookie(cookie)

    def request(self, url_path, method, data=None, headers={}, timeout=10):
        full_url = self._url_base + url_path
        new_header = headers.copy()
        if "Host" not in headers:
            new_header["Host"] = self._server_name
        with self.get_proxy():
            return self._request(method, full_url, data, new_header, timeout)

    def _request(self, method, url, data, headers, timeout):
        if self.use_requests:
            rsp = self._session.request(method, url=url,
                                 data=data, headers=headers,
                                 timeout=timeout)
            return rsp.headers, rsp.content, rsp.status_code, rsp.reason
        else:
            from six.moves.urllib import request, error
            req = request.Request(url, data=data, headers=headers)
            req.get_method = lambda : method
            try:
                rsp = self._session.open(req, timeout=timeout)
            except error.HTTPError as e:
                return e.headers, e.read(), e.code, e.msg
            else:
                return rsp.headers, rsp.read(), rsp.code, rsp.msg

    def close(self):
        self._session.close()
