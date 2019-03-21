# -*- coding: utf-8 -*-

import unittest

from qt4s.message.definition import Message, Uint32, Array, Map, Double, String, Field, Uint8, Float, Buffer
from qt4s.message.utils import size_of, offset_of, field_size_of
from qt4s.message.serializers.binary import BinarySerializer
from rsa.common import byte_size


class ByteLenString(Message):
    _struct_ = [
        Field("len", Uint8),
        Field("string", String, size_ref="len")
    ]


class Bar(Message):
    _struct_ = [
        Field("byte_len_string", ByteLenString)
    ]


class FooMap(Message):
    _struct_ = [
        Field("map", Map(String, Uint32))
    ]


class FooBuff(Message):
    _struct_ = [
        Field("buf_len", Uint32, size_ref_hook=lambda x: x - 4),
        Field("buf", Buffer, size_ref="buf_len", size_ref_hook=lambda x: x + 4),
        Field("a", Float)
    ]


class FooMessage(Message):
    _struct_ = [
        Field("cmd", String, byte_size=16),
        Field("username_len", Uint8, size_ref_hook=lambda x: x - 4),
        Field("username", String, size_ref="username_len", size_ref_hook=lambda x: x + 4),
        Field("version", Uint32, default=0),
        Field("timestamp", Float),
        Field("double_data", Double),
        Field("seq", Uint32),
        Field("len", Uint32),
        Field("uint32_list", Array(Uint32), array_size=5),
        Field("array_size", Uint8, default=0),
        Field("string_list", Array(ByteLenString), size_ref="array_size"),
        Field("bar", Bar)
    ]


class SizedBuff(Message):
    _struct_ = [
        Field("code", Uint8),
        Field("buff", String, byte_size=16),
        Field("buff1_len", Uint8),
        Field("buff1", Buffer, size_ref="buff1_len"),
        Field("buff2", Buffer, byte_size=0)
    ]


class SizeOfTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.foo = FooMessage()
        cls.foo.cmd = "test"
        cls.foo.username = "qt4s"
        cls.foo.username_len = len(cls.foo.username) + 4
        cls.foo.timestamp = 1.0003234
        cls.foo.double_data = 13243433324324.34234
        cls.foo.version = 1
        cls.foo.seq = 0xff
        cls.foo.len = 0
        cls.foo.uint32_list = [1, 2, 3, 4, 5]
        for item in ["a", "bb", "ccc", "dddd"]:
            elem = ByteLenString()
            elem.len = len(item)
            elem.string = item
            cls.foo.string_list.append(elem)
            cls.foo.array_size += 1
        cls.foo.bar.byte_len_string.len = 7
        cls.foo.bar.byte_len_string.string = "size_of"

    def test_field_size_of_string(self):
        self.foo.dumps(BinarySerializer())
        self.assertEqual(field_size_of(self.foo, "cmd", BinarySerializer()), 16)
        self.assertEqual(field_size_of(self.foo, "username", BinarySerializer()), 4)

    def test_field_size_of_number(self):
        self.assertEqual(field_size_of(self.foo, "version", BinarySerializer()), 4)
        self.assertEqual(field_size_of(self.foo, "timestamp", BinarySerializer()), 4)
        self.assertEqual(field_size_of(self.foo, "double_data", BinarySerializer()), 8)

    def test_field_size_of_array(self):
        self.assertEqual(field_size_of(self.foo, "uint32_list", BinarySerializer()), 20)
        self.assertEqual(field_size_of(self.foo, "string_list", BinarySerializer()), 14)

    def test_field_size_of_map(self):
        foo_map = FooMap()
        foo_map.map["xxx"] = 1
        self.assertRaises(TypeError, size_of, self.foo, "mapping", BinarySerializer())

    def test_size_offset_of(self):
        self.assertEqual(offset_of(self.foo, "cmd", BinarySerializer()), 0)
        self.assertEqual(offset_of(self.foo, "username", BinarySerializer()), 17)
        self.assertEqual(offset_of(self.foo, "version", BinarySerializer()), 21)

    def test_size_of_nested(self):
        self.assertEqual(field_size_of(self.foo, "bar.byte_len_string.len", BinarySerializer()), 1)
        self.assertEqual(field_size_of(self.foo, "bar.byte_len_string.string", BinarySerializer()), 7)
        self.assertEqual(field_size_of(self.foo, "bar.byte_len_string", BinarySerializer()), 8)


class SerializingTest(unittest.TestCase):
    """test serializing
    """

    @classmethod
    def setUpClass(cls):
        cls.foo_buff = FooBuff()
        cls.foo_buff.buf = "abcdefg"
        cls.foo_buff.a = 3.1415926
        cls.data = cls.foo_buff.dumps(BinarySerializer())

    def test_dump_size_ref(self):
        self.assertEqual(self.foo_buff.buf_len, 11)
        self.assertEqual(len(self.data), 15)

    def test_dump_without_serializer(self):
        foo_buff = FooBuff()
        foo_buff.buf = "xxx"
        foo_buff.a = 1.1111
        self.assertRaises(ValueError, foo_buff.dumps)

        foo_buff.fill_size_ref(BinarySerializer())
        data = foo_buff.dumps()
        self.assertEqual(data, {"buf" : "xxx",
                                "a" : 1.1111,
                                "buf_len" : 7})

    def test_load_size_ref(self):
        foo_buff = FooBuff()
        foo_buff.loads(self.data, BinarySerializer())
        self.assertEqual(foo_buff.buf_len, 11)
        self.assertEqual(foo_buff.buf, "abcdefg")
        self.assertTrue((foo_buff.a - 3.1415926) < 0.00001)

    def test_load_byte_sized(self):
        sized_buff = SizedBuff()
        sized_buff.code = 10
        sized_buff.buff = "test"
        sized_buff.buff1 = "abcdefg"
        sized_buff.buff2 = "1234567"
        data = sized_buff.dumps(BinarySerializer())

        loaded_buff = SizedBuff()
        remain_data = loaded_buff.loads(data, BinarySerializer())
        self.assertEqual(remain_data, None)
        self.assertEqual(loaded_buff.code, 10)
        self.assertEqual(loaded_buff.buff1_len, 7)
        self.assertEqual(loaded_buff.buff1, "abcdefg")
        self.assertEqual(loaded_buff.buff2, "1234567")


if __name__ == "__main__":
    unittest.main(defaultTest="SerializingTest.test_load_byte_sized")
#     unittest.main()
