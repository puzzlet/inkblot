#!/usr/bin/env python
# -*- coding: cp949 -*-
# vim: ts=8 sts=4 et
#
# Copyright 2000 Dominic Mitchell <dom@happygiraffe.net>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
# OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
# IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

"""
Python Whois tools.

Server(domain)    - Return an appropriate whois server for a domain.
Whois(domain, server=None)    - Return whois output for domain.
"""

__rcs_id__='$Id: whois.py 103 2005-05-15 12:42:13Z barosl $'
__version__='$Revision: 1.2 $'[11:-2]

import os
import re
import sys
import string
import socket

# Obtain full list from http://www.geektools.com/dist/whoislist.gz.

whoislist = "./whoislist"

INTERNIC = "whois.crsnic.net"

# In case whoislist isn't present.
defaultservers = {
    '.com':    INTERNIC,
    '.net':    INTERNIC,
    '.org':    INTERNIC,
    '.edu':    INTERNIC,
    '.uk':    'whois.nic.uk',
}
servers = {}

def Server(domain):
    """Return the whois server for domain."""

    server = INTERNIC            # Default.
    for tld in servers.keys():
        l = len(tld)
        if domain[-l:] == tld:
            server = servers[tld]
            break
    
    return server

def digest_ARIN(winfo):
    r = {}
    try:
        r[u'owner'] = re.findall(r'OrgName:\s+(.+)', winfo)[0].decode('latin1')
        r[u'netname'] = re.findall(r'NetName:\s+(.*)', winfo)[0].decode('latin1')
        r[u'netblock'] = re.findall(r'NetRange:\s+([0-9\.]+) - ([0-9\.]+)', winfo)[0]
    except IndexError:
        r[u'owner'], r[u'netname'] = re.findall(r'(.+) (.+) \(NET-', winfo)[0]
        r[u'netblock'] = re.findall(r'([0-9\.]+) - ([0-9\.]+)', winfo)[0]
    r[u'source'] = u'ARIN'
    return r

def digest_RIPE(winfo): # Used by RIPE, APNIC
    r = {}
    r[u'netblock'] = re.findall(r'inetnum:\s+([0-9\.]+) {1,2}- {1,2}([0-9\.]+)', winfo)[0]
    r[u'netname'] = re.findall(r'netname:\s+(.+)', winfo)[0].decode('latin1')
    r[u'owner'] = re.findall(r'descr:\s+(.+)', winfo)[0].decode('latin1')
    try:
        r[u'route'] = re.findall(r'route:[\s0-9\./]+\ndescr:\s+(.*)', winfo)[0].decode('latin1')
    except IndexError:
        pass
    r[u'source'] = re.findall(r'source:\s+(.+)', winfo)[0].decode('latin1')
    return r

def digest_KRNIC(winfo):
    r = {}
    try:
        r[u'netblock'] = re.findall(r'IPv4�ּ�\s+: ([0-9\.]+)-([0-9\.]+)', winfo)[0]
    except IndexError:
        r[u'netblock'] = u'no block' # ISP Only Format
        r[u'netname'] = re.findall(r'���񽺸�\s+: (.+)', winfo)[0].decode('cp949')
        r[u'owner'] = re.findall(r'�� �� ��\s+: (.+)', winfo)[0].decode('cp949')
    else:
        r[u'netname'] = re.findall(r'��Ʈ��ũ �̸�\s+: (.+)', winfo)[0].decode('cp949')
        r[u'owner'] = re.findall(r'�����\s+: (.+)', winfo)[0].decode('cp949')
        try: r[u'route'] = re.findall(r'���� ISP��\s+: (.+)', winfo)[0].decode('cp949')
        except IndexError: r[u'route'] = u'unknown'
    r[u'source'] = u'KRNIC'
    return r

def digest_JPNIC(winfo):
    r = {}
    try:
        r[u'netblock'] = re.findall(r'a\. \[Network Number\]\s+([0-9\.]+)-([0-9\.]+)', winfo)[0]
    except:
        r[u'netblock'] = re.findall(r'a\. \[Network Number\]\s+([0-9\.]+)', winfo)[0].decode('ascii')
    r[u'netname'] = re.findall(r'b\. \[Network Name\]\s+(.+)', winfo)[0].decode('shift-jis')
    r[u'owner'] = re.findall(r'g\. \[Organization\]\s+(.+)', winfo)[0].decode('shift-jis')
    r[u'source'] = u'JPNIC'
    return r

_=re.compile
ipwregion = {   # whois server     search suffix,  redirect match, digest
    'ARIN':     ('whois.arin.net', '',  None, digest_ARIN),
    'RIPE':     ('whois.ripe.net', '',  _('(be found in the RIPE database at whois.ripe.net)|(European Regional Internet Registry/RIPE NCC|RIPE Network Coordination Centre)'), digest_RIPE),
    'APNIC':    ('whois.apnic.net', '', _('refer to the APNIC Whois Database'), digest_RIPE),

    'KRNIC':    ('whois.nic.or.kr', '', _('(For more information, using KRNIC Whois Database)|(please refer to the KRNIC Whois DB)'), digest_KRNIC),
    'JPNIC':    ('whois.nic.ad.jp', '/e', _('(JPNIC whois server at whois.nic.ad.jp)|(Japan Network Information Center \(NETBLK-JAPAN-NET\))'), digest_JPNIC),
}

def IPWhois(addr):
    ip = socket.gethostbyname(addr) # this may cause socket.gaierror exception
    
    winfo = Whois(ip, ipwregion['ARIN'][0])
    wdigest = ipwregion['ARIN'][3]
    while 1:
        for server, suffix, redir, digest in ipwregion.values():
            if redir and redir.search(winfo):
                winfo = Whois(ip+suffix, server)
                wdigest = digest
                break
        else:
            break

    r = wdigest(winfo)
    r[u'ipv4addr'] = ip.decode('ascii')
    if isinstance(r[u'netblock'], tuple):
        r[u'netblock'] = u'-'.join(r[u'netblock'])
    return r


def Whois(domain, server=None):
    """Return the whois output for a domain."""

    if server == None:
        server = Server(domain)

    server = socket.gethostbyname(server)
    port = socket.getservbyname('whois', 'tcp')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server, port))

    # The protocol itself.
    sock.send(domain + '\r\n')
    #sock.shutdown(1)     # No more sends. XXX: this doesn't work on RIPE
    data = ''
    while 1:
        newdata = sock.recv(16384)
        if not newdata: break
        data = data + newdata
    sock.close()
    # Zap any CR's we see.
    if string.find(data, '\r') >= 0:
        data = string.join(string.split(data, '\r'), '')
    return data

def WhoisList(domain, server=None):
    """Return the whois output for a domain, as a list of lines."""
    data = Whois(domain, server)
    if string.find(data, '\r') >= 0:
        data = string.join(string.split(data, '\r'), '')
    data = string.split(data, '\n')
    # Tidying.
    if data[-1] == '': del data[-1]
    return data

def _init():
    """Initialise the servers dict from a file."""
    global servers

    try:
        # To create this module, run listmgr.py
        import whoislist
        servers = whoislist.servers
    except ImportError:
        servers = defaultservers

# Call when module is first imported.
_init()

if __name__ == '__main__':
    try:
        from pprint import pprint
        name = sys.argv[1]
        dom = sys.argv[2]
        print "%% whois -h %s '%s'" % (dom, name)
        pprint(WhoisList(name, dom))
    except IndexError:
        print "usage: whoisserver.py name domain"

# vim: ai et sw=4 ts=4
