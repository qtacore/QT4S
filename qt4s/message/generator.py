# -*- coding: utf-8 -*-
'''Python代码生成器
'''

import types


class StructType(object):
    '''结构类型（基类）
    '''

    def __init__(self, typename):
        self.name = typename


class BuildInStructType(StructType):
    '''内置类型，比如int32、bool等
    '''

    def __init__(self, typename):
        super(BuildInStructType, self).__init__(typename)


class ArrayStructType(StructType):
    '''数组结构类型
    '''

    def __init__(self, elementtype):
        self.elementtype = elementtype
        super(ArrayStructType, self).__init__('Array(%s)' % self.elementtype)


class MapStructType(StructType):
    '''映射表结构类型
    '''

    def __init__(self, keytype, valuetype):
        self.ktype = keytype
        self.vtype = valuetype
        super(MapStructType, self).__init__('Map(%s,%s)' % (self.ktype, self.vtype))


class FieldDef(object):
    '''一个域的定义
    '''

    def __init__(self, name, type, options):
        self.name = name
        self.type = type
        self.options = options


class MessageDef(object):
    '''一个消息定义
    '''

    def __init__(self, name, struct):
        self.name = name
        self.struct = struct


class AnnoymousMessageDef(MessageDef):
    '''匿名的消息定义
    '''

    def __init__(self, struct):
        super(AnnoymousMessageDef, self).__init__('::anonymous', struct)


class TypedefMessageDef(MessageDef):
    '''通过typedef定义的消息类型
    '''

    def __init__(self, name, struct):
        super(TypedefMessageDef, self).__init__(name, struct)


class MessageDefReference(MessageDef):
    '''引用其他结构定义类型
    '''

    def __init__(self, typename, nsname=None):
        super(MessageDefReference, self).__init__(typename, None)
        self._ref = None
        self.ns = nsname

    def is_resolved(self):
        '''是否是有效的引用
        '''
        return self._ref != None

    def set_ref(self, msgdef):
        '''设置引用的消息定义类型
        '''
        self._ref = msgdef

    def get_ref(self):
        '''查询引用的消息定义类型
        '''
        return self._ref


class ServiceDef(object):
    '''服务定义
    '''

    def __init__(self, name, rpcs):
        self.name = name
        self.rpcs = rpcs


class RpcDef(object):
    '''RPC定义
    '''

    def __init__(self, name, in_msgs, out_msgs, inout_msgs, return_msgs):
        self.name = name
        self.ins = in_msgs
        self.outs = out_msgs
        self.inout = inout_msgs
        self.returns = return_msgs


class ConstDef(object):
    '''常量定义
    '''

    def __init__(self, type, name, value):
        self.type = type
        self.name = name
        self.value = value


class EnumDef(object):
    '''枚举值定义
    '''

    def __init__(self, name, valuelist):
        self.name = name
        self.values = []
        for idx, (vname, vdata) in enumerate(valuelist):
            if vdata is None:
                if idx == 0:
                    self.values.append((vname, 0))
                else:
                    self.values.append((vname, self.values[idx - 1][1] + 1))
            else:
                self.values.append((vname, vdata))


class ImportDef(object):
    '''导入定义
    '''

    def __init__(self, name):
        self.name = name[1:-1]


class EnumValueRef(object):
    '''引用枚举值
    '''

    def __init__(self, name):
        self.name = name


class ConstValueRef(object):
    '''引用常量
    '''

    def __init__(self, name):
        self.name = name


class ValueRef(object):
    '''变量名引用
    '''

    def __init__(self, name, ns=None):
        self.name = name
        self.namespace = ns


class LangSpecificDefHandler(object):
    '''语言相关扩展定义处理句柄
    '''

    def on_generate(self, fd, context, curr_ns, d):
        pass


