from __future__ import absolute_import

import logging

import gevent.queue
import gevent.pool
from gevent import socket

from geventirc import message
from geventirc import replycode
from geventirc import handlers

IRC_PORT = 194
IRCS_PORT = 994

logger = logging.getLogger(__name__)


class Client(object):

    def __init__(self, hostname, nick, port=IRC_PORT,
            local_hostname=None, server_name=None, real_name=None):
        self.hostname = hostname
        self.port = port
        self.nick = nick
        self._socket = None
        self.real_name = real_name or nick
        self.local_hostname = local_hostname or socket.gethostname()
        self.server_name = server_name or 'gevent-irc'
        self._recv_queue = gevent.queue.Queue()
        self._send_queue = gevent.queue.Queue()
        self._group = gevent.pool.Group()
        self._handlers = {}
        self._global_handlers = set([])

    def add_handler(self, to_call, *commands):
        if not commands:
            if hasattr(to_call, 'commands'):
                commands = to_call.commands
            else:
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
            self._socket.sendall(command.encode())

    def _process_loop(self):
        self.send_message(message.Nick(self.nick))
        self.send_message(
                message.User(
                    self.nick,
                    self.local_hostname,
                    self.server_name,
                    self.real_name))
        while True:
            data = self._recv_queue.get()
            msg = message.CTCPMessage.decode(data)
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


if __name__ == '__main__':

    class MeHandler(object):
        commands = ['PRIVMSG']

        def __call__(self, client, msg):
            if client.nick == msg.params[0]:
                nick, _, _ = msg.prefix_parts
                client.send_message(
                        message.Me(nick, "do nothing it's just a bot"))

    nick = 'geventbot'
    client = Client('irc.freenode.net', nick, port=6667)
    client.add_handler(handlers.ping_handler, 'PING')
    client.add_handler(handlers.JoinHandler('#flood!'))
    # client.add_handler(hello.start, '001')
    client.add_handler(handlers.ReplyWhenQuoted("I'm just a bot"))
    client.add_handler(handlers.print_handler)
    client.add_handler(handlers.nick_in_user_handler, replycode.ERR_NICKNAMEINUSE)
    client.add_handler(handlers.ReplyToDirectMessage("I'm just a bot"))
    client.add_handler(MeHandler())
    client.start()
    client.join()


