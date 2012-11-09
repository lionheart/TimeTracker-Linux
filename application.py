#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygtk

pygtk.require('2.0')

import gtk
import gtk.gdk
import pango
import gobject

from threading import Thread, Lock
from thread import error as thread_error

from random import Random, randint, sample
from time import sleep, time

import os
import sys

import gettext
from gettext import gettext as _

gettext.textdomain(__file__[:-3])

gtk.gdk.threads_init()

path = os.path.dirname(os.path.abspath(__file__))

from libs.Helpers import get_libs_path
from data import Config as data_config

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
        gtk.gdk.threads_enter()

        gtk.main()

        gtk.gdk.threads_leave()
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
    App(builder_file=builder_files)
    App.callback()
    App.main()
    return

if __name__ == "__main__":
    main()
