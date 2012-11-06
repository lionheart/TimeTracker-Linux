import os, sys, math
import gtk, gobject
from time import time, sleep, mktime
import string

import pytz
from dateutil.parser import parse
from dateutil.tz import tzoffset

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
        return True if string == "True" or string == True else False

    def bool_to_string(self, bool):
        return "True" if bool == True or bool == "True" else "False"

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
        self.username = None #current logged in user email
        self.uri = None #current uri
        self.harvest = None #harvest instance
        self.daily = None #harvest instance used for posting data
        self.projects = [] #list of projects
        self.clients = [] #list of clients
        self.tasks = [] #list of tasks
        self.entries_vbox = None #used to hold the entries and to empty easily
        self.today_start = datetime.today().replace(hour=0, minute=0, second=0) #today_$time for when day changes to keep view intact
        self.today_end = self.today_start + timedelta(1)
        self.start_time = time() #when self.running == True this is used to calculate the notification interval
        self.time_delta = 0 #difference between now and starttime
        self.today_total = 0 #total hours today
        self.away_from_desk = False #used to start stop interval timer and display away popup menu item
        self.save_passwords = True #used to save password, toggled by checkbutton
        self.show_timetracker = True #show timetracker window on interval, overridden by config or prefs dialog
        self.interval_dialog_showing = False # whether or not the interval diloag is being displayed
        self.always_on_top = False #keep timetracker iwndow always on top
        self.attention = False #state to set attention icon
        self.timezone_offset_hours = 0 #number of hours to add to the updated_at time that is set on time entries
        self.current = {
            'all': {}, #holds all the current entries for the day
        }
        self.set_custom_label(self.stop_all_button, 'Force Stop')
        self.config_filename = kwargs.get('config', 'harvest.cfg')

        self.set_status_icon()

        self.auth()

        interval = self.config.get('prefs', 'interval')
        self.interval = 0.33 if not interval else interval

        self.center_windows()

        self.start_interval_timer()
        self.start_elapsed_timer()

        self._status_button = StatusButton()
        self._notifier = Notifier('TimeTracker', gtk.STOCK_DIALOG_INFO, self._status_button)

        self.about_dialog.set_logo(gtk.gdk.pixbuf_new_from_file(media_path + "logo.svg"))

    def handle_visible_state(self):
        if self.running:
            #self.hours_hbox.show_all()
            self.submit_button.hide()
        else:
            self.hours_hbox.hide()
            self.submit_button.show()

    def toggle_current_timer(self, id):
        self.away_from_desk = False
        for entry in self.harvest.toggle_entry(id):
            self.set_entries()

        if not self.running:
            self.statusbar.push(0, "Stopped")

    def start_elapsed_timer(self):
        if self.elapsed_timer_timeout_instance:
            gobject.source_remove(self.elapsed_timer_timeout_instance)

        #do it here so we dont have to wait in the beginning
        self.process_timer_shtuff()

        self.elapsed_timer_timeout_instance = gobject.timeout_add(1000, self.elapsed_timer)

    def elapsed_timer(self):
        self.process_timer_shtuff()

        gobject.timeout_add(1000, self.elapsed_timer)

    def process_timer_shtuff(self):
        self.set_status_icon()
        if self.running:
            dt = parse(self.current['updated_at'].replace(tzinfo=pytz.utc).strftime("%Y-%m-%d %H:%M:%S%z"))
            self.time_delta = round(round(time() - self.start_time) / 3600, 3)
            self.current['_hours'] = self.current['hours'] + self.time_delta #amount of time to add real time in app while timer running

            try:
                timezone_offset = int(self.timezone_offset_hours)
            except Exception as e:
                timezone_offset = 0

            updated_at = dt.astimezone(tzoffset(None, 3600 * timezone_offset))
            #updated_at = datetime.fromtimestamp(updated_at.timetuple())
            minutes_running = (time() - mktime(updated_at.timetuple())+(8*60*60)) / 60  #minutes timer has been running
            seconds_running = (time() - mktime(updated_at.timetuple())+(8*60*60)) % 60
            time_running = "%02d:%02d" % (minutes_running, seconds_running)
            self.current['_label'].set_text("%0.02f on %s for %s" % (
                self.current['_hours'], self.current['task'].name, self.current['project'].name))
            self.hours_entry.set_text("%s"%(self.current['_hours'])) #set updated current time while running for modify
            self.statusbar.push(0, "%s" % ("Working %s started_at %s" % (time_running,
                                                                         updated_at) if self.running else "Idle"))

    def start_interval_timer(self):
        if self.running:
            if self.interval_timer_timeout_instance:
                gobject.source_remove(self.interval_timer_timeout_instance)

            interval = int(round(3600000 * float(self.interval)))

            self.interval_timer_timeout_instance = gobject.timeout_add(interval, self.interval_timer)

    def interval_timer(self):
        if self.running and not self.away_from_desk:
            self.call_notify("TimeTracker", "Are you still working on?\n%s" % self.current['text'])
            self.timetracker_window.show()
            self.timetracker_window.present()

            self.interval_dialog("Are you still working on this task?")

        interval = int(round(3600000 * float(self.interval)))
        gobject.timeout_add(interval, self.interval_timer)

    def set_prefs(self):
        if self.interval:
            self.interval_entry.set_text(self.interval)

        if self.uri:
            self.harvest_url_entry.set_text(self.uri)

        if self.username:
            self.harvest_email_entry.set_text(self.username)

        if self.password: #password may not be saved in keyring
            self.harvest_password_entry.set_text(self.password)

    def get_prefs(self):
        #self.username = self.harvest_email_entry.get_text()
        #self.uri = self.harvest_url_entry.get_text()
        self.interval = self.interval_entry.get_text()
        self.timezone_offset_hours = self.timezone_offset_entry.get_text()
        self.countdown = self.bool_to_string(self.countdown_checkbutton.get_active())
        self.show_notification = self.bool_to_string(self.show_notification_checkbutton.get_active())
        self.save_passwords = self.bool_to_string(self.save_password_checkbutton.get_active())
        self.show_timetracker = self.bool_to_string(self.show_timetracker_checkbutton.get_active())

    def set_status_icon(self):
        if self.attention:
            if not self.icon:
                self.icon = gtk.status_icon_new_from_file(media_path + "attention.svg")
            else:
                self.icon.set_from_file(media_path + "attention.svg")
            self.icon.set_tooltip("AWAY: Working on %s" % (self.current['text']))
            return

        if self.running:
            if self.away_from_desk:
                if not self.icon:
                    self.icon = gtk.status_icon_new_from_file(media_path + "away.svg")
                else:
                    self.icon.set_from_file(media_path + "away.svg")
                self.icon.set_tooltip("AWAY: Working on %s" %(self.current['text']))
            else:
                if not self.icon:
                    self.icon = gtk.status_icon_new_from_file(media_path + "working.svg")
                else:
                    self.icon.set_from_file(media_path + "working.svg")
                self.icon.set_tooltip("Working on %s" % (self.current['text']))
        else:
            if not self.icon:
                self.icon = gtk.status_icon_new_from_file(media_path + "idle.svg")
            else:
                self.icon.set_from_file(media_path + "idle.svg")
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
            self.show_notification = self.string_to_bool(self.config.get('prefs', 'show_notification'))

        if not self.config.has_option('prefs', 'save_passwords'):
            self.config.set('prefs', 'save_passwords', 'True')
        else:
            self.save_passwords = self.string_to_bool(self.config.get('prefs', 'save_passwords'))

        if not self.config.has_option('prefs', 'show_timetracker'):
            self.config.set('prefs', 'show_timetracker', 'True')
        else:
            self.show_timetracker = self.string_to_bool(self.config.get('prefs', 'show_timetracker'))

        if not self.config.has_option('prefs', 'always_on_top'):
            self.config.set('prefs', 'always_on_top', 'False')
        else:
            self.always_on_top = self.string_to_bool(self.config.get('prefs', 'always_on_top'))

        if not self.config.has_option('prefs', 'timezone_offset_hours'):
            self.config.set('prefs', 'timezone_offset_hours', '0')
        else:
            self.timezone_offset_hours = self.config.get('prefs', 'timezone_offset_hours')

        #get password
        self.password = self.get_password()

        #write file in case write not exists or options missing
        self.config.write(open(self.config_filename, 'w'))

    def set_config(self):
        self.config.set('auth', 'uri', self.uri)
        self.config.set('auth', 'username', self.username)
        self.config.set('prefs', 'interval', self.interval)
        self.config.set('prefs', 'countdown', self.countdown)
        self.config.set('prefs', 'show_notification', self.show_notification)
        self.config.set('prefs', 'show_timetracker', self.show_timetracker)
        self.config.set('prefs', 'timezone_offset_hours', self.timezone_offset_hours)
        self.config.set('prefs', 'save_passwords', self.save_passwords)

        self.save_password()

        self.config.write(open(self.config_filename, 'w'))

    def get_password(self):
        if self.username:
            try:
                return keyring.get_password('TimeTracker', self.username)
            except KeyRingError, e:
                try: #try again, just in case
                    return keyring.get_password('TimeTracker', self.username)
                except KeyRingError as e:
                    self.warning_message(self.preferences_window, "Unable to get Password from Gnome KeyRing")
                    exit(1)

    def save_password(self):
        if self.save_passwords and self.username and self.password:
            keyring.set_password('TimeTracker', self.username, self.password)


    def format_time(self, seconds):
        minutes = math.floor(seconds / 60)
        if minutes > 1:
            return "%d minutes" % minutes
        else:
            return "%d minute" % minutes

    def set_message_text(self, text):
        self.prefs_message_label.set_text(text)
        self.main_message_label.set_text(text)

    def start_pulsing_button(self):
        if self.string_to_bool(self.pulsing_icon):
            self._status_button.start_pulsing()

    def _stop_pulsing_button(self):
        self._status_button.stop_pulsing()

    def call_notify(self, summary=None, message=None, reminder_message_func=None, show=True):
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
            self.get_config() #set instance vars from config
            uri = self.config.get('auth', 'uri')
            username = self.config.get('auth', 'username')
            password = ''
            print "using auth from config: ", username
            if username != '':
                password = keyring.get_password('TimeTracker', username)

                if not password: #for cases where not saved in keyring yet
                    self.preferences_window.show()
                    self.preferences_window.present()
                    self.running = False
                    self.logged_in = False
                    return False

                return self._harvest_login(uri, username, password)
            else:
                return self.logged_in
        else:
            print "using auth from dialog: ", username
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
                print "Inactive Project: ", project.id, project.name

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
                if self.running and i[0] == self.current['id']:
                    self.set_custom_label(button, "Continue")
                else:
                    self.set_custom_label(button, "Start")
                edit_button = None
            else:
                button = gtk.Button(stock="gtk-stop")
                button.set_tooltip_text("Stopping the timer will show a more accurate time. Stop, then continue, to update")
                edit_button = gtk.Button(stock="gtk-edit")
                self.set_custom_label(edit_button, "Modify")
                edit_button.connect("clicked", self.on_edit_timer_entry, i[0])

            button.connect('clicked', self.on_timer_toggle_clicked, i[0]) #timer entry id
            hbox.pack_start(button)

            #show edit button for current task so user can modify the entry
            if edit_button:
                hbox.pack_start(edit_button)
            if self.running and i[0] == self.current['id']:
                self.current['_label'] = gtk.Label()
                self.current['_label'].set_text(
                    "%0.02f on %s for %s" % (i[1]['hours'], i[1]['task'].name, i[1]['project'].name))
                hbox.pack_start(self.current['_label'])
            else:
                label = gtk.Label()
                label.set_text("%0.02f on %s for %s" % (i[1]['hours'], i[1]['task'].name, i[1]['project'].name))
                hbox.pack_start(label)

                #unset some unneeded data
            del i[1]['project'], i[1]['task']

            button = gtk.Button(stock="gtk-remove")
            button.connect('clicked', self.on_timer_entry_removed, i[0])
            hbox.pack_start(button)

            self.entries_vbox.pack_start(hbox)
        self.entries_vbox.show_all()


    def set_entries(self):
        total = 0
        entries_count = 0
        self.current['all'] = {}
        current_id = None

        if not self.harvest:
            self.set_message_text("Not Connected to Harvest")
            self.attention = True #set attention icon
            return

        #store harvest data in App instance to use inside application
        for user in self.harvest.users():
            if user.email == self.username:
                self.attention = False #if we get here we can safely remove attention icon
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
            #harvest timer is running
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

        #fill the vbox with time entries
        self._update_entries_box()

        #show hide button and hours entry
        self.handle_visible_state()

        self.entries_expander_label.set_text("%s Entries %0.02f hours Total" % (entries_count, total))

    def is_entry_active(self, entry):
        #time_difference = self.current['timer_started_at'] - datetime.fromtimestamp(self.start_time).replace(tzinfo=pytz.utc)
        return entry.timer_started_at.replace(tzinfo=pytz.utc) >= entry.updated_at.replace(tzinfo=pytz.utc)

    def _harvest_login(self, URI, EMAIL, PASS):
        '''
        Login to harvest and get data
        '''
        if not URI or not EMAIL or not PASS:
            self.logged_in = False
            self.running = False
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
            self.logged_in = False
            self.running = False
            self.attention = True
            self.warning_message(None, "Error Connecting!")

        try:
            for u in self.harvest.users():
                self.user_id = u.id
                if not u.is_admin:
                    self.warning_message(self.timetracker_window, "You are not admin, cannot proceed.")
                    exit(1)

                self.harvest.id = u.id #set to overwrite for when auth with diff account
                self.daily.id = u.id #set to overwrite for when auth with diff account
                break
        except HarvestError as e:
            self.logged_in = False
            self.running = False
            self.attention = True
            self.set_message_text("Unable to Connect to Harvest\n\nPerhaps you don't have the proper privileges in harvest\n\n%s" % (e))
            return False

        try:
            self.get_data_from_harvest()


            self.create_liststore(self.project_combobox, self.projects)
            self.create_liststore(self.client_combobox, self.clients)
            self.create_liststore(self.task_combobox, self.tasks)

            self.get_config()

            self.uri = URI
            self.username = EMAIL
            self.password = PASS

            self.logged_in = True


            self.get_prefs()

            self.set_prefs()

            #save valid config
            self.set_config()

            #populate entries
            self.set_entries()

            self.set_message_text("%s Logged In" % (self.username))
            self.preferences_window.hide()
            self.timetracker_window.show()
            self.timetracker_window.present()
            return True

        except HarvestError as e:
            self.logged_in = False
            self.running = False
            self.attention = True
            self.set_message_text("Unable to Connect to Harvest\n%s" % (e))
            return False

        except ValueError as e:
            self.logged_in = False
            self.running = False
            self.attention = True
            self.set_message_text("ValueError\n%s" % (e))
            return False
