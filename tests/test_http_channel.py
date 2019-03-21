# -*- coding: utf-8 -*-
"""test cases for http channel
"""

import os
import sys
import threading
import unittest

from qt4s.channel.http import HttpChannel, HttpRequest, HttpResponse, \
    HttpResponseError
from qt4s.channel.httpbody import Binary, Attachment, MultiPart, UrlEncoded, \
    Image, Html
from six.moves.urllib import parse
from tests.simple_servers import HttpEchoServer
import shutil


class HttpChannelTest(unittest.TestCase):
    """http channel tests
    """

    @classmethod
    def setUpClass(cls):
        cls.http_server = HttpEchoServer()
        threading.Thread(target=cls.http_server.serve_forever).start()
        cls.http_host, cls.http_port = cls.http_server.server_address
        cls.chan = HttpChannel(host=cls.http_host, port=cls.http_port)

    @classmethod
    def tearDownClass(cls):
        cls.http_server.shutdown()

    def test_direct_request(self):
        rsp = self.chan.get("/")
        self.assertEqual(rsp.body.data, "http get")

    def test_send_error(self):
        try:
            self.chan.get("/404")
        except HttpResponseError as e:
            self.assertEqual(e.response.status_code, 404)
            self.assertEqual(e.response.reason, "Not Found")

    def test_send(self):
        req = HttpRequest("/", timeout=1)
        rsp = self.chan.send(req)
        self.assertTrue(isinstance(rsp, HttpResponse))
        self.assertEqual(rsp.body.data, "http get")

    def test_params(self):
        params = {"x" : 1, "y" : "foo"}
        rsp = self.chan.get("/params", params=params)
        self.assertEqual(rsp.body.data, parse.urlencode(params))

    def test_requests(self):
        uri = "/"
        self.http_methods_request(self.chan, uri)

    def http_methods_request(self, chan, uri):
        rsp = chan.request(uri, timeout=1)
        self.assertEqual(rsp.body.data, "http get")
        rsp = chan.get(uri, timeout=1)
        self.assertEqual(rsp.body.data, "http get")

        rsp = chan.request(uri, method="POST", body=Binary("http post"), timeout=1)
        self.assertEqual(rsp.body.data, "http post")
        rsp = chan.post(uri, body=Binary("http post"), timeout=1)
        self.assertEqual(rsp.body.data, "http post")
        rsp = chan.post(uri, body="http post", timeout=1)
        self.assertEqual(rsp.body.data, "http post")

        rsp = chan.request(uri, method="HEAD", timeout=1)
        self.assertEqual(rsp.headers["Content-Length"], "100")
        rsp = chan.head(uri, timeout=1)
        self.assertEqual(rsp.headers["Content-Length"], "100")

        rsp = chan.request(uri, method="OPTIONS", timeout=1)
        self.assertEqual(rsp.body.data, "http options")
        rsp = chan.options(uri, timeout=1)
        self.assertEqual(rsp.body.data, "http options")

        rsp = chan.request(uri, method="PUT", body=Binary("http put"), timeout=1)
        self.assertEqual(rsp.body.data, "http put")
        rsp = chan.put(uri, body=Binary("http put"), timeout=1)
        self.assertEqual(rsp.body.data, "http put")

        rsp = chan.request(uri, method="DELETE", timeout=1)
        self.assertEqual(rsp.body.data, "http delete")
        rsp = chan.delete(uri, timeout=1)
        self.assertEqual(rsp.body.data, "http delete")

        rsp = chan.request(uri, method="PATCH", body=Binary("http patch"), timeout=1)
        self.assertEqual(rsp.body.data, "http patch")
        rsp = chan.patch(uri, body=Binary("http patch"), timeout=1)
        self.assertEqual(rsp.body.data, "http patch")

    def test_urllib(self):
        chan = HttpChannel(host=self.http_host, port=self.http_port)
        chan.use_requests = False
        self.http_methods_request(chan, "/")

    def test_attachment(self):
        uri = "/attachment"
        rsp = self.chan.get(uri)
        self.assertEqual(type(rsp.body), Attachment)
        self.assertEqual(rsp.body.data, "<HTML>qt4s</HTML>")

        file_dir = "test_attachment_%s%s" % (sys.version_info[0], sys.version_info[1])
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        self.addCleanup(shutil.rmtree, file_dir)
        rsp.body.save(file_dir)
        self.assertTrue(os.path.exists(os.path.join(file_dir, "qt4s.html")))

    def test_mutlipart(self):
        uri = "/multipart"
        body = MultiPart()
        body.add_field("x", "xx")
        body.add_field("y", "oo")
        file_dir = "test_multipart_%s%s" % (sys.version_info[0], sys.version_info[1])
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        file_path = os.path.join(file_dir, "test_multipart.txt")
        with open(file_path, "w") as fd:
            fd.write(file_path)
        fd = open(file_path, "rb")
        self.addCleanup(shutil.rmtree, file_dir)
        self.addCleanup(fd.close)
        body.add_file("filename", os.path.basename(file_path), fd)
        rsp = self.chan.post(uri, body=body)
        self.check_multipart(rsp)

        fd.seek(os.SEEK_SET)  # reset file pos
        rsp = self.chan.post(uri, body={"x" : "xx", "y": "oo"}, files={"filename" : fd})
        self.check_multipart(rsp)

    def check_multipart(self, rsp):
        multi_part = rsp.body
        file_dir = "test_multipart_%s%s" % (sys.version_info[0], sys.version_info[1])
        file_path = os.path.join(file_dir, "test_multipart.txt")
        self.assertEqual(dict(multi_part.form_fields), {"x" : "xx", "y" : "oo"})
        self.assertEqual(multi_part.files, [('filename',
                                             'filename="test_multipart.txt"',
                                             'Content-Type: text/plain',
                                             file_path)])

    def test_urlencoded(self):
        uri = "/urlencoded"
        data = {"x" : "xx", "y" : "oo"}
        rsp = self.chan.post(uri, body=UrlEncoded(data))
        self.assertEqual(type(rsp.body), UrlEncoded)
        self.assertEqual(rsp.body, data)

    def test_image(self):
        uri = "/image"
        for image_type in ["png", "bmp", "jpeg", "svg+xml"]:
            rsp = self.chan.get(uri + "/" + image_type)
            self.assertEqual(type(rsp.body), Image)
            self.assertEqual(rsp.body.data, "qt4s." + image_type)

    def test_html(self):
        uri = "/qt4s.html"
        rsp = self.chan.get(uri)
        self.assertEqual(type(rsp.body), Html)
        elems = rsp.body.xpath("body")
        self.assertEqual(len(elems), 1)
        self.assertEqual(elems[0].text_content(), "qt4s")


if __name__ == "__main__":
    unittest.main(defaultTest="HttpChannelTest.test_requests")
