# -*- coding: utf-8 -*-
'''
消息定义模块
'''

import fnmatch
import json
import pprint
import types

from collections import OrderedDict
from testbase.util import Singleton
from qt4s.message.utils import field_size_of, size_of


class GlobalIndent(object):
    __metaclass__ = Singleton

    def __init__(self):
        self._indent = -1

    @property
    def indent(self):
        return self._indent

    @indent.setter
    def indent(self, val):
        self._indent = val


class OrderedDictEx(OrderedDict):
    __indent = 0

    def __repr__(self, _repr_running={}):
        GlobalIndent().indent += 1
        _indent_str = GlobalIndent().indent * "    "
        # _str="%s{\n" % _indent_str
        _str = "{\n"
        for key in self.keys():
            _str += "    %s%s: %s\n" % (_indent_str, key, self.get(key))
        if GlobalIndent().indent > 0:
            _str += _indent_str + "    }"
        else:
            _str += _indent_str + "}"
        GlobalIndent().indent -= 1
        return _str


class _UninitializedType(object):
    '''表示未初始化值类型
    '''

    def __eq__(self, obj):
        return type(obj) == type(self)

    def __repr__(self):
        return '<Uninitialized>'


Uninitialized = _UninitializedType()


class StructTypeBase(object):
    '''结构类型基类
    '''
    _msgclass = None

    def __init__(self, params, message):
        '''确保StructTypeBase的子类不被用户直接实例化并使用
        框架实例化其子类时，都会在params参数中增加params['sugar']='sugar'，而用户直接使用则不会有这个参数
        '''
        sugar = params.get('__sugar', None)
        if sugar != 'sugar':
            raise Exception('create instance "%s" type is not allowed' % type(self).__name__)
        self.__msg = message

    @classmethod
    def set_message_class(cls, message_class):
        '''设置对应的消息类型
        '''
        cls._msgclass = message_class

    @classmethod
    def create(cls, params):
        '''创建实例
        '''
        if cls._msgclass:
            msg = cls._msgclass(__params=params)
            return msg.get_struct()
        else:
            return cls(params, None)

    def get_message(self):
        '''获取对应的消息对象
        '''
        return self.__msg

    def from_assignment(self, value, field=None):
        '''作为组合结构类型的成员时，对象接受赋值时调用此函数对赋值进行处理，再存储
        '''
        pass

    def to_use(self):
        '''作为组合结构类型的成员时，查询对象成员时调用此函数进行处理，再返回给用户使用
        '''
        pass

    def construct(self, value, field=None):
        '''从Python基本类型构造
        '''
        pass

    def reduce(self, allow_uninit_field=False):
        '''退化为Python基本类型
        '''
        pass

    def need_reduce(self):
        '''作为组合结构类型的成员时，控制是否需要将成员reduce的结果加入到Dict中
        '''
        return True

    def dumps(self, serializer=None):
        '''序列化
        '''
        from qt4s.message.serializers.python import PythonSerializer
        serializer = serializer or PythonSerializer()
        data = self.reduce()
        return serializer.dumps(type(self), data)

    def loads(self, value, deserializer=None):
        '''反序列化
        '''
        if deserializer:
            data, remain = deserializer.loads(type(self), value)
        else:
            data = value
            remain = None
        self.construct(data)
        return remain

    def __eq__(self, other):
        if not type(self) == type(other):
            return False

        return self.to_use() == other.to_use()


class Null(StructTypeBase):
    '''空类型
    '''

    def __init__(self):
        super(Null, self).__init__({'__sugar':'sugar'}, None)

    def from_assignment(self, value, field=None):
        '''作为组合结构类型的成员时，对象接受赋值时调用此函数对赋值进行处理
        '''
        if value != None:
            raise ValueError('only none is allowed')

    def to_use(self, allow_uninit_field=False):
        '''作为组合结构类型的成员时，查询对象成员时调用此函数进行处理
        '''
        return None

    construct = from_assignment
    reduce = to_use

    def __repr__(self):
        return repr(None)


class Number(StructTypeBase):
    '''数值（包括整数型和浮点数）
    '''

    def __init__(self, params, message):
        self._value = Uninitialized
        super(Number, self).__init__(params, message)

    def _check_type(self, value, field=None):
        '''检查赋值类型
        '''
        raise NotImplementedError()

    def from_assignment(self, value, field=None):
        '''作为组合结构类型的成员时，对象接受赋值时调用此函数对赋值进行处理
        '''
        self._check_type(value, field)
        self._value = value

    def to_use(self, allow_uninit_field=False):
        '''作为组合结构类型的成员时，查询对象成员时调用此函数进行处理
        '''
        if self._value == Uninitialized:
            raise ValueError("access uninitialized value")
        return self._value

    construct = from_assignment
    reduce = to_use

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, str(self._value))

    def __eq__(self, obj):
        return type(self) == type(obj) and self._value == obj._value


class Float(Number):
    '''浮点数类型
    '''

    def _check_type(self, value, field=None):
        '''检查赋值类型
        '''

        try:
            value = float(value)
        except:
            excs = 'required a float type instance, not %s' % str(type(value).__name__)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)


class Double(Float):
    '''双浮点数类型
    '''
    pass


class Integer(Number):
    '''整型数
    '''

    def _check_type(self, value, field=None):
        '''检查赋值类型
        '''
        value_type = type(value)
        if value_type != types.IntType and value_type != types.LongType:
            excs = 'required a int type instance, not %s' % str(value_type.__name__)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)
        self._check_range(value, field)

    def _check_range(self, value, field=None):
        '''检查取值范围
        '''
        raise NotImplementedError()


class Int8(Integer):
    '''8位有符号整型数
    '''
    MAX = int(2 ** 7 - 1)
    MIN = int(-2 ** 7)

    def _check_range(self, value, field=None):
        '''检查取值范围
        '''
        if value > Int8.MAX or value < Int8.MIN:
            excs = 'value %d not in the range [%d, %d]' % (value, Int8.MIN, Int8.MAX)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)


