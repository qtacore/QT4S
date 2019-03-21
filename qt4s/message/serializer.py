# -*- coding: utf-8 -*-
'''协议消息的系列化和反系列化

使用示例：

'''

import json
import urllib


class SerializerItf(object):
    '''序列化器接口
    '''
    field_size_of_support = False

    def dumps(self, struct_class, value):
        '''序列化
        :param value: 需要序列化的结构数据
        :type value: python内置数据类型
        :returns: 序列化结果
        :rtype: 根据不同的序列化器而不同
        '''
        raise NotImplementedError

    def loads(self, struct_class, value):
        '''反序列化
        :param value: 序列化结果
        :type value: 根据不同的序列化器而不同
        :returns: 反序列化后的结构数据
        :rtype: python内置数据类型
        '''
        raise NotImplementedError

    def field_size_of(self, value, field_name):
        """get specific field's size of value
        
        :param value: Message object
        :type  value: Message
        :param field_name: field name of value
        :type  field_name: str
        """
        raise NotImplementedError

    def size_of(self, value):
        """get Message value's size
        
        :param value: Message object
        :type  value: Message
        """
        raise NotImplementedError

    def offset_of(self, value, field_name):
        """get specific field's offset of value
        
        :param value: Message object
        :type  value: Message
        :param field_name: field name of value
        :type  field_name: str
        """
        raise NotImplementedError


class JsonSerializer(SerializerItf):
    '''JSON序列化
    '''

    def dumps(self, struct_class, value):
        '''序列化
        '''
        return json.dumps(value)

    def loads(self, struct_class, value):
        '''反序列化
        '''
        return json.loads(value), None


class UrlQuerySerializer(SerializerItf):
    '''URL请求参数格式
    '''

    def dumps(self, struct_class, value):
        '''序列化
        '''
        return urllib.urlencode(value)

