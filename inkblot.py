#!/usr/bin/env python
# coding:utf-8
import os
import sys
import imp
import traceback
import collections

import irclib

from BufferingBot import BufferingBot, Message

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
        self.config = None
        self.config_file_name = config_file_name
        self.config_timestamp = self.get_config_time()
        self.config = eval(open(self.config_file_name).read())

        server = self.config['server']
        nickname = self.config['nickname']
        BufferingBot.__init__(self, [server], nickname, b'inkblot')
        
        self.plugins = []

        self.handlers = collections.defaultdict(list)

        self.version = self.config['version']
        self.load_plugins()

        self.connection.add_global_handler('welcome', self._on_connected)
        self.check_config_file()

    def _on_connected(self, connection, event):
        for chan in self.config['channels']:
            self.connection.join(chan)

    def get_config_time(self):
        return os.stat(self.config_file_name).st_mtime

    @periodic(1)
    def check_config_file(self):
        try:
            t = self.get_config_time()
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
            self.buffer.push(Message('privmsg', (reply_to, message)))

    def reload(self):
        print("reloading...")
        data = eval(open(self.config_file_name).read())
        self.config = data
        if self.version >= data['version']:
            return
        self.config_timestamp = os.stat(self.config_file_name).st_mtime
        self.version = data['version']
        irclib.DEBUG = data.get('debug', False)
        self.reload_plugins()
        print("reloaded.")

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
                        reply = event.target() # XXX freenode only
                        tb = traceback.format_exc()
                        print(tb)
                        self.buffer.push(Message('privmsg', (reply, tb.splitlines()[-1])))
                self.handlers[action].append(handler)
                self.connection.add_global_handler(action, handler, 0)
        self.plugins.append(plugin)

    def reload_plugins(self): # XXX
        for action, handlers in self.handlers.items():
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
    print("profile:", profile)
    config_file_name = os.path.join(INKBLOT_ROOT, '%s.py' % profile)
    inkblot = Inkblot(config_file_name)
    print("Inkblot.start()")
    inkblot.start()

if __name__ == '__main__':
    main()

