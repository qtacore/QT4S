# -*- coding: utf-8 -*-
'''二进制编码序列化器
1、基本数据类型编码和C语言编码一致
2、字符串和数组类型，使用size_ref参数指定表示对应长度的域的名字

使用实例：
        
class WordLenBuffer(Message):
    _struct_ = [
        Field('B2_len', Uint16),
        Field('B2_buf', String, size_ref='B2_len')
    ]
    
    def set_buffer(self, buf ):
        self.B2_buf = buf
        self.B2_len = len(buf)
        
    def get_buffer(self):
        return self.B2_buf
    
class Test(Message):
    _struct_ = [
        Field('Len', Uint32),
        Field('B2', WordLenBuffer)
    ]
    
test = Test()
test.Len = 0x12345678
test.B2.set_buffer("XXXXXXXX")
buf = test.dumps(BinarySerializer())
test2 = Test()
test2.loads(buf, BinarySerializer())
assert test2.B2.get_buffer() == "XXXXXXXX"
assert test2.Len == 0x12345678
'''

import struct
import traceback

from qt4s.message.serializer import SerializerItf
from qt4s.message.definition import *


class BinaryEncodeError(Exception):
    '''编码时出错
    '''
    pass


class BinaryDecodeError(Exception):
    '''解码时出错
    '''
    pass


class BinaryEndian(object):
    '''字节序方式
    '''
    Native = '='
    LittleEndian = '<'
    BigEndian = '>'
    Network = '!'


class BufferWriter(object):
    '''数据缓冲区写操作
    '''

    def __init__(self):
        self._buf = ''
        self._pos = 0

    def write_data(self, data):
        '''写入数据
        '''
        self._buf += data
        self._pos += len(data)

    def detach(self):
        '''获取字符串
        '''
        buf = self._buf
        self._buf = None
        return buf

    def get_pos(self):
        '''获取当前偏移量
        '''
        return self._pos

    def get_buffer(self, begin=None, end=None):
        '''获取缓存区字符串
        '''
        if begin is None:
            begin = 0
        if end is None:
            end = len(self._buf)
        return self._buf[begin:end]


class BufferReader(object):
    '''缓冲区读操作
    '''

    def __init__(self, buf):
        self._buf = buf
        self._pos = 0

    def is_eof(self):
        '''判断是否结束
        '''
        return len(self._buf) <= self._pos

    def read_data(self, fmt, size):
        '''读数据
        '''
        data = struct.unpack_from(fmt, self._buf, self._pos)[0]
        self._pos += size
        return data

    def read_raw_data(self, size=None):
        '''读数据
        '''
        if size is None:
            data = self._buf[self._pos:]
            self._pos += (len(self._buf) - self._pos)
        else:
            data = self._buf[self._pos:self._pos + size]
            self._pos += size
        return data

    def get_pos(self):
        '''获取当前偏移量
        '''
        return self._pos

    def get_buffer(self, begin=None, end=None):
        '''获取缓存区字符串
        '''
        if begin is None:
            begin = 0
        if end is None:
            end = len(self._buf)
        return self._buf[begin:end]


class BinaryDecodeTracer(object):
    '''记录解码过程
    '''

    def __init__(self):
        self._depth = 0
        self._logs = []

    def inc_depth(self):
        self._depth += 1

    def dec_depth(self):
        self._depth -= 1

    def log(self, struct_type, data, value, field_info):
        if self._depth == 0:
            return
        if isinstance(field_info, int):
            field_info = '[%s]' % field_info
        if data is None:
            log = '%s%s' % ('-' * self._depth, field_info)
        elif value is None:
            log = '%s%s %s' % ('-' * self._depth, field_info, data.encode('hex'),)
        else:
            log = '%s%s %s(%s)' % ('-' * self._depth, field_info, data.encode('hex'), value)
        if log == 'None':
            raise
        self._logs.append(log)

    def get_traceback(self):
        return '\n'.join(self._logs)


TYPE_FLAG_MAP = {
    Float:'f',
    Double:'d',
    Bool:'?',
    Uint64:'Q',
    Int64:'q',
    Uint32:'I',
    Int32:'i',
    Uint16:'H',
    Int16:'h',
    Uint8:'B',
    Int8:'b',
}


