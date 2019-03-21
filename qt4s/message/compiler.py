# -*- coding: utf-8 -*-
'''将各种格式的形式化描述转换为qt4s.message框架定义的Python代码
'''

import locale
import os
import sys

qt4sroot = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(qt4sroot)

from qt4s.message.generator import CodeGenerator, Context
os_encoding = locale.getdefaultlocale()[1]


class ProtoSyntaxError(Exception):
    '''协议语法错误
    '''

    def __init__(self, msg, filepath, lineno, colno):
        self.msg = msg
        self.lineno = lineno
        self.colno = colno
        self.filepath = filepath

    def __str__(self):
        return 'at %s %d:%d, %s' % (self.filepath, self.lineno, self.colno, self.msg)


class ProtoLexicalError(Exception):
    '''协议词法错误
    '''

    def __init__(self, msg, filepath, lineno, colno):
        self.msg = msg
        self.lineno = lineno
        self.colno = colno
        self.filepath = filepath

    def __str__(self):
        return 'at %s %d:%d, %s' % (self.filepath, self.lineno, self.colno, self.msg)


class Parser(object):
    '''解析器接口
    '''

    def parse(self):
        '''解析
        '''
        pass


class Compiler(object):
    '''编译器
    '''

    def __init__(self, parser_class, generator_class, import_paths, subfix='proto', ext=None):
        '''构造函数
        '''
        self._cls = parser_class
        self._gen_cls = generator_class
        self._paths = import_paths
        self._subfix = subfix
        self._ext = ext

    def compile(self, proto_file):
        '''编译
        '''
        ctx = Context(self._cls, self._paths)
        ctx.import_module(proto_file)
        generator = self._gen_cls(ctx)
        for parser in ctx.get_parsers():
            dstfile = parser.get_source_path()
            dstfilename = os.path.basename(dstfile).replace('.', '_') + '.py'
            dstfile = os.path.join(os.path.dirname(dstfile), dstfilename)
            generator.generate(parser.get_module(), dstfile, self._ext)


class CompilerApp(object):
    '''编译器
    '''
    USAGE = """\
用法: %(ProgName)s [选项] 协议形式化描述文件或目录

协议形式化描述文件或目录：
    描述协议格式的的文件或目录，比如*.proto、*.jce等。如果指定的是目录，则会编译该目录下的所有协议文件

选项：
  -h               显示本帮助信息
  -i  includeDirs  设置工作目录，设置导入文件路径
  -t  protoType    指定协议形式化描述的类型，可选的选项有jce、json、protobuf等

例子:
  %(ProgName)s -t jce C:\workspace\test.jce
        解析test.jce文件，并生成对应的QT4S消息定义Python代码文件test_jce.py
  
"""

    def __init__(self, proto_map):
        self._protomap = proto_map
        self.includeDirs = []
        self._parse_args()

    def _print_usage(self):
        '''打印帮助信息
        '''
        msg = CompilerApp.USAGE.decode('utf8').encode(os_encoding)
        print msg % {'ProgName':os.path.basename(sys.argv[0])}
        sys.exit(0)

    def _parse_args(self):
        '''解析参数
        '''
        import getopt
        argv = sys.argv
        try:
            options, args = getopt.getopt(argv[1:], 'ht:i:')
            for opt, value in options:
                if opt in ('-h'):
                    self.printUsage()
                if opt in ('-t'):
                    self.protoType = value
                if opt in ('-i'):
                    self.includeDirs = value.split(';')
            if len(args) == 0:
                self._print_usage()
            else:
                self.target = args[0]
        except getopt.error:
            self._print_usage()

    def run(self):
        '''主过程
        '''
        protoinfo = self._protomap[self.protoType]
        if os.path.isfile(self.target):
            imps = [os.path.dirname(self.target)]
            ext = protoinfo.get('extension', None)
            c = Compiler(protoinfo['class'], protoinfo.get('generator', CodeGenerator), imps, protoinfo['subfix'], ext)
            print 'compiling %s' % self.target
            c.compile(self.target)
        else:
            imps = [self.target]
            c = Compiler(protoinfo['class'], protoinfo.get('generator', CodeGenerator), imps, protoinfo['subfix'])
            for it in os.listdir(self.target):
                if it[-4 - len(protoinfo['subfix']):] == '_%s.py' % (protoinfo['subfix']):
                    item = os.path.join(self.target, it)
                    if os.path.isfile(item):
                        print 'clean', item
                        os.remove(item)

            for it in os.listdir(self.target):
                subfix = it[it.rfind('.') + 1:].lower()
                if subfix == protoinfo['subfix']:
                    item = os.path.join(self.target, it)
                    dst = os.path.join(os.path.dirname(self.target), os.path.basename(self.target).replace('.', '_') + '.py')
                    if os.path.isfile(dst):
                        continue
                    else:
                        print 'compiling %s' % item
                        c.compile(item)


if __name__ == '__main__':
    from qt4s.message.parsers.jce import JceParser, JceCodeGenerator, JceLangExt
    from qt4s.message.parsers.taf import TAFJceCodeGenerator
    protomap = {
        'jce': {
            'class': JceParser,
            'subfix':'jce',
            'generator': JceCodeGenerator,
            'extension': JceLangExt(),
        },

        'taf':{
            'class': JceParser,
            'subfix':'jce',
            'generator': TAFJceCodeGenerator,
            'extension': JceLangExt(),
        }
    }
    CompilerApp(protomap).run()
