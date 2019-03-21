# -*- coding: utf-8 -*-
'''JCE文件分析
'''

from qt4s._ply import lex, yacc
from qt4s._ply.lex import TOKEN
import types
import os
import re

from qt4s.message.compiler import Parser, ProtoLexicalError, ProtoSyntaxError
from qt4s.message.generator import CodeGenerator, LangSpecificDefHandler
from qt4s.message import generator


class KeyDef(object):
    '''JCE Key关键字定义
    '''

    def __init__(self, struct_name, field_names):
        self.struct = struct_name
        self.fields = field_names


class JceLexer(object):
    '''Jce文件语法分析器
    '''

    def build(self, file_path, **kwargs):
        """ Builds the lexer from the specification. Must be
            called after the lexer object is created.

            This method exists separately, because the PLY
            manual warns against calling lex.lex inside
            __init__
        """
        self.lexer = lex.lex(object=self, **kwargs)
        self.doxygenCommentCache = ''
        self._file_path = file_path

    def input(self, text):
        self.lexer.input(text)

    def token(self):
        self.last_token = self.lexer.token()
        return self.last_token

    def find_colno_by_lexpos(self, lexpos):
        if lexpos > 0:
            last_cr = self.lexer.lexdata.rfind('\n', 0, lexpos)
            return lexpos - last_cr
        else:
            return len(self.lexer.lexdata)

    def _find_tok_column(self, token):
        """ Find the column of the token in its line.
        """
        last_cr = self.lexer.lexdata.rfind('\n', 0, token.lexpos)
        return token.lexpos - last_cr

    def _error(self, msg, token):
        '''notify error
        '''
        location = self._make_tok_location(token)
        raise ProtoLexicalError(msg, self._file_path, location[0], location[1])
        self.lexer.skip(1)

    def _make_tok_location(self, token):
        return (token.lineno, self._find_tok_column(token))

    buildin_structtype = (
        'DOUBLE', 'FLOAT',
        'BYTE', 'INT', 'SHORT', 'LONG',
        'STRING',
        'BOOL',
        'VOID'
    )
    keywords = [
        'MODULE',
        'ENUM',
        'STRUCT',
        'INTERFACE',
        'OPTIONAL',
        'REQUIRE',
        'VECTOR',
        'MAP',
        'UNSIGNED',
        'CONST',
        'OUT',
        'KEY'
    ]

    keywords += list(buildin_structtype)
    keyword_map = {}
    for keyword in keywords:
        keyword_map[keyword.lower()] = keyword

    tokens = keywords + [
              'ID',
              'INT_CONST_DEC', 'INT_CONST_OCT', 'INT_CONST_HEX',
              'FLOAT_CONST', 'HEX_FLOAT_CONST',
              'BOOL_CONST',

              'STRING_LITERAL',
              'MACRO_INCLUDE',
#              'COMMENT_SINGLELINE',
#              'COMMENT_MULTILINE',
#              'NEWLINE',
              'LBRACE',
              'RBRACE',
              'LBRACKET',
              'RBRACKET',
              'LBRAKET',
              'RBRAKET',
              'LANGLE',
              'RANGLE',
              'SEMI',
              'EQUALS',
              'COMMA',

              'PLUS', 'MINUS',
              'NSOPS'
              ]

    # t_ignore = "\t \r.?@\f"
    t_ignore = "\t \r"

    t_MACRO_INCLUDE = r'\#include'
    t_NSOPS = r'::'
    t_LBRACE = r'{'
    t_RBRACE = r'}'
    t_LBRAKET = '\('
    t_RBRAKET = '\)'
    t_LBRACKET = r'\['
    t_RBRACKET = r'\]'
    t_LANGLE = r'<'
    t_RANGLE = r'>'
    t_SEMI = r';'
    t_EQUALS = r'='
    t_COMMA = r','
    t_PLUS = r'\+'
    t_MINUS = r'-'

    # valid C identifiers (K&R2: A.2.3), plus '$' (supported by some compilers)
    identifier = r'[a-zA-Z_$][0-9a-zA-Z_$]*'

    hex_prefix = '0[xX]'
    hex_digits = '[0-9a-fA-F]+'

    # integer constants (K&R2: A.2.5.1)
    integer_suffix_opt = r'(([uU]ll)|([uU]LL)|(ll[uU]?)|(LL[uU]?)|([uU][lL])|([lL][uU]?)|[uU])?'
    decimal_constant = '(0' + integer_suffix_opt + ')|([1-9][0-9]*' + integer_suffix_opt + ')'
    octal_constant = '0[0-7]*' + integer_suffix_opt
    hex_constant = hex_prefix + hex_digits + integer_suffix_opt

    bad_octal_constant = '0[0-7]*[89]'

    # character constants (K&R2: A.2.5.2)
    # Note: a-zA-Z and '.-~^_!=&;,' are allowed as escape chars to support #line
    # directives with Windows paths as filenames (..\..\dir\file)
    # For the same reason, decimal_escape allows all digit sequences. We want to
    # parse all correct code, even if it means to sometimes parse incorrect
    # code.
    #
    simple_escape = r"""([a-zA-Z._~!=&\^\-\\?'"])"""
    decimal_escape = r"""(\d+)"""
    hex_escape = r"""(x[0-9a-fA-F]+)"""
    bad_escape = r"""([\\][^a-zA-Z._~^!=&\^\-\\?'"x0-7])"""

    escape_sequence = r"""(\\(""" + simple_escape + '|' + decimal_escape + '|' + hex_escape + '))'
    cconst_char = r"""([^'\\\n]|""" + escape_sequence + ')'
    char_const = "'" + cconst_char + "'"
    wchar_const = 'L' + char_const
    unmatched_quote = "('" + cconst_char + "*\\n)|('" + cconst_char + "*$)"
    bad_char_const = r"""('""" + cconst_char + """[^'\n]+')|('')|('""" + bad_escape + r"""[^'\n]*')"""

    # string literals (K&R2: A.2.6)
    string_char = r"""([^"\\\n]|""" + escape_sequence + ')'
    string_literal = '"' + string_char + '*"'
    bad_string_literal = '"' + string_char + '*' + bad_escape + string_char + '*"'

    # floating constants (K&R2: A.2.5.3)
    exponent_part = r"""([eE][-+]?[0-9]+)"""
    fractional_constant = r"""([0-9]*\.[0-9]+)|([0-9]+\.)"""
    floating_constant = '((((' + fractional_constant + ')' + exponent_part + '?)|([0-9]+' + exponent_part + '))[FfLl]?)'
    binary_exponent_part = r'''([pP][+-]?[0-9]+)'''
    hex_fractional_constant = '(((' + hex_digits + r""")?\.""" + hex_digits + ')|(' + hex_digits + r"""\.))"""
    hex_floating_constant = '(' + hex_prefix + '(' + hex_digits + '|' + hex_fractional_constant + ')' + binary_exponent_part + '[FfLl]?)'

    boolean_constant = r'\b(true)\b|\b(false)\b'

    @TOKEN(string_literal)
    def t_STRING_LITERAL(self, t):
        # t.value = eval(t.value)
        return t

    @TOKEN(floating_constant)
    def t_FLOAT_CONST(self, t):
        t.value = float(t.value)
        return t

    @TOKEN(hex_floating_constant)
    def t_HEX_FLOAT_CONST(self, t):
        t.value = float(t.value)
        return t

    @TOKEN(hex_constant)
    def t_INT_CONST_HEX(self, t):
        t.value = int(t.value, 16)
        return t

    @TOKEN(bad_octal_constant)
    def t_BAD_CONST_OCT(self, t):
        msg = "Invalid octal constant"
        self._error(msg, t)

    @TOKEN(octal_constant)
    def t_INT_CONST_OCT(self, t):
        t.value = int(t.value, 8)
        return t

    @TOKEN(decimal_constant)
    def t_INT_CONST_DEC(self, t):
        t.value = int(t.value)
        return t

    @TOKEN(boolean_constant)
    def t_BOOL_CONST(self, t):
        t.value = bool(t.value)
        return t

    @TOKEN(unmatched_quote)
    def t_UNMATCHED_QUOTE(self, t):
        msg = "Unmatched '"
        self._error(msg, t)
    # unmatched string literals are caught by the preprocessor

    @TOKEN(bad_string_literal)
    def t_BAD_STRING_LITERAL(self, t):
        msg = "String contains invalid escape code"
        self._error(msg, t)

    def t_ID(self, t):
        r'[a-zA-Z_$][0-9a-zA-Z_$]*'
        t.type = self.keyword_map.get(t.value, "ID")
        return t

    def t_COMMENT_SINGLELINE(self, t):
        r'\/\/.*\n'
        if t.value.startswith("///") or t.value.startswith("//!"):
            if self.doxygenCommentCache:
                self.doxygenCommentCache += "\n"
            if t.value.endswith("\n"):
                self.doxygenCommentCache += t.value[:-1]
            else:
                self.doxygenCommentCache += t.value
        t.lexer.lineno += len(filter(lambda a: a == "\n", t.value))
        # return t

    def t_COMMENT_MULTILINE(self, t):
        r'/\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/'
        if t.value.startswith("/**") or t.value.startswith("/*!"):
            # not sure why, but get double new lines
            v = t.value.replace("\n\n", "\n")
            # strip prefixing whitespace
            v = re.sub("\n[\s]+\*", "\n*", v)
            self.doxygenCommentCache += v
        t.lexer.lineno += len(filter(lambda a: a == "\n", t.value))
        # return t

    def t_NEWLINE(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)
        # return t

    def t_error(self, t):
        msg = 'Illegal character %s' % repr(t.value[0])
        self._error(msg, t)


