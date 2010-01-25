# encoding: utf-8
import re
import urllib

def get_mediawiki_page(page, enc):
    page = page.replace(u' ', u'_')
    page = urllib.quote(page.encode(enc))
    page = re.sub('%23(.*)', lambda x: '#'+x.group(1).replace('%', '.'), page)
    page = re.sub('%3A(.*)', r':\1', page)
    return page.decode('ascii')

LOCATION = {
    u'b': u'wikibooks',
    u'm': u'meta',
    u's': u'wikisource',
    u'wikt': u'wiktionary',
}

def get_wikipedia_url(page, lang=u'ko', location=u'wikipedia'):
    left, partitioned, right = page.partition(u':')
    while partitioned:
        if left in LOCATION:
            location = LOCATION[left]
        elif re.match(ur'^[a-z][a-z]$', left) is not None:
            lang = left
        else:
            break
        page = right
        return get_wikipedia_url(page, lang, location)
    page = get_mediawiki_page(page, 'utf-8')
    if location in (u'meta', u'commons'):
        return u'http://%s.wikimedia.org/wiki/%s' % (location, page)
    return u'http://%s.%s.org/wiki/%s' % (lang, location, page)

def on_msg(bot, connection, event):
    msg = event.arguments()[0]
    if event.source() in ['uniko', 'kouni']:
        msg = re.sub(r'^<.*?> ', '', msg, 1)
    try: # XXX
        msg = msg.decode('utf-8')
    except UnicodeDecodeError:
        return
    if u'[[' not in msg:
        return
    MAX_CNT = 5
    cnt = 0
    visit = {}
    for page in re.findall(ur'\[\[(.+?)\]\]', msg):
        if page != page.strip(): continue
        if page in visit: continue
        visit[page] = True
        if cnt >= MAX_CNT:
            bot.reply(event, u'최대 %d개까지만 출력합니다.' % MAX_CNT)
            return
        label = u''
        url = get_wikipedia_url(page)
        bot.reply(event, u'\x02[%s]\x02 %s' % (page, url))
        cnt += 1

def on_privmsg(bot, connection, event):
    on_msg(bot, connection, event)

def on_pubmsg(bot, connection, event):
    on_msg(bot, connection, event)