class Uint8(Integer):
    '''8位无符号整型数
    '''
    MAX = int(2 ** 8)
    MIN = 0

    def _check_range(self, value, field=None):
        '''检查取值范围
        '''
        if value < 0:
            value = 0x100 + value
        if value > Uint8.MAX or value < Uint8.MIN:
            excs = 'value %d not in the range [%d, %d]' % (value, Uint8.MIN, Uint8.MAX)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)


class Int16(Integer):
    '''16位有符号整型数
    '''
    MAX = int(2 ** 15 - 1)
    MIN = int(-2 ** 15)

    def _check_range(self, value, field=None):
        '''检查取值范围
        '''
        if value > Int16.MAX or value < Int16.MIN:
            excs = 'value %d not in the range [%d, %d]' % (value, Int16.MIN, Int16.MAX)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)


class Uint16(Integer):
    '''16位无符号整型数
    '''
    MAX = int(2 ** 16)
    MIN = 0

    def _check_range(self, value, field=None):
        '''检查取值范围
        '''
        if value > Uint16.MAX or value < Uint16.MIN:
            excs = 'value %d not in the range [%d, %d]' % (value, Uint32.MIN, Uint32.MAX)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)


class Int32(Integer):
    '''32位有符号整型数
    '''
    MAX = int(2 ** 31 - 1)
    MIN = int(-2 ** 31)

    def _check_range(self, value, field=None):
        '''检查取值范围
        '''
        if value > Int32.MAX or value < Int32.MIN:
            excs = 'value %d not in the range [%d, %d]' % (value, Int32.MIN, Int32.MAX)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)


class Uint32(Integer):
    '''32位无符号整型数
    '''
    MAX = int(2 ** 32)
    MIN = 0

    def _check_range(self, value, field=None):
        '''检查取值范围
        '''
        if value > Uint32.MAX or value < Uint32.MIN:
            excs = 'value %d not in the range [%d, %d]' % (value, Uint32.MIN, Uint32.MAX)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)


class Long(Number):
    '''整型数
    '''

    def _check_type(self, value, field=None):
        '''检查赋值类型
        '''
        value_type = type(value)
        if  value_type not in [ types.LongType, types.IntType]:
            excs = 'required a long type instance, not %s' % str(value_type.__name__)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)

    def _check_range(self, value, field=None):
        '''检查取值范围
        '''
        raise NotImplementedError()


class Int64(Long):
    '''64位有符号整型数
    '''
    MAX = int(2 ** 63 - 1)
    MIN = int(-2 ** 63)

    def _check_range(self, value, field=None):
        '''检查取值范围
        '''
        if value > Int64.MAX or value < Int64.MIN:
            excs = 'value %d not in the range [%d, %d]' % (value, Int64.MIN, Int64.MAX)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)


class Uint64(Long):
    '''64位无符号整型数
    '''
    MAX = int(2 ** 64)
    MIN = 0

    def _check_range(self, value, field=None):
        '''检查取值范围
        '''
        if value > Uint64.MAX or value < Uint64.MIN:
            excs = 'value %d not in the range [%d, %d]' % (value, Uint64.MIN, Uint64.MAX)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)


class String(StructTypeBase):
    '''字符串类型
    '''

    def __init__(self, params, message):
        self._value = Uninitialized
        self._encoding = params.get('encoding', 'utf8')
        self._as_buffer = params.get('buffer', False)
        self._byte_size = params.get('byte_size', None)
        super(String, self).__init__(params, message)

    def _check_and_process_type(self, value, field=None):
        '''检查赋值类型
        '''
        value_type = type(value)
        if isinstance(value, types.UnicodeType):
            if self._as_buffer:
                try:
                    value = str(value)
                except:
                    excs = 'required a string instance, not %s' % str(value_type.__name__)
                    if field:
                        excs = 'field "%s" %s' % (field.name, excs)
                    raise ValueError(excs)
            else:
                if self._encoding != 'unicode':
                    value = value.encode(self._encoding)

        elif isinstance(value, types.StringType):
            if not self._as_buffer:
                if self._encoding != 'unicode':
                    try:
                        value = value.decode(self._encoding)
                    except UnicodeDecodeError:
                        try:
                            value = value.decode('utf8')
                        except UnicodeDecodeError:  # 有些协议会用str类型存放二进制数据，这里的编码只能是尽力而为
                            pass
                else:
                    try:
                        value = value.decode('utf8')
                    except UnicodeDecodeError:  # 有些协议会用str类型存放二进制数据，这里的编码只能是尽力而为
                        pass
        else:
            try:
                value = str(value)
            except:
                excs = 'required a string instance, not %s' % str(value_type.__name__)
                if field:
                    excs = 'field "%s" %s' % (field.name, excs)
                raise ValueError(excs)
        return value

    def from_assignment(self, value, field=None):
        '''作为组合结构类型的成员时，对象接受赋值时调用此函数对赋值进行处理
        '''
        value = self._check_and_process_type(value, field)
        if self._byte_size and len(value) > self._byte_size:
            raise ValueError("assigned buffer size overflow")
        self._value = value

    def to_use(self):
        '''作为组合结构类型的成员时，查询对象成员时调用此函数进行处理
        '''
        if self._value == Uninitialized:
            raise ValueError("access uninitialized value")
        if self._encoding == 'unicode' or self._as_buffer:
            return self._value
        else:
            try:
                return self._value.encode(self._encoding)
            except UnicodeDecodeError:
                return self._value

    construct = from_assignment

    def reduce(self, allow_uninit_field=False):
        value = self.to_use()
        if self._byte_size and len(value) < self._byte_size:
            value += '\x00' * (self._byte_size - len(value))
        return value

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, str(self._value))

    def __eq__(self, obj):
        return type(self) == type(obj) and self._value == obj._value


class Buffer(String):
    '''缓冲区类型
    '''

    def __init__(self, params, message):
        params['buffer'] = True
        super(Buffer, self).__init__(params, message)


