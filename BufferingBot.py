import time
import heapq
import collections
import traceback

import irclib
import ircbot

def periodic(period):
    """Decorate a class instance method so that the method would be
    periodically executed by irclib framework.
    """
    def decorator(f):
        def new_f(self, *args):
            try:
                f(self, *args)
            except StopIteration:
                return
            finally:
                self.ircobj.execute_delayed(period, new_f, (self,) + args)
        return new_f
    return decorator

class Packet():
    def __init__(self, command, arguments, timestamp=None):
        self.command = command
        self.arguments = arguments
        self.timestamp = time.time() if timestamp is None else timestamp

    def __repr__(self):
        return '<Packet %s %s %s>' % (
            repr(self.command),
            repr(self.arguments),
            repr(self.timestamp)
        )

    def __cmp__(self, packet):
        return cmp(self.timestamp, packet.timestamp)

    def is_system_message(self):
        if self.command in ['privmsg', 'privnotice']:
            return self.arguments[1].startswith('--') # XXX
        return False

class PacketBuffer(object):
    """Buffer of Packet objects, sorted by their timestamp.
    If some of its Packet's timestamp lags over self.timeout, it purges all the queue.
    Note that this uses heapq mechanism hence not thread-safe.
    """

    def __init__(self, timeout=10.0):
        self.timeout = timeout
        self.heap = []

    def __len__(self):
        return len(self.heap)

    def _dump(self):
        print self.heap

    def peek(self):
        return self.heap[0]

    def push(self, packet):
        return heapq.heappush(self.heap, packet)

    def _pop(self):
        if not self.heap:
            return None
        return heapq.heappop(self.heap)

    def pop(self):
        if self.peek().timestamp < time.time() - self.timeout:
            self.purge()
        return self._pop()

    def purge(self):
        stale = time.time() - self.timeout
        line_counts = collections.defaultdict(int)
        while self.heap:
            packet = self.peek()
            if packet.timestamp > stale:
                break
            if packet.command in ['join']: # XXX
                break
            packet = self._pop()
            if packet.command in ['privmsg', 'privnotice']:
                try:
                    target, message = packet.arguments
                except:
                    traceback.print_exc()
                    self.push(packet)
                    return
                if not packet.is_system_message():
                    line_counts[target] += 1
        for target, line_count in line_counts.iteritems():
            message = "-- Message lags over %f seconds. Skipping %d line(s).." \
                % (self.timeout, line_count)
            packet = Packet(
                command = 'privmsg',
                arguments = (target, message)
            )
            self.push(packet)

    def has_buffer_by_command(self, command):
        return any(_.command == command for _ in self.heap)

class BufferingBot(ircbot.SingleServerIRCBot):
    def __init__(self, network_list, nickname, realname,
                 reconnection_interval=60, use_ssl=False):
        ircbot.SingleServerIRCBot.__init__(self, network_list, nickname,
                                           realname, reconnection_interval,
                                           use_ssl)
        self.buffer = PacketBuffer(10.0)
        self.last_tick = 0
        self.on_tick()

    @periodic(0.2)
    def on_tick(self):
        if not self.connection.is_connected():
            return
        self.flood_control()

    def get_delay(self, packet):
        # TODO: per-network configuration
        delay = 0
        if packet.command == 'privmsg':
            delay = 2
            try:
                target, msg = packet.arguments
                delay = 0.5 + len(msg) / 35.
            except:
                traceback.print_exc()
        if delay > 4:
            delay = 4
        return delay

    def flood_control(self):
        """Delays message according to the length of packet.
        As you see, this doesn't acquire any lock hence thread-unsafe.
        """
        if not self.connection.is_connected():
            self._connect()
            return
        packet = None
        local = False
        if len(self.buffer):
            print '--- buffer ---'
            self.buffer._dump()
            self.pop_buffer(self.buffer)

    def pop_buffer(self, buffer):
        if not buffer:
            return
        packet = buffer.peek()
        if packet.command == 'privmsg':
            try:
                target, msg = packet.arguments
                if irclib.is_channel(target) and target not in self.channels:
                    return
            except:
                traceback.print_exc()
                return
        delay = self.get_delay(packet)
        tick = time.time()
        if self.last_tick + delay > tick:
            return
        self.process_packet(packet)
        packet_ = buffer.pop()
        if packet != packet_:
            print packet
            print packet_
            assert False
        self.last_tick = tick

    def process_packet(self, packet):
        try:
            if False:
                pass
            elif packet.command == 'join':
                self.connection.join(*packet.arguments)
            elif packet.command == 'mode':
                self.connection.mode(*packet.arguments)
            elif packet.command == 'privmsg':
                self.connection.privmsg(*packet.arguments)
            elif packet.command == 'privnotice':
                self.connection.privnotice(*packet.arguments)
            elif packet.command == 'topic':
                self.connection.topic(*packet.arguments)
            elif packet.command == 'who':
                self.connection.who(*packet.arguments)
            elif packet.command == 'whois':
                self.connection.whois(*packet.arguments)
        except irclib.ServerNotConnectedError:
            self.push_packet(packet)
            self._connect()
        except:
            traceback.print_exc()
            self.push_packet(packet)

    def push_packet(self, packet):
        self.buffer.push(packet)