class NamespaceSlice(object):
    '''名字空间片段
    '''

    def __init__(self, name, exprs, error_handler):
        self.name = name
        self._messages = []
        self._annoymsgs = []
        self._services = []
        self._consts = []
        self._enums = []
        self._error = error_handler
        self._lang_deps_defs = []
        for it in exprs:
            self.add_def(it, it.lexpos, it.lineno)

    def add_def(self, d, lexpos, lineno):
        '''增加一个定义
        '''
        if isinstance(d, MessageDef):
            self.add_message_def(d, lexpos, lineno)
        elif isinstance(d, ConstDef):
            self.add_const_def(d, lexpos, lineno)
        elif isinstance(d, EnumDef):
            self.add_enum_def(d, lexpos, lineno)
        elif isinstance(d, ServiceDef):
            self.add_service_def(d, lexpos, lineno)
        else:
            self._lang_deps_defs.append(d)

    def add_const_def(self, constdef, lexpos, lineno):
        '''增加一个常量定义
        '''
        for const in self._consts:
            if const.name == constdef.name:
                return self._error(lexpos, lineno, 'redefine constant "%s"' % constdef.name)
        else:
            self._consts.append(constdef)

    def get_const_def(self, name):
        '''获取一个常量定义
        '''
        for it in self._consts:
            if it.name == name:
                return it

    def get_const_defs(self):
        '''全部常量定义
        '''
        return self._consts

    def add_enum_def(self, enumdef, lexpos, lineno):
        '''增加一个枚举值定义
        '''
        for enum in self._enums:
            if enum.name == enumdef.name:
                return self._error(lexpos, lineno, 'redefine enum type "%s"' % enumdef.name)
        else:
            self._enums.append(enumdef)

    def get_enum_def(self, name):
        '''获取一个枚举定义
        '''
        for it in self._enums:
            if it.name == name:
                return it

    def get_enum_def_by_valuename(self, name):
        '''根据枚举值名称获取一个枚举定义
        '''
        for enumdef in self._enums:
            for vname, _ in enumdef.values:
                if vname == name:
                    return enumdef

    def get_enum_defs(self):
        '''全部枚举定义
        '''
        return self._enums

    def add_message_def(self, message, lexpos, lineno):
        '''增加一个消息定义
        '''
        if type(message) == AnnoymousMessageDef:
            self._annoymsgs.append(message)
        else:
            for msg in self._messages:
                if msg.name == message.name:
                    self._error(lexpos, lineno, 'redefine message "%s"' % msg.name)
            self._messages.append(message)

    def get_message_def(self, name):
        '''获取一个消息定义
        '''
        for it in self._messages:
            if it.name == name:
                return it

    def get_message_defs(self):
        '''全部消息定义
        '''
        return self._messages + self._annoymsgs

    def get_lang_defs(self):
        '''获取特定语言相关的定义
        '''
        return self._lang_deps_defs

    def _resolve_message_ref(self, name):
        '''解析一个消息引用
        '''
        msgdef = self.get_message_def(name)
        if msgdef is not None:
            return msgdef
        enumdef = self.get_enum_def(name)
        if enumdef is not None:
            return enumdef

    def resolve_message_ref(self, ref, context):
        '''解析一个消息引用
        '''
        msgdef = self._resolve_message_ref(ref.name)
        if msgdef is not None:
            return msgdef

        for nsslice in context.get_all_namespace_slice_by_name(self.name):
            if nsslice == self:
                continue
            msgdef = nsslice._resolve_message_ref(ref.name)
            if msgdef is not None:
                return msgdef
        else:
            return self._error(ref.lexpos, ref.lineno, 'unsolved message type "%s"' % ref.name)

    def _resolve_value_ref(self, name):
        '''解析一个常量或枚举值引用
        '''
        msgdef = self.get_const_def(name)
        if msgdef is not None:
            return msgdef
        enumdef = self.get_enum_def_by_valuename(name)
        if enumdef is not None:
            return enumdef

    def resolve_value_ref(self, ref, context):
        '''解析一个常量或枚举值引用
        '''
        d = self._resolve_value_ref(ref.name)
        if d is not None:
            return d
        if ref.namespace is None:
            nslices = context.get_all_namespace_slice_by_name(self.name)
        else:
            nslices = context.get_all_namespace_slice_by_name(ref.namespace)
        for nsslice in nslices:
            if nsslice == self:
                continue
            d = nsslice._resolve_value_ref(ref.name)
            if d is not None:
                return d
        else:
            return self._error(ref.lexpos, ref.lineno, 'unsolved message type "%s"' % ref.name)

    def add_service_def(self, service, lexpos, lineno):
        '''增加一个服务定义
        '''
        for it in self._services:
            if it.name == service.name:
                return self._error(lexpos, lineno, 'redefine service "%s"' % service.name)
        self._services.append(service)

    def get_service_defs(self):
        '''获取全部的服务定义
        '''
        return self._services


