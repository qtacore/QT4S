# -*- coding: utf-8 -*-
'''JCE序列化器
'''

from qt4s.message.serializer import SerializerItf
from qt4s.message.definition import *
import struct


class JceEncodeError(Exception):
    '''编码时出错
    '''
    pass


class JceDecodeError(Exception):
    '''解码时出错
    '''
    pass

# def MAKE_BYTES( s ):
#    '''根据字符串生成对应的Bytes类型
#    '''
#    bs = []
#    for it in s:
#        bs.append(ord(it))
#    return bs
#
# def MAKE_BUFFER( arr ):
#    '''根据Bytes类型生成对应的字符串
#    '''
#    s = ''
#    for it in arr:
#        s += chr(it)
#    return s


class DataHeadType:
    '''头信息
    '''
    INT8 = 0
    INT16 = 1
    INT32 = 2
    INT64 = 3
    FLOAT = 4
    DOUBLE = 5
    STRING1 = 6
    STRING4 = 7
    MAP = 8
    LIST = 9
    STRUCTBEGIN = 10
    STRUCTEND = 11
    ZERO = 12
    BYTES = 13


_headType_StructTypeMap = {
    0: Uint8,
    1: Uint16,
    2: Uint32,
    3: Uint64,
    4: Float,
    5: Double,
    6: String,
    7: String,
    12: Uint8,
    13: Buffer
}


class BufferWriter(object):
    '''数据缓冲区写操作
    '''

    def __init__(self):
        self._buf = ''
        self._pos = 0

    def write_head(self, vtype, tag):
        '''写入一个信息头
        '''
        if tag < 15 :
            head = (tag << 4) | vtype;
            data = struct.pack('!B', head)
        else:
            head = ((0xF0 | vtype) << 8) | tag;
            data = struct.pack('!H', head)
        self._buf += data
        self._pos += len(data)

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
            end = self._pos
        return self._buf[begin:end]


class BufferReader(object):
    '''缓冲区读操作
    '''

    def __init__(self, buf):
        self._buf = buf
        self._pos = 0

    def read_head(self):
        '''读一个信息头
        '''
        # print 'read head, pos=', self._pos
        head = struct.unpack_from('!B', self._buf, self._pos)[0]
        tag = (head & 0xF0) >> 4
        vtype = (head & 0x0F)
        posinc = 1
        if tag >= 15:
            posinc = 2
            tag = struct.unpack_from('!B', self._buf, self._pos + 1)[0]
        self._pos += posinc
        return vtype, tag

    def is_eof(self):
        '''判断是否结束
        '''
        return len(self._buf) <= self._pos

    def read_data(self, size):
        '''读数据
        '''
        buf = self._buf[self._pos:self._pos + size]
        self._pos += size
        return buf

    def get_buffer(self, begin=None, end=None):
        '''获取缓存区字符串
        '''
        if begin is None:
            begin = 0
        if end is None:
            end = self._pos
        return self._buf[begin:end]

    def get_pos(self):
        '''获取当前偏移量
        '''
        return self._pos


