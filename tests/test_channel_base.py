# -*- coding: utf-8 -*-
"""test for channel.base module
"""
import unittest

from qt4s.message.definition import Message, Field, Int32, String, Uint8, Buffer, Uint32
from qt4s.message.serializers.binary import BinarySerializer
from qt4s.message.serializers.jce import JceSerializer
from qt4s.message.serializers.protobuf import ProtobufSerializer
from qt4s.message.utils import size_of
from tests.test_message.demo_jce import DemoJce
from tests.test_message.demo_pb2 import AddressBook
from qt4s.channel.sock import RequestBase, ResponseBase


class FooHead(Message):
    _struct_ = [
        Field("len", Int32),
        Field("seq", Int32),
        Field("cmd", String, byte_size=16),
        Field("token", Buffer, byte_size=16)
    ]


class FooReqBody(Message):
    _struct_ = [
        Field("a", Int32),
        Field("b", Int32),
    ]


class FooRspBody(Message):
    _struct_ = [
        Field("ret", Int32),
        Field("msg_len", Uint8),
        Field("msg", String, size_ref="msg_len"),
    ]


class FooResponse(ResponseBase):
    _struct_ = [
        Field("head", FooHead,),
        Field("bin_body", FooRspBody)
    ]
    _length_field_ = "head.len"
    _serializer_ = BinarySerializer()


class FooRequest(RequestBase):
    _struct_ = [
        Field("head", FooHead),
        Field("bin_body", FooReqBody),
        Field("jce_body_len", Uint32),
        Field("jce_body", DemoJce, serializer=JceSerializer(), size_ref="jce_body_len"),
        Field("pb_body_len", Uint32, size_ref_hook=lambda x: x - 4),
        Field("pb_body", AddressBook, serializer=ProtobufSerializer(), size_ref="pb_body_len", size_ref_hook=lambda x: x + 4)
    ]
    _length_field_ = "head.len"
    _serializer_ = BinarySerializer()
    response_class = FooResponse

    def get_sequence_id(self):
        return self.head.seq


class PacketTest(unittest.TestCase):
    """composite message test
    """

    @classmethod
    def setUpClass(cls):
        cls.bin_body = FooReqBody()
        cls.bin_body.a = 100
        cls.bin_body.b = -200
        cls.bin_body_len = size_of(cls.bin_body, BinarySerializer())

        cls.jce_body = DemoJce()
        cls.jce_body.id = 2424323
        cls.jce_body.name = "demo_jce"
        cls.jce_body.array = [13, 24, 35]
        cls.jce_body.mapping["ooo"] = 1
        cls.jce_body_len = len(cls.jce_body.dumps(JceSerializer()))

        cls.pb_body = AddressBook()
        person = cls.pb_body.people.add()
        person.id = 1
        person.name = "foo"
        person.email = "foo@foo.com"
        phone = person.phones.add()
        phone.type = person.MOBILE
        phone.number = "13312345678"
        cls.pb_body_len = len(cls.pb_body.dumps(ProtobufSerializer())) + 4  # including size ref field

        cls.head = FooHead()
        cls.head.cmd = "add" + "\x00" * 13
        cls.head.seq = 0xffff
        cls.head.token = "333" + "\x00" * 13
        cls.head_len = size_of(cls.head, BinarySerializer())

        cls.req = FooRequest()
        cls.req.head = cls.head
        cls.req.bin_body = cls.bin_body
        cls.req.jce_body = cls.jce_body
        cls.req.pb_body = cls.pb_body

        cls.buff = cls.req.dumps()

    def check_req(self, req):
        field_list = ["head",
                      "bin_body",
                      "jce_body_len",
                      "jce_body",
                      "pb_body_len",
                      "pb_body"]

        self.assertEqual(req.head.seq, 0xffff)
        self.assertEqual(req.bin_body.a, 100)
        self.assertEqual(req.jce_body.name, "demo_jce")
        self.assertEqual(req.pb_body.people[0].phones[0].number, "13312345678")

        req_field_list = map(lambda x: x.name, req.get_struct().get_fields())
        self.assertEqual(field_list, req_field_list)

    def test_access_field(self):
        self.check_req(self.req)

    def test_dumps_loads(self):
        total_len = 0
        head_buff = self.head.dumps(BinarySerializer())
        head_len = len(head_buff)
        self.assertEqual(head_buff, self.buff[total_len:(total_len + head_len)])
        total_len += head_len

        bin_body_buff = self.bin_body.dumps(BinarySerializer())
        bin_body_len = len(bin_body_buff)
        self.assertEqual(bin_body_buff, self.buff[total_len:(total_len + bin_body_len)])
        total_len += bin_body_len

        jce_body_buff = BinarySerializer().dumps(Uint32, self.jce_body_len)
        jce_body_buff += self.jce_body.dumps(JceSerializer())
        jce_body_len = len(jce_body_buff)
        self.assertEqual(jce_body_buff, self.buff[total_len:(total_len + jce_body_len)])
        total_len += jce_body_len

        pb_body_buff = BinarySerializer().dumps(Uint32, self.pb_body_len)
        pb_body_buff += self.pb_body.dumps(ProtobufSerializer())
        pb_body_len = len(pb_body_buff)
        self.assertEqual(pb_body_buff, self.buff[total_len:(total_len + pb_body_len)])
        total_len += pb_body_len

        self.assertEqual(total_len, len(self.buff))

        loaded_req = FooRequest()
        loaded_req.loads(self.buff)
        self.check_req(loaded_req)

    def test_set_length_fields(self):
        self.assertEqual(self.req["head"].len, len(self.buff))

    def test_get_buffer_length(self):
        loaded_req = FooRequest()
        length = loaded_req.get_message_length(self.buff, BinarySerializer())
        self.assertEqual(length, len(self.buff))

    def test_request_method(self):
        self.assertEqual(self.req.get_timeout(), 10)
        self.assertEqual(self.req.response_class, FooResponse)
        self.assertEqual(self.req.get_sequence_id(), 0xffff)

    def test_response(self):
        rsp = FooResponse()
        rsp.set_request(self.req)
        rsp.head.from_assignment(self.head.dumps())
        rsp.bin_body.ret = 0
        rsp.bin_body.msg = "success"
        rsp_buf = rsp.dumps()
        loaded_rsp = FooResponse()
        loaded_rsp.set_request(self.req)
        loaded_rsp.loads(rsp_buf)
        self.assertEqual(rsp, loaded_rsp)
        self.assertEqual(rsp.request, self.req)


if __name__ == "__main__":
    unittest.main(defaultTest="PacketTest")
