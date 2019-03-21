# -*- coding: utf-8 -*-
'''TAF使用的JCE文件分析

TAF使用的JCE文件中会包含interface字段
'''

import jce
from qt4s.message import generator
from StringIO import StringIO

TAB = '    '


class TAFJceCodeGenerator(jce.JceCodeGenerator):
    """TAF专用的JCE定义生成器
    """

    def write_service_def(self, fd, svcdef):
        fd.write('class %s:\n\n' % svcdef.name)
        for it in svcdef.rpcs:
            msgdef = self._construct_msg(it.name + 'Req', it.ins)
            self._write_message_def(fd, '%s.%s.request' % (svcdef.name, it.name), msgdef)
            msgdef = self._construct_msg(it.name + 'Rsp', it.outs)
            self._write_message_def(fd, '%s.%s.response' % (svcdef.name, it.name), msgdef)
            fd.write('\n')

    def _construct_msg(self, msgname, params):
        fields = []
        for struct_type, name in params:
            fields.append(generator.FieldDef(name, struct_type, {}))
        return generator.MessageDef(msgname, fields)

    def _write_message_def(self, fd, tafname, msgdef):
        sfd = StringIO()
        tab = self.tab
        sfd.write(self.msgdef_template % {'classname': msgdef.name,
                                       'tafname': "'%s'" % tafname,
                                       'struct': self.format_struct(msgdef.struct, tab)})

        data = sfd.getvalue()
        for line in data.split('\n'):
            fd.write(TAB + line + '\n')
