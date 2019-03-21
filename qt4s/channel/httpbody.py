# -*- coding: utf-8 -*-
"""http body
"""

import fnmatch
import itertools
import json
import mimetypes
import os
import six

from six.moves.urllib import parse
from testbase.util import Singleton, smart_text
from qt4s.message.definition import Message, Buffer, Field
from qt4s.message.serializers.binary import BinarySerializer

try:
    from lxml import html
    has_lxml = True
except:
    has_lxml = False

if six.PY2:
    from mimetools import choose_boundary
    choose_boundary_func = choose_boundary
else:
    from email.generator import _make_boundary
    choose_boundary_func = _make_boundary


class HttpBody(object):
    '''http body
    '''

    def dumps(self, serializer=None):
        '''dump to binary
        '''
        raise NotImplementedError()

    def loads(self, data, confs={}, serializer=None):
        '''load from binary
        '''
        raise NotImplementedError()

    @property
    def content_type(self):
        '''content type
        '''
        raise NotImplementedError()

    def matched_content_type(self, content_type):
        '''is matched content type
        '''
        return self.content_type == content_type

    def __str__(self):
        return self.dumps()


class Binary(Message, HttpBody):
    _struct_ = [
        Field("data", Buffer)
    ]
    _serializer_ = BinarySerializer()

    @property
    def content_type(self):
        return ""

    def loads(self, value, confs={}, deserializer=None):
        return Message.loads(self, value, deserializer=deserializer)

    def dumps(self, serializer=None):
        return Message.dumps(self, serializer=serializer)


class UrlEncoded(dict, HttpBody):
    '''url encoded body
    '''
    _content_type = 'application/x-www-form-urlencoded'

    def __init__(self, d=None, charset='UTF-8'):
        self._charset = charset
        if d is not None:
            self.update(d)

    def dumps(self, serializer=None):
        '''dump to binary
        '''
        return parse.urlencode(self)

    @property
    def content_type(self):
        '''content type
        '''
        return '; '.join([self._content_type, 'charset=%s' % self._charset])

    def matched_content_type(self, content_type):
        '''is matched content type
        '''
        return self._content_type == content_type

    def loads(self, data, confs=None, serializer=None):
        '''load from binary
        '''
        d = parse.parse_qs(data, keep_blank_values=True, strict_parsing=True)
        td = {}
        for key in d:
            if len(d[key]) == 1:
                td[key] = d[key][0]
            else:
                td[key] = d[key]
        self.clear()
        self.update(td)
        return self


class Json(dict, HttpBody):
    '''json http body
    '''
    content_type = 'application/json'

    def __init__(self, d=None):
        if d is not None:
            self.update(d)

    def dumps(self, serializer=None):
        '''dump to binary
        '''
        return json.dumps(self)

    def loads(self, data, confs=None, serializer=None):
        '''load from binary
        '''
        d = json.loads(data)
        self.clear()
        self.update(d)

    def matched_content_type(self, content_type):
        data_type = content_type.split("/")[-1]
        return "json" in data_type


class MultiPart(HttpBody):
    '''HTTP MultiPart
    '''

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = choose_boundary_func()

    def __setitem__(self, name, value):
        self.add_field(name, value)

    def __contains__(self, name):
        for field_name, _ in self.form_fields:
            if field_name == name:
                return True
        else:
            return False

    @property
    def content_type(self):
        '''content type
        '''
        return 'multipart/form-data; boundary=%s' % self.boundary

    def matched_content_type(self, content_type):
        '''is matched content type
        '''
        for it in content_type.split(';'):
            if it.strip().lower() == 'multipart/form-data':
                return True
        else:
            return False

    def add_field(self, name, value):
        '''add a field to body
        '''
        self.form_fields.append((name, str(value)))

    def _to_encoding(self, content, encoding):
        import locale
        if isinstance(content, unicode):
            return content.encode(encoding)
        try:
            return content.decode(locale.getdefaultlocale()[1]).encode(encoding)
        except UnicodeDecodeError:
            try:
                return content.decode('utf8').encode(encoding)
            except UnicodeDecodeError:
                return content

    def add_file(self, fieldname, filename, fileHandle, mimetype=None, encoding='utf8'):
        '''add a file to body
        '''
        if isinstance(fieldname, unicode):
            fieldname = self._to_encoding(fieldname, "utf8")
        if isinstance(filename, unicode):
            filename = self._to_encoding(filename, "utf8")
        body = fileHandle.read()
        if encoding:
            body = self._to_encoding(body, encoding)
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((fieldname, filename, mimetype, body))

    def dumps(self, serializer=None):
        '''dump to binary
        '''
        parts = []
        part_boundary = '--' + self.boundary

        # Add the form fields
        parts.extend(
            [ part_boundary,
              'Content-Disposition: form-data; name="%s"' % name,
              '',
              value,
            ]
            for name, value in self.form_fields
            )

        # Add the files to upload
        parts.extend(
            [ part_boundary,
              'Content-Disposition: form-data; name="%s"; filename="%s"' % \
                 (field_name, filename),
              'Content-Type: %s' % content_type,
              '',
              body,
            ]
            for field_name, filename, content_type, body in self.files
            )

        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)

    def loads(self, data, confs=None, serializer=None):
        '''load from binary
        '''
        index = data.find("\r\n")
        if index < 0:
            raise ValueError("cannot find \\r\\n in data")
        self.boundary = data[:index]
        data_parts = data.split("\r\n")
        prefix_len = len("Content-Disposition:")
        pos = 0
        parts_count = len(data_parts)
        while pos < parts_count:
            if data_parts[pos] == self.boundary:
                content_disposition = data_parts[pos + 1]
                if not content_disposition:
                    continue
                disposition = content_disposition[prefix_len:].split(";")
                disposition = list(map(lambda x: x.strip(), disposition))
                if disposition[0] == "form-data":
                    key = disposition[1].split("=")[-1].strip("\"'")
                    if len(disposition) == 2:
                        value = data_parts[pos + 3]
                        self.form_fields.append((key, value))
                        pos += 4
                    elif len(disposition) == 3:
                        file_name = disposition[2]
                        content_type = data_parts[pos + 2]
                        body = data_parts[pos + 4]
                        self.files.append((key, file_name, content_type, body))
                        pos += 5
                    else:
                        raise ValueError("unrecognized disposition: %s" % content_disposition)
                else:
                    raise ValueError("unrecognized disposition: %s" % disposition[0])
            else:
                pos += 1


