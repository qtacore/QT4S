# -*- coding: utf-8 -*-
'''QT4S命令
'''

import argparse
import os
import sys
import subprocess
import pkg_resources

from testbase.management import Command

from qt4s.message.parsers.jce import JceParser, JceCodeGenerator, JceLangExt
from qt4s.message.parsers.taf import TAFJceCodeGenerator
from qt4s.message.compiler import Compiler


class ProtoCompile(Command):
    '''将协议文件转换为QT4S消息格式
    '''
    name = 'protoc'
    parser = argparse.ArgumentParser("compile protocol file into message definition file")
    parser.add_argument('target', help="protocol file path")
    parser.add_argument('-t', '--type', dest='type', default='auto', help="designate protocol file type, could be \"pb\" \"jce\" default is \"auto\"")
    parser.add_argument('-I', '--include', default=[], nargs='*', dest='include_paths', help="include protocol file path")

    def _compile_pb(self, protoc_path, target, include_paths):
        include_paths = include_paths[:]
        target_dir = os.path.dirname(target)
        include_paths.append(target_dir)
        cmdlines = [protoc_path, target, '--python_out', target_dir]
        for include_path in include_paths:
            cmdlines.append('-I')
            cmdlines.append(include_path)
        print 'compiling: ' + target
        subprocess.call(cmdlines)

    def execute(self, args):
        '''执行过程
        '''
        if args.type.lower() == 'auto':
            if args.target.lower().endswith('.proto'):
                args.type = 'pb'
            elif args.target.lower().endswith('.jce'):
                args.type = 'jce'

        args.target = os.path.abspath(args.target)
        if args.type.lower() == 'pb':

            tools_dir = pkg_resources.resource_filename("qt4s.message", "tools")  # @UndefinedVariable
            if sys.platform == 'win32':
                protoc_path = os.path.join(tools_dir, 'protoc.exe')
            else:
                protoc_path = os.path.join(tools_dir, 'protoc')
                os.chmod(protoc_path, 0755)

            if os.path.isfile(args.target):
                self._compile_pb(protoc_path, args.target, args.include_paths)

            elif os.path.isdir(args.target):

                args.include_paths.append(args.target)
                for filename in os.listdir(args.target):
                    if filename.endswith('_pb2.py'):
                        filepath = os.path.join(args.target, filename)
                        if os.path.isfile(filepath):
                            print 'clean', filepath
                            os.remove(filepath)

                for filename in os.listdir(args.target):
                    if filename.endswith('.proto'):
                        filepath = os.path.join(args.target, filename)
                        dstname = os.path.basename(filename)
                        dstname = dstname[0:dstname.rfind('.')] + '_pb2.py'
                        dstfile = os.path.join(os.path.dirname(args.target), dstname)
                        if os.path.isfile(dstfile):
                            continue
                        else:
                            self._compile_pb(protoc_path, filepath, args.include_paths)

            else:
                raise RuntimeError("target not found")

        else:
            if args.type.lower() == 'jce':
                generator_class = JceCodeGenerator
                parser_class = JceParser
                extension = JceLangExt()
                subfix = 'jce'

            elif args.type.lower() == 'taf':
                generator_class = TAFJceCodeGenerator
                parser_class = JceParser
                extension = JceLangExt()
                subfix = 'jce'

            else:
                raise ValueError("unsupported protocol type: \"%s\"" % args.type)

            if os.path.isfile(args.target):
                args.include_paths.append(os.path.dirname(args.target))
                c = Compiler(parser_class, generator_class, args.include_paths, subfix, extension)
                print 'compiling %s' % args.target
                c.compile(args.target)

            elif os.path.isdir(args.target):
                args.include_paths.append(args.target)
                c = Compiler(parser_class, generator_class, args.include_paths, subfix, extension)
                for filename in os.listdir(args.target):
                    if filename.endswith('_%s.py' % subfix):
                        filepath = os.path.join(args.target, filename)
                        if os.path.isfile(filepath):
                            print 'clean', filepath
                            os.remove(filepath)

                for filename in os.listdir(args.target):
                    if filename.endswith('.%s' % subfix):
                        filepath = os.path.join(args.target, filename)
                        dstfile = os.path.join(args.target, filename.replace('.', '_') + '.py')
                        if os.path.isfile(dstfile):
                            continue
                        else:
                            print 'compiling %s' % filepath
                            c.compile(filepath)

            else:
                raise RuntimeError("target not found")