class JceSerializer(SerializerItf):
    '''JCE序列化
    '''

    def __init__(self, ignore_unknown_tag=True):
        self._buf = None
        self._ignore_unknown_field = ignore_unknown_tag

    def dumps(self, struct_class, value):
        '''序列化
        '''
        self._buf = BufferWriter()
        if issubclass(struct_class, Dict):
            self._internal_dump_dict(value, struct_class)
        else:
            raise ValueError('JCE encoder only accept Dict struct message')
        return self._buf.detach()

    def _dumps(self, struct_class, tag, value):
        '''序列化
        '''
        if issubclass(struct_class, Dict):
            self._dump_dict(tag, value, struct_class)
        elif issubclass(struct_class, MapBase):
            self._dump_map(tag, value, struct_class.key_struct, struct_class.value_struct)
        elif issubclass(struct_class, ArrayBase):
            self._dump_array(tag, value, struct_class.element_struct)
        elif struct_class == String:
            self._dump_string(tag, value)
        elif struct_class == Buffer:
            self._dump_buffer(tag, value)
        elif struct_class == Float:
            self._dump_float(tag, value)
        elif struct_class == Double:
            self._dump_double(tag, value)
        elif struct_class == Bool:
            self._dump_bool(tag, value)
        elif struct_class == Uint64:
            self._dump_int64(tag, value, True)
        elif struct_class == Int64:
            self._dump_int64(tag, value, False)
        elif struct_class == Uint32:
            self._dump_int32(tag, value, True)
        elif struct_class == Int32:
            self._dump_int32(tag, value, False)
        elif struct_class == Uint16:
            self._dump_int16(tag, value, True)
        elif struct_class == Int16:
            self._dump_int16(tag, value, False)
        elif struct_class == Uint8:
            self._dump_int8(tag, value, True)
        elif struct_class == Int8:
            self._dump_int8(tag, value, False)
        else:
            raise JceEncodeError('unsupported structure "%s"' % struct_class.__name__)

    def _dump_int64(self, tag, value, unsigned):
        '''序列化64数值
        '''
        if value <= Int32.MAX and value >= Int32.MIN:
            self._dump_int32(tag, value, unsigned)
        else:
            self._buf.write_head(DataHeadType.INT64, tag)
            self._buf.write_data(struct.pack('!q', value))

    def _dump_int32(self, tag, value, unsigned):
        '''序列化32数值
        '''
        if value <= Int16.MAX and value >= Int16.MIN:
            self._dump_int16(tag, value, unsigned)
        else:
            self._buf.write_head(DataHeadType.INT32, tag)
            flag = '!i'
            if unsigned: flag = '!I'
            self._buf.write_data(struct.pack(flag, value))

    def _dump_int16(self, tag, value, unsigned):
        '''序列化16数值
        '''
        if value <= Int8.MAX and value >= Int8.MIN:
            self._dump_int8(tag, value, unsigned)
        else:
            flag = '!h'
            if unsigned: flag = '!H'
            self._buf.write_head(DataHeadType.INT16, tag)
            self._buf.write_data(struct.pack(flag, value))

    def _dump_int8(self, tag, value, unsigned):
        '''序列化8数值
        '''
        if value == 0:
            self._buf.write_head(DataHeadType.ZERO, tag)
        else:
            flag = '!b'
            if unsigned: flag = '!B'
            self._buf.write_head(DataHeadType.INT8, tag)
            self._buf.write_data(struct.pack(flag, value))

    def _dump_bool(self, tag, value):
        '''序列化布尔值
        '''
        self._dump_int8(tag, {True:1, False:0}[value], True)

    def _dump_double(self, tag, value):
        '''序列化浮点数
        '''
        self._buf.write_head(DataHeadType.DOUBLE, tag)
        self._buf.write_data(struct.pack('!d', value))

    def _dump_float(self, tag, value):
        '''序列化浮点数
        '''
        self._buf.write_head(DataHeadType.FLOAT, tag)
        self._buf.write_data(struct.pack('!f', value))

    def _dump_string(self, tag, value):
        '''序列化字符串
        '''
        length = len(value)
        if length <= 255:
            self._buf.write_head(DataHeadType.STRING1, tag)
            self._buf.write_data(struct.pack('!B', length))
        else:
            self._buf.write_head(DataHeadType.STRING4, tag)
            self._buf.write_data(struct.pack('!I', length))
        self._buf.write_data(value)

    def _dump_buffer(self, tag, value):
        '''序列化字符串
        '''
        self._buf.write_head(DataHeadType.BYTES, tag)
        self._buf.write_head(DataHeadType.INT8, 0)
        self._dump_int32(0, len(value), True)
        self._buf.write_data(value)

    def _dump_array(self, tag, value, element_struct):
        '''序列化数组
        '''
        if element_struct == Uint8 or element_struct == Int8:
            raise ValueError('use Bytes type to replace vector<byte>')
        else:
            self._buf.write_head(DataHeadType.LIST, tag)
            self._dump_int32(0, len(value), True)
            for it in value:
                self._dumps(element_struct, 0, it)

    def _dump_dict(self, tag, value, struct_class):
        '''序列化字典结构
        '''
        self._buf.write_head(DataHeadType.STRUCTBEGIN, tag)
        self._internal_dump_dict(value, struct_class)
        self._buf.write_head(DataHeadType.STRUCTEND, 0)

    def _internal_dump_dict(self, value, struct_class):
        '''序列化字典结构
        '''
        for it in struct_class.get_fields():
            if not it.required:
                try:
                    value[it.name]
                except KeyError:
                    continue
            self._dumps(it.type, it.params['tag'], value[it.name])

    def _dump_map(self, tag, mapdata, kstruct, vstruct):
        '''序列化映射表
        '''
        self._buf.write_head(DataHeadType.MAP, tag)
        self._dump_int32(0, len(mapdata), True)
        for key in mapdata:
            val = mapdata[key]
            self._dumps(kstruct, 0, key)
            self._dumps(vstruct, 1, val)

    def _get_field(self, struct_class, tag):
        '''通过tag找到对应的域
        '''
        for field in struct_class.get_fields():
            if field.params['tag'] == tag:
                return field
        else:
            if not self._ignore_unknown_field:
                raise JceDecodeError('invalid tag value %d for structure "%s"' % (tag, struct_class.__name__))

    def loads(self, struct_class, buf):
        '''反序列化
        '''
        dictdata = {}
        self._buf = BufferReader(buf)
        while not self._buf.is_eof():
            vtype, tag = self._buf.read_head()
            field = self._get_field(struct_class, tag)
            if field is not None:
                dictdata[field.name] = self._loads(field.type, vtype)
            else:
                value = self._loads_unknown(vtype)
                err_msg = "no field match tag=%r value=%s for struct class %r" % (tag, value, struct_class)
                if self._ignore_unknown_field:
                    print(err_msg)
                else:
                    raise JceDecodeError(err_msg)
        return dictdata, None

    def loads_unknown(self, buf):
        dict_data = {}
        self._buf = BufferReader(buf)
        while not self._buf.is_eof():
            vtype, tag = self._buf.read_head()
            dict_data[tag] = self._loads_unknown(vtype)
        return dict_data

    def _loads(self, struct_class, vtype):
        '''反序列化
        '''
        if issubclass(struct_class, Dict):
            return self._load_dict(vtype, struct_class)
        elif issubclass(struct_class, MapBase):
            return self._load_map(vtype, struct_class, struct_class.key_struct, struct_class.value_struct)
        elif issubclass(struct_class, ArrayBase):
            return self._load_array(vtype, struct_class, struct_class.element_struct)
        elif struct_class == String:
            return self._load_string(vtype, struct_class)
        elif struct_class == Buffer:
            return self._load_buffer(vtype, struct_class)
        elif struct_class == Float:
            return self._load_float(vtype, struct_class)
        elif struct_class == Double:
            return self._load_double(vtype, struct_class)
        elif struct_class == Bool:
            return self._load_bool(vtype, struct_class)
        elif struct_class == Uint64:
            return self._load_int64(vtype, struct_class, True)
        elif struct_class == Int64:
            return self._load_int64(vtype, struct_class, False)
        elif struct_class == Uint32:
            return self._load_int32(vtype, struct_class, True)
        elif struct_class == Int32:
            return self._load_int32(vtype, struct_class, False)
        elif struct_class == Uint16:
            return self._load_int16(vtype, struct_class, True)
        elif struct_class == Int16:
            return self._load_int16(vtype, struct_class, False)
        elif struct_class == Uint8:
            return self._load_int8(vtype, struct_class, True)
        elif struct_class == Int8:
            return self._load_int8(vtype, struct_class, False)
        else:
            raise JceDecodeError('unsupported structure "%s"' % struct_class.__name__)

    def _loads_unknown(self, vtype):
        struct_class = _headType_StructTypeMap.get(vtype, None)
        if struct_class:
            return self._loads(struct_class, vtype)
        elif vtype == DataHeadType.MAP:
            return self._load_map_unknown()
        elif vtype == DataHeadType.LIST:
            return self._load_array_unknown()
        elif vtype == DataHeadType.STRUCTBEGIN:
            return self._load_dict_unknown()
        else:
            raise JceDecodeError('unsupported vtype "%s"' % vtype)

    def _load_dict(self, vtype, struct_class):
        '''反序列化字典
        '''
        if vtype == DataHeadType.STRUCTBEGIN:
            dictdata = {}
            while True:
                evtype, tag = self._buf.read_head()
                if evtype == DataHeadType.STRUCTEND:
                    assert tag == 0
                    break

                field = self._get_field(struct_class, tag)
                if field is not None:
                    dictdata[field.name] = self._loads(field.type, evtype)
                else:
                    # dictdata['unknown_%s'%tag] = self._loads_unknown(evtype)
                    self._loads_unknown(evtype)
            return dictdata
        else:
            raise JceDecodeError('inconsistent type, structure is "%s", data head is "%d"' % (struct_class.__name__, vtype))

    def _load_dict_unknown(self):
        dictdata = {}
        while True:
            evtype, tag = self._buf.read_head()
            if evtype == DataHeadType.STRUCTEND:
                assert tag == 0
                break
            dictdata['unknown_%s' % tag] = self._loads_unknown(evtype)
        return dictdata

    def _load_map(self, vtype, struct_class, kstruct, vstruct):
        '''反序列化映射表
        '''
        if vtype == DataHeadType.MAP:
            _vtype, _vtag = self._buf.read_head()
            assert _vtag == 0
            size = self._load_int32(_vtype, Uint32, True)
            m = {}
            for _ in range(size):
                kvtype, tag = self._buf.read_head()
                assert tag == 0
                k = self._loads(kstruct, kvtype)
                vvtype, tag = self._buf.read_head()
                assert tag == 1
                v = self._loads(vstruct, vvtype)
                m[k] = v
            return m
        else:
            raise JceDecodeError('inconsistent type, structure is "%s", data head is "%d"' % (struct_class.__name__, vtype))

    def _load_map_unknown(self):
        _vtype, _vtag = self._buf.read_head()
        assert _vtag == 0
        size = self._load_int32(_vtype, Uint32, True)
        m = {}
        for _ in range(size):
            kvtype, tag = self._buf.read_head()
            assert tag == 0
            k = self._loads_unknown(kvtype)
            vvtype, tag = self._buf.read_head()
            assert tag == 1
            v = self._loads_unknown(vvtype)
            m[k] = v
        return m

    def _load_array(self, vtype, struct_class, element_struct):
        '''反序列化数组
        '''
        if element_struct == Uint8 or element_struct == Int8:
            # return self._load_simplelist(vtype, struct_class, element_struct)
            raise ValueError('use Bytes type to replace vector<byte>')
        else:
            if vtype == DataHeadType.LIST:
                _vtype, _vtag = self._buf.read_head()
                assert _vtag == 0
                size = self._load_int32(_vtype, struct_class, True)
                listdata = []
                for _ in range(size):
                    evtype, tag = self._buf.read_head()
                    assert tag == 0
                    listdata.append(self._loads(element_struct, evtype))
                return listdata
            else:
                raise JceDecodeError('inconsistent type, structure is "%s", data head is "%d"' % (struct_class.__name__, vtype))

    def _load_array_unknown(self):
        _vtype, _vtag = self._buf.read_head()
        assert _vtag == 0
        size = self._load_int32(_vtype, Uint32, True)
        listdata = []
        for _ in range(size):
            evtype, tag = self._buf.read_head()
            assert tag == 0
            listdata.append(self._loads_unknown(evtype))
        return listdata

