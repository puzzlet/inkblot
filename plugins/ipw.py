import re
import imp

from lib import whois; imp.reload(whois)

def on_msg(bot, connection, event):
    msg = event.arguments()[0]
    # XXX
    source = event.source()
    source = source.split(b'!', 1)[1]
    source = source.split(b'@')[0]
    if b'=' in source: source = source.split(b'=',1)[1]
    if b'~' in source: source = source.split(b'~',1)[1]
    if source in [b'I|', b'|I', b'|']:
        msg = re.sub(b'^<.*?> ', b'', msg, 1)
    if not msg.startswith(b'!ipw'):
        return

    ip = msg.strip()
    ip = ip.split(b' ',1)[1]
    res = whois.IPWhois(ip.decode('utf8'))
    output = ''
    output += '[\x1f%s\x1f] ' % res['source']
    if ip != res['ipv4addr']:
        output += '%s (%s)' % (ip, res['ipv4addr'])
    else:
        output += ip
    if 'route' in res:
        output += ' \x02%(owner)s\x02 (%(route)s/%(netname)s, %(netblock)s)' % res
    else:
        output += ' : \x02%(owner)s\x02 (%(netname)s, %(netblock)s)' % res
    bot.reply(event, output)

def on_privmsg(bot, connection, event):
    on_msg(bot, connection, event)

def on_pubmsg(bot, connection, event):
    on_msg(bot, connection, event)