class BinarySerializer(SerializerItf):
    '''二进制编码序列化器
    '''
    field_size_of_support = True

    def __init__(self, endian=BinaryEndian.Network):
        self._endian = endian
        self._buf = None

    def dumps(self, struct_class, value):
        '''序列化
        '''
        self._buf = BufferWriter()
        self._dumps(struct_class, value)
        return self._buf.detach()

    def _dumps(self, struct_class, value, config=None, parent_class=None, parent_value=None):
        '''序列化
        '''
        if config and "serializer" in config:
            serializer = config["serializer"]
            data = serializer.dumps(struct_class, value)
            self._buf.write_data(data)
        else:
            if issubclass(struct_class, Dict):
                self._dump_dict(value, struct_class, config, parent_class, parent_value)
            elif issubclass(struct_class, ArrayBase):
                self._dump_array(value, struct_class.element_struct, config, parent_class, parent_value)
            elif struct_class == String or struct_class == Buffer:
                self._dump_string(value, config, parent_class, parent_value)
            elif issubclass(struct_class, (Number, Bool)):
                flag = TYPE_FLAG_MAP[struct_class]
                self._dump_basic_type(flag, value)
            else:
                raise BinaryEncodeError('unsupported structure "%s"' % struct_class.__name__)

    def _get_field_from_struct(self, struct, name):
        '''在一个结构定义中查找对应的域
        '''
        for it in struct.get_fields():
            if it.name == name:
                return it

    def _dump_basic_type(self, flag, value):
        '''序列化基本数据类型
        '''
        self._buf.write_data(struct.pack(self._endian + flag, value))

    def _dump_size_ref(self, value, config, parent_class, parent_value):
        '''检查Ref数据
        '''
        if config and parent_class:
            size_ref = config.get('size_ref', None)
            size_ref_hook = config.get('size_ref_hook', None)
            if size_ref is not None:
                size_value = parent_value[size_ref]
                if size_ref_hook:
                    size_value = size_ref_hook(size_value)
                if len(value) != size_value:
                    raise ValueError('size mismatch actual(%s) != expected(%s)' % (len(value), size_value))

    def _dump_string(self, value, config, parent_class, parent_value):
        '''序列化字符串
        '''
#         self._dump_size_ref(value, config, parent_class, parent_value)
        self._buf.write_data(value)

    def _dump_array(self, value, element_struct, config, parent_class, parent_value):
        '''序列化数组
        '''
