# -*- coding: utf-8 -*-
'''数据库使用支持

使用示例::

    db = Database( 'localhost', 3306, 'root', '****', 'foo')
    results = db.table('tttt').select().where(Field('sss')!='90')
    print results[1]
    print len(results)
    for it in results:
        print it.id, it

    results = db.table('tttt').select('sss').where(Field('sss')=='XXX')
    for it in results:
        print it

    results = db.table('tttt').select('sss')
    for it in results:
        print it
    
'''

import _proxy
import socket
import MySQLdb as mysql

from MySQLdb.cursors import DictCursor
from testbase.conf import settings


class SelectStmt(object):
    '''SQL查询语句
    '''

    def __init__(self, db, tablename, colnames=None, filters=None):
        self._db = db
        self._tablename = tablename
        self._colnames = colnames
        self._filters = filters

    def to_sql(self):
        '''转换为对应的SQL语句
        '''
        if not self._colnames:
            cols = '*'
        else:
            cols = ','.join(self._colnames)
        sql = 'SELECT %s FROM %s' % (cols, self._tablename)
        if self._filters:
            sql += ' WHERE (%s)' % (' and '.join(self._filters))
        # print sql
        return sql


class Row(object):
    '''数据库表行
    '''

    def __init__(self, tablename, colnames, values):
        self._tablename = tablename
        self._colnames = colnames
        self._vals = values

    def __repr__(self):
        obj = []
        for idx, name in enumerate(self._colnames):
            obj.append('%s=%s' % (name, repr(self._vals[idx])))
        if self._tablename.startswith('t_'):
            tname = self._tablename[2:]
        else:
            tname = self._tablename
        return '<%s: %s>' % (tname, ' '.join(obj))

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            for idx, it in enumerate(self._colnames):
                if it == name:
                    return self._vals[idx]
            else:
                return object.__getattribute__(self, name)

    def __getitem__(self, name):
        for idx, it in enumerate(self._colnames):
            if it == name:
                return self._vals[idx]
        else:
            raise KeyError()


class CursorIterator(object):
    '''封装MYSQL的CursorIterator
    '''

    def __init__(self, tablename, colnames, cur_it):
        self._tablename = tablename
        self._colnames = colnames
        self._cur_it = cur_it

    def __iter__(self):
        return self

    def next(self):
        return Row(self._tablename, self._colnames, self._cur_it.next())


class RowList(object):
    '''数据库表行集合
    '''

    def __init__(self, db, tablename, colnames, filters=None):
        self._sql = SelectStmt(db, tablename, colnames)
        self._colnames = colnames
        self._tablename = tablename
        self._db = db
        self._cur = None
        self._filters = filters

    def __del__(self):
        if self._cur:
            self._cur.close()

    def _query(self):
        if self._cur:
            return
        self._cur = self._db.cursor()
        if not self._colnames:
            self._colnames = self._get_all_colnames()
        sql = SelectStmt(self._db, self._tablename, self._colnames, self._filters)
        self._cur.execute(sql.to_sql())

    def __iter__(self):
        self._query()
        return CursorIterator(self._tablename, self._colnames, self._cur.__iter__())

    def _get_all_colnames(self):
        '''获取表格的全部行的名称
        '''
        self._cur.execute('show columns from %s' % self._tablename)
        colnames = []
        for it in self._cur:
            colnames.append(it[0])
        return colnames

    def where(self, *filters):
        '''增加筛选条件
        '''
        if self._filters is not None:
            raise Exception('only one where-cause allowed')
        return RowList(self._db, self._tablename, self._colnames, filters)

    def __getitem__(self, idx):
        self._query()
        for id, it in enumerate(self):
            if id == idx:
                return it
        else:
            raise IndexError('row index out of range')

    def __len__(self):
        self._query()
        length = 0
        for _ in self._cur: length += 1
        return length


class Table(object):
    '''数据库表使用接口
    '''

    def __init__(self, db, name):
        self._db = db
        self._name = name

    def select(self, *colnames):
        '''执行Select查询
        '''
        return RowList(self._db, self._name, colnames)

#     def execute_sql(self, sql_str):
#         '''执行sql语句
#         '''
#         return self._db.cursor().execute( sql_str )


class Field(object):
    '''字段
    '''

    def __init__(self, name):
        self._name = name

    def _repr(self, v):
        if isinstance(v, unicode):
            return v.encode('utf8')
        else:
            return repr(v)

    def __eq__(self, val):
        return '%s=%s' % (self._name, self._repr(val))

    def __lt__(self, val):
        return '%s<%s' % (self._name, self._repr(val))

    def __gt__(self, val):
        return '%s>%s' % (self._name, self._repr(val))

    def __le__(self, val):
        return '%s<=%s' % (self._name, self._repr(val))

    def __ge__(self, val):
        return '%s>=%s' % (self._name, self._repr(val))

    def __ne__(self, val):
        return '%s!=%s' % (self._name, self._repr(val))

    def like(self, val):
        return '%s like %s' % (self._name, self._repr(val))


class Database(object):
    '''数据库使用接口
    '''

    def __init__(self, host, port, user, passwd, database, location=None, autocommit=True, charset=None):
        if location is None:
            location = settings.QT4S_DEFAULT_LOCATION
        proxy = _proxy.ProxyController().get_tcp_proxy_clib(location)
        if proxy:
            self._proxy = proxy.context(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, (host, port))
        else:
            self._proxy = None
        self._host = host
        self._port = port
        self._user = user
        self._passwd = passwd
        self._database = database
        self._conn = None
        self._cursors = []
        self._autocommit = True
        self._charset = charset

    def _get_conn(self):
        if self._conn is None:
            if self._proxy:
                with self._proxy:
                    self._conn = mysql.connect(host=self._host, port=self._port,
                                               user=self._user, passwd=self._passwd,
                                               db=self._database, charset=self._charset)
            else:
                self._conn = mysql.connect(host=self._host, port=self._port,
                                               user=self._user, passwd=self._passwd,
                                               db=self._database, charset=self._charset)
            self._conn.autocommit(self._autocommit)
        return self._conn

    def table(self, name):
        '''获取特定数据表的操作接口
        '''
        return Table(self._get_conn(), name)

    def cursor(self, cursorclass=None):
        if cursorclass:
            cursor = self._get_conn().cursor(cursorclass=cursorclass)
        else:
            cursor = self._get_conn().cursor()
        self._cursors.append(cursor)
        return cursor

    def dict_cursor(self):
        return self.cursor(DictCursor)

    def commit(self):
        return self._get_conn().commit()

    def execute(self, operation):
        '''执行SQL语句，并返回对应的cursor
        '''
        cursor = self.cursor()
        cursor.execute(operation)
        return cursor

    def __del__(self):
        self.close()

    def close(self):
        '''close database
        '''
        for cursor in self._cursors:
                cursor.close()
        if self._conn:
            self._conn.close()
            self._conn = None

