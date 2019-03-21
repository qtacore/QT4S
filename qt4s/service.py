# -*- coding: utf-8 -*-
'''服务定义
'''

import types
import inspect
import sys
import pkgutil

_default_rpc_timeout = 60


class Channel(object):
    '''通道接口
    '''
    _g_channels = []

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        Channel._g_channels.append(obj)
        return obj

    def call_method(self, methodid, request, response_class, timeout):
        '''调用方法
        '''
        pass

    def close(self):
        '''销毁通道
        '''
        pass

    @staticmethod
    def close_all():
        '''销毁全部的通道
        '''
        for it in Channel._g_channels:
            it.close()


class Service(object):
    '''服务定义接口
    '''
    _name_ = None
    _services_ = ()
    _methods_ = ()
    _methodnamehook_ = None
    _request_timeout_ = 10

    def __init__(self, channel):
        self._parent = None
        self._channel = channel
        self._method_root = MethodInstanceHop('+')
        for it in self._methods_:
            self._create_method_instance(it)
        for it in self._services_:
            if type(it) == types.DictType:
                self._create_subservices(it['_name_'], it.get('_methods_', list()), it.get('_services_', list()))
            elif type(it) == type and issubclass(it, Service):
                self._create_subservice_instance(it)
            else:
                raise ValueError('type of element of "_services_" should be Dict instance or Service type, not %s' % str(it))

    def _set_prefix(self, prefix):
        '''设置名称前缀（父服务调用）
        '''
        self._prefix = prefix

    def _set_parent(self, service):
        '''设置父服务（父服务调用）
        '''
        self._parent = service

    def _accept(self, name):
        '''函数实例跳板查询下个节点是否和调用函数名符合
        '''
        return self._name_.lower() == name.lower()

    def _create_method_instance(self, methodclass, prefix=None):
        '''创建一个方法实例
        '''
        if prefix:
            methodname = prefix + '.' + methodclass.name
        else:
            methodname = methodclass.name
        curr = self._method_root
        names = methodname.split('.')
        for name in names[0:-1]:
            if not isinstance(curr, MethodInstanceHop):
                raise Exception("method name '%s' conflict" % methodname)
            method = curr._get_next(name)
            if method is None:
                method = MethodInstanceHop(name)
                curr._append_next(method)
            curr = method
        if curr._get_next(names[-1]) != None:
            raise Exception("redefine method '%s'" % methodname)
        method = MethodInstance(methodclass, self, prefix)
        curr._append_next(method)
        return self._method_root._get_next(names[0])

    def _create_subservice_instance(self, serviceclass, prefix=None):
        '''创建一个子服务实例
        '''
        if prefix:
            subservicename = prefix + '.' + serviceclass._name_
        else:
            subservicename = serviceclass._name_
        curr = self._method_root
        names = subservicename.split('.')
        for name in names[0:-1]:
            if not isinstance(curr, MethodInstanceHop):
                raise Exception("subservice name '%s' conflict" % subservicename)
            hop = curr._get_next(name)
            if hop is None:
                method = MethodInstanceHop(name)
                curr._append_next(method)
            curr = hop
        if curr._get_next(names[-1]) != None:
            raise Exception("redefine subservice '%s'" % subservicename)
        subservice = serviceclass(self._channel)
        subservice._set_prefix(prefix)
        subservice._set_parent(self)
        curr._append_next(subservice)
        return self._method_root._get_next(names[0])

    def _create_subservices(self, service_name, methodclasses, subservices):
        '''处理子服务创建
        '''
        for it in methodclasses:
            self._create_method_instance(it, service_name)
        for it in subservices:
            if type(it) == types.DictType:
                self._create_subservices(service_name + '.' + it['_name_'], it['_methods_'], it.get('_services_', []))
            elif issubclass(it, Service):
                self._create_subservice_instance(it, service_name)
            else:
                raise ValueError('type of element of "_services_" should be Dict/Service instance')

    def __getattribute__(self, name):
        '''查询对象属性，返回对应的方法实例或方法实例跳板
        '''
        try:
            return super(Service, self).__getattribute__(name)
        except AttributeError:
            for method in self._method_root._get_all_next():
                if method._accept(name):
                    return method
            else:
                raise

    def call_method(self, methodname, req, rst_class, timeout):
        '''调用RPC方法
        '''
        if self._name_:
            methodname = self._name_ + '.' + methodname

        if self._parent:  # 为子服务
            if self._prefix:
                methodname = self._prefix + '.' + methodname
            if self._methodnamehook_:
                methodname = self._methodnamehook_(methodname)
            return self._parent.call_method(methodname, req, rst_class, timeout)
        else:
            if self._methodnamehook_:
                methodname = self._methodnamehook_(methodname)
            return self._channel.call_method(methodname, req, rst_class, timeout)


