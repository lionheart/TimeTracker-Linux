import os, sys, math
import gtk, gobject
from time import time
import string
import keyring
from gnomekeyring import IOError as KeyRingError
import ConfigParser
from Notifier import Notifier
from StatusButton import StatusButton

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

    def center_windows(self):
        self.timetracker_window.set_position(gtk.WIN_POS_CENTER)
        self.preferences_window.set_position(gtk.WIN_POS_CENTER)

    def get_textview_text(self, widget):
        buffer = self.notes_textview.get_buffer()
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())

    def string_to_bool(self, string):
        return True if string == "True" else False

    def bool_to_string(self, bool):
        return "True" if bool else "False"

class logicFunctions(logicHelpers):
    def __init__(self, *args, **kwargs):
        super(self, logicFunctions).__init__(*args, **kwargs) 
        
    def init(self, *args, **kwargs):
        #initialize state variables
        self.running = False #timer is running and tracking time
        self.timeout_instance = None #gint of the timeout_add
        self.logged_in = False #used for state whether user is logged in or not
        self.user_id = None #current user id
        self.harvest = None #harvest instance
        self.daily = None #harvest instance used for posting data
        self.projects = [] #list of projects
        self.clients = [] #list of clients
        self.tasks = [] #list of tasks
        self.entries_vbox = None #used to hold the entries and to empty easily
        self.today_start = datetime.today().replace(hour=0, minute=0, second=0) #today_$time for when day changes to keep view intact
        self.today_end = self.today_start + timedelta(1)
        self.start_time = time() #when self.running == True this is used to calculate the notification interval
        self.today_total = 0 #total hours today
        self.current = {
            'all': {}, #holds all the current entries for the day
        }
        self.set_custom_label(self.stop_all_button, 'Force Stop')
        self.config_filename = kwargs.get('config', 'harvest.cfg')

        self.init_status_icon()

        self.get_config()
        self.auth()
        self.set_prefs()

        self.interval = self.config.get('prefs', 'interval')

        self.center_windows()
        self.start_interval_timer()

        self._status_button = StatusButton()
        self._notifier = Notifier('TimeTracker', gtk.STOCK_DIALOG_INFO, self._status_button)


    def start_interval_timer(self):
        if self.running:
            if self.timeout_instance:
                gobject.source_remove(self.timeout_instance)

            interval = int(round(3600000 * float(self.interval)))

            self.timeout_instance = gobject.timeout_add(interval, self.show_timetracker_after_interval)

    def set_prefs(self):
        self.interval_entry.set_text(self.interval)
        self.harvest_url_entry.set_text(self.uri)
        self.harvest_email_entry.set_text(self.username)

        if self.password: #password may not be saved in keyring
            self.harvest_password_entry.set_text(self.password)

    def init_status_icon(self):
        self.icon = gtk.status_icon_new_from_file(media_path + "/idle.png")
        self.icon.set_tooltip("Idle")
        self.state = "idle"
        self.tick_interval = 10 #number of seconds between each poll

        self.icon.set_visible(True)
        self.start_working_time = 0

    def get_config(self):
        self.config = ConfigParser.SafeConfigParser()

        self.config.read(self.config_filename)

        if not self.config.has_section('auth'):
            self.config.add_section('auth')

        if not self.config.has_option('auth', 'uri'):
            self.config.set('auth', 'uri', '')
        else:
            self.uri = self.config.get('auth', 'uri')

        if not self.config.has_option('auth', 'username'):
            self.config.set('auth', 'username', '')
        else:
            self.username = self.config.get('auth', 'username')

        if not self.config.has_section('prefs'):
            self.config.add_section('prefs')

        if not self.config.has_option('prefs', 'interval'):
            self.config.set('prefs', 'interval', '0.33')
        else:
            self.interval = self.config.get('prefs', 'interval')

        if not self.config.has_option('prefs', 'countdown'):
            self.config.set('prefs', 'countdown', 'False')
        else:
            self.countdown = self.config.get('prefs', 'countdown')

        if not self.config.has_option('prefs', 'show_notification'):
            self.config.set('prefs', 'show_notification', 'True')
        else:
            self.show_notification = self.config.get('prefs', 'show_notification')


        self.password = self.get_password()

        #write file in case write not exists or options missing
        self.config.write(open(self.config_filename, 'w'))

    def get_password(self):
        if self.username:
            try:
                return keyring.get_password('TimeTracker', self.username)
            except KeyRingError, e:
                try: #try again, just in case
                    return keyring.get_password('TimeTracker', self.username)
                except KeyRingError, e:
                    self.warning_message(self.preferences_window, "Unable to get Password from Gnome KeyRing")
                    exit(1)

    def save_password(self):
        if self.username and self.password:
            keyring.set_password('TimeTracker', self.username, self.password)

    def set_config(self):
        self.config.set('auth', 'uri', self.uri)
        self.config.set('auth', 'username', self.username)

        self.save_password()

        self.config.write(open(self.config_filename, 'w'))

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

    def set_message_text(self, text):
        self.prefs_message_label.set_text(text)
        self.main_message_label.set_text(text)

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
        self.timetracker_window.present()

    def show_timetracker_after_interval(self):
        if self.running:
            self.call_notify("TimeTracker", "interval elapsed: %s"%self.interval)
            self.timetracker_window.show()
            self.timetracker_window.present()

            interval = int(round(3600000 * float(self.interval)))

            self.timeout_instance = gobject.timeout_add(interval, self.show_timetracker_after_interval)

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

    def start_pulsing_button(self):
        if self.string_to_bool(self.pulsing_icon):
            self._status_button.start_pulsing()

    def _stop_pulsing_button(self):
        self._status_button.stop_pulsing()

    def call_notify(self, summary=None, message=None,
                     reminder_message_func=None, show=True):
        if self.string_to_bool(self.show_notification):
            if show:
                self._notifier.begin(summary, message, reminder_message_func)
            else:
                self._notifier.end()
            
class uiLogic(uiBuilder, uiCreator, logicFunctions):
    def __init__(self,*args, **kwargs):
        super(uiLogic, self).__init__(*args, **kwargs)
        
        #get all the widgets from the glade ui file
        if self.builder_build(widget_list_dict = {}, *args, **kwargs):
            #initialize application
            self.init()

