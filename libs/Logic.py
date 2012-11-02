import os, sys, math
import gtk, gobject
from time import time
import string

class InterfaceException(Exception):
    pass

class ParameterException(Exception):
    pass

class FunctionParameterException(ParameterException):
    pass
    
try:
    from UI import uiBuilder, uiCreator, uiTreeView, uiLabel, uiEntry
except ImportError:
    raise 'User Interface Import Error'
    sys.exit(1)


from harvest import Harvest, HarvestError
from datetime import datetime, timedelta

from O import objectify, object_caller

libs_path = os.path.dirname(os.path.abspath(__file__)) + '/'
sys.path.append(libs_path+"../data")
import Config
media_path = libs_path +'../' + Config.media_path_dir


class logicHelpers(objectify):
    def __init__(self, *args, **kwargs):
        super(logicHelpers, self).__init__(*args, **kwargs)

    def clear_entry(self, entry):
        entry.set_text('')
    
    def focus(self, control):
        control.grab_focus()

    def clear_focus(self, control):
        self.clear_entry(control)
        self.focus(control)
        return

    def hide(self, widget):
        widget.hide()

    def sensitive(self, control, bool = False):
        control.set_sensitive( bool )

    def show_warning(self, message):
        self.warning_dialog_message_label.set_text( message )
        return self.warning_dialog.run()
    def center_windows(self):
        self.timetracker_window.set_position(gtk.WIN_POS_CENTER)
        self.preferences_window.set_position(gtk.WIN_POS_CENTER)


class logicFunctions(logicHelpers):
    def __init__(self, *args, **kwargs):
        super(self, logicFunctions).__init__(*args, **kwargs) 
        
    def init(self, *args, **kwargs):
        self.harvest = None
        self.projects = []
        self.clients = []
        self.tasks = []
        self.icon = gtk.status_icon_new_from_file( media_path + "/idle.png")
        self.icon.set_tooltip("Idle")
        self.state = "idle"
        self.tick_interval = 10 #number of seconds between each poll

        self.icon.set_visible(True)
        self.start_working_time = 0
        self.get_projects()

        self.center_windows()

    def format_time(self, seconds):
        minutes = math.floor(seconds / 60)
        if minutes > 1:
            return "%d minutes" % minutes
        else:
            return "%d minute" % minutes

    def set_state(self, state):
        old_state = self.state
        self.icon.set_from_file(media_path + state + ".png")
        if state == "idle":
            delta = time() - self.start_working_time
            if old_state == "ok":
                self.icon.set_tooltip("Good! Worked for %s." %
                                      self.format_time(delta))
            elif old_state == "working":
                self.icon.set_tooltip("Not good: worked for only %s." %
                                      self.format_time(delta))
        else:
            if state == "working":
                self.start_working_time = time()
            delta = time() - self.start_working_time
            self.icon.set_tooltip("Working for %s..." % self.format_time(delta))
        self.state = state
    def show_about_dialog(self, widget):
        about_dialog = gtk.AboutDialog()

        about_dialog.set_destroy_with_parent(True)
        about_dialog.set_name("TimeTracker")
        about_dialog.set_version("1.0")
        about_dialog.set_authors(["Alex Goretoy"])

        about_dialog.run()
        about_dialog.destroy()

    def left_click(self, event):
        self.timetracker_window.show()
        delta = time() - self.start_working_time
        if self.state == "idle":
            self.set_state("working")
        else:
            self.set_state("idle")
        if not self.harvest:
            self.auth(None, None, None)


    def update(self):
        delta = time() - self.start_working_time
        print delta
        if self.state == "idle":
            pass
        else:
            self.icon.set_tooltip("Working for %s..." % self.format_time(delta))
            if self.state == "working":
                if delta > MIN_WORK_TIME:
                    self.set_state("ok")
        source_id = gobject.timeout_add(self.tick_interval * 1000, self.update)
    def right_click(self, icon, button, time):
        menu = gtk.Menu()

        away = gtk.MenuItem("Away for meeting")
        updates = gtk.MenuItem("Check for updates")
        prefs = gtk.MenuItem("Preferences")
        about = gtk.MenuItem("About")
        quit = gtk.MenuItem("Quit")

        away.connect("activate", self.away_for_meeting)
        updates.connect("activate", self.check_for_updates)
        prefs.connect("activate", self.show_preferences)
        about.connect("activate", self.show_about_dialog)
        quit.connect("activate", gtk.main_quit)

        menu.append(away)
        menu.append(updates)
        menu.append(prefs)
        menu.append(about)
        menu.append(quit)

        menu.show_all()

        menu.popup(None, None, gtk.status_icon_position_menu, button, time, self.icon)


                    
    def _reset_spin_range( self, spin, list, idx = None ):
        spin.set_range( 1, len( list ) + 1 )  
        if not idx:
            spin.set_value( len( list ) + 1 )
        else:
            spin.set_value( idx )
            

            
class uiLogic(uiBuilder, uiCreator, logicFunctions):
    def __init__(self,*args, **kwargs):
        super(uiLogic, self).__init__(*args, **kwargs)
        
        #get all the widgets from the glade ui file
        if self.builder_build(widget_list_dict = {}, *args, **kwargs):
            #initialize application
            self.init()