#    def _load_simplelist(self, vtype, struct_class, element_struct):
#        '''反序列化数组
#        '''
#        if vtype == DataHeadType.BYTES:
#            _vtype, _vtag = self._buf.read_head()
#            assert _vtype == DataHeadType.INT8
#            assert _vtag == 0
#            _vtype, _vtag = self._buf.read_head()
#            assert _vtag == 0
#            size = self._load_int32(_vtype, struct_class, True)
#            listdata = []
#            for it in self._buf.read_data(size):
#                listdata.append(ord(it))
#            return listdata
#        else:
#            raise JceDecodeError('inconsistent type, structure is "%s", data head is "%d"'%(struct_class.__name__, vtype))

    def _load_string(self, vtype, struct_class):
        '''反序列化字符串
        '''
        if vtype == DataHeadType.STRING1:
            size = struct.unpack_from('!B', self._buf.read_data(1))[0]
            return self._buf.read_data(size)
        elif vtype == DataHeadType.STRING4:
            size = struct.unpack_from('!I', self._buf.read_data(4))[0]
            return self._buf.read_data(size)
        else:
            raise JceDecodeError('inconsistent type, structure is "%s", data head is "%d"' % (struct_class.__name__, vtype))

    def _load_buffer(self, vtype, struct_class):
        '''反序列化缓冲区
        '''
        if vtype == DataHeadType.BYTES:
            _vtype, _vtag = self._buf.read_head()
            assert _vtype == DataHeadType.INT8
            assert _vtag == 0
            _vtype, _vtag = self._buf.read_head()
            assert _vtag == 0
            size = self._load_int32(_vtype, struct_class, True)
            return self._buf.read_data(size)
        else:
            raise JceDecodeError('inconsistent type, structure is "%s", data head is "%d"' % (struct_class.__name__, vtype))

    def _load_int8(self, vtype, struct_class, unsigend):
        '''反序列化8位数
        '''
        if vtype == DataHeadType.ZERO:
            return 0
        elif vtype == DataHeadType.INT8:
            flag = '!b'
            if unsigend: flag = '!B'
            return struct.unpack_from(flag, self._buf.read_data(1))[0]
        else:
            raise JceDecodeError('inconsistent type, structure is "%s", data head is "%d"' % (struct_class.__name__, vtype))

    def _load_int16(self, vtype, struct_class, unsigend):
        '''反序列化16位数
        '''
        if vtype == DataHeadType.ZERO:
            return 0
        elif vtype == DataHeadType.INT8:
            flag = '!b'
            if unsigend: flag = '!B'
            return struct.unpack_from(flag, self._buf.read_data(1))[0]
        elif vtype == DataHeadType.INT16:
            flag = '!h'
            if unsigend: flag = '!H'
            return struct.unpack_from(flag, self._buf.read_data(2))[0]
        else:
            raise JceDecodeError('inconsistent type, structure is "%s", data head is "%d"' % (struct_class.__name__, vtype))

    def _load_int32(self, vtype, struct_class, unsigend):
        '''反序列化32位数
        '''
        if vtype == DataHeadType.ZERO:
            return 0
        elif vtype == DataHeadType.INT8:
            flag = '!b'
            if unsigend: flag = '!B'
            return struct.unpack_from(flag, self._buf.read_data(1))[0]
        elif vtype == DataHeadType.INT16:
            flag = '!h'
            if unsigend: flag = '!H'
            return struct.unpack_from(flag, self._buf.read_data(2))[0]
        elif vtype == DataHeadType.INT32:
            flag = '!i'
            if unsigend: flag = '!I'
            return struct.unpack_from(flag, self._buf.read_data(4))[0]
        else:
            raise JceDecodeError('inconsistent type, structure is "%s", data head is "%d"' % (struct_class.__name__, vtype))

    def _load_int64(self, vtype, struct_class, unsigend):
        '''反序列化64位数
        '''
        if vtype == DataHeadType.ZERO:
            return 0
        elif vtype == DataHeadType.INT8:
            flag = '!b'
            if unsigend: flag = '!B'
            return struct.unpack_from(flag, self._buf.read_data(1))[0]
        elif vtype == DataHeadType.INT16:
            flag = '!h'
            if unsigend: flag = '!H'
            return struct.unpack_from(flag, self._buf.read_data(2))[0]
        elif vtype == DataHeadType.INT32:
            flag = '!i'
            if unsigend: flag = '!I'
            return struct.unpack_from(flag, self._buf.read_data(4))[0]
        elif vtype == DataHeadType.INT64:
            flag = '!q'
            if unsigend: flag = '!Q'
            return struct.unpack_from(flag, self._buf.read_data(8))[0]
        else:
            raise JceDecodeError('inconsistent type, structure is "%s", data head is "%d"' % (struct_class.__name__, vtype))

    def _load_bool(self, vtype, struct_class):
        '''反序列化布尔
        '''
        value = self._load_int8(vtype, struct_class, True)
        if value == 0:
            return False
        else:
            return True

    def _load_float(self, vtype, struct_class):
        '''反序列化浮点数
        '''
        if vtype == DataHeadType.ZERO:
            return 0
        elif vtype == DataHeadType.FLOAT:
            return struct.unpack_from('!f', self._buf.read_data(4))[0]
        else:
            raise JceDecodeError('inconsistent type, structure is "%s", data head is "%d"' % (struct_class.__name__, vtype))

    def _load_double(self, vtype, struct_class):
        '''反序列化双浮点数
        '''
        if vtype == DataHeadType.ZERO:
            return 0
        elif vtype == DataHeadType.FLOAT:
            return struct.unpack_from('!f', self._buf.read_data(4))[0]
        elif vtype == DataHeadType.DOUBLE:
            return struct.unpack_from('!d', self._buf.read_data(8))[0]
        else:
            raise JceDecodeError('inconsistent type, structure is "%s", data head is "%d"' % (struct_class.__name__, vtype))

    def size_of(self, value):
        if not isinstance(value, Message):
            raise ValueError("%r does not match Message object" % value)
        return len(value.dumps(self))


