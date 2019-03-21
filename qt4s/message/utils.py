# -*- coding: utf-8 -*-
"""utils
"""

def field_size_of(value, field_name, serializer):
    return serializer.field_size_of(value, field_name)

def size_of(value, serializer):
    return serializer.size_of(value)


def offset_of(value, field_name, serializer):
    return serializer.offset_of(value, field_name)
