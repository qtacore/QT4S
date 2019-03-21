# -*- coding: utf-8 -*-
'''协议消息模块测试
'''

import unittest

from qt4s.message.definition import Int32, Uint32, Uint64, Int64, String, Bool, Field, Array, Map, Variant, Uninitialized
from qt4s.message.definition import Message
from qt4s.message.serializers.binary import BinarySerializer


class Baby(Message):
    _struct_ = [
        Field("name", String, optional=True),
        Field("age", Int32, optional=True),
    ]


class Mother(Message):
    _struct_ = [
        Field("name", String),
        Field("age", Int32),
        Field("alive", Bool,),
        Field("baby", Baby, optional=True),
    ]


class Mother2(Message):
    _struct_ = [
        Field("name", String),
        Field("age", Int32),
        Field("alive", Bool),
        Field("baby", [
            Field("name", String, optional=True),
            Field("age", Uint32, optional=True),
        ], optional=True)
    ]


class DictStructTest(unittest.TestCase):

    def setUp(self):
        self.d = {
            'name': 'alice',
            'age': 32,
            'alive': True,
            'baby':{
                'name': 'jojo',
                'age':2
            }
        }

    def test_normal(self):
        mother = Mother()
        self.assertRaises(AttributeError, getattr, mother, 'name')
        # self.assertEqual(type(mother.baby), Baby.get_struct_class().get_message_class())
        mother.name = 'alice'
        mother.age = 32
        mother.alive = True
        mother.baby.name = 'xxxx'
        mother.baby.age = 2
        baby = Baby()
        baby.name = 'jojo'
        baby.age = 2
        mother.baby = baby
        self.assertEqual(mother.dumps(), self.d)
        monther2 = Mother()
        monther2.loads(self.d)
        self.assertEqual(monther2.name, 'alice')
        self.assertEqual(monther2.age, 32)
        self.assertEqual(monther2.alive, True)
        self.assertEqual(monther2.baby.name, 'jojo')
        self.assertEqual(monther2.baby.age, 2)

    def test_assign_wrong_type(self):
        mother = Mother()
        self.assertRaises(ValueError, setattr, mother, 'age', "xxx")
        self.assertRaises(ValueError, setattr, mother, 'baby', 8888888)
        d = self.d.copy()
        d['age'] = "xxx"
        mother2 = Mother()
        self.assertRaises(ValueError, mother2.construct, d)

    def test_assign_wrong_type_str(self):
        mother = Mother()
        mother.name = 888

    def test_optional(self):
        mother = Mother()
        mother.name = 'alice'
        mother.age = 32
        mother.alive = True
        d = self.d.copy()
        del d['baby']
        self.assertEqual(mother.dumps(), d)
        mother.baby = Baby()
        d['baby'] = {}
        self.assertEqual(mother.dumps(), d)

    def test_lack_field(self):
        mother = Mother()
        self.assertRaises(ValueError, mother.reduce)

    def test_sync(self):
        mother = Mother()
        baby = mother.baby
        baby.name = "xxx"
        self.assertEqual(mother.baby.name, "xxx")

        mother = Mother()
        baby = Baby()
        mother.baby = baby
        baby.name = "xxx"
        self.assertEqual(mother.baby.name, "xxx")

    def test_assign_from_another(self):
        mother1 = Mother()
        mother1.baby.name = "xxx"

        mother2 = Mother()
        mother2.baby = mother1.baby

    def test_annoy(self):
        mother = Mother2()
        self.assertRaises(AttributeError, getattr, mother, 'name')
        mother.name = 'alice'
        mother.age = 32
        mother.alive = True
        mother.baby.name = 'jojo'
        mother.baby.age = 2
        self.assertEqual(mother.dumps(), self.d)
        monther2 = Mother2()
        monther2.loads(self.d)
        self.assertEqual(monther2.name, 'alice')
        self.assertEqual(monther2.age, 32)
        self.assertEqual(monther2.alive, True)
        self.assertEqual(monther2.baby.name, 'jojo')
        self.assertEqual(monther2.baby.age, 2)


class SingleNumber(Message):
    _struct_ = Int64


class NumberOwner(Message):
    _struct_ = [
        Field('one', SingleNumber),
        Field('extra', Int64)
    ]