class Html(HttpBody):
    '''http body
    '''
    content_type = 'text/html'

    def __init__(self):
        self._root = None
        self._data = None

    def dumps(self, serializer=None):
        '''dump to binary
        '''
        return self._data

    def loads(self, data, confs, serializer=None):
        '''load from binary
        '''
        if confs.has_key('charset'):
            try:
                data = data.decode(confs['charset']).encode('utf8')
            except UnicodeDecodeError:
                data = smart_text(data)
            root = html.fromstring(data)
        else:
            root = html.fromstring(data)
        if root.tag == 'html':
            self._data = data
            self._root = root

    def xpath(self, path):
        '''get elements from xpath
        '''
        return self._root.xpath(path)


class Image(HttpBody):
    '''http body
    '''
    content_type = 'image/*'

    def __init__(self):
        self.data = None

    def dumps(self, serializer=None):
        '''dump to binary
        '''
        return self.data

    def loads(self, data, confs, serializer=None):
        '''load from binary
        '''
        self.data = data

    def matched_content_type(self, content_type):
        return fnmatch.fnmatch(content_type, self.content_type)


class Attachment(HttpBody):
    '''http body
    '''
    content_type = "text/html"

    def __init__(self, disposition):
        self.data = None
        self.disposition = disposition
        self.file_name = disposition.get("filename", "unknown").strip("\"'")

    def dumps(self, serializer=None):
        raise NotImplementedError

    def loads(self, data, confs={}, serializer=None):
        if "charset" in confs:
            data = data.decode(confs["charset"])
        self.data = data

    def save(self, file_path=None):
        if file_path:
            if os.path.isdir(file_path):
                file_path = os.path.join(file_path, self.file_name)
        else:
            file_path = self.file_name
        with open(file_path, "wb") as fd:
            fd.write(self.data)


class MIMEAutoDecoderMgr(object):
    '''http body manager
    '''
    __metaclass__ = Singleton

    def __init__(self):
        self._body_types = {}

    def register(self, body_type):
        '''register a http body type
        '''
        name = body_type.__name__.lower()
        if name in self._body_types:
            raise RuntimeError('http body type named "%s" is already registered' % name)
        self._body_types[name] = body_type

    def decode(self, data, content_type, content_disposition="", serializer=None):
        '''decode a known content type
        '''
        if content_type.find(';'):
            items = content_type.split(';')
            items = [item.strip() for item in items]
            content_type = items[0]
            content_confs = {}
            for it in items[1:]:
                attrname, attrval = it.split('=')
                content_confs[attrname] = attrval
        else:
            content_confs = []

        if content_disposition:
            disposition_parts = content_disposition.split(";")
            if disposition_parts[0] == "attachment":
                dispostion = {}
                for disposition_part in disposition_parts[1:]:
                    key, value = disposition_part.split("=")
                    dispostion[key.strip()] = value.strip()
                body = Attachment(dispostion)
                body.loads(data)
                return body

        self._body_types.pop("binary", None)  # left Binary as last one
        body_types = self._body_types.values()
        for body_type in body_types:
            body = body_type()
            if body.matched_content_type(content_type):
                body.loads(data, content_confs, serializer)
                break
        else:
            body = Binary()
            body.loads(data, content_confs, serializer)
        return body


if has_lxml:
    MIMEAutoDecoderMgr().register(Html)

MIMEAutoDecoderMgr().register(Json)
MIMEAutoDecoderMgr().register(UrlEncoded)
MIMEAutoDecoderMgr().register(MultiPart)
MIMEAutoDecoderMgr().register(Image)
MIMEAutoDecoderMgr().register(Binary)

