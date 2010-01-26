#-*- encoding: utf-8 -*-
import re
import sqlite3 as sqlite

con = sqlite.connect('lib/mathnet.db')
def search(eng):
    """mathnet에서 영어 to 한국어 용어를 검색."""
    global con
    pq = "select english, korean from mathnet where %s order by length(english) asc limit 3"
    q = pq % ("english = '%s'"%eng)
    f = con.execute(q).fetchall()
    if not f:
        q = pq % ("english like '%"+eng+"%'")
        f = con.execute(q).fetchall()
    return f


def on_pubmsg(bot, connection, event):
    msg = event.arguments()[0]
    source = str(event.source())
    source = source.split('!', 1)[1]
    source = source.split('@')[0]
    if '=' in source: source = source.split('=',1)[1]
    if '~' in source: source = source.split('~',1)[1]
    if source in ['uniko', 'kouni', '|']:
        msg = re.sub(r'^<.*?> ', '', msg, 1)

    commands = ['mathnet', 'mn']
    for command in commands:
        if msg.startswith('!'+command+" "): break
    else: return

    output = u''
    try:
        s = msg.split(' ', 1)[1].strip()
        f = search(s)
        if f:
            output += " / ".join(" = ".join(i) for i in f)
        else:
            output += u"'%s': 검색 결과가 없습니다."%s
    except IndexError:
        return

    bot.reply(event, output)

on_privmsg = on_pubmsg
