# -*- coding: utf-8 -*-
#---------------------------------------------------
#
# 该文件由QT4S代码生成器自动生成，请不要编辑
#
# ---------------------------------------------------
from qt4s.message.definition import *


class DemoJce(Message):
    __taf_class__ = "DemoJce.DemoJce"
    _struct_ = [
        Field("id", Int64, tag=0, optional=True),
        Field("name", String, tag=1, optional=True),
        Field("array", Array(Int64), tag=2, optional=True),
        Field("mapping", Map(String,Int64), tag=3, optional=True)
    ]

