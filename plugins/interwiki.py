# encoding: utf-8
import re
import urllib.request, urllib.parse, urllib.error

def get_mediawiki_page(page, enc):
    page = page.replace(' ', '_')
    page = urllib.parse.quote(page.encode(enc))
    page = re.sub('%23(.*)', lambda x: '#'+x.group(1).replace('%', '.'), page)
    page = re.sub('%3A(.*)', r':\1', page)
    return page

LOCATION = {
    'b': 'wikibooks',
    'm': 'meta',
    'mw': 'mediawiki',
    's': 'wikisource',
    'wikt': 'wiktionary',
}

def get_wikipedia_url(page, lang='ko', location='wikipedia'):
    left, partitioned, right = page.partition(':')
    while partitioned:
        if left in LOCATION:
            location = LOCATION[left]
        elif re.match(r'^[a-z][a-z]$', left) is not None:
            lang = left
        else:
            break
        page = right
        return get_wikipedia_url(page, lang, location)
    page = get_mediawiki_page(page, 'utf-8')
    if location in ('meta', 'commons'):
        return 'http://%s.wikimedia.org/wiki/%s' % (location, page)
    elif location in ('mediawiki'):
        return 'http://www.%s.org/wiki/%s' % (location, page)
    return 'http://%s.%s.org/wiki/%s' % (lang, location, page)

def on_msg(bot, connection, event):
    msg = event.arguments()[0]
    try: # XXX
        msg = msg.decode('utf-8')
    except UnicodeDecodeError:
        return
    if '[[' not in msg:
        return
    MAX_CNT = 5
    cnt = 0
    visit = {}
    for page in re.findall(r'\[\[(.+?)\]\]', msg):
        if page != page.strip(): continue
        if page in visit: continue
        visit[page] = True
        if cnt >= MAX_CNT:
            bot.reply(event, '최대 %d개까지만 출력합니다.' % MAX_CNT)
            return
        label = ''
        url = get_wikipedia_url(page)
        bot.reply(event, '\x02[%s]\x02 %s' % (page, url))
        cnt += 1

def on_privmsg(bot, connection, event):
    on_msg(bot, connection, event)

def on_pubmsg(bot, connection, event):
    on_msg(bot, connection, event)