class Context(object):
    '''全局共享上下文
    '''

    def __init__(self, parser_class, import_paths, debug=0):
        self._import_paths = import_paths
        self._parsers = {}
        self._parser_class = parser_class

    def get_import_paths(self):
        '''查询导入模块搜索路径
        '''
        return self._import_paths

    def import_module(self, file_path):
        '''导入指定的模块，返回对应的解析器
        '''
        for name in self._parsers:
            if name == file_path:
                return self._parsers[name]
        else:
            parser = self._parser_class(file_path, self)
            parser.parse()
            self._parsers[file_path] = parser
            return parser

    def get_parsers(self):
        '''获取全部模块的解析器
        '''
        return self._parsers.values()

    def get_all_namespace_slice_by_name(self, name):
        '''获取对应名字的全部名字空间片段
        '''
        nss = []
        for parser in self._parsers.values():
            for nsslice in parser.get_module().get_namespace_slices():
                if nsslice.name == name:
                    nss.append(nsslice)
        return nss


class Module(object):
    '''一个模块，一般和一个描述文件对应
    '''

    def __init__(self, file_path, error_handler):
        self._file_path = file_path
        self._nsslices = []
        self._imps = []
        self._error = error_handler

    def add_import_def(self, impdef):
        '''增加一个导入
        '''
        self._imps.append(impdef)

    def get_import_defs(self):
        '''获取全部的导入
        '''
        return self._imps

    def add_namespace_slice(self, ns_slice, lexpos, lineno):
        '''增加一个名字空间片段
        '''
        for it in self._nsslices:
            if it.name == ns_slice.name:
                return self._error(lexpos, lineno, 'redefine name space "%s"' % ns_slice.name)
        self._nsslices.append(ns_slice)

    def get_namespace_slices(self):
        '''获取全部名字空间片段
        '''
        return self._nsslices

    def resolve_all(self, context):
        '''解析全部引用
        '''
        #  TO DO: 检查符号之间的依赖关系
        for nsslice in self._nsslices:
            nsslice.resolve_all_ref(context)


