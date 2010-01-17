import re

import whois; reload(whois)

from BufferingBot import Packet

def on_msg(bot, connection, event):
    msg = event.arguments()[0]
    if event.source in ['uniko', 'kouni']:
        msg = re.sub(r'^<.*?> ', '', msg, 1)
    if not msg.startswith('!ipw'):
        return

    ip = msg.strip()
    res = whois.IPWhois(ip.encode('utf-8'))
    output = u''
    output += u'[\x1f%s\x1f] ' % res['source']
    if ip != res['ipv4addr']:
        output += u'%s (%s)' % (ip, res['ipv4addr'])
    else:
        output += ip
    if res.has_key('route'):
        output += u' \x02%(owner)s\x02 (%(route)s/%(netname)s, %(netblock)s)' % res
    else:
        output += u' : \x02%(owner)s\x02 (%(netname)s, %(netblock)s)' % res
    bot.reply(event, output)

def on_privmsg(bot, connection, event):
    on_msg(bot, connection, event)

def on_pubmsg(bot, connection, event):
    on_msg(bot, connection, event)

