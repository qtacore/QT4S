# -*- coding: utf-8 -*-
'''JSON序列化器
'''

from qt4s.message.serializer import SerializerItf
from qt4s.message.definition import Message, Variant, Field
import json


class JSONSerializer(SerializerItf):
    '''JSON序列化器
    '''

    def dumps(self, struct_class, value):
        '''序列化
        :param value: 需要序列化的结构数据
        :type value: python内置数据类型
        :returns: 序列化结果
        :rtype: 根据不同的序列化器而不同
        '''
        try:
            return json.dumps(value)
        except ValueError:
            raise ValueError("invalid json data: %s" % value)

    def loads(self, struct_class, value):
        '''反序列化
        :param value: 序列化结果
        :type value: 根据不同的序列化器而不同
        :returns: 反序列化后的结构数据
        :rtype: python内置数据类型
        '''
        return json.loads(value), None


class JsonData(Message):
    '''Json数据
    '''
    _struct_ = [
        Field("data", Variant)
    ]

    def __repr__(self):
        return 'JsonData(%s)' % self.data


def __j_handle_date(val):
    if isinstance(val, JsonData):
        return val.data
    elif isinstance(val, list) or isinstance(val, tuple):
        list_val = []
        for it in val:
            list_val.append(__j_handle_date(it))
        return list_val
    elif isinstance(val, dict):
        raise ValueError("不支持dict类型")
    else:
        return val


def _J(*args, **kwargs):
    if args and kwargs:
        raise ValueError("参数错误")
    obj = JsonData()
    if args:
        if len(args) > 1:
            raise ValueError("参数错误")
        obj.data = __j_handle_date(args[0])
    else:
        for name in kwargs:
            val = kwargs[name]
            setattr(obj.data, name, __j_handle_date(val))
    return obj

