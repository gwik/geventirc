DELIM = " "
INVALID_CHARS = ["\r", "\n", "\0"]


def is_valid_param(param):
    for invalid in INVALID_CHARS:
        if invalid in param:
            return False
    return True


class Message(object):

    @classmethod
    def decode(cls, data):
        prefix = ''
        buf = data
        trailing = None

        if buf.startswith(':'):
            prefix, buf = buf[1:].split(DELIM, 1)
        command, buf = buf.split(DELIM, 1)
        try:
            buf, trailing = buf.split(' :', 1)
        except ValueError:
            pass
        params = buf.split(' ')
        if trailing is not None:
            params.append(trailing)

        return cls(prefix, command, params)

    def __init__(self, prefix, command, params):
        assert command, 'command is mandatory'
        self.prefix = prefix
        self.command = command
        self.params = params

    @property
    def prefix_parts(self):
        """ return tuple(<servername/nick>, <user agent>, <host>)
        """
        server_name = None
        user = None
        host = None
        pos = self.prefix.find('!')
        if pos >= 0:
            server_name, userhost = self.prefix[:pos], self.prefix[pos+1:]
            pos = self.prefix.find('@')
            if pos >= 0:
                user, host = userhost[:pos], userhost[pos+1:]
            else:
                host = userhost
        else:
            server_name = self.prefix
        return server_name, user, host

    def encode(self):
        buf = ''
        if self.prefix is not None:
            buf += self.prefix + DELIM
        buf += self.command + DELIM
        if self.params is None:
            pass
        elif isinstance(self.params, basestring):
            assert not self.params.startswith(':'), 'params must not start with :'
            assert is_valid_param(self.params), 'invalid param: ' + self.params
            buf += ":" + self.params
        else:
            for param in self.params:
                assert is_valid_param(param), 'invalid param: ' + self.params
                if DELIM in param:
                    buf += ":"
                buf += param + DELIM
        buf += "\r\n"
        return buf


class Command(Message):

    def __init__(self, prefix, params, command=None):
        if command is None:
            command = self.__class__.__name__.upper()
        super(Command, self).__init__(prefix, command, params)


class Nick(Command):

    def __init__(self, nickname, hopcount=None, prefix=None):
        params = [nickname]
        if hopcount is not None:
            assert isinstance(hopcount, int), 'hopcount should be int if not none'
            params.append(str(hopcount))
        super(Nick, self).__init__(prefix, params)


class User(Command):

    def __init__(self, username, hostname, servername, realname, prefix=None):
        params = [username, hostname, servername, realname]
        super(User, self).__init__(prefix, params)


class Quit(Command):

    def __init__(self, msg, prefix=None):
        params = None
        if msg is not None:
            params = msg
        super(Quit, self).__init__(prefix, params)


class Join(Command):

    def __init__(self, channels, prefix=None):
        params = []
        if isinstance(channels, basestring):
            if channels.startswith('#'):
                params = channels
            else:
                params = "#" + channels
        else:
            chans = []
            keys = []
            for channel, key in channels:
                if key is None:
                    chans.append('#' + channel)
                else:
                    chans.append('&' + channel)
                    keys.append(key)
            params = [",".join(chans), ",".join(keys)]

        assert params, 'invalid channel ' + channels
        super(Join, self).__init__(prefix, params)


class PrivMsg(Command):

    def __init__(self, to, msg, prefix=None):
        super(PrivMsg, self).__init__(prefix, [to, msg])


class Pong(Command):
    def __init__(self, prefix=None):
        super(Pong, self).__init__(prefix, None)



