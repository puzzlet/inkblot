#-*- encoding: utf-8 -*-
import re
import sqlite3 as sqlite

con = sqlite.connect('lib/mathnet.db')
def search(eng):
    """mathnet에서 영어 to 한국어 용어를 검색."""
    global con
    pq = "select english, korean from mathnet where %s order by length(english) asc limit 3"
    q = pq % ("english = '?'")
    f = con.execute(q, (eng,)).fetchall()
    if not f:
        q = pq % ("english like '%?%'")
        f = con.execute(q, (eng,)).fetchall()
    return f

def on_pubmsg(bot, connection, event):
    msg = event.arguments()[0]
    source = event.source()
    source = source.split(b'!', 1)[1]
    source = source.split(b'@')[0]
    if b'=' in source: source = source.split(b'=',1)[1]
    if b'~' in source: source = source.split(b'~',1)[1]
    if source in [b'I|', b'|I', b'|']:
        msg = re.sub(b'^<.*?> ', b'', msg, 1)

    commands = [b'mathnet', b'mn']
    for command in commands:
        if msg.startswith(b'!'+command+b" "): break
    else: return

    output = ''
    try:
        msg = msg.decode('utf8') # XXX
        s = msg.split(' ', 1)[1].strip()
        f = search(s)
        if f:
            output += " / ".join(" = ".join(i) for i in f)
        else:
            output += "'%s': 검색 결과가 없습니다."%s
    except IndexError:
        return

    bot.reply(event, output)

on_privmsg = on_pubmsg
