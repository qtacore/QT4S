# -*- coding: utf-8 -*-

import json
import unittest

from qt4s.message.definition import Message, Field, String, Uint32, Uint16, Uninitialized
from tests.test_message.demo_jce import DemoJce
from tests.test_message.demo_pb2 import AddressBook
from qt4s.message.serializers.binary import BinarySerializer
from qt4s.message.serializers.jce import JceSerializer
from qt4s.message.serializers.protobuf import ProtobufSerializer


class FooMessage(Message):
    _struct_ = [
        Field("x", Uint32),
        Field("s_len", Uint16),
        Field("s", String, size_ref="s_len"),
        Field("jce_len", Uint16),
        Field("jce", DemoJce, serializer=JceSerializer(), size_ref="jce_len"),
        Field("pb_len", Uint16),
        Field("pb", AddressBook, serializer=ProtobufSerializer(), size_ref="pb_len"),
        Field("option1", Uint32, optional=True),
        Field("option2", Uint32, optional=True, default=2),
        Field("unknown", String)
    ]


class PythonSerializerTest(unittest.TestCase):

    def test_dumps_and_loads(self):
        foo = FooMessage()
        foo.x = 3
        foo.s = "xxxx"
        foo.jce.id = 1
        foo.jce.name = "foo"
        foo.jce.array = [1, 2, 3]
        foo.jce.mapping = {"a" : 1}
        person = foo.pb.people.add()
        person.id = 1
        person.name = "foo"
        person.email = "foo@foo.com"
        phone = person.phones.add()
        phone.type = person.MOBILE
        phone.number = "13312345678"

        foo.fill_size_ref(BinarySerializer())

        foo_json = str(foo)
        foo_json_dict = json.loads(foo_json)
        self.assertEqual(foo_json_dict["unknown"], str(Uninitialized))

        self.assertRaises(ValueError, foo.dumps)
        foo.unknown = "xxx"
        foo_dict = foo.dumps()
        self.assertEqual(foo_dict["x"], 3)
        self.assertEqual(foo_dict["s_len"], len(foo_dict["s"]))
        self.assertEqual(foo_dict["s"], foo.s)
        self.assertEqual(foo_dict["jce_len"], foo.jce_len)
        self.assertEqual(foo_dict["jce"], foo.jce.dumps())
        self.assertEqual(foo_dict["pb_len"], foo.pb_len)
        self.assertEqual(foo_dict["pb"], foo.pb.dumps())
        self.assertTrue("option1" not in foo_dict)
        self.assertTrue("option2" not in foo_dict)
        self.assertEqual(foo_dict["unknown"], "xxx")


if __name__ == "__main__":
    unittest.main()
