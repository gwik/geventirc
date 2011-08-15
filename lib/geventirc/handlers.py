import gevent
from geventirc import message
from geventirc import replycode


def ping_handler(client, msg):
    client.send_message(message.Pong())

def print_handler(client, msg):
    print msg.encode()[:-2]


class JoinHandler(object):

    commands = ['001']

    def __init__(self, channel):
        self.channel = channel

    def __call__(self, client, msg):
        client.send_message(message.Join(self.channel))


def nick_in_user_handler(self, client, msg):
    client.nick = msg.params[1] + '_'
    client.send_message(message.Nick(client.nick))


class NickServHandler(object):

    commands = ['001',
        replycode.ERR_NICKNAMEINUSE,
        replycode.ERR_NICKCOLLISION]

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


class ReplyWhenQuoted(object):

    commands = ['PRIVMSG']

    def __init__(self, reply):
        self.reply = reply

    def __call__(self, client, msg):
        channel, content = msg.params[0], " ".join(msg.params[1:])
        if client.nick in content:
            # check if this is a direct message
            if channel != client.nick:
                client.msg(channel, self.reply)


class ReplyToDirectMessage(object):

    commands = ['PRIVMSG']

    def __init__(self, reply):
        self.reply = reply

    def __call__(self, client, msg):
        channel = msg.params[0]
        if client.nick == channel:
            nick, user_agent, host = msg.prefix_parts
            if nick is not None:
                client.msg(nick, self.reply)


class PeriodicMessage(object):
    """ Send a message every interval or `wait`

    !!! gevent 1.0 only !!!
    """

    commands = ['001']

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


