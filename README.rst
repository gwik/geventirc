=========
geventirc
=========

Introduction
============

`geventirc` is a simple irc client library using gevent::

    from geventirc import Client
    
    nick = 'geventircbot'
    irc = Client('irc.freenode.net', nick,  port=6667)
    irc.start()
    irc.join()


Handlers
========

`handlers` react to messages from server, they can be any python
callable::


    from gevenirc import Client
    from gevenirc import message
    from gevenirc import handlers

    def join_and_say_hello_handler(client, msg):
        client.send_message(message.Join('#gevent'))
        client.msg('#gevent', 'Hello #gevent guys!')


    class ReplyWhenQuoted(object):
        """ Reply when someone quotes me.
        """

        commands = ['PRIVMSG']

        def __init__(self, reply):
            self.reply = reply

        def __call__(self, client, msg):
            channel, content = msg.params
            if client.nick in content:
                client.msg(self.reply)


    def print_handler(self, client, msg):
        """ Print every message from server to standard output.
        """
        print msg.encode()[-2]

    nick = 'geventircbot'
    nickserv_handler = handlers.NickServHandler(nick, 'somepassword')

    irc = Client('irc.freenode.net', nick,  port=6667)
    # this handler doesn't provide a commands attribute nor specify at
    # registration so it receives everything.
    irc.add_handler(print_handler)
    # 001 code means that you have successfully connected and can
    # join channels.
    irc.add_handler(join_and_say_hello_handler, '001')
    # nickserv_handler has a commands attribute which tell which
    # commands it's reacts to.
    irc.add_handler(nickserv_handler)
    irc.add_handler(ReplyWhenQuoted("I'm just a bot"))
    irc.start()
    irc.join() # join means join the current greenlet, not join irc channel


Contact & Help
==============

twitter: @gwik
email: antonin.amand@gmail.com
Join #gevent on freenode and talk to gwik.

License
=======

MIT, see LICENSE.txt
