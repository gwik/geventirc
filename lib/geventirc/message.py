DELIM = chr(40)
INVALID_CHARS = ["\r", "\n", "\0"]
CR = "\r"
NL = "\n"
NUL = chr(0)

def is_valid_param(param):
    for invalid in INVALID_CHARS:
        if invalid in param:
            return False
    return True

def irc_split(data):
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
    return prefix, command, params

def irc_unsplit(prefix, command, params):
    buf = ''
    if self.prefix is not None:
        buf += prefix + DELIM
    buf += command + DELIM
    if params is None:
        pass
    elif isinstance(params, basestring):
        assert not self.params.startswith(':'), 'params must not start with :'
        assert is_valid_param(params), 'invalid param: ' + params
        buf += ":" + params
    else:
        for param in self.params:
            assert is_valid_param(param), 'invalid param: ' + params
            if DELIM in param:
                buf += ":"
            buf += param + DELIM
    buf += "\r\n"
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
        irc_unsplit(self.prefix, self.command, self.params)


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

    @classmethod
    def decode(cls, data):
        prefix, command, params = irc_split(data)
        params = map(lambda x: ctcp_dequote(low_level_dequote(x)), params)
        return cls(command, params, prefix=None)

    def encode(self):
        # XXX wrong what about normal params ?
        ctcp_params = []
        for tag, data in self.params:
            if data:
                if isinstance(data, basestring):
                    data = " ".join(map(str, data))
                m = tag + " " + data
            else:
                m = str(tag)
            m = low_level_quote(m)
            m = X_DELIM + ctcp_quote(m) + X_DELIM
            ctcp_params.append(m)

        return irc_unsplit(self.prefix, self.command, ctcp_params)