class NonDictStructTest(unittest.TestCase):

    def test_normal(self):
        owner = NumberOwner()
        owner.extra = 888
        owner.one = 999
        d = {
             'one': 999,
             'extra': 888
        }
        self.assertEqual(owner.dumps(), d)
        owner2 = NumberOwner()
        owner2.loads(d)
        self.assertEqual(owner2.one, 999)
        self.assertEqual(owner2.extra, 888)

        owner3 = NumberOwner()
        self.assertRaises(ValueError, setattr, owner3, 'one', SingleNumber())

    def test_number(self):
        n = SingleNumber()
        n.value = 999
        self.assertEqual(n.dumps(), 999)
        n.loads(888)
        self.assertEqual(n.value, 888)


class Carrage(Message):
    _struct_ = [
        Field("id", Uint64)
    ]


class Train(Message):
    _struct_ = [
        Field("name", String),
        Field("carrages", Array(Carrage))
    ]


class NumberList(Message):
    _struct_ = Array(Int64)


class ArrayStructTest(unittest.TestCase):

    def test_normal(self):
        train = Train()
        train.name = "T1234"
        c1 = Carrage()
        c1.id = 1
        c2 = Carrage()
        c2.id = 2
        train.carrages = [c1]
        train.carrages.append(c2)

        c3 = train.carrages.add()
        c3.id = 3

        c0 = Carrage()
        c0.id = 0
        train.carrages.insert(0, c0)
        d = {
             'name': "T1234",
             "carrages": [
                {
                    'id':0,
                 },
                {
                    'id': 1,
                 },
                 {
                    'id': 2
                  },
                 {
                    'id': 3
                  }
            ]
        }
        self.assertEqual(train.dumps(), d)
        train2 = Train()
        train2.loads(d)
        self.assertEqual(train.name, "T1234")
        for idx, _ in enumerate(train2.carrages):
            self.assertEqual(train.carrages[idx].id, idx)

    def test_number_list(self):
        nums = NumberList()
        nums.append(1)
        nums.append(6)
        nums[1] = 2
        nums.insert(0, 0)
        self.assertEqual(nums.dumps(), [0, 1, 2])

        nums = NumberList()
        nums.loads([0, 1, 2, 3])
        for idx, _ in enumerate(nums):
            self.assertEqual(nums[idx], idx)
        self.assertEqual(1 in nums, True)

    def test_compare(self):
        train = Train()
        train.name = "T1234"
        c1 = Carrage()
        c1.id = 1
        train.carrages = [c1]

        train2 = Train()
        train2.name = "T1234"
        c2 = Carrage()
        c2.id = 1
        train2.carrages = [c2]
        self.assertEqual(train.carrages, train2.carrages)


class MapStruct(Message):
    _struct_ = [
        Field("name", String),
        Field("mm", Map(String, Int32)),
        Field("nm", Map(Int32, Int32))
    ]


class MapStructType(unittest.TestCase):

    def test_normal(self):
        m = MapStruct()
        m.name = "xxxxxxx"
        m.mm = {"5":5, "2":2}
        m.nm = {}
        d = {
            "name": "xxxxxxx",
            "mm":{"5":5, "2":2},
            "nm": {}
        }
        self.assertEqual(m.dumps(), d)

        self.assertRaises(ValueError, setattr, m, 'nm', {"x":5, 2:2})

        m2 = MapStruct()
        m2.loads(d)
        self.assertEqual(m2.mm["5"], 5)
        self.assertEqual(m2.mm["2"], 2)


class Options(Message):
    _struct_ = [
        Field("d", Bool, default=True),
        Field("d2", Bool, default=True, optional=True),
        Field("1", Int32, display="n"),
        Field("a", String, allow_none=True),
        Field("o", String, optional=True),
        Field("x", String)
    ]


class OptionTest(unittest.TestCase):

    def test_optional_assign_none(self):
        opt = Options()
        opt.d2 = Uninitialized

    def test_normal(self):
        opt = Options()
        opt.n = 333
        opt.a = None
        opt.x = "xxx"
        self.assertEqual(opt.d, True)
        # self.assertRaises(ValueError, setattr, opt, 'x', None)
        d = {
            'd': True,
            '1': 333,
            'a': None,
            'x': 'xxx'
        }
        self.assertEqual(opt.dumps(), d)

        d = {
            '1': 333,
            'a': None,
            'x': 'xxx'
        }
        opt = Options()
        opt.loads(d)
        self.assertEqual(opt.n, 333)
        self.assertEqual(opt.d, True)
        self.assertEqual(opt.d2, True)
        self.assertEqual(opt.a, None)
        self.assertEqual(opt.x, 'xxx')
        d['d'] = True
        self.assertEqual(opt.dumps(), d)