class JceParser(Parser):
    '''JCE文件解析器
    '''
    precedence = (
    )

    def __init__(self, file_path, context):
        '''构造函数
        '''
        self.lexer = JceLexer()
        self.lexer.build(file_path)
        self.tokens = self.lexer.tokens
        self.parser = yacc.yacc(module=self)
        self._file_path = file_path
        self._context = context
        self._module = generator.Module(file_path, self._error)

    def get_source_path(self):
        '''获取源文件路径
        '''
        return self._file_path

    def get_module(self):
        '''获取对应的模块
        '''
        return self._module

    def parse(self):
        '''解析
        '''
        self._parse(self._file_path)

    def _parseString(self, data):
        '''解析字符串
        '''
        self.parser.parse(data)

    def _parse(self, filename):
        '''解析文件
        '''
        with open(filename, 'r') as fd:
            return self._parseString(fd.read())

    def _import_module(self, name, lexpos, lineno):
        '''处理import
        '''
        name = name[1:-1]
        for path in self._context.get_import_paths():
            modulepath = os.path.join(path, name)
            if os.path.isfile(modulepath):
                self._context.import_module(modulepath)
                break
        else:
            return self._error(lexpos, lineno, 'include resolve error, "%s" not found' % name)

    def _error(self, lexpos, lineno, msg):
        '''处理错误
        '''
        raise ProtoSyntaxError(msg, self._file_path, lineno, self.lexer.find_colno_by_lexpos(lexpos))

    # ----- 以下是语法分析定义 -----
    def p_scope_define(self, p):
        """scope : scopeitem
                 | scope scopeitem
        """
        pass

    def p_scopeitem_define(self, p):
        """scopeitem : namespace
                     | importexpr
        """
        pass

    def p_namespace_define(self, p):
        """ namespace :  MODULE ID LBRACE exprs RBRACE SEMI
        """
        nsslice = generator.NamespaceSlice(p[2], p[4], self._error)
        for expr in p[4]:
            expr.nsslice = nsslice
        self._module.add_namespace_slice(nsslice, p.lexpos(2), p.lineno(2))
        p[0] = nsslice

    def p_exprs_define(self, p):
        """exprs :
                 | expr
                 | exprs expr
        """
        if len(p) == 1:
            p[0] = []
        elif len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = p[1]
            p[0].append(p[2])

    def p_expr_define(self, p):
        """expr : messagedef
                | constdeclexpr
                | enumexpr
                | servicedef
                | keydef
        """
        p[0] = p[1]

    # messagedef
    def p_messagedef_define(self, p):
        """messagedef : STRUCT ID LBRACE fielddefs RBRACE SEMI"""
        p[0] = generator.MessageDef(p[2], p[4])
        p[0].lexpos, p[0].lineno = p.lexpos(2), p.lineno(2)

    def p_fielddefs_define(self, p):
        """fielddefs :
                     | fielddefs fielddef
        """
        if len(p) == 1:
            p[0] = []
        else:
            p[0] = p[1]
            p[0].append(p[2])

    def p_fielddef_define(self, p):
        """fielddef : fieldid optionsfield structtype ID arroption defaultvalue SEMI
        """
        opts = p[2]
        opts['tag'] = p[1]
        if p[5] is not None:
            elementtype = p[3]
            if type(elementtype) == generator.BuildInStructType and elementtype.name == 'uint8':
                structtype = generator.BuildInStructType('buffer')
                opts['string_size'] = p[5]
            else:
                structtype = generator.ArrayStructType(p[3])
                opts['array_size'] = p[5]
        else:
            structtype = p[3]
        if p[6] is not None:
            opts['default'] = p[6]

        p[0] = generator.FieldDef(p[4], structtype, opts)

    def p_fieldid_define(self, p):
        """fieldid : INT_CONST_DEC
                    | INT_CONST_OCT
        """
        p[0] = int(p[1])

    def p_optionsfield_define(self, p):
        """optionsfield : REQUIRE
                        | OPTIONAL
        """
        if p[1] == 'optional':
            p[0] = {'optional':True}
        else:
            p[0] = {}

    def p_arroption_define(self, p):
        """arroption : 
                    | LBRACKET fieldid RBRACKET
        """
        if len(p) == 4:
            p[0] = p[2]
        else:
            p[0] = None

    def p_defaultvalue_define(self, p):
        """defaultvalue : 
                        | EQUALS constvalue
        """
        if len(p) == 1:
            p[0] = None
        else:
            p[0] = p[2]

    def p_structtype_define(self, p):
        """structtype : DOUBLE
                      | FLOAT
                      | BOOL
                      | STRING
                      | integertype
                      | arraystruct
                      | mapstruct
                      | ID
                      | ID NSOPS ID 
        """
        if len(p) == 4:
            msgdef = generator.MessageDefReference(p[3], p[1])
            msgdef.lexpos = p.lexpos(1)
            msgdef.lineno = p.lineno(1)
            p[0] = msgdef
        else:
            if type(p[1]) == types.StringType:
                if p[1].upper() in self.lexer.buildin_structtype:
                    msgdef = generator.BuildInStructType(p[1])
                else:
                    msgdef = generator.MessageDefReference(p[1])
                    msgdef.lexpos = p.lexpos(1)
                    msgdef.lineno = p.lineno(1)
                p[0] = msgdef
            else:
                p[0] = p[1]

    jcetypemap = {
        'bool': 'bool',
        'byte': 'uint8',
        'short': 'int16',
        'int': 'int32',
        'long': 'int64',
        'float': 'float',
        'double': 'double',
        'string': 'string',
    }
    unsigned_jcetypemap = {
        'bool': 'bool',
        'byte': 'int16',
        'short': 'int32',
        'int': 'int64',
        'long': 'uint64',
        'float': 'float',
        'double': 'double',
        'string': 'string',
    }

    def p_integerrtype_define(self, p):
        """ integertype : UNSIGNED bareintegertype
                       | bareintegertype
        """
        if len(p) == 3:
            p[0] = generator.BuildInStructType(self.unsigned_jcetypemap[p[2]])
        else:
            p[0] = generator.BuildInStructType(self.jcetypemap[p[1]])

    def p_bareintegertype_define(self, p):
        """ bareintegertype : INT
                            | SHORT
                            | BYTE
                            | LONG
        """
        p[0] = p[1]

    def p_arraystruct_define(self, p):
        """arraystruct : VECTOR LANGLE structtype RANGLE
        """
        elementtype = p[3]
        if type(elementtype) == generator.BuildInStructType and elementtype.name == 'uint8':
            p[0] = generator.BuildInStructType('buffer')
        else:
            p[0] = generator.ArrayStructType(p[3])

    def p_mapstruct_define(self, p):
        """mapstruct : MAP LANGLE structtype COMMA structtype RANGLE
        """
        p[0] = generator.MapStructType(p[3], p[5])

    # constdeclexpr
    def p_constdeclexpr_define(self, p):
        """constdeclexpr : CONST constabletype ID EQUALS constvalue SEMI
        """
        p[0] = generator.ConstDef(p[2], p[3], p[5])
        p[0].lineno, p[0].lexpos = p.lineno(2), p.lexpos(2)

    def p_constabletype_define(self, p):
        """constabletype : integertype
                         | FLOAT
                         | DOUBLE
                         | STRING
                         | BOOL
        """
        p[0] = p[1]

    def p_constvalue_define(self, p):
        """constvalue : BOOL_CONST
                      | STRING_LITERAL
                      | integerconst
                      | floatconst
                      | refvalue
        """
        p[0] = p[1]

    def p_refvalue_define(self, p):
        """refvalue : ID
                        | ID NSOPS ID
        """
        if len(p) == 2:
            ref = generator.ValueRef(p[1])
            ref.lexpos = p.lexpos(1)
            ref.lineno = p.lineno(1)
        else:
            ref = generator.ValueRef(p[3], p[1])
            ref.lexpos = p.lexpos(3)
            ref.lineno = p.lineno(3)
        p[0] = ref

    def p_integerconst_define(self, p):
        """integerconst : signop bareintegerconst
        """
        if p[1] == '-':
            p[0] = -p[2]
        else:
            p[0] = p[2]

    def p_bareintegerconst_define(self, p):
        """bareintegerconst : INT_CONST_HEX
                          | INT_CONST_OCT
                          | INT_CONST_DEC
        """
        p[0] = p[1]

    def p_signop_define(self, p):
        """signop : 
                  | PLUS
                  | MINUS
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = '+'

    def p_floatconst_define(self, p):
        """floatconst : signop barefloatconst
        """
        if p[1] == '-':
            p[0] = -p[2]
        else:
            p[0] = p[2]

    def p_barefloatconst_define(self, p):
        """barefloatconst : FLOAT_CONST
                          | HEX_FLOAT_CONST
        """
        p[0] = p[1]

    # enumexpr
    def p_enumexpr_define(self, p):
        """enumexpr : ENUM ID LBRACE enumvalues RBRACE SEMI
        """
        p[0] = generator.EnumDef(p[2], p[4])
        p[0].lineno, p[0].lexpos = p.lineno(2), p.lexpos(2)

    def p_enumvalues_define(self, p):
        """enumvalues : enumvalue
                      | enumvalues COMMA enumvalue
        """
        if len(p) == 4:
            p[0] = p[1]
            if p[3] is not None:
                p[0].append(p[3])
        else:
            p[0] = []
            if p[1] is not None:
                p[0].append(p[1])

    def p_enumvalue_define(self, p):
        """enumvalue : 
                     | ID
                     | ID EQUALS integerconst
        """
        if len(p) == 2:
            p[0] = (p[1], None)
        elif len(p) == 1:
            p[0] = None
        else:
            p[0] = (p[1], p[3])

    # servicedef
    def p_servicedef_define(self, p):
        """servicedef : INTERFACE ID LBRACE rpcdefs RBRACE SEMI
        """
        p[0] = generator.ServiceDef(p[2], p[4])
        p[0].lineno, p[0].lexpos = p.lineno(2), p.lexpos(2)

    def p_rpcdefs_define(self, p):
        """rpcdefs : 
                   | rpcdefs rpcdef
        """
        if len(p) == 1:
            p[0] = []
        else:
            p[1].append(p[2])
            p[0] = p[1]

    def p_rpcdef_define(self, p):
        """rpcdef : returntype ID LBRAKET params RBRAKET SEMI
        """
        in_msgs = []
        out_msgs = []
        for inoutflag, structtype, name in p[4]:
            if inoutflag == 0:
                in_msgs.append((structtype, name))
            else:
                out_msgs.append((structtype, name))
        p[0] = generator.RpcDef(p[2], in_msgs, out_msgs, [], p[1])

    def p_returntype_define(self, p):
        """returntype : structtype
                      | VOID
        """
        p[0] = p[1]

    def p_params_define(self, p):
        """params : 
                 | param
                 | params COMMA param
        """
        if len(p) == 1:
            p[0] = []
        elif len(p) == 2:
            p[0] = [p[1]]
        else:
            p[1].append(p[3])
            p[0] = p[1]

    def p_param_define(self, p):
        """param : inoutflag structtype ID
        """
        p[0] = (p[1], p[2], p[3])

    def p_inoutflag_define(self, p):
        """inoutflag :
                     | OUT
        """
        if len(p) == 1:
            p[0] = 0
        else:
            p[0] = 1

    # keydef
    def p_keydef_define(self, p):
        """keydef : KEY LBRACKET ID COMMA keyfields RBRACKET SEMI
        """
        p[0] = KeyDef(p[3], p[5])
        p[0].lexpos, p[0].lineno = p.lexpos(0), p.lineno(0)

    def p_keyfields_define(self, p):
        """keyfields : ID
                    | keyfields COMMA ID
        """
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[1].append(p[3])
            p[0] = p[1]

    # importexpr
    def p_importexpr_define(self, p):
        """importexpr : MACRO_INCLUDE STRING_LITERAL
        """
        self._import_module(p[2], p.lexpos(2), p.lineno(2))
        p[0] = generator.ImportDef(p[2])
        self._module.add_import_def(p[0])

    def p_error(self, p):
        '''处理错误
        '''
        if p != None:
            self._error(p.lexpos, p.lineno, 'invalid syntax in file: %s at pos=%s,line=%s' % (self._file_path, p.lexpos, p.lineno))
        else:
            # resort the stack order
            stack = ""
            for sym in self.parser.symstack[1:]:
                stack += sym.type + " "
            stack += "--> " + self.parser.symstack[0].type
            self._error(0, 0, "unexpected end of file:\nsymstack=%s" % stack)


class JceCodeGenerator(CodeGenerator):

    msgdef_template = """class %(classname)s(Message):
    __taf_class__ = %(tafname)s
    _struct_ = %(struct)s"""

    def write_message_def(self, fd, msgdef):
        tab = self.tab
        tafname = '"%s.%s"' % (msgdef.nsslice.name, msgdef.name)
        fd.write(self.msgdef_template % {'classname': msgdef.name,
                                       'tafname': tafname,
                                       'struct': self.format_struct(msgdef.struct, tab)})


class JceLangExt(LangSpecificDefHandler):
    '''JCE语言扩展
    '''

    def on_generate(self, fd, context, curr_ns, d):
        msg_def = curr_ns.get_message_def(d.struct)
        for fieldname in d.fields:
            for it in msg_def.struct:
                if it.name == fieldname:
                    break
            else:
                raise ValueError("key defition error, invalid field '%s' for '%s'" % (fieldname, d.struct))
        print 'WARNING: unsupported jce keyword "key" for "%s", ignore it' % d.struct

