#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

import pygtk
pygtk.require('2.0')

if sys.platform != "win32":
    try:
        print "Using gi"
        from gi.repository import Gtk as gtk
        from gi.repository import GObject as gobject
        from gi.repository import Gdk as gdk
    except ImportError:
        print "Using gtk"
        import gtk
        import gtk.gdk as gdk
        import gobject
else:
    import gtk
    import gtk.gdk as gdk
    import gobject

#import pango
from threading import Thread, Lock
from thread import error as thread_error

from random import Random, randint, sample
from time import sleep, time



import gettext
from gettext import gettext as _

gettext.textdomain(__file__[:-3]) #set app file location without .py as the textdomain for translations

gdk.threads_init()

path = os.path.dirname(os.path.abspath(__file__))

from libs.Helpers import get_libs_path
from data import PathConfig as data_config

get_libs_path(data_config.libs_path_dir, path)

from libs.Logic import uiLogic
from libs.Signals import uiSignals

class App(uiSignals, uiLogic):
    def __init__( self, *args, **kwargs ):
        super(App, self).__init__(*args, **kwargs)

    def callback( self, *args, **kwargs ):
        super(App, self).callback(*args, **kwargs)

    @staticmethod
    def main( *args, **kwargs ):
        gdk.threads_enter()

        try:
            gtk.main()
        except (KeyboardInterrupt, SystemExit):
            kwargs.get("application").quit_gracefully() #defined inside of logic

        gdk.threads_leave()
        return

    @staticmethod
    def get_builder_files( dir='.', list=[], ext='.ui' ):
        for dirname, dirnames, filenames in os.walk(dir):
            for subdirname in dirnames:
                list.extend(App.get_builder_files(subdirname, list, ext))
            for filename in filenames:
                if filename.endswith(ext):
                    if os.path.isfile(os.path.join(dirname, filename)):
                        list += [os.path.join(dirname, filename)]
        return list


def main():
    builder_files = App.get_builder_files(dir='%s/%s' % ( path, data_config.ui_path_dir ))
    app = App(builder_file=builder_files)
    App.callback(app, function = lambda f, *args, **kwargs: f(*args, **kwargs))
    App.main(application=app)
    return

if __name__ == "__main__":
    main()
