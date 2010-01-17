#!/usr/bin/env python
# coding:utf-8
import os
import sys
import imp
import traceback
import collections

import irclib
irclib.DEBUG = 1

from BufferingBot import BufferingBot, Packet

def periodic(period):
    """Decorate a class instance method so that the method would be
    periodically executed by irclib framework.
    """
    def decorator(f):
        def new_f(self, *args):
            try:
                f(self, *args)
            except StopIteration:
                return
            finally:
                self.ircobj.execute_delayed(period, new_f, (self,) + args)
        return new_f
    return decorator

class Inkblot(BufferingBot):
    def __init__(self, config_file_name):
        BufferingBot.__init__(self, [('irc.freenode.net', 6665)], 'inkblot', 'bot run by wikipedia-ko/PuzzletChung')
        self.plugins = []
        self.config_file_name = config_file_name
        self.handlers = collections.defaultdict(list)
        self.config_timestamp = os.stat(self.config_file_name).st_mtime
        data = eval(open(self.config_file_name).read())
        self.version = data['version']
        self.load_plugins()
        self.connection.add_global_handler('welcome', self._on_connected)
        self.check_config_file()

    def _on_connected(self, connection, event):
        self.connection.join('#puzzlet')
        self.connection.join('#wikipedia-ko')

    @periodic(1)
    def check_config_file(self):
        try:
            t = os.stat(self.config_file_name).st_mtime
            if t <= self.config_timestamp:
                return
            self.reload()
        except Exception:
            traceback.print_exc()

    def reply(self, event, message):
        try:
            message = message.encode('utf-8')
        except:
            traceback.print_exc()
            return
        eventtype = event.eventtype().lower()
        target = event.target()
        source = event.source()
        if source:
            source = irclib.nm_to_n(source)
        if eventtype in ('privmsg', 'pubmsg'):
            reply_to = target if irclib.is_channel(target) else source
            self.buffer.push(Packet('privmsg', (reply_to, message)))

    def reload(self):
        print "reloading"
        data = eval(open(self.config_file_name).read())
        if self.version >= data['version']:
            return
        self.config_timestamp = os.stat(self.config_file_name).st_mtime
        self.version = data['version']
        self.reload_plugins()

    def load_plugins(self):
        import_path = os.path.join(INKBLOT_ROOT, 'plugins') # XXX
        plugin_names = []
        for x in os.listdir(import_path):
            if x.endswith('.py') and not x.startswith('__'):
                plugin_names.append(x[:-3])
        for plugin_name in plugin_names:
            try:
                fp, filename, opt = imp.find_module(plugin_name, [import_path])
            except ImportError:
                traceback.print_exc()
                continue
            try:
                plugin = imp.load_module(plugin_name, fp, filename, opt)
                self.load_plugin(plugin)
            except Exception:
                traceback.print_exc()
            finally:
                if fp:
                    fp.close()

    def load_plugin(self, plugin):
        for action in ['privmsg', 'pubmsg']:
            if hasattr(plugin, 'on_'+action):
                def handler(connection, event):
                    try:
                        getattr(plugin, 'on_'+action).__call__(self, connection, event)
                    except:
                        reply = event.target() # XXX
                        tb = traceback.format_exc()
                        print tb
                        self.buffer.push(Packet('privmsg', (reply, tb.splitlines()[-1])))
                self.handlers[action].append(handler)
                self.connection.add_global_handler(action, handler, 0)
        self.plugins.append(plugin)

    def reload_plugins(self): # XXX
        for action, handlers in self.handlers.iteritems():
            for handler in handlers:
                self.connection.remove_global_handler(action, handler)
        self.load_plugins()

INKBLOT_ROOT = os.path.dirname(os.path.abspath(__file__))
def main():
    profile = None
    if len(sys.argv) > 1:
        profile = sys.argv[1]
    if not profile:
        profile = 'config'
    print profile
    config_file_name = os.path.join(INKBLOT_ROOT, '%s.py' % profile)
    inkblot = Inkblot(config_file_name)
    inkblot.start()

if __name__ == '__main__':
    main()

