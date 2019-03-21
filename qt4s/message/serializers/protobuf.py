# -*- coding: UTF-8 -*-

import gc
from qt4s.message.serializer import SerializerItf, JsonSerializer


class ProtobufSerializer(SerializerItf):

    def dumps(self, struct_class, value):
        # NOTE: this method would not be called
        return value.SerializeToString()

    def loads(self, struct_class, value):
        # NOTE: this method would not be called
        msg = struct_class()
        msg.ParseFromString(value)
        return msg, None

    def size_of(self, value):
        from google.protobuf.message import Message as _Message
        if not isinstance(value, _Message):
            raise ValueError("%r does not match Message object" % value)
        return len(value.dumps(self))


def _message_dumps(self, serializer=None):
    '''序列化
    '''
    from google.protobuf import json_format
    if serializer is None:
        return json_format.MessageToDict(self)
    elif type(serializer) == ProtobufSerializer:
        return self.SerializeToString()
    elif type(serializer) == JsonSerializer:
        return json_format.MessageToJson(self)
    else:
        raise RuntimeError("protobuf message do not support serializar: %s" % type(serializer))


def _message_loads(self, value, deserializer=None):
    '''反序列化
    '''
    from google.protobuf import json_format
    if deserializer is None:
        json_format.ParseDict(value, self)
    elif type(deserializer) == ProtobufSerializer:
        self.ParseFromString(value)
    elif type(deserializer) == JsonSerializer:
        json_format.Parse(value, self)
    else:
        raise RuntimeError("protobuf message do not support deserializar: %s" % type(deserializer))


def _add_methods_to_message_class(msg_class):
    msg_class.dumps = _message_dumps
    msg_class.loads = _message_loads


def _patch_ref_message_class(meta_class):
    for it in gc.get_referrers(meta_class):
        if type(it) == meta_class:
            it.dumps = _message_dumps
            it.loads = _message_loads


def _create_new_meta_class(meta_class):

    class _new_meta_class(meta_class):

        def __new__(cls, name, bases, dictionary):
            superclass = super(_new_meta_class, cls)
            new_class = superclass.__new__(cls, name, bases, dictionary)
            new_class.dumps = _message_dumps
            new_class.loads = _message_loads
            return new_class

    return _new_meta_class


def add_methods_to_protobuf_message_class():
    try:
        from google.protobuf import reflection
    except ImportError:
        pass
    else:
        meta_class = reflection.GeneratedProtocolMessageType
        if not meta_class:
            return
        # some message class can has been created before we hook, so patch it directly.
        _patch_ref_message_class(meta_class)
        _new_meta_class = _create_new_meta_class(meta_class)
        _new_meta_class.__name__ = meta_class.__module__.rsplit(".", 1)[-1] + "_" + "GeneratedProtocolMessageType"
        reflection.GeneratedProtocolMessageType = _new_meta_class


add_methods_to_protobuf_message_class()