# class Request(Message):
#
#    _struct_ = [
#        Field("version", Int64),
#        Field("body", Raw)
#    ]
#
# class RawTest(unittest.TestCase):
#
#    def test_normal(self):
#        req = Request()
#        req.version = 343
#        req.body = {'x': 9}
#        d = {
#             'version': 343,
#             'body':{
#                     'x': 9
#            }
#        }
#        self.assertEqual(req.dumps(), d)
#
#        req.body = [6,7,8]
#        d['body'] = [6,7,8]
#        self.assertEqual(req.dumps(), d)
#
#        req.body = 8888
#        d['body'] = 8888
#        self.assertEqual(req.dumps(), d)


class StringContainer(Message):
    _struct_ = [
        Field("str", String),
        Field("str2", String, optional=True, encoding='gbk')
    ]


class StringEncoding(unittest.TestCase):

    def test_normal(self):

        con = StringContainer()
        con.str = "中文"
        self.assertEqual(con.str, "中文")
        self.assertEqual(type(con.str), type("中文"))

        con.str = u"中文"
        self.assertEqual(con.str, "中文")
        self.assertEqual(type(con.str), type("中文"))

        con = StringContainer()
        con.str = "中文"
        con.str2 = "中文"
        con.str2 = "中文".decode('utf8')
        con.str2 = "中文".decode('utf8').encode('gbk')
        self.assertEqual(con.dumps()['str2'], "中文".decode('utf8').encode('gbk'))


class Variant1(Message):
    _struct_ = [
        Field("id", Int64, default=1),
        Field("str", String)
    ]

    @property
    def data(self):
        return 'data_' + self.str


class Variant2(Message):
    _struct_ = [
        Field("id", Int64, default=2),
        Field("num", Int64)
    ]

    @property
    def data(self):
        return 'data_' + str(self.num)


class Variant3(Message):
    _struct_ = [
        Field("id", Int64, default=3),
        Field("flag", Bool)
    ]

    @property
    def data(self):
        return 'data_' + str(self.flag)


class VariantMessage(Message):
    _struct_ = Variant


class VariantArray(Message):
    _struct_ = Array(Variant)


class VariantDict(Message):
    _struct_ = [
        Field("var", Variant)
    ]


class VariantTest(unittest.TestCase):

    def test_struct_value_error(self):
        self.assertRaises(ValueError, VariantMessage)

    def test_as_dict(self):
        arr = VariantArray()
        var = VariantDict()
        var.var.x = 88
        var.var.y = 999
        arr.append(var)
        data = [{'var':{'x':88, 'y':999}}]
        self.assertEqual(arr.dumps(), data)

        arr = VariantArray()
        arr.loads(data)
        self.assertEqual(arr[0].var.x, 88)
        self.assertEqual(arr[0].var.y, 999)

    def test_as_array(self):
        arr = VariantArray()
        var = VariantDict()
        var.var.x = 88
        var.var.y = 999
        arr.append([1, 2, 3, var])
        data = [[1, 2, 3, {'var':{'x':88, 'y':999}}]]
        self.assertEqual(arr.dumps(), data)

        arr = VariantArray()
        arr.loads(data)
        self.assertEqual(arr[0][3].var.x, 88)
        self.assertEqual(arr[0][3].var.y, 999)

    def test_as_basic(self):
        arr = VariantArray()
        arr.append(7)
        arr.append(True)
        self.assertEqual(arr.dumps(), [7, True])
        arr.loads([7, True])
        self.assertEqual(arr[0], 7)
        self.assertEqual(arr[1], True)

    def test_as_raw(self):
        arr = VariantArray()
        arr.append({'x': 'xxx'})
        self.assertEqual(arr[0].x, 'xxx')

    def test_interpeter_dict(self):
        l = [
         {
            'id':1,
            'str':'xxx'
          },
          {
            'id':2,
            'num':999
           },
           {
            'id':3,
            'flag': False
            },

         ]

        arr = VariantArray()
        arr.loads(l)
        self.assertEqual(type(arr[0]), Variant)
        objs = []
        typemap = {1:Variant1, 2:Variant2, 3:Variant3}
        for it in arr:
            objs.append(Variant.interpret(it, typemap[it.id]))
        self.assertEqual(objs[0].data, 'data_xxx')
        self.assertEqual(objs[1].data, 'data_999')
        self.assertEqual(objs[2].data, 'data_False')

    def test_interpeter_basetype(self):
        l = [1, True, "xx"]
        arr = VariantArray()
        arr.loads(l)

        class VInt(Message):
            _struct_ = Int32

        class VBool(Message):
            _struct_ = Bool

        class VStr(Message):
            _struct_ = String

        msg = Variant.interpret(arr[0], VInt)
        self.assertEqual(msg.value, 1)

        msg = Variant.interpret(arr[1], VBool)
        self.assertEqual(msg.value, True)

        msg = Variant.interpret(arr[2], VStr)
        self.assertEqual(msg.value, "xx")

    def test_interpeter_array(self):
        d = VariantDict()
        d.var.x = [1, 2]

        class VArray(Message):
            _struct_ = Array(Int32)

        msg = Variant.interpret(d.var.x, VArray)
        self.assertEqual(msg[0], 1)
        self.assertEqual(msg[1], 2)


