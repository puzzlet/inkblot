#!/usr/bin/env python
# -*- coding: utf8 -*-
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
    for tld in list(servers.keys()):
        l = len(tld)
        if domain[-l:] == tld:
            server = servers[tld]
            break
    
    return server

def digest_ARIN(winfo):
    r = {}
    try:
        r['owner'] = re.findall(b'OrgName:\\s+(.+)', winfo)[0].decode('latin1')
        r['netname'] = re.findall(b'NetName:\\s+(.*)', winfo)[0].decode('latin1')
        r['netblock'] = re.findall(b'NetRange:\\s+([0-9\\.]+) - ([0-9\\.]+)', winfo)[0]
    except IndexError:
        r['owner'], r['netname'] = re.findall(b'(.+) (.+) \\(NET-', winfo)[0]
        r['netblock'] = re.findall(b'([0-9\\.]+) - ([0-9\\.]+)', winfo)[0]
    r['source'] = 'ARIN'
    return r

def digest_RIPE(winfo): # Used by RIPE, APNIC
    r = {}
    r['netblock'] = re.findall(b'inetnum:\\s+([0-9\\.]+) {1,2}- {1,2}([0-9\\.]+)', winfo)[0]
    r['netname'] = re.findall(b'netname:\\s+(.+)', winfo)[0].decode('latin1')
    r['owner'] = re.findall(b'descr:\\s+(.+)', winfo)[0].decode('latin1')
    try:
        r['route'] = re.findall(b'route:[\\s0-9\\./]+\\ndescr:\\s+(.*)', winfo)[0].decode('latin1')
    except IndexError:
        pass
    r['source'] = re.findall(b'source:\\s+(.+)', winfo)[0].decode('latin1')
    return r

def digest_KRNIC(winfo):
    winfo = winfo.decode('cp949')
    r = {}
    try:
        r['netblock'] = re.findall(r'IPv4주소\s+: ([0-9\.]+)-([0-9\.]+)', winfo)[0]
    except IndexError:
        r['netblock'] = 'no block' # ISP Only Format
        r['netname'] = re.findall(r'서비스명\s+: (.+)', winfo)[0]
        r['owner'] = re.findall(r'기 관 명\s+: (.+)', winfo)[0]
    else:
        r['netname'] = re.findall(r'네트워크 이름\s+: (.+)', winfo)[0]
        r['owner'] = re.findall(r'기관명\s+: (.+)', winfo)[0]
        try: r['route'] = re.findall(r'연결 ISP명\s+: (.+)', winfo)[0]
        except IndexError: r['route'] = 'unknown'
    r['source'] = 'KRNIC'
    return r

def digest_JPNIC(winfo):
    r = {}
    try:
        r['netblock'] = re.findall(b'a\\. \\[Network Number\\]\\s+([0-9\\.]+)-([0-9\\.]+)', winfo)[0]
    except:
        r['netblock'] = re.findall(b'a\\. \\[Network Number\\]\\s+([0-9\\.]+)', winfo)[0].decode('ascii')
    r['netname'] = re.findall(b'b\\. \\[Network Name\\]\\s+(.+)', winfo)[0].decode('shift-jis')
    r['owner'] = re.findall(b'g\\. \\[Organization\\]\\s+(.+)', winfo)[0].decode('shift-jis')
    r['source'] = 'JPNIC'
    return r

_=re.compile
ipwregion = {   # whois server     search suffix,  redirect match, digest
    'ARIN':     ('whois.arin.net', '',  None, digest_ARIN),
    'RIPE':     ('whois.ripe.net', '',  _(b'(be found in the RIPE database at whois.ripe.net)|(European Regional Internet Registry/RIPE NCC|RIPE Network Coordination Centre)'), digest_RIPE),
    'APNIC':    ('whois.apnic.net', '', _(b'refer to the APNIC Whois Database'), digest_RIPE),

    'KRNIC':    ('whois.nic.or.kr', '', _(b'(For more information, using KRNIC Whois Database)|(please refer to the KRNIC Whois DB)'), digest_KRNIC),
    'JPNIC':    ('whois.nic.ad.jp', '/e', _(b'(JPNIC whois server at whois.nic.ad.jp)|(Japan Network Information Center \(NETBLK-JAPAN-NET\))'), digest_JPNIC),
}

def IPWhois(addr):
    ip = socket.gethostbyname(addr) # this may cause socket.gaierror exception
    ip = ip.encode('utf8')
    
    winfo = Whois(ip, ipwregion['ARIN'][0])
    wdigest = ipwregion['ARIN'][3]
    while 1:
        for server, suffix, redir, digest in list(ipwregion.values()):
            print(repr(redir))
            print(repr(winfo))
            if redir and redir.search(winfo):
                winfo = Whois(ip+suffix, server)
                wdigest = digest
                break
        else:
            break

    r = wdigest(winfo)
    r['ipv4addr'] = ip.decode('ascii')
    if isinstance(r['netblock'], tuple):
        r['netblock'] = b'-'.join(r['netblock'])
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
    sock.send(domain + b'\r\n')
    #sock.shutdown(1)     # No more sends. XXX: this doesn't work on RIPE
    data = b''
    while 1:
        newdata = sock.recv(16384)
        if not newdata: break
        data = data + newdata
    sock.close()
    # Zap any CR's we see.
    data = b''.join(data.split(b'\r'))
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
        print("%% whois -h %s '%s'" % (dom, name))
        pprint(WhoisList(name, dom))
    except IndexError:
        print("usage: whoisserver.py name domain")

# vim: ai et sw=4 ts=4