class Tab(object):
    '''缩进
    '''
    CONTENT = '    '

    def __init__(self):
        self._cnt = 0

    def inc(self):
        self._cnt += 1

    def dec(self):
        self._cnt -= 1

    def __str__(self):
        return self.CONTENT * self._cnt


class JceDisplayFormatter(SerializerItf):
    '''用于格式化展示JCE编码格式
    '''

    def __init__(self):
        super(JceDisplayFormatter, self).__init__()
        self._prefix = Tab()
        self._display = ''

    def _write_line(self, line):
        '''格式化一行
        '''
        self._display += '%s%s\n' % (str(self._prefix), line)

    def dumps(self, struct_class, value):
        '''序列化
        '''
        if issubclass(struct_class, Dict):
            self._write_line('{')
            self._internal_dump_dict(value, struct_class)
            self._write_line('}')
        else:
            raise ValueError('JCE encoder only accept Dict struct message')
        return self._display

    def _dumps(self, struct_class, tag, name, value):
        '''序列化
        '''
        if issubclass(struct_class, Dict):
            self._dump_dict(tag, name, value, struct_class)
        elif issubclass(struct_class, MapBase):
            self._dump_map(tag, name, value, struct_class.key_struct, struct_class.value_struct)
        elif issubclass(struct_class, ArrayBase):
            self._dump_array(tag, name, value, struct_class.element_struct)
        elif struct_class == String:
            self._dump_string(tag, name, value)
        elif struct_class == Buffer:
            self._dump_buffer(tag, name, value)
        elif struct_class == Float:
            self._dump_float(tag, name, value)
        elif struct_class == Double:
            self._dump_double(tag, name, value)
        elif struct_class == Bool:
            self._dump_bool(tag, name, value)
        elif struct_class == Uint64:
            self._dump_int64(tag, name, value, True)
        elif struct_class == Int64:
            self._dump_int64(tag, name, value, False)
        elif struct_class == Uint32:
            self._dump_int32(tag, name, value, True)
        elif struct_class == Int32:
            self._dump_int32(tag, name, value, False)
        elif struct_class == Uint16:
            self._dump_int16(tag, name, value, True)
        elif struct_class == Int16:
            self._dump_int16(tag, name, value, False)
        elif struct_class == Uint8:
            self._dump_int8(tag, name, value, True)
        elif struct_class == Int8:
            self._dump_int8(tag, name, value, False)
        else:
            raise JceEncodeError('unsupported structure "%s"' % struct_class.__name__)

    def _dump_integer(self, tag, name, value, unsigned):
        '''序列化数值
        '''
        self._write_line('%s = %s,' % (name, value))

    _dump_int64 = _dump_integer
    _dump_int32 = _dump_integer
    _dump_int16 = _dump_integer
    _dump_int8 = _dump_integer

    def _dump_base_type(self, tag, name, value):
        '''序列化基本类型
        '''
        self._write_line('%s = %s,' % (name, value))

    _dump_bool = _dump_base_type
    _dump_float = _dump_base_type
    _dump_double = _dump_base_type

    def _dump_string(self, tag, name, value):
        '''序列化字符串
        '''
        self._write_line('%s = "%s",' % (name, value))

    def _dump_buffer(self, tag, name, value):
        '''序列化缓冲区
        '''
        self._write_line('%s = %s,' % (name, value.encode('hex')))

    def _dump_array(self, tag, name, arrvalue, element_struct):
        '''序列化数组
        '''
        if element_struct == Uint8 or element_struct == Int8:
            self._dump_simplelist(tag, name, arrvalue)
        else:
            self._write_line('%s = [' % name)
            self._prefix.inc()
            for idx, it in enumerate(arrvalue):
                self._dumps(element_struct, tag, '[%d]' % idx, it)
            self._prefix.dec()
            self._write_line('],')

    def _dump_simplelist(self, tag, name, arrvalue):
        '''序列化SimpleList
        '''
        sdata = ''
        for it in arrvalue:
            sdata += '\\x%02x' % it
        self._write_line('%s = "%s",' % (name, sdata))

    def _dump_dict(self, tag, name, value, struct_class):
        '''序列化字典结构
        '''
        self._write_line('%s = {' % name)
        self._internal_dump_dict(value, struct_class)
        self._write_line('},')

    def _internal_dump_dict(self, value, struct_class):
        '''序列化字典结构
        '''
        self._prefix.inc()
        for it in struct_class.get_fields():
            if not it.required:
                try:
                    value[it.name]
                except KeyError:
                    continue
            self._dumps(it.type, it.params['tag'], it.name, value[it.name])
        self._prefix.dec()

    def _dump_map(self, tag, name, mapdata, kstruct, vstruct):
        '''序列化映射表
        '''
        self._write_line('%s = {' % name)
        self._prefix.inc()
        for key in mapdata:
            self._dumps(vstruct, tag, '<%s>' % str(key), mapdata[key])
        self._prefix.dec()
        self._write_line('}')


