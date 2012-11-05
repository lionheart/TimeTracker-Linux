import os, sys, math
import gtk, gobject
from time import time, sleep
import string

from base64 import b64encode
import ConfigParser
import keyring

from gnomekeyring import IOError as KeyRingError

from datetime import datetime, timedelta
from harvest import Harvest, Daily, HarvestStatus, HarvestError

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
        self.icon = None #timetracker icon
        self.running = False #timer is running and tracking time
        self.interval_timer_timeout_instance = None #gint of the timeout_add for interval
        self.elapsed_timer_timeout_instance = None #gint of the timeout for elapsed time
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
        self.away_from_desk = False #used to start stop interval timer and display away popup menu item
        self.current = {
            'all': {}, #holds all the current entries for the day
        }
        self.set_custom_label(self.stop_all_button, 'Force Stop')
        self.config_filename = kwargs.get('config', 'harvest.cfg')

        self.set_status_icon()

        self.get_config()
        self.auth()
        self.set_prefs()

        self.interval = self.config.get('prefs', 'interval')

        self.center_windows()

        self.start_interval_timer()
        self.start_elapsed_timer()

        self._status_button = StatusButton()
        self._notifier = Notifier('TimeTracker', gtk.STOCK_DIALOG_INFO, self._status_button)


    def start_interval_timer(self):
        if self.running:
            if self.interval_timer_timeout_instance:
                gobject.source_remove(self.interval_timer_timeout_instance)

            interval = int(round(3600000 * float(self.interval)))

            self.interval_timer_timeout_instance = gobject.timeout_add(interval, self.interval_timer)

    def start_elapsed_timer(self):
        if self.elapsed_timer_timeout_instance:
            gobject.source_remove(self.elapsed_timer_timeout_instance)

        self.elapsed_timer_timeout_instance = gobject.timeout_add(1000, self.elapsed_timer)

    def set_prefs(self):
        self.interval_entry.set_text(self.interval)
        self.harvest_url_entry.set_text(self.uri)
        self.harvest_email_entry.set_text(self.username)

        if self.password: #password may not be saved in keyring
            self.harvest_password_entry.set_text(self.password)

    def set_status_icon(self):
        if self.running:
            if self.away_from_desk:
                if not self.icon:
                    self.icon = gtk.status_icon_new_from_file(media_path + "/away.png")
                else:
                    self.icon.set_from_file(media_path + "/away.png")
                self.icon.set_tooltip("AWAY: Working on %s" %(self.current['text']))
            else:
                if not self.icon:
                    self.icon = gtk.status_icon_new_from_file(media_path + "/working.png")
                else:
                    self.icon.set_from_file(media_path + "/working.png")
                self.icon.set_tooltip("Working on %s" % (self.current['text']))
        else:
            if not self.icon:
                self.icon = gtk.status_icon_new_from_file(media_path + "/idle.png")
            else:
                self.icon.set_from_file(media_path + "/idle.png")
            self.icon.set_tooltip("Idle")

        self.icon.set_visible(True)

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

    def left_click(self, event):
        self.timetracker_window.show()
        self.timetracker_window.present()

    def interval_timer(self):
        if self.running and not self.away_from_desk:
            self.call_notify("TimeTracker", "Are you still working on?\n%s"%self.current['text'])
            self.timetracker_window.show()
            self.timetracker_window.present()

        interval = int(round(3600000 * float(self.interval)))
        gobject.timeout_add(interval, self.interval_timer)
    def elapsed_timer(self):
        self.set_status_icon()
        delta = round(round(time() - self.start_time)/ 3600, 2)
        self.status_label.set_text("%s" % ("Running %s started at %s" % (self.current['hours'] + delta, datetime.fromtimestamp(self.start_time).strftime("%H:%M:%S")) if self.running else "Stopped"))
        gobject.timeout_add(1000, self.elapsed_timer)

    def right_click(self, icon, button, time):
        #create popup menu
        menu = gtk.Menu()
        if not self.away_from_desk:
            away = gtk.ImageMenuItem(gtk.STOCK_MEDIA_STOP)
            away.set_label("Away from desk")
        else:
            away = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PLAY)
            away.set_label("Back at desk")

        updates = gtk.MenuItem("Check for updates")
        prefs = gtk.MenuItem("Preferences")
        about = gtk.MenuItem("About")
        quit = gtk.MenuItem("Quit")

        away.connect("activate", self.on_away_from_desk)
        updates.connect("activate", self.on_check_for_updates)
        prefs.connect("activate", self.on_show_preferences)
        about.connect("activate", self.on_show_about_dialog)
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

    def save_username_and_uri(self, uri, username):
        if not self.config.has_option('timetracker_login', "uri"):
            self.config.set('timetracker_login', "uri", uri)

        if not self.config.has_option('timetracker_login', "username"):
            self.config.set('timetracker_login', "username", username)

    def auth(self, uri=None, username=None, password=None):
        #check harvest status
        if not self.check_harvest_up():
            return False

        if not uri and not username and not password:
            uri = self.config.get('auth', 'uri')
            username = self.config.get('auth', 'username')
            password = ''
            print
            "using auth from config: ", username
            if username != '':
                password = keyring.get_password('TimeTracker', username)

                if not password: #for cases where not saved in keyring yet
                    self.preferences_window.show()
                    self.preferences_window.present()
                    return False

                return self._harvest_login(uri, username, password)
            else:
                return self.logged_in
        else:
            print
            "using auth from dialog: ", username
            return self._harvest_login(uri, username, password)

    def check_harvest_up(self):
        if HarvestStatus().status == "down":
            self.warning_message(self.preferences_window, "Harvest Is Down")
            exit(1)
            return False
        else:
            #status is "up"
            return True

    def create_liststore(self, combobox, items):
        '''
            Create a liststore filled with items, connect it to a combobox and activate the first index
        '''
        liststore = combobox.get_model()
        if not liststore:
            liststore = gtk.ListStore(str, str)
            cell = gtk.CellRendererText()
            combobox.pack_start(cell)
            combobox.add_attribute(cell, 'text', 0)
            combobox.add_attribute(cell, 'text', 0)

        else:
            liststore.clear()

        for p in items:
            liststore.append([items[p], p])

        combobox.set_model(liststore)
        combobox.set_active(0)

    def get_data_from_harvest(self):
        '''
        Gets active/activated projects, clients and tasks defined in the account
        '''
        self.projects = {}
        self.clients = {}
        self.tasks = {}
        for project in self.harvest.projects():
            if project.active:
                s = ""
                if project.code:
                    s = "%s - %s" % (project.code, project.name)
                else:
                    s = "%s" % (project.name)

                self.projects[project.id] = s
            else:
                print
                "Inactive Project: ", project.id, project.name

        for client in self.harvest.clients():
            self.clients[client.id] = client.name

        for task in self.harvest.tasks():
            if not task.deactivated:
                self.tasks[task.id] = task.name

    def _update_entries_box(self):
        if self.entries_vbox:
            self.entries_viewport.remove(self.entries_vbox)
        self.entries_vbox = gtk.VBox(False, 0)
        self.entries_viewport.add(self.entries_vbox)

        for i in iter(sorted(self.current['all'].iteritems())):
            hbox = gtk.HBox(False, 0)
            if not i[1]['active']:
                button = gtk.Button(stock="gtk-ok")
                if self.current.has_key('id') and i[0] == self.current['id']:
                    self.set_custom_label(button, "Continue")
                else:
                    self.set_custom_label(button, "Start")
                edit_button = None
            else:
                button = gtk.Button(stock="gtk-stop")
                if self.current['hours'] > 0.0:
                    edit_button = gtk.Button(stock="gtk-edit")
                    self.set_custom_label(edit_button, "Modify")
                    edit_button.connect("clicked", self.on_edit_timer_entry, i[0])
                else:
                    edit_button = None

            button.connect('clicked', self.on_timer_toggle_clicked, i[0]) #timer entry id
            hbox.pack_start(button)

            #show edit button for current task so user can modify the entry
            if edit_button:
                hbox.pack_start(edit_button)

            label = gtk.Label()
            label.set_text(i[1]['text'])
            hbox.pack_start(label)

            button = gtk.Button(stock="gtk-remove")
            button.connect('clicked', self.on_timer_entry_removed, i[0])
            hbox.pack_start(button)

            self.entries_vbox.pack_start(hbox)
        self.entries_vbox.show_all()


    def set_entries(self):
        total = 0

        self.current['all'] = {}
        current_id = None
        for user in self.harvest.users():
            if user.email == self.username:
                entries_count = 0
                for i in user.entries(self.today_start, self.today_end):
                    entries_count += 1
                    total += i.hours

                    active = self.is_entry_active(i)
                    if active:
                        current_id = i.id

                    self.current['all'][i.id] = {
                        'id': i.id,
                        'text': "%s" % (i),
                        'project_id': i.project_id,
                        'task_id': i.task_id,
                        'notes': i.notes,
                        'hours': i.hours,
                        'active': active,
                        'spent_at': i.spent_at,
                        'timer_started_at': i.timer_started_at,
                        'updated_at': i.updated_at,
                        'is_closed': i.is_closed,
                        'is_billed': i.is_billed,
                        'task': i.task,
                        'project': i.project,

                    }
                break

        if current_id:
            self.current.update(self.current['all'][current_id])
            self.current['client_id'] = self.harvest.project(self.current['project_id']).client_id

            self.set_comboboxes(self.project_combobox, self.current['project_id'])
            self.set_comboboxes(self.task_combobox, self.current['task_id'])
            self.set_comboboxes(self.client_combobox, self.current['client_id'])

            self.hours_entry.set_text("%s" % (self.current['hours']))

            textbuffer = gtk.TextBuffer()
            textbuffer.set_text(self.current['notes'])
            self.notes_textview.set_buffer(textbuffer)

            self.start_time = time()

            self.running = True
        else:
            self.hours_entry.set_text("")
            textbuffer = gtk.TextBuffer()
            textbuffer.set_text("")
            self.notes_textview.set_buffer(textbuffer)

            self.running = False

        self._update_entries_box()

        self.entries_expander_label.set_text("%s Entries %0.02f hours Total" % (entries_count, total))

    def _harvest_login(self, URI, EMAIL, PASS):
        '''
        Login to harvest and get data
        '''
        if not URI or not EMAIL or not PASS:
            return False

        try:
            if not PASS:
                PASS = self.get_password()

            EMAIL = EMAIL.replace("\r\n", "").strip()
            PASS = PASS.replace("\r\n", "").strip()

            #fail if pass not set and not in keyring
            if not URI or not EMAIL or not PASS:
                return False

            if self.harvest: #user is logged in and changes login credentials
                self.harvest.uri = URI #set to overwrite for when auth with diff account
                self.harvest.headers['Authorization'] = 'Basic ' + b64encode('%s:%s' % (EMAIL, PASS))
            else:
                self.harvest = Harvest(URI, EMAIL, PASS)

            if self.daily: #user is logged in and changes login credentials
                self.daily.uri = URI #set to overwrite for when auth with diff account
                self.daily.headers['Authorization'] = 'Basic ' + b64encode('%s:%s' % (EMAIL, PASS))
            else:
                self.daily = Daily(URI, EMAIL, PASS)

        except HarvestError:
            self.warning_message(None, "Error Connecting!")

        try:
            for u in self.harvest.users():
                self.user_id = u.id
                self.harvest.id = u.id #set to overwrite for when auth with diff account
                self.daily.id = u.id #set to overwrite for when auth with diff account
                break
        except HarvestError, e:
            self.logged_in = False
            self.set_message_text("Unable to Connect to Harvest\n%s" % (e))
            return False

        try:
            self.get_data_from_harvest()

            self.create_liststore(self.project_combobox, self.projects)
            self.create_liststore(self.client_combobox, self.clients)
            self.create_liststore(self.task_combobox, self.tasks)

            self.uri = URI
            self.username = EMAIL
            self.password = PASS
            self.logged_in = True

            #save valid config
            self.set_config()

            #populate entries
            self.set_entries()

            self.set_message_text("%s Logged In" % (self.username))
            self.preferences_window.hide()
            self.timetracker_window.show()
            self.timetracker_window.present()
            return True

        except HarvestError, e:
            self.logged_in = False
            self.set_message_text("Unable to Connect to Harvest\n%s" % (e))
            return False

        except ValueError, e:
            self.logged_in = False
            self.set_message_text("ValueError\n%s" % (e))
            return False
