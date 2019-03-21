# -*- coding: utf-8 -*-
"""python serializer
"""

from qt4s.message.serializer import SerializerItf
from qt4s.message.definition import StructTypeBase, Dict

try:
    from google.protobuf.message import Message as ProtoMessage
except:
    ProtoMessage = None


class PythonSerializer(SerializerItf):
    """python object serializer
    """

    def _dump_dict(self, struct_class, dict_value):
        value = {}
        for field in struct_class.get_fields():
            if field.name in dict_value:
                field_value = dict_value[field.name]
            else:
                if field.required is False:
                    continue
                elif field.has_default:
                    field_value = field.params["default"]
                else:
                    raise ValueError('required field "%s" of %s is not set' % (field.name, struct_class))
            if issubclass(field.type, StructTypeBase):
                value[field.name] = field_value
            else:
                value[field.name] = self.dumps(field.type, field_value)
        return value

    def dumps(self, struct_class, value):
        if issubclass(struct_class, StructTypeBase):
            if issubclass(struct_class, Dict):
                return self._dump_dict(struct_class, value)
            else:
                return value
        elif issubclass(struct_class, ProtoMessage):
            return value.dumps()
        else:
            raise TypeError("unsupported struct_class %r" % struct_class)

    def loads(self, struct_class, value):
        if issubclass(struct_class, StructTypeBase):
            return value
        elif issubclass(struct_class, ProtoMessage):
            obj = struct_class()
            obj.loads(value)
        else:
            raise TypeError("unsupported struct_class %r" % struct_class)
        return value