class Bool(StructTypeBase):
    '''布尔类型
    '''

    def __init__(self, params, message):
        self._value = Uninitialized
        super(Bool, self).__init__(params, message)

    def _check_type(self, value, field=None):
        '''检查赋值类型
        '''
        value_type = type(value)
        if value_type != types.BooleanType:
            excs = 'required a boolean instance, not %s' % str(value_type.__name__)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)

    def from_assignment(self, value, field=None):
        '''作为组合结构类型的成员时，对象接受赋值时调用此函数对赋值进行处理
        '''
        self._check_type(value, field)
        self._value = value

    def to_use(self, allow_uninit_field=False):
        '''作为组合结构类型的成员时，查询对象成员时调用此函数进行处理
        '''
        if self._value == Uninitialized:
            raise ValueError("access uninitialized value")
        return self._value

    construct = from_assignment
    reduce = to_use

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, str(self._value))

    def __eq__(self, obj):
        return type(self) == type(obj) and self._value == obj._value


class CompositeType(StructTypeBase):
    '''组合类型，如数组、字典等
    '''
    pass


class ArrayBase(CompositeType):
    '''数组类型基类
    '''

    def __init__(self, params, message):
        self._dlist = []
        self._child_params = params.get('child_config', {})
        self._child_params['__sugar'] = 'sugar'
        self._arr_size = params.get('array_size', None)
        super(ArrayBase, self).__init__(params, message)

    def _check_and_process_type(self, listvalue, field=None):
        '''检查赋值类型
        '''
        if listvalue is None:
            listvalue = []
        value_type = type(listvalue)
        if value_type != types.ListType and value_type != type(self):
            excs = 'required list type, not %s' % str(value_type.__name__)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)
        if self._arr_size:
            if len(listvalue) > self._arr_size:
                raise ValueError("list size overflow")
            delta = self._arr_size - len(listvalue)
            if delta:
                raise Exception("to do")
        dlist = []
        for it in listvalue:
            dlist.append(self._process_elements_while_assignment(it, self._child_params))
        return dlist

    def _process_elements_while_assignment(self, listvalue, child_config):
        '''处理元素
        '''
        raise NotImplementedError()

    def from_assignment(self, value, field=None):
        '''作为组合结构类型的成员时，对象接受赋值时调用此函数对赋值进行处理
        '''
        if isinstance(value, Message) and isinstance(value.get_struct(), type(self)):
            self._dlist = value.get_struct()._dlist
        elif isinstance(value, type(self)):
            self._dlist = value._dlist
        else:
            self._dlist = self._check_and_process_type(value, field)

    def to_use(self):
        '''作为组合结构类型的成员时，查询对象成员时调用此函数进行处理
        '''
        return self

    def _process_elements_while_construct(self, listvalue, child_config):
        '''处理元素
        '''
        raise NotImplementedError()

    def construct(self, listvalue, field=None):
        '''作为组合结构类型的成员时，从字典初始化时调用
        '''
        value_type = type(listvalue)
        if value_type != types.ListType:
            excs = 'required list type, not %s' % str(value_type.__name__)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)

        self._dlist = []
        for it in listvalue:
            self._dlist.append(self._process_elements_while_construct(it, self._child_params))

    def reduce(self, allow_uninit_field=False):
        '''作为组合结构类型的成员时，转换为字典时调用
        '''
        listvalue = []
        for it in self._dlist:
            listvalue.append(it.reduce(allow_uninit_field))
        return listvalue

    def __repr__(self):
        return pprint.pformat(self.dumps())
        # return '%s(%s)'%('Array', str(self._dlist))

    def __len__(self):
        return len(self._dlist)

    def __getitem__(self, idx):
        return self._dlist[idx].to_use()

    def __setitem__(self, idx, obj):
        self._dlist[idx] = self._process_elements_while_assignment(obj, self._child_params)

    def __iter__(self):
        iters = []
        for it in self._dlist:
            iters.append(it.to_use())
        return iters.__iter__()

    def __contains__(self, item):
        for it in self._dlist:
            if it.to_use() == item:
                return True
        else:
            return False

    def __eq__(self, obj):
        if isinstance(obj, ArrayBase):
            return obj._dlist == self._dlist
        elif isinstance(obj, types.ListType):
            to_use = [ it.to_use() for it in self._dlist ]
            return obj == to_use
        else:
            return False

    def append(self, obj):
        if self._arr_size:
            raise RuntimeError("fixed size array could not append")
        self._dlist.append(self._process_elements_while_assignment(obj, self._child_params))

    def add(self):
        if self._arr_size:
            raise RuntimeError("fixed size array could not add")
        obj = self.element_struct.create(None)
        self._dlist.append(obj)
        return obj

    def insert(self, idx, obj):
        if self._arr_size:
            raise RuntimeError("fixed size array could not insert")
        self._dlist.insert(idx, self._process_elements_while_assignment(obj, self._child_params))


def _get_struct_type(datatype):
    '''获取消息类型或结构类型对应的结构类型
    '''
    if issubclass(datatype, Message):
        msg_datatype = datatype
        item_datatype = datatype.get_struct_class()
    else:
        msg_datatype = None
        item_datatype = datatype
    item_datatype.set_message_class(msg_datatype)
    return item_datatype


_array_type_cache = {}


def Array(datatype):
    '''数组类型生成器
    '''

    item_datatype = _get_struct_type(datatype)
    array_type = _array_type_cache.get(item_datatype, None)
    if array_type:
        return array_type

    class _ArrayType(ArrayBase):
        '''生成的类型
        '''
        element_struct = item_datatype

        def _process_elements_while_assignment(self, value, child_config):
            '''处理元素
            '''
            obj = item_datatype.create(child_config)
            obj.from_assignment(value)
            return obj

        def _process_elements_while_construct(self, value, child_config):
            '''处理元素
            '''
            obj = item_datatype.create(child_config)
            obj.construct(value)
            return obj

    _array_type_cache[item_datatype] = _ArrayType
    return _ArrayType


