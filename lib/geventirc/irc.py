from __future__ import absolute_import

import logging

import gevent.queue
import gevent.pool
from gevent import socket

from geventirc import message
from geventirc import replycode

IRC_PORT = 194
IRCS_PORT = 994

logger = logging.getLogger(__name__)


class Client(object):

    def __init__(self, hostname, nick, port=IRC_PORT, charset='utf-8'):
        self.hostname = hostname
        self.port = port
        self.nick = nick
        self._socket = None
        self.charset = charset
        self._recv_queue = gevent.queue.Queue()
        self._send_queue = gevent.queue.Queue()
        self._group = gevent.pool.Group()
        self._handlers = {}
        self._global_handlers = set([])

    def add_handler(self, to_call, *commands):
        if not commands:
            self._global_handlers.add(to_call)
            return

        for command in commands:
            command = str(command).upper()
            if self._handlers.has_key(command):
                self._handlers[command].add(to_call)
                continue
            self._handlers[command] = set([to_call])

    def _handle(self, msg):
        handlers = self._global_handlers | self._handlers.get(msg.command, set())
        if handlers is not None:
            for handler in handlers:
                self._group.spawn(handler, self, msg)

    def send_message(self, msg):
        self._send_queue.put(msg.encode())

    def start(self):
        address = None
        try:
            address = (socket.gethostbyname(self.hostname), self.port)
        except socket.gaierror:
            logger.error('hostname not found')
            raise

        logger.info('connecting to %r...' % (address,))
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect(address)
        self._group.spawn(self._send_loop)
        self._group.spawn(self._process_loop)
        self._group.spawn(self._recv_loop)
        # give control back to the hub
        gevent.sleep(0)

    def _recv_loop(self):
        buf = ''
        while True:
            data = self._socket.recv(512)
            buf += data
            pos = buf.find("\r\n")
            while pos >= 0:
                line = buf[0:pos]
                self._recv_queue.put(line)
                buf = buf[pos + 2:]
                pos = buf.find("\r\n")

    def _send_loop(self):
        while True:
            command = self._send_queue.get()
            print 'send: ' + command.encode()[:-2]
            self._socket.sendall(command.encode())

    def _process_loop(self):
        client.send_message(message.Nick(self.nick))
        client.send_message(
                message.User(
                    'gwik', 'cafeine.local', 'cafeine', 'Antonin Amand'))
        while True:
            data = self._recv_queue.get()
            msg = message.Message.decode(data)
            self._handle(msg)

    def stop(self):
        self._group.kill()
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def join(self):
        self._group.join()

    def msg(self, to, content):
        self.send_message(message.PrivMsg(to, content))

    def quit(self, msg=None):
        self.send_message(message.Quit(msg))
        self.stop()


def print_handler(client, msg):
    print msg.encode()[:-2]

def join_handler(client, msg):
    client.send_message(message.Join('#flood!'))
    client.send_message(message.PrivMsg('#flood!', 'hello there'))

def ping_handler(client, msg):
    client.send_message(message.Pong())


class NickInUseHandler(object):

    def __call__(self, client, msg):
        self.nick = msg.params[1] + '_'
        client.send_message(message.Nick(self.nick))


class NickServHandler(object):

    def __init__(self, nick, password):
        self.nick = nick
        self.current_nick = None
        self.password = password

    def __call__(self, client, msg):
        if msg.command == str(replycode.ERR_NICKNAMEINUSE) or \
                msg.command == str(replycode.ERR_NICKCOLLISION):
            nick = msg.params[1]
            self.current_nick = nick + '_'
            client.send_message(message.Nick(self.current_nick))
            return
        if msg.command == '001':
            client.send_message(message.Nick(self.nick))
            self.current_nick = self.nick
            msg = message.PrivMsg('nickserv', 'identify ' + self.password)
            client.send_message(msg)


class Hello(object):

    def __init__(self, channel, msg='hello', wait=1.0):
        self.channel = channel
        self.msg = 'hello'
        self.wait = wait

    def start(self, client, msg):
        self.client = client
        self._schedule()

    def _schedule(self):
        timer = gevent.get_hub().loop.timer(self.wait)
        timer.start(self.__call__)

    def run(self):
        self.client.msg(self.channel, self.msg)
    
    def __call__(self):
        gevent.spawn(self.run)
        self._schedule()


if __name__ == '__main__':
    nick = 'geventbot'
    client = Client('irc.freenode.net', nick, port=6667)
    hello = Hello('#flood!')
    client.add_handler(ping_handler, 'PING')
    client.add_handler(join_handler, '001')
    client.add_handler(hello.start, '001')
    client.add_handler(print_handler)
    client.add_handler(NickInUseHandler(), replycode.ERR_NICKNAMEINUSE)
    client.start()
    client.join()


