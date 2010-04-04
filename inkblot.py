#!/usr/bin/env python
# -*- encoding: utf-8 -*-
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
    def decorator(fun):
        def new_fun(self, *args):
            try:
                fun(self, *args)
            except StopIteration:
                return
            finally:
                self.ircobj.execute_delayed(period, new_fun, (self,) + args)
        return new_fun
    return decorator

class Inkblot(BufferingBot):
    def __init__(self, config_file_name):
        self.config = None
        self.config_file_name = config_file_name
        self.config_timestamp = self._get_config_time()
        self.config = self._get_config_data()

        server = self.config['server']
        nickname = self.config['nickname']
        BufferingBot.__init__(self, [server], nickname, b'inkblot')
        
        self.plugins = []

        self.handlers = collections.defaultdict(list)

        self.load_plugins()

        self.connection.add_global_handler('welcome', self._on_connected)

        self.version = self.config['version']
        self._check_config_file()

    def _get_config_time(self):
        if not os.access(self.config_file_name, os.F_OK):
            return -1
        return os.stat(self.config_file_name).st_mtime

    def _get_config_data(self):
        if not os.access(self.config_file_name, os.R_OK):
            return None
        try:
            return eval(open(self.config_file_name).read())
        except SyntaxError:
            traceback.print_exc()
        return None

    @periodic(1)
    def _check_config_file(self):
        try:
            t = self._get_config_time()
            if t <= self.config_timestamp:
                return
            self.reload()
        except Exception:
            traceback.print_exc()

    def _on_connected(self, connection, event):
        for chan in self.config['channels']:
            self.connection.join(chan)

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
        data = eval(open(self.config_file_name).read())
        if self.version >= data['version']:
            return
        print("reloading...")
        self.config = data
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
                file_obj, filename, opt = imp.find_module(plugin_name,
                    [import_path])
            except ImportError:
                traceback.print_exc()
                continue
            try:
                plugin = imp.load_module(plugin_name, file_obj, filename, opt)
                self.load_plugin(plugin)
            except Exception:
                traceback.print_exc()
            finally:
                if file_obj:
                    file_obj.close()

    def load_plugin(self, plugin):
        for action in ['privmsg', 'pubmsg']:
            if hasattr(plugin, 'on_'+action):
                def handler(connection, event):
                    try:
                        getattr(plugin, 'on_'+action).__call__(
                            self, connection, event)
                    except:
                        reply = event.target() # XXX freenode only
                        tb = traceback.format_exc()
                        print(tb)
                        self.buffer.push(
                            Message('privmsg', (reply, tb.splitlines()[-1])))
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