class MapBase(CompositeType):
    '''映射表类型基类
    '''

    def __init__(self, params, message):
        self._ddata = {}
        self._child_params = params.get('child_config', {})
        self._child_params['__sugar'] = 'sugar'
        super(MapBase, self).__init__(params, message)

    def _check_and_process_type(self, dictvalue, field=None):
        '''检查赋值类型
        '''
        value_type = type(dictvalue)
        if value_type != types.DictType:
            excs = 'required dict type, not %s' % str(value_type.__name__)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)
        ddata = {}
        for key in dictvalue:
            key_new = self._process_key_while_assignment(key, self._child_params)
            ddata[key_new] = self._process_value_while_assignment(dictvalue[key], self._child_params)
        return ddata

    def _process_value_while_assignment(self, dictvalue, child_config):
        '''处理元素
        '''
        raise NotImplementedError()

    def _process_key_while_assignment(self, dictvalue, child_config):
        '''处理键值
        '''
        raise NotImplementedError()

    def from_assignment(self, value, field=None):
        '''作为组合结构类型的成员时，对象接受赋值时调用此函数对赋值进行处理
        '''
        if isinstance(value, Message) and isinstance(value.get_struct(), type(self)):
            self._ddata = value.get_struct()._ddata
        elif isinstance(value, type(self)):
            self._ddata = value._ddata
        else:
            self._ddata = self._check_and_process_type(value, field)

    def to_use(self):
        '''作为组合结构类型的成员时，查询对象成员时调用此函数进行处理
        '''
        return self

    def _process_key_while_construct(self, listvalue, child_config):
        '''处理键值
        '''
        raise NotImplementedError()

    def _process_value_while_construct(self, listvalue, child_config):
        '''处理元素
        '''
        raise NotImplementedError()

    def construct(self, dictvalue, field=None):
        '''作为组合结构类型的成员时，从字典初始化时调用
        '''
        value_type = type(dictvalue)
        if value_type != types.DictType:
            excs = 'required dict type, not %s' % str(value_type.__name__)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)

        self._ddata = {}
        for key in dictvalue:
            key_new = self._process_key_while_construct(key, self._child_params)
            self._ddata[key_new] = self._process_value_while_construct(dictvalue[key], self._child_params)

    def reduce(self, allow_uninit_field=False):
        '''作为组合结构类型的成员时，转换为字典时调用
        '''
        dictvalue = {}
        for key in self._ddata:
            dictvalue[key.reduce(allow_uninit_field)] = self._ddata[key].reduce(allow_uninit_field)
        return dictvalue

    def __repr__(self):
        return pprint.pformat(self.dumps())
        # return '%s(%s)'%('Map', str(self._ddata))

    def __len__(self):
        return len(self._ddata)

    def __getitem__(self, key):
        k = self._process_key_while_assignment(key, self._child_params)
        for it in self._ddata:
            if it == k:
                return self._ddata[it].to_use()
        raise KeyError("%s not found" % str(key))

    def __setitem__(self, key, obj):
        self._ddata[self._process_key_while_assignment(key, self._child_params)] = self._process_value_while_assignment(obj, self._child_params)

    def __iter__(self):
        iters = []
        for it in self._ddata:
            iters.append(it.to_use())
        return iters.__iter__()

    def __contains__(self, item):
        for it in self._ddata:
            if it.to_use() == item:
                return True
        else:
            return False

    def __eq__(self, obj):
        if type(self) == type(obj):
            return self._ddata.items() == obj._ddata.items()
        elif isinstance(obj, types.DictType):
            to_use = {}
            for it in self._ddata:
                to_use[it.to_use()] = self._ddata[it].to_use()
            return to_use == obj
        else:
            return False

    def keys(self):
        '''返回全部键
        '''
        keys = []
        for it in self._ddata:
            keys.append(it.to_use())
        return keys

    def get(self, key):
        '''获取对应的键值
        '''
        k = self._process_key_while_assignment(key, self._child_params)
        for it in self._ddata:
            if it == k:
                return self._ddata[it].to_use()

    def has_key(self, key):
        '''是否存在键
        '''
        k = self._process_key_while_assignment(key, self._child_params)
        for it in self._ddata:
            if it == k:
                return True
        return False


_map_type_cache = {}


def Map(ktype, vtype):
    '''映射表类型
    '''

    kdatatype = _get_struct_type(ktype)
    vdatatype = _get_struct_type(vtype)
    map_type = _map_type_cache.get((kdatatype, vdatatype), None)
    if map_type:
        return map_type

    class _MapType(MapBase):
        '''生成的类型
        '''
        key_struct = kdatatype
        value_struct = vdatatype

        def _process_key_while_construct(self, value, child_config):
            '''处理键值
            '''
            obj = kdatatype.create(child_config)
            obj.construct(value)
            return obj

        def _process_value_while_construct(self, value, child_config):
            '''处理元素
            '''
            obj = vdatatype.create(child_config)
            obj.construct(value)
            return obj

        def _process_key_while_assignment(self, value, child_config):
            '''处理键值
            '''
            obj = kdatatype.create(child_config)
            obj.from_assignment(value)
            return obj

        def _process_value_while_assignment(self, value, child_config):
            '''处理元素
            '''
            obj = vdatatype.create(child_config)
            obj.from_assignment(value)

            return obj

    _map_type_cache[(kdatatype, vdatatype)] = _MapType
    return _MapType


class Tuple(CompositeType):
    """
    """

    def __init__(self, params, message):
        self._tuple_data = {}
        self._child_params = params.get('child_config', {})
        self._child_params['__sugar'] = 'sugar'
        super(Tuple, self).__init__(params, message)

    def from_assignment(self, value, field=None):
        '''作为组合结构类型的成员时，对象接受赋值时调用此函数对赋值进行处理，再存储
        '''
        if not isinstance(value, tuple):
            raise ValueError("assign to Tuple field must be tuple object")
        self._tuple_data = value

    def to_use(self):
        '''作为组合结构类型的成员时，查询对象成员时调用此函数进行处理，再返回给用户使用
        '''
        return self._tuple_data

    def construct(self, value, field=None):
        '''从Python基本类型构造
        '''
        self.from_assignment(value, field)

    def reduce(self, allow_uninit_field=False):
        '''退化为Python基本类型
        '''
        return self.to_use()

    def need_reduce(self):
        '''作为组合结构类型的成员时，控制是否需要将成员reduce的结果加入到Dict中
        '''
        return False


