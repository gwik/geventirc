DELIM = chr(040)
INVALID_CHARS = ["\r", "\n", "\0"]
CR = "\r"
NL = "\n"
NUL = chr(0)


class ProtocolViolationError(StandardError):
    pass

def is_valid_param(param):
    for invalid in INVALID_CHARS:
        if invalid in param:
            return False
    return True

def irc_split(data):
    prefix = ''
    buf = data
    trailing = None
    command = None

    if buf.startswith(':'):
        try:
            prefix, buf = buf[1:].split(DELIM, 1)
        except ValueError:
            pass
    try:
        command, buf = buf.split(DELIM, 1)
    except ValueError:
        raise ProtocolViolationError('no command received: %r' % buf)
    try:
        buf, trailing = buf.split(DELIM + ':', 1)
    except ValueError:
        pass
    params = buf.split(DELIM)
    if trailing is not None:
        params.append(trailing)
    return prefix, command, params

def irc_unsplit(prefix, command, params):
    buf = ''
    if prefix is not None:
        buf += prefix + DELIM
    buf += command + DELIM
    if params is None:
        pass
    elif isinstance(params, basestring):
        assert not params.startswith(':'), 'params must not start with :'
        buf += ":" + params
    else:
        if params:
            rparams, trailing = params[:-1], params[-1]
            if rparams:
                buf += DELIM.join(rparams) + DELIM
            if trailing:
                buf += ":" + trailing
    return buf


class Message(object):

    @classmethod
    def decode(cls, data):
        prefix, command, params = irc_split(data)
        return cls(command, params, prefix=prefix)

    def __init__(self, command, params, prefix=None):
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
        return irc_unsplit(self.prefix, self.command, self.params) + "\r\n"


class Command(Message):

    def __init__(self, params, command=None, prefix=None):
        if command is None:
            command = self.__class__.__name__.upper()
        super(Command, self).__init__(command, params, prefix=prefix)


class Nick(Command):

    def __init__(self, nickname, hopcount=None, prefix=None):
        params = [nickname]
        if hopcount is not None:
            assert isinstance(hopcount, int), 'hopcount should be int if not none'
            params.append(str(hopcount))
        super(Nick, self).__init__(params, prefix=prefix)


class User(Command):

    def __init__(self, username, hostname, servername, realname, prefix=None):
        params = [username, hostname, servername, realname]
        super(User, self).__init__(params, prefix=prefix)


class Quit(Command):

    def __init__(self, msg, prefix=None):
        params = None
        if msg is not None:
            params = msg
        super(Quit, self).__init__(params, prefix=prefix)


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
        super(Join, self).__init__(params, prefix=prefix)


class PrivMsg(Command):

    def __init__(self, to, msg, prefix=None):
        super(PrivMsg, self).__init__([to, msg], prefix=prefix)


class Pong(Command):
    def __init__(self, prefix=None):
        super(Pong, self).__init__(None, prefix=prefix)


X_DELIM = chr(001)
X_QUOTE = chr(134)
M_QUOTE = chr(020)

_low_level_quote_table = {
    NUL: M_QUOTE + '0',
    NL: M_QUOTE + 'n',
    CR: M_QUOTE + 'r',
    M_QUOTE: M_QUOTE * 2
}

_low_level_dequote_table = {}
for k, v in _low_level_quote_table.items():
    _low_level_dequote_table[v] = k

_ctcp_quote_table = {
    X_DELIM: X_QUOTE + 'a',
    X_QUOTE: X_QUOTE * 2
}

_ctcp_dequote_table = {}
for k, v in _ctcp_quote_table.items():
    _ctcp_dequote_table[v] = k

def _quote(string, table):
    cursor = 0
    buf = ''
    for pos, char in enumerate(string):
        if pos is 0:
            continue
        if char in table:
            buf += string[cursor:pos] + table[char]
            cursor = pos + 1
    buf += string[cursor:]
    return buf

def _dequote(string, table):
    cursor = 0
    buf = ''
    last_char = ''
    for pos, char in enumerate(string):
        if pos is 0:
            last_char = char
            continue
        if last_char + char in table:
            buf += string[cursor:pos] + table[char]
            cursor = pos + 1
        last_char = char

    buf += string[cursor:]
    return buf

def low_level_quote(string):
    return _quote(string, _low_level_quote_table)

def low_level_dequote(string):
    return _dequote(string, _low_level_dequote_table)

def ctcp_quote(string):
    return _quote(string, _ctcp_quote_table)

def ctcp_dequote(string):
    return _dequote(string, _ctcp_dequote_table)


class CTCPMessage(Message):

    def __init__(self, command, params, ctcp_params, prefix=None):
        super(CTCPMessage, self).__init__(command, params, prefix=prefix)
        self.ctcp_params = ctcp_params

    @classmethod
    def decode(cls, data):
        prefix, command, params = irc_split(data)
        extended_messages = []
        normal_messages = []
        if params:
            params = DELIM.join(params)
            decoded = low_level_dequote(params)
            messages = decoded.split(X_DELIM)
            messages.reverse()

            odd = False
            extended_messages = []
            normal_messages = []

            while messages:
                message = messages.pop()
                if odd:
                    if message:
                        ctcp_decoded = ctcp_dequote(message)
                        split = ctcp_decoded.split(DELIM, 1)
                        tag = split[0]
                        data = None
                        if len(split) > 1:
                            data = split[1]
                        extended_messages.append((tag, data))
                else:
                    if message:
                        normal_messages += filter(None, message.split(DELIM))
                odd = not odd

        return cls(command, normal_messages, extended_messages, prefix=prefix)

    def encode(self):
        ctcp_buf = ''
        for tag, data in self.ctcp_params:
            if data:
                if not isinstance(data, basestring):
                    data = DELIM.join(map(str, data))
                m = tag + DELIM + data
            else:
                m = str(tag)
            ctcp_buf += X_DELIM + ctcp_quote(m) + X_DELIM

        return irc_unsplit(
                self.prefix, self.command, self.params + 
                [low_level_quote(ctcp_buf)]) + "\r\n"


class Me(CTCPMessage):

    def __init__(self, to, action, prefix=None):
        super(Me, self).__init__(
                'PRIVMSG', [to], [('ACTION', action)], prefix=prefix)