#         self._dump_size_ref(value, config, parent_class, parent_value)
        for it in value:
            self._dumps(element_struct, it)

    def _dump_dict(self, value, struct_class, config, parent_class, parent_value):
        '''序列化字典结构
        '''
        for it in struct_class.get_fields():
            if not it.required:
                    try:
                        value[it.name]
                    except KeyError:
                        continue
            self._dumps(it.type, value[it.name], it.params, struct_class, value)

    def loads(self, struct_class, buf):
        '''反序列化
        '''
        self._tracer = BinaryDecodeTracer()
        try:
            self._buf = BufferReader(buf)
            obj = self._loads(struct_class)
            if self._buf.is_eof():
                remain = None
            else:
                remain = self._buf.get_buffer(begin=self._buf.get_pos())
            return obj, remain
        except:
            stack = traceback.format_exc()
            raise BinaryDecodeError("Error: %s\nFollowing is decoding trace:\n%s" % (stack, self._tracer.get_traceback()))

    def _loads(self, struct_class, config=None, parent_class=None, parent_value=None, field_info=None):
        '''反序列化
        '''
        if config and "serializer" in config:
            serializer = config["serializer"]
            ref_size = None
            if "size_ref" in config:
                ref_size = parent_value[config["size_ref"]]

            if "size_ref_hook" in config:
                for field in parent_class.get_fields():
                    if field.name == config["size_ref"]:
                        if "size_ref_hook" not in field.params:
                            raise RuntimeError('size_ref_hook of field "%s" is not set' % config["size_ref"])
                        ref_size = field.params["size_ref_hook"](ref_size)
                        break
            field_buff = self._buf.read_raw_data(ref_size)
            field_value, _ = serializer.loads(struct_class, field_buff)
            return field_value
        else:
            if issubclass(struct_class, Dict):
                return self._load_dict(struct_class, field_info)
            elif issubclass(struct_class, ArrayBase):
                return self._load_array(config, struct_class, struct_class.element_struct, parent_class, parent_value, field_info)
            elif struct_class == String or struct_class == Buffer:
                return self._load_string(config, parent_class, parent_value, field_info)
            elif issubclass(struct_class, Number):
                flag = TYPE_FLAG_MAP[struct_class]
                return self._load_basic_type(flag, struct_class, field_info)
            else:
                raise BinaryDecodeError('unsupported structure "%s"' % struct_class.__name__)

    def _load_basic_type(self, flag, struct_class, field_info):
        '''反序列化基本类型
        '''
        size = struct.calcsize(flag)
        data = self._buf.get_buffer(self._buf.get_pos(), self._buf.get_pos() + size)
        value = self._buf.read_data(self._endian + flag, size)
        self._tracer.log(struct_class, data, value, field_info)
        return value

    def _load_string(self, config, parent_class, parent_value, field_info):
        '''序列化字符串
        '''
        if config:
            if "size_ref" in config:
                for temp_field_info in parent_class.get_fields():
                    if temp_field_info.name == config["size_ref"]:
                        byte_size = parent_value[config["size_ref"]]
                        if "size_ref_hook" in temp_field_info.params:
                            byte_size = temp_field_info.params["size_ref_hook"](byte_size)
                        break
                else:
                    raise ValueError('no size_ref field named: "%s"' % config["size_ref"])
            else:
                byte_size = config.get('byte_size', None)
                if byte_size == 0:  # magic size
                    byte_size = None
        else:
            byte_size = None
        if byte_size is None:
            value = self._buf.read_raw_data(None)
        else:
            value = self._buf.read_raw_data(byte_size)
        self._tracer.log(String, value, None, field_info)
        return value

    def _load_array(self, config, struct_class, element_class, parent_class, parent_value, field_info):
        '''序列化数组
        '''
        self._tracer.log(struct_class, None, None, field_info)
        self._tracer.inc_depth()
        size_ref = config.get('size_ref', None)
        array_size = config.get('array_size', None)
        if size_ref is None and array_size is None:
            raise BinaryDecodeError('array type require "size_ref" or "array_size" option')
        if size_ref:
            size = parent_value.get(size_ref, None)
            if size is None:
                raise BinaryDecodeError('array type field decoding require "%s" field' % size_ref)
            arrdata = []
            for i in range(size):
                arrdata.append(self._loads(element_class, None, struct_class, arrdata, i))
            self._tracer.dec_depth()
            return arrdata
        else:  # array_size
            if array_size == 0:
                arrdata = []
                i = 0
                while not self._buf.is_eof():
                    arrdata.append(self._loads(element_class, None, struct_class, arrdata, i))
                    i += 1
                self._tracer.dec_depth()
                return arrdata
            else:
                arrdata = []
                for i in range(array_size):
                    arrdata.append(self._loads(element_class, None, struct_class, arrdata, i))
                self._tracer.dec_depth()
                return arrdata

    def _load_dict(self, struct_class, field_info):
        '''序列化字典
        '''
        self._tracer.log(struct_class, None, None, field_info)
        self._tracer.inc_depth()
        mapdata = {}
        for it in struct_class.get_fields():
            if self._buf.is_eof() and not it.required:
                continue
            mapdata[it.name] = self._loads(it.type, it.params, struct_class, mapdata, it.name)
        self._tracer.dec_depth()
        return mapdata

    def size_of(self, value):
        total_size = 0
        if isinstance(value, Message):
            for field_info in value.get_fields():
                total_size += self.field_size_of(value, field_info.name)
        else:
            if isinstance(value, type):
                value_type = value
            else:
                value_type = type(value)
            if issubclass(value_type, Number):
                flag = TYPE_FLAG_MAP[value_type]
                total_size += struct.calcsize(flag)
            elif issubclass(value_type, (ArrayBase, MapBase)):
                raise ValueError("size_of Array and Map type is not supported")
            else:
                raise ValueError('unsupported value=%r' % value)
        return total_size

    def get_field_info(self, value, field_name):
        if not isinstance(value, Message):
            raise TypeError("value=%r does not match Message type" % value)

        field_parts = field_name.split(".")
        found_parts = []
        field_value = value
        field_info = None
        parent_value = None
        for field_part in field_parts:
            for temp_info in field_value.get_fields():
                if temp_info.name == field_part:
                    field_info = temp_info
                    if issubclass(temp_info.type, Number):  # incase uninitialized
                        field_value = None
                    else:
                        parent_value = field_value
                        field_value = getattr(field_value, field_part)
                    found_parts.append(field_part)
                    break
        if found_parts != field_parts:
            raise ValueError("%r has no field named: %s" % (value, field_name))
        return field_info, field_value, parent_value

    def field_size_of(self, value, field_name):
        field_size = 0
        field_info, field_value, _ = self.get_field_info(value, field_name)
        if "serializer" in field_info.params:
            field_serializer = field_info.params["serializer"]
        else:
            field_serializer = self
        if issubclass(field_info.type, (Number, Bool)):
            field_size += field_serializer.size_of(field_info.type)
        elif issubclass(field_info.type, (String, Buffer)):
            byte_size = field_info.params.get("byte_size")
            if byte_size:
                field_size += byte_size
            else:
                field_size += len(field_value)
        elif issubclass(field_info.type, ArrayBase):
            if issubclass(field_value.element_struct, (Dict, MapBase, ArrayBase)):
                for elem_value in field_value:
                    field_size += self.size_of(elem_value)
            else:
                field_size += len(field_value) * self.size_of(field_value.element_struct)
        elif issubclass(field_info.type, MapBase):
            raise TypeError("binary serializer does not support Map type")
        else:
            field_size += size_of(field_value, field_serializer)
        return field_size

    def offset_of(self, value, field_name):
        field_parts = field_name.split(".")
        field_value = value
        total_offset = 0
        for field_part in field_parts[:-1]:
            total_offset += self.offset_of(field_value, field_part)
            field_value = getattr(field_value, field_part)
        for field_info in field_value.get_fields():
            if field_info.name == field_parts[-1]:
                break
            else:
                total_offset += self.field_size_of(field_value, field_info.name)
        else:
            raise ValueError('no field named "%s" found' % field_name)
        return total_offset