class Field(object):
    '''字典类型的字段定义
    '''

    def __init__(self, name, datatype, **config):
        '''构造函数
        :param name: 域名
        :param datatype: 结构类型
        :type name: string
        :type datatype: type
        :param config: 扩展配置，有如下的扩展配置
            - default: 默认值，但对应的域没有赋值时，且不是optional, 序列化时使用这个默认值；
                                                            当反序列化时，如果缺少这个域，且不是optional, 则使用默认值
            - optional: 可选域，默认为False，如果为真，当序列化或反序列化时缺少这个域值时不会导致异常
            - allow_none: 是否允许使用None对域赋值，默认为False，如果为真，允许赋值为None
            - display: 域的展示名称，当定义这个配置时，访问该域需要使用display指定的名称，不影响序列化和反序列化的结果
            - encoding: 字符编码，只有当为String类型的域才有效
            - size_ref: 当前字段序列化后的长度参考字段
            - size_ref_hook: 序列化后长度处理函数，对于当前字段，处理后得到参考字段的值；对于参考字段，处理后得到被参考字段的二进制长度
            - serializer: 序列化当前字段使用的序列化器对象
        '''
        self.name = name
        if type(datatype) == types.ListType or type(datatype) == types.TupleType:
            fields = datatype
            msgtype = type('AnonymousMessage_%s' % name, (Message,), {'_struct_': fields})
            datatype = msgtype.get_struct_class()
        elif issubclass(datatype, Message):
            msgtype = datatype
            datatype = datatype.get_struct_class()
        else:
            msgtype = None
        self.type = datatype
        if issubclass(datatype, StructTypeBase):
            self.type.set_message_class(msgtype)
        if "default" in config:
            self.has_default = True
            self.default = config['default']
        else:
            self.has_default = False
        self.required = not (config.get('optional', False))
        self.display = config.get('display', self.name)
        self.allow_none = config.get('allow_none', False)
        self.params = config
        self.params['__sugar'] = 'sugar'

    def __repr__(self):
        return '<Field "%s" object at 0x%08X>' % (self.name, id(self))


class BaseClassIterator(object):
    '''基类遍历
    '''

    def __init__(self, cls):
        self._cls = cls
        self._bases = []
        self._iter_class(cls)

    def _iter_class(self, cls):
        '''遍历基类
        '''
        for it in cls.__bases__:
            if it in self._bases:
                raise RuntimeError('cyclic inheritance')
            self._iter_class(it)
            self._bases.append(it)

    def __iter__(self):
        '''遍历接口
        '''
        return self._bases.__iter__()


class Dict(CompositeType):
    '''字典类型
    '''

    def __init__(self, params, message):
        self.__ddict = {}
        self.__has_assign = False
        super(Dict, self).__init__(params, message)

    @classmethod
    def get_fields(cls):
        '''获取定义的域列表
        '''
        fields = []
        for it in cls.__bases__:
            if issubclass(it, Dict) and it != Dict:
                if it._fields_ is cls._fields_:
                    continue
                fields += it.get_fields()
        fields += cls._fields_
        return fields

    def _get_fields(self):
        '''获取定义的域列表
        '''
        return type(self).get_fields()

    def _init_fields(self, args, kwargs):
        '''初始化
        '''
        if args:
            if kwargs:
                raise ValueError('ignored arguments %s' % str(kwargs))
            fields = self._get_fields()
            if len(args) != len(fields):
                msgclass = type(self.get_message()).__name__
                raise TypeError('%s take %d argument (%d given)' % (msgclass, len(fields), len(args)))
            for idx, field in enumerate(fields):
                setattr(self, field.name, args[idx])
        elif kwargs:
            for it in kwargs:
                if it[0:2] == '__':
                    continue
                setattr(self, it, kwargs[it])

    def from_assignment(self, value, field=None):
        '''作为组合结构类型的成员时，对象接受赋值时调用此函数对赋值进行处理，再存储
        '''
        if isinstance(value, Message) and isinstance(value.get_struct(), type(self)):
            self.__ddict = value.get_struct().__ddict
        elif isinstance(value, Dict):
            self.__ddict = value.__ddict
        elif isinstance(value, dict):
            self.loads(value)
        else:
            value_type = type(value)
            excs = 'required a %s instance, not %s' % (type(self.get_message()).__name__, value_type.__name__)
            if field:
                excs = 'field "%s" %s' % (field.name, excs)
            raise ValueError(excs)
        self.__has_assign = True

    def to_use(self):
        '''作为组合结构类型的成员时，查询对象成员时调用此函数进行处理，再返回给用户使用
        '''
        return self.get_message()

    def construct(self, dict_data, field=None):
        '''从Python基本类型构造
        '''
        d = dict_data.copy()
        for field in self._get_fields():
            try:
                value = d[field.name]
                del d[field.name]
            except KeyError:
                if not field.has_default:
                    if field.required:
                        raise ValueError('loss field "%s" of "%s"' % (field.name, type(self.get_message()).__name__))
            else:
                if value is None and field.allow_none:
                    self.__ddict[field.name] = Null()
                else:
                    if issubclass(field.type, StructTypeBase):
                        obj = field.type.create(field.params)
                        obj.construct(value, field)
                    else:
                        obj = value
                    self.__ddict[field.name] = obj
        if d:
            raise ValueError('contain unknown field: %s' % str(d))

    def reduce(self, allow_uninit_field=False):
        '''退化为Python基本类型
        '''
        d = OrderedDictEx()
        for field in self._get_fields():
            value = self.__ddict.get(field.name, None)
            if value is None:
                if field.required:
                    if field.has_default:
                        obj = field.type.create(field.params)
                        obj.from_assignment(field.default, field)
                        d[field.name] = obj.to_use()
                    elif issubclass(field.type, ArrayBase):
                        d[field.name] = []
                    else:
                        if allow_uninit_field:
                            d[field.name] = Uninitialized
                        else:
                            raise ValueError('required field "%s" of "%s" is not set' % (field.name, type(self.get_message()).__name__))
            else:
                if isinstance(value, StructTypeBase):
                    if value.need_reduce():
                        d[field.name] = value.reduce(allow_uninit_field)
                else:
                    d[field.name] = value
        return d

    def need_reduce(self):
        '''作为组合结构类型的成员时，控制是否需要将成员reduce的结果加入到Dict中
        '''
        if self.__has_assign:
            return True
        return len(self.__ddict) > 0

    def __setattr__(self, name, value):
        '''设置成员属性
        '''
        if name[0:7] == '_Dict__' or name[0:17] == '_StructTypeBase__':
            super(Dict, self).__setattr__(name, value)
        else:
            for field in self._get_fields():
                if field.name == name or field.display == name:
                    if value == Uninitialized:
                        return
                    if value is None and field.allow_none:
                        self.__ddict[field.name] = Null()
                    else:
                        if issubclass(field.type, StructTypeBase):
                            obj = field.type.create(field.params)
                            obj.from_assignment(value, field)
                        else:
                            obj = value
                        self.__ddict[field.name] = obj
                    return
            raise TypeError('assign unknown field: %s' % name)

    def __getattribute__(self, name):
        '''查询成员属性
        '''
        try:
            return super(Dict, self).__getattribute__(name)
        except AttributeError:
            for field in self._get_fields():
                if field.name == name or field.display == name:
                    obj = self.__ddict.get(field.name, None)
                    if obj is None:
                        if issubclass(field.type, StructTypeBase):
                            if issubclass(field.type, CompositeType):
                                obj = field.type.create(field.params)
                                self.__ddict[field.name] = obj
                            elif field.has_default:
                                obj = field.type.create(field.params)
                                obj.from_assignment(field.default, field)
                            else:
                                raise AttributeError("access uninitialized field '%s' of '%s'" % (field.name, type(self.get_message()).__name__))
                        else:
                            obj = field.type()
                            self.__ddict[field.name] = obj
                    if isinstance(obj, StructTypeBase):
                        return obj.to_use()
                    else:
                        return obj
            else:
                raise AttributeError('query unknown field: %s' % name)

    def __eq__(self, obj):
        if type(self) != type(obj):
            return False
        for field in self._get_fields():
            if issubclass(field.type, CompositeType):
                if getattr(self, field.name).reduce() != getattr(obj, field.name).reduce():
                    return False
            else:
                if getattr(self, field.name) != getattr(obj, field.name):
                    return False
        return True

    def __repr__(self):
        return pretty_print(self)