class MethodInstance(object):
    '''方法实例
    '''

    def __init__(self, method_class, service, prefix=None):
        self._class = method_class
        self._service = service
        self._prefix = prefix

    def _accept(self, name):
        '''函数实例跳板查询下个节点是否和调用函数名符合
        '''
        return self._class.name.split('.')[-1].lower() == name.lower()

    def _get_method_name(self):
        '''获取完整的函数名
        '''
        methodname = self._class.name
        if self._prefix:
            methodname = self._prefix + '.' + methodname
        return methodname

    def __call__(self, req, timeout=None):
        req_cls = type(req)
        if req_cls != self._class.request_class:
            request_cls_path = self._class.request_class.__module__ + "." + self._class.request_class.__name__
            req_cls_path = req_cls.__module__ + "." + req_cls.__name__
            raise ValueError("req class type does not match pre-defined class type, %s != %s" % (req_cls_path, request_cls_path))
        if timeout == None:
            timeout = self._service._request_timeout_
        return self._service.call_method(self._get_method_name(), req, self._class.response_class, timeout)

    def __repr__(self):
        return '<Method Instance "%s" at 0x%08X>' % (self._get_method_name(), id(self))


class MethodInstanceHop(object):
    '''方法实例跳板
    '''

    def __init__(self, part_name):
        self._part_name = part_name
        self._next_parts = []

    def _append_next(self, next):
        '''增加下一个方法实例跳板
        '''
        self._next_parts.append(next)

    def _get_next(self, name):
        '''获取下一个方法实例跳板
        '''
        for it in self._next_parts:
            if it._accept(name):
                return it

    def _get_all_next(self):
        '''获取全部下一个方法实例跳板
        '''
        return self._next_parts

    def _accept(self, name):
        '''函数实例跳板查询下个节点是否和调用函数名符合
        '''
        return self._part_name.lower() == name.lower()

    def __getattribute__(self, name):
        '''查询属性，获取对应的方法实例或者方法实例跳板
        '''
        try:
            return super(MethodInstanceHop, self).__getattribute__(name)
        except AttributeError:
            for next_part in self._next_parts:
                if next_part._accept(name):
                    return next_part
            else:
                raise

    def __repr__(self):
        return '<Method Instance Hop "%s" at 0x%08X>' % (self._part_name, id(self))


class MethodClass(object):
    '''方法类
    '''

    def __init__(self, name, request_class, response_class):
        self._name = name
        self._request_class = request_class
        self._response_class = response_class

    @property
    def name(self):
        return self._name

    @property
    def response_class(self):
        return self._response_class

    @property
    def request_class(self):
        return self._request_class


Method = MethodClass


class MethodDiscovery(object):
    '''自动搜索协议中请求类和回复类并构造Service
    只有符合以下规则的接口才会被发现：
    
        接口名为Service.XXX，请求类为XXXReq，回包类为XXXResp
        
        对于不符合规则的接口，则可以在Service的_methods_手动定义
    '''

    def __init__(self, service_cls, reqclssubfix='Req', rspclssubfix='Resp', ignore_modules=None, prefix_match=False):
        '''构造函数
        '''
        self._service_cls = service_cls
        if ignore_modules is None:
            ignore_modules = []
        self._ignore_modules = ignore_modules
        self._registereds = []
        self._reqclssubfix = reqclssubfix
        self._rspclssubfix = rspclssubfix
        self._prefix_match = prefix_match

    def search(self, toppkg):
        '''自动搜索并构造Method
        '''
        if inspect.ismodule(toppkg):
            self._parse_module(toppkg)
        else:
            self._walk_package(toppkg)

    def _walk_package(self, pkg):
        for _, submodulename, ispkg in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + '.'):
            __import__(submodulename)
            if not ispkg:
                self._parse_module(sys.modules[submodulename])
            else:
                self._walk_package(sys.modules[submodulename])

    def _is_msg_class(self, cls):
        '''判断一个类是否为消息定义类
        '''
        # print cls, getattr(cls, 'ParseFromString', None)
        if getattr(cls, '__taf_class__', None):
            return True
        elif getattr(cls, 'ParseFromString', None):
            return True
        else:
            return False

    def _parse_module(self, mod):
        if mod in self._ignore_modules:
            return
        for name in mod.__dict__:
            cls = mod.__dict__[name]
            if self._is_msg_class(cls):
                if not self._prefix_match:
                    is_match = cls.__name__[-len(self._reqclssubfix):] == self._reqclssubfix
                else:
                    is_match = cls.__name__[0:len(self._reqclssubfix)] == self._reqclssubfix
                if is_match:
                    reqcls = cls
                    if reqcls in self._registereds:
                        continue
                    if not self._prefix_match:
                        apiname = reqcls.__name__[0:-len(self._reqclssubfix)]
                        rspclsname = apiname + self._rspclssubfix
                    else:
                        apiname = reqcls.__name__[len(self._reqclssubfix):]
                        rspclsname = self._rspclssubfix + apiname
                    rspcls = getattr(mod, rspclsname, None)
                    # print rspcls
                    if rspcls is not None:
                        method = Method(apiname, reqcls, rspcls)
                        if not self._has_conflict_method(method):
                            self._service_cls._methods_.append(method)
                            self._registereds.append(reqcls)

    def _has_conflict_method(self, method):
        '''检测是否有名字冲突
        '''
        for it in self._service_cls._methods_:
            if it.name == method.name:
                msg = 'method name confict: %s and %s' % (method.request_class, it.request_class)
                raise RuntimeError(msg)
        return False