class FastMsg(Message):
    _struct_ = [
        Field("name", String),
        Field("id", Int32)
    ]


class FastNum(Message):
    _struct_ = Uint32


class FastArr(Message):
    _struct_ = Array(Int32)


class FastCreateTest(unittest.TestCase):

    def test_fast_create(self):
        msg = FastMsg("xxx", 90)
        self.assertEqual(msg.name, "xxx")
        self.assertEqual(msg.id, 90)

        self.assertRaises(TypeError, FastMsg, "77")

        msg = FastMsg(name="xxx", id=90)
        self.assertEqual(msg.name, "xxx")
        self.assertEqual(msg.id, 90)

    def test_fast_create_num(self):
        msg = FastNum(888)
        self.assertEqual(msg.value, 888)

    def test_fast_create_array(self):
        msg = FastArr([6, 7, 8, 8])
        self.assertEqual(msg[0], 6)
        self.assertEqual(msg[1], 7)
        self.assertEqual(msg[2], 8)
        self.assertEqual(msg[3], 8)


class DType1(Message):
    _struct_ = [
        Field("name", Map(Int32, String)),
        Field("arr", Array(Int32)),
    ]


class DType2(Message):
    _struct_ = [
        Field("name", Map(Int32, String)),
        Field("arr", Array(Int32)),
    ]


class DynamicTypeAssignTest(unittest.TestCase):

    def test_map_assign(self):
        m1 = DType1()
        m = {
        1:"XXXX",
        2:"ZZZZ"
        }
        m1.name = m

        m2 = DType2()
        m2.name = m1.name

        self.assertEqual(m2.name, m1.name)
        self.assertEqual(m1.name[1], m2.name[1])
        self.assertEqual(m2.name, m)

    def test_list_assign(self):
        m1 = DType1()
        l = [1, 2, 3]
        m1.arr = l

        m2 = DType2()
        m2.arr = m1.arr

        self.assertEquals(m1.arr, m2.arr)
        self.assertEqual(m2.arr, l)


class BItem(Message):
    _struct_ = [
        Field("foo", Uint32),
    ]


class BArrayRefSize(Message):
    _struct_ = [
        Field("size", Uint32),
        Field("arr", Array(BItem), size_ref="size")
    ]


class BArrayFixSize(Message):
    _struct_ = [
        Field("arr", Array(BItem), array_size=3)
    ]


class BArrayFixSize0(Message):
    _struct_ = [
        Field("arr", Array(BItem), array_size=0)
    ]


class BinaryArraySizeTest(unittest.TestCase):

    def test_size_ref(self):
        s = BArrayRefSize()
        s.size = 3
        item = s.arr.add()
        item.foo = 1
        item = s.arr.add()
        item.foo = 2
        item = s.arr.add()
        item.foo = 3
        buf = s.dumps(BinarySerializer())
        s2 = BArrayRefSize()
        s2.loads(buf, BinarySerializer())
        self.assertEqual(s.dumps(), s2.dumps())

    def test_fix_size(self):
        s = BArrayFixSize()
        item1 = BItem()
        item1.foo = 1
        item2 = BItem()
        item2.foo = 2
        item3 = BItem()
        item3.foo = 3
        s.arr = [item1, item2, item3]
        buf = s.dumps(BinarySerializer())
        s2 = BArrayFixSize()
        s2.loads(buf, BinarySerializer())
        self.assertEqual(s.dumps(), s2.dumps())

    def test_fix_size_0(self):
        s = BArrayFixSize0()
        item1 = BItem()
        item1.foo = 1
        item2 = BItem()
        item2.foo = 2
        s.arr = [item1, item2]
        buf = s.dumps(BinarySerializer())
        s2 = BArrayFixSize0()
        s2.loads(buf, BinarySerializer())
        self.assertEqual(s.dumps(), s2.dumps())


if __name__ == "__main__":
#     unittest.main(defaultTest="OptionTest.test_normal")
    unittest.main()