class Variant(CompositeType):
    '''可变结构类型
    '''

    def __init__(self, params, message):
        self.__data = {}
        self.__params = params
        super(Variant, self).__init__(params, message)

    def __repr__(self):
        return repr(self.__data)

    def _is_supported_base_type(self, t):
        '''是否是支持的基本类型
        '''
        return t in [
                types.IntType, types.LongType, types.FloatType,
                types.BooleanType,
                types.StringType, types.UnicodeType,
                types.NoneType
            ]

    def _from_assignment_dict(self, dictvalue):
        '''赋值时处理字典类型
        '''
        d = {}
        for name in dictvalue:
            value = dictvalue[name]
            datatype = type(value)
            if issubclass(datatype, Message):
                d[name] = value
            elif datatype == Variant:
                d[name] = value
            elif datatype == types.ListType or datatype == types.TupleType:
                d[name] = self._from_assignment_list(value)
            elif datatype == types.DictType:
                d[name] = self._from_assignment_dict(value)
            elif self._is_supported_base_type(datatype):
                d[name] = value
        return d

    def _from_assignment_list(self, listvalue):
        '''赋值时处理列表类型
        '''
        l = []
        for value in listvalue:
            datatype = type(value)
            if issubclass(datatype, Message):
                l.append(value)
            elif datatype == Variant:
                l.append(value)
            elif datatype == types.ListType or datatype == types.TupleType:
                l.append(self._from_assignment_list(value))
            elif datatype == types.DictType:
                l.append(self._from_assignment_dict(value))
            elif self._is_supported_base_type(datatype):
                l.append(value)
            elif datatype == Variant:
                l.append(value.__data)
            else:
                raise ValueError('assign unsupported type "%s"' % datatype.__name__)
        return l

    def from_assignment(self, value, field=None):
        '''作为组合结构类型的成员时，对象接受赋值时调用此函数对赋值进行处理
        '''
        datatype = type(value)
        if issubclass(datatype, Message):
            self.__data = value
        elif datatype == Variant:
            self.__data = value.__data
        elif datatype == types.ListType or datatype == types.TupleType:
            self.__data = self._from_assignment_list(value)
        elif datatype == types.DictType:
            self.__data = self._from_assignment_dict(value)
        elif self._is_supported_base_type(datatype):
            self.__data = value
        else:
            raise ValueError('assign unsupported type "%s"' % datatype.__name__)

    def to_use(self):
        '''作为组合结构类型的成员时，查询对象成员时调用此函数进行处理
        '''
        if type(self.__data) == types.DictType:
            return self
        else:
            return self.__data

    def _construct_list(self, listdata):
        '''从列表构造
        '''
        l = []
        for it in listdata:
            if self._is_supported_base_type(type(it)):
                l.append(it)
            elif type(it) == types.DictType:
                l.append(self._construct_variant(it))
            elif type(it) == types.ListType or type(it) == types.TupleType:
                l.append(self._construct_list(it))
            else:
                raise ValueError('list contain an unsupported type "%s"' % type(it).__name__)
        return l

    def _construct_dict(self, dictdata):
        '''从字典构造
        '''
        ddict = {}
        for name in dictdata:
            obj = dictdata[name]
            if self._is_supported_base_type(type(obj)):
                ddict[name] = obj
            elif type(obj) == types.DictType:
                ddict[name] = self._construct_variant(obj)
            elif type(obj) == types.ListType or type(obj) == types.TupleType:
                ddict[name] = self._construct_list(obj)
            else:
                raise ValueError('dict contain an unsupported type "%s"' % type(obj).__name__)
        return ddict

    def _construct_variant(self, dictdata):
        '''从字典构造为Variant
        '''
        var = Variant(self.__params, None)
        var.construct(dictdata)
        return var

    def construct(self, data, field=None):
        '''从Python基本类型构造
        '''
        data_type = type(data)
        if data_type == types.DictType:
            self.__data = self._construct_dict(data)
        elif data_type == types.ListType:
            self.__data = self._construct_list(data)
        elif self._is_supported_base_type(data_type):
            self.__data = data
        else:
            raise ValueError('unsupported type "%s"' % data_type.__name__)

    def _reduce_list(self, listdata, allow_uninit_field):
        '''退化为列表
        '''
        l = []
        for it in listdata:
            if type(it) == Variant:
                l.append(it.reduce(allow_uninit_field))
            elif type(it) == types.ListType or type(it) == types.TupleType:
                l.append(self._reduce_list(it))
            elif isinstance(it, Message):
                l.append(it.get_struct().reduce(allow_uninit_field))
            else:
                l.append(it)
        return l

    def _reduce_dict(self, dictdata, allow_uninit_field):
        '''退化为字典
        '''
        d = {}
        for name in dictdata:
            obj = dictdata[name]
            if type(obj) == Variant:
                d[name] = obj.reduce(allow_uninit_field)
            elif type(obj) == types.ListType or type(obj) == types.TupleType:
                d[name] = self._reduce_list(obj, allow_uninit_field)
            elif isinstance(obj, Message):
                d[name] = obj.get_struct().reduce(allow_uninit_field)
            else:
                d[name] = obj
        return d

    def reduce(self, allow_uninit_field=False):
        '''退化为Python基本类型
        '''
        data_type = type(self.__data)
        if data_type == types.DictType:
            return self._reduce_dict(self.__data, allow_uninit_field)
        elif data_type == types.ListType or data_type == types.TupleType:
            return self._reduce_list(self.__data, allow_uninit_field)
        elif issubclass(data_type, Message):
            return self.__data.reduce(allow_uninit_field)
        else:
            return self.__data

    def _assign_process_list(self, listdata):
        l = []
        for it in listdata:
            if type(it) in [
                types.IntType, types.LongType, types.FloatType,
                types.BooleanType,
                types.StringType, types.UnicodeType,
                types.NoneType
            ]:
                l.append(it)
            elif isinstance(it, Message):
                l.append(it.get_struct())
            elif type(it) == types.ListType or type(it) == types.TupleType:
                l.append(self._assign_process_list(it))
            elif type(it) == Variant:
                l.append(it.__data)
            else:
                raise ValueError('list contain an unsupported type "%s"' % type(it).__name__)
        return l

    def __setattr__(self, name, value):
        if name[0:10] == '_Variant__' or name[0:17] == '_StructTypeBase__':
            super(Variant, self).__setattr__(name, value)
        else:
            if type(value) in [
                types.IntType, types.LongType, types.FloatType,
                types.BooleanType,
                types.StringType, types.UnicodeType,
                types.NoneType
            ]:
                self.__data[name] = value
            elif isinstance(value, Message):
                self.__data[name] = value.get_struct()
            elif type(value) == types.ListType or type(value) == types.TupleType:
                self.__data[name] = self._assign_process_list(value)
            elif type(value) == Variant:
                self.__data[name] = value.__data
            else:
                raise ValueError('assign field with an unsupported type "%s"' % type(value).__name__)

    def __getattribute__(self, name):
        '''查询成员属性
        '''
        try:
            return super(Variant, self).__getattribute__(name)
        except AttributeError:
            value = self.__data.get(name, Uninitialized)
            if value == Uninitialized:
                raise ValueError("access uninitialized field '%s' of '%s'" % (name, type(self).__name__))
            return value

    def __getitem__(self, *args, **kwargs):
        if hasattr(self.__data, "__getitem__"):
            return self.__data.__getitem(*args, **kwargs)
        else:
            raise TypeError("Vairant type=%s does not support indexing" % type(self.__data))

    @staticmethod
    def _interpret_list(listobj):
        listdata = []
        for it in listobj:
            if isinstance(it, Message) or isinstance(it, Variant):
                listdata.append(it.reduce())
            elif type(it) == types.ListType or type(it) == types.TupleType:
                listdata.append(Variant._interpret_list(it))
            else:
                listdata.append(it)
        return listdata

    @staticmethod
    def interpret(variant, message_class):
        '''转换为其他类型
        '''
        varianttype = type(variant)
        if varianttype == Variant:
            msg = message_class()
            msg.construct(variant.reduce())
            return msg
        elif isinstance(variant, Message):
            if varianttype != message_class:
                raise ValueError('invalid interpretation from "%s" to "%s"' % (varianttype.__name__, message_class.__name__))
            else:
                return variant
        elif varianttype == types.ListType or varianttype == types.TupleType:
            msg = message_class()
            msg.construct(Variant._interpret_list(variant))
            return msg
        else:
            msg = message_class()
            msg.construct(variant)
            return msg