class WNSSerializer(JceSerializer):
    '''WNS序列化器
    '''

    def wns_loads(self, struct_class, buf):
        '''反序列化
        '''
        if issubclass(struct_class, Message):
            message_class = struct_class
            struct_class = struct_class.get_struct_class()
        else:
            message_class = None
        self._buf = BufferReader(buf)
        vtype, tag = self._buf.read_head()
        assert tag == 0
        if not self._buf.is_eof():
            remain = self._buf.get_buffer(begin=self._buf.get_pos())
        else:
            remain = None
        rawdata = self._loads(struct_class, vtype)
        if message_class is None:
            return rawdata, remain
        else:
            obj = message_class()
            obj.construct(rawdata)
        return obj, remain

    def wns_dumps(self, struct_class, obj):
        '''序列化
        '''
        if issubclass(struct_class, Message):
            struct_class = struct_class.get_struct_class()
        self._buf = BufferWriter()
        if isinstance(obj, StructTypeBase) or isinstance(obj, Message):
            value = obj.reduce()
        else:
            value = obj
        self._dumps(struct_class, 0, value)
        return self._buf.detach()


class WNSAttributeSet(Message):
    '''WNS属性编码
    '''
    _struct_ = Map(String, Buffer)


class WNSAttributes(Message):
    '''WNS包编码
    '''
    _struct_ = Map(String, WNSAttributeSet)

    _struct_taf_name_map = {
        Bool: 'bool',
        Int8: 'char',
        Uint8: 'char',
        Int16: 'short',
        Uint16: 'short',
        Int32: 'int32',
        Uint32: 'int32',
        Int64: 'int64',
        Uint64: 'int64',
        Float: 'float',
        Double: 'double',
        String: 'string'
    }

    def _get_taf_name(self, struct_type):
        '''获取对应结构的编码名称
        '''
        if issubclass(struct_type, Message):
            msg_type = struct_type
            struct_type = struct_type.get_struct_class()
        name = self._struct_taf_name_map.get(struct_type, None)
        if name:
            return name
        if issubclass(struct_type, ArrayBase):
            return 'list<%s>' % self._get_taf_name(struct_type.element_struct)
        elif issubclass(struct_type, MapBase):
            return 'map<%s,%s>' % (self._get_taf_name(struct_type.key_struct),
                                 self._get_taf_name(struct_type.value_struct))
        elif issubclass(struct_type, Dict):
            return msg_type.__taf_class__
        else:
            raise ValueError('unsupported struct %s' % struct_type.__name__)
        return self.__taf_class__

    def put(self, struct_type, name, value):
        '''存入
        '''
        tafname = self._get_taf_name(struct_type)
        try:
            attrs = self[name]
        except KeyError:
            attrs = WNSAttributeSet()
            self[name] = attrs
        jce = WNSSerializer()
        attrs[tafname] = jce.wns_dumps(struct_type, value)

    class _NoParam(object):
        pass

    def get(self, struct_type, name, default=_NoParam):
        '''取出
        '''
        jce = WNSSerializer()
        tafname = self._get_taf_name(struct_type)
        try:
            data = self[name][tafname]
        except KeyError:
            if default is self._NoParam:
                raise
            else:
                return default
        return jce.wns_loads(struct_type, data)[0]

    def dumps(self):
        '''序列化
        '''
        jce = WNSSerializer()
        return jce.wns_dumps(WNSAttributes._struct_, self)

    def loads(self, buf):
        '''反序列化
        '''
        jce = WNSSerializer()
        raw, remain = jce.wns_loads(WNSAttributes._struct_, buf)
        super(WNSAttributes, self).loads(raw)
        return remain


UniAttributes = WNSAttributes