class CodeGenerator(object):
    '''生成对应的Python代码
    '''
    header_text = """# -*- coding: utf-8 -*-
#---------------------------------------------------
#
# 该文件由QT4S代码生成器自动生成，请不要编辑
#
# ---------------------------------------------------
from qt4s.message.definition import *
"""

    msgdef_template = """class %(classname)s(Message):
    _struct_ = %(struct)s"""

    fields_template = """[
%(fields)s
%(tab)s]"""

    field_template = """%(tab)sField("%(name)s", %(type)s%(options)s)"""

    constdef_template = '%(valuename)s = %(value)s'

    tab = '    '

    def __init__(self, context):
        self._context = context
        self._curr_ns = None

    def generate(self, module, filename, ext):
        '''生成代码
        '''
        with open(filename, 'w') as fd:
            fd.write(self.header_text)
            for impdef in module.get_import_defs():
                self.write_import(fd, impdef)
            self.write_newline(fd)
            for nsslice in module.get_namespace_slices():
                self._curr_ns = nsslice
                for const in nsslice.get_const_defs():
                    self.write_const_def(fd, const)
                for enum in nsslice.get_enum_defs():
                    self.write_enum_def(fd, enum)
                for msgdef in nsslice.get_message_defs():
                    if type(msgdef) != AnnoymousMessageDef:
                        self.write_message_def(fd, msgdef)
                        self.write_newline(fd)
                for svcdef in nsslice.get_service_defs():
                    self.write_service_def(fd, svcdef)
                    self.write_newline(fd)
                if ext:
                    for d in nsslice.get_lang_defs():
                        ext.on_generate(fd, self._context, self._curr_ns, d)

    def write_newline(self, fd):
        fd.write('\r\n')

    def write_import(self, fd, impdef):
        fd.write('from %s import *\n' % impdef.name.replace('.', '_'))

    def write_const_def(self, fd, constdef):
        fd.write(self.constdef_template % {'valuename': constdef.name,
                                         'value': constdef.value})
        self.write_newline(fd)

    def write_enum_def(self, fd, enumdef):
        fd.write('class %s:\n' % enumdef.name)
        for vname, vdata in enumdef.values:
            fd.write('%s%s = %d\n' % (self.tab, vname, vdata))
        fd.write('\n')

    def write_message_def(self, fd, msgdef):
        tab = self.tab
        fd.write(self.msgdef_template % {'classname': msgdef.name,
                                       'struct': self.format_struct(msgdef.struct, tab)})

    def write_service_def(self, fd, svcdef):
        pass

    def format_struct(self, struct, tab):
        if type(struct) == types.ListType:
            return self.fields_template % {'fields':self.format_fields(struct, tab + self.tab),
                                         'tab':tab}
        else:
            return struct.name

    def format_fields(self, fields, tab):
        fieldstrs = []
        for field in fields:
            fieldstrs.append(self.field_template % {'name': field.name,
                                                  'type': self.format_type(field.type, tab),
                                                  'tab': tab,
                                                  'options':self.format_options(field.options)})
        return ',\n'.join(fieldstrs)

    def format_options(self, options):
        if options:

            optpairs = []
            for optname in options:
                if optname == 'default' and type(options['default']) == ValueRef:
                    optval = self.format_value_ref(options['default'])
                    optpairs.append('%s=%s' % (optname, optval))
                else:
                    optpairs.append('%s=%s' % (optname, repr(options[optname])))
            return ', ' + ', '.join(optpairs)

        else:
            return ''

    def format_value_ref(self, ref):
        d = self._curr_ns.resolve_value_ref(ref, self._context)
        if type(d) == EnumDef:
            return '%s.%s' % (d.name, ref.name)
        elif type(d) == ConstDef:
            return d.name
        else:
            assert False, "internal error"

    def format_type(self, typeinfo, tab):
        # print type(typeinfo), BuildInStructType
        if type(typeinfo) == BuildInStructType:
            return typeinfo.name[0].upper() + typeinfo.name[1:]
        elif (type(typeinfo) == TypedefMessageDef or
               type(typeinfo) == MessageDef):
            return typeinfo.name
        elif type(typeinfo) == ArrayStructType:
            return self.format_arraytype(typeinfo, tab + self.tab)
        elif type(typeinfo) == AnnoymousMessageDef:
            return self.format_struct(typeinfo.struct, tab + self.tab)
        elif type(typeinfo) == MapStructType:
            return self.format_maptype(typeinfo, tab + self.tab)
        elif type(typeinfo) == MessageDefReference:
            if typeinfo.ns is None:
                ns = self._curr_ns
            else:
                ns = self._context.get_all_namespace_slice_by_name(typeinfo.ns)
                if not ns:
                    raise RuntimeError("namespace `%s` not found,you need to add an \"#include\" clause or the path is incorrect" % typeinfo.ns)
                ns = ns[0]
            msgdef = ns.resolve_message_ref(typeinfo, self._context)
            if type(msgdef) == MessageDef:
                return msgdef.name
            elif type(msgdef) == EnumDef:
                return 'Int32'
            else:
                assert False, "internal error"
        else:
            raise ValueError("invlaid typeinfo type: %s" % type(typeinfo).__name__)

    def format_arraytype(self, arrtype, tab):
        return 'Array(%s)' % self.format_type(arrtype.elementtype, tab)

    def format_maptype(self, maptype, tab):
        return 'Map(%s,%s)' % (self.format_type(maptype.ktype, tab),
                              self.format_type(maptype.vtype, tab))