class Message(object):
    '''消息定义接口
    '''
    _serializer_ = None

    def __init__(self, *args, **kwargs):
        '''构造函数
        '''
        params = kwargs.get('__params', None)
        if params is None:
            params = {'__sugar':'sugar'}
        self.__struct = type(self).get_struct_class()(params, self)
        self._init_fields(args, kwargs)

    def _init_fields(self, args, kwargs):
        '''通过Message构造函数参数初始化结构
        '''
        struct_class = type(self).get_struct_class()
        if issubclass(struct_class, Dict):
            self.__struct._init_fields(args, kwargs)
        elif args and issubclass(struct_class, ArrayBase):
            if len(args) != 1:
                raise ValueError("array struct message only accept a list type instance")
            if type(args[0]) != types.ListType and type(args[0]) != types.TupleType:
                raise ValueError("array struct message only accept list type instance, not %s" % type(args[0]).__name__)
            for it in args[0]:
                self.append(it)
        elif args:
            if len(args) != 1:
                struct_name = struct_class.__name__.lower()
                raise ValueError("%s struct message only accept %s type instance" % (struct_name, struct_name))
            self.value = args[0]

    @classmethod
    def get_struct_class(cls):
        '''获取结构类型
        '''
        struct = cls._struct_
        if type(struct) == types.ListType or type(struct) == types.TupleType:
            # 带域的类型，即Dict
            # 获取对应的基类
            base_classes = []
            for it in cls.__bases__:
                if it == Message:
                    continue
                if issubclass(it, Message):
                    base_classes.append(it.get_struct_class())
            if not base_classes:
                base_classes.append(Dict)
            struct_class = type(cls.__name__ + '_Dict', tuple(base_classes), {'_fields_': struct,
                                                                '__module__' : cls.__module__})
            cls._struct_ = struct_class
        else:
            # 不带域的类型，比如String、Array
            struct_class = struct
        if struct_class == Variant:
            raise ValueError('Variant type could not be _struct_')
        struct_class.set_message_class(cls)
        return struct_class

    def get_struct(self):
        '''获取结构
        '''
        return self.__struct

    def __setattr__(self, name, value):
        '''设置成员属性
        '''
        if fnmatch.fnmatch(name, "_*__*"):
            super(Message, self).__setattr__(name, value)
        else:
            if name == 'value' and not isinstance(self.__struct, CompositeType):
                self.__struct.from_assignment(value)
            else:
                setattr(self.__struct, name, value)

    def __getattribute__(self, name):
        '''查询成员属性
        '''
        try:
            return super(Message, self).__getattribute__(name)
        except AttributeError:
            if name == 'value' and not isinstance(self.__struct, CompositeType):
                return self.__struct.to_use()
            else:
                if fnmatch.fnmatch(name, "_*__struct"):
                    return {}
                else:
                    return getattr(self.__struct, name)

    def __repr__(self):
        return repr(self.__struct)

    def __iter__(self):
        '''中转数组类型的调用
        '''
        if isinstance(self.__struct, ArrayBase) or isinstance(self.__struct, MapBase):
            return self.__struct.__iter__()
        raise TypeError("'%s' object is not iterable" % type(self).__name__)

    def __contains__(self, item):
        if isinstance(self.__struct, ArrayBase) or isinstance(self.__struct, MapBase):
            return item in self.__struct
        raise TypeError("'%s' object is not iterable" % type(self).__name__)

    def __len__(self):
        '''中转数组类型的调用
        '''
        if isinstance(self.__struct, ArrayBase) or isinstance(self.__struct, MapBase):
            return len(self.__struct)
        raise TypeError("'%s' object has not len()" % type(self).__name__)

    def __nonzero__(self):
        return True

    def __getitem__(self, idx):
        '''中转数组类型的调用
        '''
        if isinstance(self.__struct, ArrayBase) or isinstance(self.__struct, MapBase):
            return self.__struct[idx]
        elif issubclass(self.__class__, Message):
            return getattr(self, idx)
        raise TypeError("'%s' object does not support indexing" % type(self).__name__)

    def __setitem__(self, idx, value):
        '''中转数组类型的调用
        '''
        if isinstance(self.__struct, ArrayBase) or isinstance(self.__struct, MapBase):
            self.__struct[idx] = value
        else:
            raise TypeError("'%s' object does not support indexing" % type(self).__name__)

    def __eq__(self, other):
        if type(self) != type(other):
            return False

        for field in self.__struct.get_fields():
            self_value = getattr(self.get_struct(), field.name)
            other_value = getattr(other.get_struct(), field.name)
            if not self_value == other_value:  # neq is not overridden
                return False
        return True

    def fill_size_ref(self, serializer):
        if serializer is None:
            return

        if isinstance(self.__struct, Dict):
            for field in self.__struct.get_fields():
                field_serializer = field.params.get("serializer", serializer)
                if not field_serializer:
                    raise ValueError("you must explicitly offer a serializer to fill_size_ref")
                if issubclass(field.type, Dict):
                    getattr(self, field.name).fill_size_ref(field_serializer)
                if "size_ref" in field.params:
                    if issubclass(field.type, ArrayBase):
                        field_size = len(getattr(self, field.name))
                    elif issubclass(field.type, (String, Buffer)):
                        field_size = field_size_of(self, field.name, field_serializer)
                    else:
                        field_size = size_of(getattr(self, field.name), field_serializer)
                    if "size_ref_hook" in field.params:
                        field_size = field.params["size_ref_hook"](field_size)
                    setattr(self, field.params["size_ref"], field_size)

    def get_message_length(self, value, deserializer):
        return len(value)

    def set_message_length(self, serializer):
        pass

    def dumps(self, serializer=None):
        '''序列化
        '''
        from qt4s.message.serializers.python import PythonSerializer
        serializer = serializer or self._serializer_ or PythonSerializer()
        struct_class = self.get_struct_class()
        if serializer.field_size_of_support is False:
            data = self.__struct.reduce()
            return serializer.dumps(struct_class, data)
        else:
            self.fill_size_ref(serializer)
            self.set_message_length(serializer)
            data = self.__struct.reduce()
            buf = serializer.dumps(struct_class, data)
            return buf

    def loads(self, value, deserializer=None):
        '''反序列化
        '''
        from qt4s.message.serializers.python import PythonSerializer
        deserializer = deserializer or self._serializer_ or PythonSerializer()
        struct_class = self.get_struct_class()
        if isinstance(deserializer, PythonSerializer):
            data = deserializer.loads(struct_class, value)
            remain_data = None
        else:
            total_length = self.get_message_length(value, deserializer)
            if total_length is None:
                raise ValueError("no packet could be loaded from given data")

            packet_buf = value[:total_length]
            remain_buf = value[total_length:]
            data, remain_data = deserializer.loads(struct_class, packet_buf)
            if remain_data:
                remain_data += remain_buf
        self.__struct.construct(data)
        return remain_data


def pretty_print(obj):
    from qt4s.message.serializers.python import PythonSerializer
    reduced_obj = obj.reduce(True)
    dumped_obj = PythonSerializer().dumps(type(obj), reduced_obj)
    target_objs = [dumped_obj]
    while target_objs:
        target_obj = target_objs.pop()
        for key in target_obj.keys():
            value = target_obj[key]
            if isinstance(value, dict):
                target_objs.append(value)
            else:
                if value == Uninitialized:
                    target_obj[key] = str(Uninitialized)
    return json.dumps(dumped_obj, indent=4)

