"""socket channel of qt4s
"""
import threading

from qt4s.addressing.direct import DirectAddressing
from qt4s.channel.base import ChannelBase, IRequest, IResponse
from qt4s.connections.sock import SocketCallback, SocketConn, EnumConnType
from qt4s.message.definition import Message
from qt4s.message.utils import size_of, field_size_of, offset_of
from qt4s.util import SequenceGenerator

_no_packet = object()


class SocketConnectionTimeoutError(Exception):
    pass


class SocketGetResponseTimeoutError(Exception):
    pass


class PacketBase(Message):
    """base class of a packet
    """
    _struct_ = []
    _length_fields_ = None

    def __init__(self, *args, **kwargs):
        super(PacketBase, self).__init__(*args, **kwargs)

    def get_sequence_id(self):
        """get the unique sequence id of current request or response 
        """
        raise NotImplementedError

    def set_message_length(self, serializer):
        if getattr(self, "_length_field_", None) is None:
            return

        packet_size = size_of(self, serializer)
        attr_parts = self._length_field_.split(".")
        value = self
        for attr_part in attr_parts[:-1]:
            value = getattr(self, attr_part)
        setattr(value, attr_parts[-1], packet_size)

    def get_message_length(self, buff, serializer):
        if getattr(self, "_length_field_", None) is None:
            return len(buff)

        serializer = serializer or self._serializer_
        buf_len = len(buff)
        length_field = self._length_field_
        start_pos = offset_of(self, length_field, serializer)
        end_pos = start_pos + field_size_of(self, length_field, serializer)
        if buf_len < end_pos:
            return None

        value = self
        field_type = None
        attr_parts = length_field.split(".")
        for attr_part in attr_parts[:-1]:
            value = getattr(self, attr_part)
        for field_info in value.get_struct().get_fields():
            if field_info.name == attr_parts[-1]:
                field_type = field_info.type
                break
        else:
            raise RuntimeError('length field named "%s" not found' % length_field)
        expected_len, _ = serializer.loads(field_type, buff[start_pos:end_pos])
        if buf_len < expected_len:
            return None
        return expected_len


class RequestBase(PacketBase, IRequest):
    response_class = None

    def __init__(self, *args, **kwargs):
        self.__timeout = kwargs.pop("timeout", 10)
        super(RequestBase, self).__init__(*args, **kwargs)

    def get_timeout(self):
        return self.__timeout

    def pre_process(self, chan):
        pass


class ResponseBase(PacketBase, IResponse):
    """base class of channel response
    """

    def __init__(self):
        super(ResponseBase, self).__init__()
        self.__request = None

    def set_request(self, request):
        self.__request = request

    @property
    def request(self):
        return self.__request

    def post_process(self, chan):
        pass


class SocketChannel(ChannelBase, SocketCallback):
    """a basic socket channel
    """

    def __init__(self, account_or_user=None, **kwargs):
        """channel constructor, allowed keyword-argument is showing as followed
        
        :param account_or_user: an account or an user for channel authenticating
        :type  account_or_user: qt4s.auth.QT4SAccount or qt4s.auth.QT4SUser
        :param net_area: target host's network area
        :type  net_area: qt4s.location.NetArea
        :param conn_type: underlayer connection type, TCP or UDP
        :type  conn_type: str
        :param connect_timeout: timeout for create connection
        :type  connect_timeout: float
        """
        super(SocketChannel, self).__init__(account_or_user=account_or_user, **kwargs)

        self._lock = threading.Lock()
        self._evt = threading.Event()
        self._seq_generator = None
        self._pending_pairs = {}
        self._connected = False
        self._tcp_buf = ""
        self._connect_timeout = self.kwargs.get("connect_timeout", 10)

    def get_connection(self):
        address = DirectAddressing(self.kwargs).get_address()
        return SocketConn(address, self)

    @property
    def connected(self):
        """is channel connected, for udp connection is always True
        """
        return self._connected

    def create_seq(self, min_val=0, max_val=0x7fffffff):
        """create an unique sequence number within channel scope
        
        :returns : an integer sequence number
        :type   : int
        """
        if not self._seq_generator:
            with self._lock:
                if not self._seq_generator:
                    self._seq_generator = SequenceGenerator(min_val, max_val)
        return self._seq_generator.create_seq()

    def get_response(self, request):
        buff = request.dumps()
        sequence_id = request.get_sequence_id()
        if request in self._pending_pairs:
            raise ValueError("request with sequence_id=%s is already in pending pairs" % sequence_id)
        if self._conn.socket_type == EnumConnType.UDP:
            sequence_id = (sequence_id, (self._conn.host, self._conn.port))
        evt = threading.Event()

        if not self._connected:  # avoid lock acquiring
            with self._lock:
                if not self._connected:
                    self.wait_for_connected()
                    self._connected = True

        self._pending_pairs[sequence_id] = (evt, _no_packet)
        self._conn.send(buff)

        evt = self._pending_pairs[sequence_id][0]
        evt.wait(request.get_timeout())
        rsp = self._pending_pairs[sequence_id][1]
        with self._lock:
            del self._pending_pairs[sequence_id]
        if rsp == _no_packet:
            raise SocketGetResponseTimeoutError("no response for sequence_id=%s in %ss" % (sequence_id,
                                                                                           request.get_timeout()))
        return rsp

    def wait_for_connected(self):
        self._conn.connect()
        self._evt.wait(self._connect_timeout)
        if not self._evt.is_set():
            err_msg = "connect %s:%s timeout for %ss" % (self._conn.host,
                                                         self._conn.port,
                                                         self._connect_timeout)
            raise SocketConnectionTimeoutError(err_msg)
        self._evt.clear()

    def on_connected(self):
        self._evt.set()

    def on_recv(self):
        with self._lock:
            response_class = self.request_class.response_class
            response = response_class()
            if self._conn.socket_type == EnumConnType.UDP:
                packet_buff, addr = self._conn.read()
                response.loads(packet_buff)
                sequence_id = response.get_sequence_id()
                sequence_id = (sequence_id, addr)
                self.notify(sequence_id, response)
            else:
                self._tcp_buf += self._conn.read()
                while True:
                    packet_len = response.get_message_length(self._tcp_buf, None)
                    if not packet_len:
                        break
                    else:
                        packet_buff = self._tcp_buf[:packet_len]
                        self._tcp_buf = self._tcp_buf[packet_len:]
                        remain_data = response.loads(packet_buff)
                        if remain_data:
                            print("[WARNING]data=%s remained after response laoding" % remain_data)
                        sequence_id = response.get_sequence_id()
                        self.notify(sequence_id, response)

    def notify(self, key, resposne):
        """notify channel that a response is available
        """
        if key in self._pending_pairs:
            evt = self._pending_pairs[key][0]
            self._pending_pairs[key] = (evt, resposne)
            evt.set()
        else:
            self.on_push(resposne)

    def on_push(self, packet):
        print("server push packet: %s" % str(packet))

