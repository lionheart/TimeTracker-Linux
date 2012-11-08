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
from Harvest import Harvest, HarvestError, HarvestStatus

from Notifier import Notifier
from StatusButton import StatusButton

class InterfaceException(Exception):
    pass

class ParameterException(Exception):
    pass

class FunctionParameterException(ParameterException):
    pass
    
try:
    from UI import uiBuilder, uiCreator
except ImportError:
    raise 'User Interface Import Error'
    sys.exit(1)

libs_path = os.path.dirname(os.path.abspath(__file__)) + '/'
sys.path.append(libs_path+"../data")
import Config
media_path = libs_path +'../' + Config.media_path_dir

class logicHelpers(object):
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

    def center_windows(self, *widgets):
        if len(widgets) > 0:
            for w in widgets:
                w.set_position(gtk.WIN_POS_CENTER)

    def string_to_bool(self, string):
        return True if string == "True" or string == True else False

    def bool_to_string(self, bool):
        return "True" if bool == True or bool == "True" else "False"


class logicFunctions(logicHelpers):
    def __init__(self, *args, **kwargs):
        super(self, logicFunctions).__init__(*args, **kwargs) 
        
    def init(self, *args, **kwargs):
        #initialize state variables
        #statusIcon
        self.icon = None #timetracker icon instance

        #timer state
        self.running = False #timer is running and tracking time

        #timeout instances
        self.interval_timer_timeout_instance = None #gint of the timeout_add for interval
        self.elapsed_timer_timeout_instance = None #gint of the timeout for elapsed time
        self.stop_timer_timeout_instance = None #gint of the timeout for stop timer when message shows and no response

        #warning message dialog instance, to close after stop_interval
        self.message_dialog_instance = None

        #harvest login
        self.username = None #current logged in user email
        self.uri = None #current uri

        #harvest instance, crud
        self.harvest = None #harvest instance


        self.projects = [] #list of projects, used in comboboxes
        self.tasks = [] #list of tasks per project, under project index, for comboboxes

        self.entries_vbox = None #used to hold the entries and to empty easily on refresh

        self.today_date = None # holds the date from harvest get_today response
        self.today_day_number = None #hold the day number of today, so we can subtract a few day later and stop all lingering timers

        self.start_time = time() #when self.running == True this is used to calculate the notification interval
        self.time_delta = 0 #difference between now and starttime

        self.today_total = 0 #total hours today

        self.away_from_desk = False #used to start stop interval timer and display away popup menu item
        self.always_on_top = False #keep timetracker iwndow always on top
        self.attention = False #state to set attention icon

        self.interval_dialog_showing = False # whether or not the interval diloag is being displayed

        self.current = {
            '__all': {}, #holds all the current entries for the day
            #merged in to self.current is the current active timer entry
        }

        self.current_entry_id = None #when running this will be set to the current active entry id
        self.current_project_id = None #when running this will have a project id set
        self.current_task_id = None # when running this will have a task id set
        self.current_hours = 0 #when running this will increment with amount of current hours to post to harvest

        self.current_selected_project_id = None #used for current selection of combobox for project, value
        self.current_selected_task_id = None #used for current selected combobox task item, value
        self.current_selected_project_idx = 0 #used for current selection of combobox for project, index
        self.current_selected_task_idx = 0 #used for current selected combobox task item, index

        self.last_project_id = None #last project worked on
        self.last_task_id = None # last task worked on
        self.last_entry_id = None # last worked on time entry, so we can continue it after having stopped all timers

        self.config_filename = kwargs.get('config', 'harvest.cfg')

        #call functions to start up app from here
        self.load_config()

        self.set_status_icon()

        self.connect_to_harvest()

        #stop any timers that were started in previous days
        self._clear_lingering_timers(7) #stop all lingering timers for the last week

        self.center_windows(self. timetracker_window, self.preferences_window)

        self.start_interval_timer() #notification interval, and warning message
        self.start_elapsed_timer() #ui interval that does things every second

        self._status_button = StatusButton()
        self._notifier = Notifier('TimeTracker', gtk.STOCK_DIALOG_INFO, self._status_button)

        self.about_dialog.set_logo(gtk.gdk.pixbuf_new_from_file(media_path + "logo.svg"))

    def handle_visible_state(self):
        '''if self.running:
            self.submit_button.hide()
        else:
            self.submit_button.show()
        '''
        pass

    def toggle_current_timer(self, id):
        self.away_from_desk = False
        self.harvest.toggle_timer(id)
        self.set_entries()

        if not self.running:
            self.statusbar.push(0, "Stopped")

    def start_elapsed_timer(self):
        if self.elapsed_timer_timeout_instance:
            gobject.source_remove(self.elapsed_timer_timeout_instance)

        #do it here so we dont have to wait in the beginning
        self.process_elapsed_timer()

        self.elapsed_timer_timeout_instance = gobject.timeout_add(1000, self.elapsed_timer)

    def elapsed_timer(self):
        self.process_elapsed_timer()

        gobject.timeout_add(1000, self.elapsed_timer)

    def process_elapsed_timer(self):
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
            if self.current.has_key("_label"):
                self.current['_label'].set_text("%0.02f on %s for %s" % (
                    self.current['_hours'], self.current['task'], self.current['project']))
            self.current_hours = "%s" % self.current['_hours'] #set updated current time while running for modify
            self.statusbar.push(0, "%s" % ("Working %s started_at %s" % (time_running,
                                                                         updated_at) if self.running else "Idle"))

    def start_interval_timer(self):
        #interval timer for when to popup the window
        if self.running:
            if self.interval_timer_timeout_instance:
                gobject.source_remove(self.interval_timer_timeout_instance)

            interval = int(round(3600000 * float(self.interval)))

            self.interval_timer_timeout_instance = gobject.timeout_add(interval, self.interval_timer)

    def clear_interval_timer(self):
        #clear interval timer, stops the timer so we can restart it again later
        self.interval_timer_timeout_instance = None

    def interval_timer(self):
        if self.running and not self.away_from_desk and not self.interval_dialog_showing:
            self.call_notify("TimeTracker", "Are you still working on?\n%s" % self.current['text'])
            self.timetracker_window.show()
            self.timetracker_window.present()
            self.interval_dialog("Are you still working on this task?")
            self.stop_interval_timer()

        interval = int(round(3600000 * float(self.interval)))
        self.interval_timer_timeout_instance = gobject.timeout_add(interval, self.interval_timer)

    def stop_interval_timer(self):
        #interval timer for stopping tacking if no response from interval dialog in
        if self.running:
            if self.stop_timer_timeout_instance:
                gobject.source_remove(self.stop_timer_timeout_instance)

            interval = int(round(1000 * int(self.stop_interval)))

            self.stop_timer_timeout_instance = gobject.timeout_add(interval, self.stop_timer_interval)

    def stop_timer_interval(self):
        if self.running: #if running it will turn off, lets empty the comboboxes
            #stop the timer
            self.toggle_current_timer(self.current_entry_id)
            if self.message_dialog_instance:
                self.message_dialog_instance.hide() #hide the dialog

            self.current_project_id = None
            self.current_task_id = None
            self.last_entry_id = self.current_entry_id
            self.refresh_comboboxes()
            self.running = False
            self.attention = True #show attention that something happened

            self.clear_interval_timer()

            #kill the stop_interval timeout instance
            #self.stop_timer_timeout_instance = None

    def set_prefs(self):
        if self.interval:
            self.interval_entry.set_text("%s" % self.interval)

        if self.stop_interval:
            self.stop_timer_interval_entry.set_text("%s" % self.stop_interval)

        if self.timezone_offset_hours:
            self.timezone_offset_entry.set_text("%s" % self.timezone_offset_hours)

        if self.uri:
            self.harvest_url_entry.set_text(self.uri)

        if self.username:
            self.harvest_email_entry.set_text(self.username)

        if self.password: #password may not be saved in keyring
            self.harvest_password_entry.set_text(self.password)

        if self.show_countdown:
            self.countdown_checkbutton.set_active(self.show_countdown)
        else:
            self.countdown_checkbutton.set_active(False)

        if self.show_notification:
            self.show_notification_checkbutton.set_active(self.show_notification)
        else:
            self.show_notification_checkbutton.set_active(False)

        if self.save_passwords:
            self.save_password_checkbutton.set_active(self.save_passwords)
        else:
            self.save_password_checkbutton.set_active(False)

        if self.show_timetracker:
            self.show_timetracker_checkbutton.set_active(self.show_timetracker)
        else:
            self.show_timetracker_checkbutton.set_active(False)

    def get_prefs(self):
        self.username = self.harvest_email_entry.get_text()
        self.uri = self.harvest_url_entry.get_text()
        self.password = self.harvest_password_entry.get_text()

        self.interval = self.interval_entry.get_text()
        self.stop_interval = self.stop_timer_interval_entry.get_text()
        self.timezone_offset_hours = self.timezone_offset_entry.get_text()

        self.show_countdown = self.string_to_bool(self.countdown_checkbutton.get_active())
        self.show_notification = self.string_to_bool(self.show_notification_checkbutton.get_active())
        self.save_passwords = self.string_to_bool(self.save_password_checkbutton.get_active())
        self.show_timetracker = self.string_to_bool(self.show_timetracker_checkbutton.get_active())

    def set_status_icon(self):
        if self.attention:
            if not self.icon:
                self.icon = gtk.status_icon_new_from_file(media_path + "attention.svg")
            else:
                self.icon.set_from_file(media_path + "attention.svg")
            self.icon.set_tooltip("ATTENTION!!!")
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

    def load_config(self):
        self.config = ConfigParser.SafeConfigParser()
        self.config.read(self.config_filename)

        is_new = False
        if not self.config.has_section('auth'):
            self.config.add_section('auth')

        if not self.config.has_option('auth', 'uri'):
            is_new = True
            self.config.set('auth', 'uri', '')
        else:
            self.uri = self.config.get('auth', 'uri')

        if not self.config.has_option('auth', 'username'):
            is_new = True
            self.config.set('auth', 'username', '')
        else:
            self.username = self.config.get('auth', 'username')

        if not self.config.has_section('prefs'):
            self.config.add_section('prefs')

        if not self.config.has_option('prefs', 'interval'):
            is_new = True
            self.config.set('prefs', 'interval', '0.33')
        else:
            self.interval = self.config.get('prefs', 'interval')

        if not self.config.has_option('prefs', 'show_countdown'):
            is_new = True
            self.config.set('prefs', 'show_countdown', 'False')
        else:
            self.show_countdown = self.string_to_bool(self.config.get('prefs', 'show_countdown'))

        if not self.config.has_option('prefs', 'show_notification'):
            is_new = True
            self.config.set('prefs', 'show_notification', 'True')
        else:
            self.show_notification = self.string_to_bool(self.config.get('prefs', 'show_notification'))

        if not self.config.has_option('prefs', 'save_passwords'):
            is_new = True
            self.config.set('prefs', 'save_passwords', 'True')
        else:
            self.save_passwords = self.string_to_bool(self.config.get('prefs', 'save_passwords'))

        if not self.config.has_option('prefs', 'show_timetracker'):
            is_new = True
            self.config.set('prefs', 'show_timetracker', 'True')
        else:
            self.show_timetracker = self.string_to_bool(self.config.get('prefs', 'show_timetracker'))

        if not self.config.has_option('prefs', 'always_on_top'):
            is_new = True
            self.config.set('prefs', 'always_on_top', 'False')
        else:
            self.always_on_top = self.string_to_bool(self.config.get('prefs', 'always_on_top'))

        if not self.config.has_option('prefs', 'timezone_offset_hours'):
            is_new = True
            self.config.set('prefs', 'timezone_offset_hours', '0')
        else:
            self.timezone_offset_hours = self.config.get('prefs', 'timezone_offset_hours')

        if not self.config.has_option('prefs', 'stop_interval'):
            is_new = True
            self.config.set('prefs', 'stop_interval', '300') #don't stop the timer for 5 minutes after the interval warning message by default
        else:
            self.stop_interval = self.config.get('prefs', 'stop_interval')

        #get password
        self.password = self.get_password()

        if is_new:
            #write file in case write not exists or options missing
            self.config.write(open(self.config_filename, 'w'))

    def save_config(self):
        if self.interval <=0 or self.interval == '':
            self.interval = 0.33

        if self.timezone_offset_hours < 0 or self.timezone_offset_hours == '':
            self.timezone_offset_hours = 0

        self.config.set('auth', 'uri', self.uri)
        self.config.set('auth', 'username', self.username)
        self.config.set('prefs', 'interval', "%s" % self.interval)
        self.config.set('prefs', 'stop_interval', "%s" % self.stop_interval)
        self.config.set('prefs', 'show_countdown', self.bool_to_string(self.show_countdown))
        self.config.set('prefs', 'show_notification', self.bool_to_string(self.show_notification))
        self.config.set('prefs', 'show_timetracker', self.bool_to_string(self.show_timetracker))
        self.config.set('prefs', 'timezone_offset_hours', "%s" %(self.timezone_offset_hours))
        self.config.set('prefs', 'save_passwords', self.bool_to_string(self.save_passwords))

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

    def check_harvest_up(self):
        if HarvestStatus().get() == "down":
            self.warning_message(self.timetracker_window, "Harvest Is Down")
            self.attention = True
            return False
        return True

    def _setup_current_data(self, harvest_data):
        self.current = {
            '__projects': harvest_data['projects'],
            '__all': harvest_data['day_entries'],
        }
        #get day entries are for
        self.today_date = harvest_data['for_day']
        self.today_day_number = datetime.strptime(self.today_date, '%Y-%m-%d').timetuple().tm_yday
        self.today_total = 0 #total hours amount for all entries combined
        self.running = False
        self.current_project_id = None
        self.current_task_id = None
        #get total hours and set current
        for entry in self.current['__all']:
            self.today_total += entry['hours']
            entry['created_at'] = datetime.strptime(entry['created_at'], "%Y-%m-%dT%H:%M:%SZ")
            entry['updated_at'] = datetime.strptime(entry['updated_at'], "%Y-%m-%dT%H:%M:%SZ")
            if entry.has_key('timer_started_at'):
                self.current_entry_id = str(entry['id'])
                self.current_project_id = str(entry['project_id'])
                self.current_task_id = str(entry['task_id'])
                self.current.update(entry)
                self.current['text'] = "%s %s %s" % (entry['hours'], entry['task'], entry['project'])
                self.running = True

            self.last_project_id = entry['project_id'] #what was the last project, this should be the last one worked on
            self.last_task_id = entry['task_id'] #and what was the last task, used for append to last entry
            self.last_entry_id = entry['id'] #used for start last entry worked on

        self.projects = {}
        self.tasks = {}

        #all projects, used for liststore for combobox
        for project in self.current['__projects']:
            self.projects[str(project['id'])] = "%s - %s" % (project['client'], project['name'])
            self.tasks[str(project['id'])] = {}
            for task in project['tasks']:
                self.tasks[str(project['id'])][str(task['id'])] = "%s" % task['name']

        self.refresh_comboboxes()

    def _update_entries_box(self):
        if self.entries_vbox:
            self.entries_viewport.remove(self.entries_vbox)
        self.entries_vbox = gtk.VBox(False, 0)
        self.entries_viewport.add(self.entries_vbox)

        for entry in self.current['__all']:
            hbox = gtk.HBox(False, 0)

            if not entry.has_key('timer_started_at'):
                button = gtk.Button(stock="gtk-ok")
                if self.running and entry['id'] == self.current['id']:
                    self.set_custom_label(button, "Continue")
                else:
                    self.set_custom_label(button, "Start")
                edit_button = None
            else:
                button = gtk.Button(stock="gtk-stop")
                button.set_tooltip_text("Stopping the timer will show a more accurate time. Stop, then continue, to update")
                edit_button = gtk.Button(stock="gtk-edit")
                self.set_custom_label(edit_button, "Modify")
                edit_button.connect("clicked", self.on_edit_timer_entry, entry['id'])

            button.connect('clicked', self.on_timer_toggle_clicked, entry['id']) #timer entry id
            hbox.pack_start(button)

            #show edit button for current task so user can modify the entry, done here to pack after start button
            if edit_button:
                hbox.pack_start(edit_button)

            if self.running and entry['id'] == self.current['id']:
                self.current['_label'] = gtk.Label() #hold label reference so we can modify the time in the label every second
                self.current['_label'].set_text(
                    "%0.02f on %s for %s" % (entry['hours'], entry['task'], entry['project']))
                hbox.pack_start(self.current['_label'])
            else:
                label = gtk.Label() #label of a not running entry, dont need reference
                label.set_text("%0.02f on %s for %s" % (entry['hours'], entry['task'], entry['project']))
                hbox.pack_start(label)

            button = gtk.Button(stock="gtk-remove")
            button.connect('clicked', self.on_timer_entry_removed, entry['id'])
            hbox.pack_start(button)

            self.entries_vbox.pack_start(hbox) #pack entry into vbox

        #show all components that were added to the vbox
        self.entries_vbox.show_all()

    def refresh_comboboxes(self):
        self.create_liststore(self.project_combobox, self.projects, self.current_selected_project_idx)
        #repopulate the tasks comboboxes, because they can be different for each project
        if self.current_selected_project_id:
            self.create_liststore(self.task_combobox, self.tasks[self.current_selected_project_id], self.current_selected_task_idx)
        else:#no current project running, just select the first entry
            self.create_liststore(self.task_combobox, {}, self.current_selected_task_idx, True, "Select Project First") #select default None option

        self.set_comboboxes(self.project_combobox, self.current_selected_project_id)
        self.set_comboboxes(self.task_combobox, self.current_selected_task_id)

    def set_entries(self):
        if not self.harvest:
            self.warning_message(self.timetracker_window, "Not Connected to Harvest")
            self.preferences_window.show()
            self.preferences_window.present()
            self.attention = True
            return

        #get data from harvest
        data = self.harvest.get_today()

        self._setup_current_data(data)

        self.attention = False #remove attention state, everything should be fine by now
        if self.current.has_key('id'):
            self.current_hours = "%s" % self.current['hours']
            if  self.current['notes']:
                textbuffer = gtk.TextBuffer()
                textbuffer.set_text(self.current['notes'])
                self.notes_textview.set_buffer(textbuffer)

            self.start_time = time()

            self.running = True
        else:
            self.current_hours = ""
            textbuffer = gtk.TextBuffer()
            textbuffer.set_text("")
            self.notes_textview.set_buffer(textbuffer)

            self.running = False

            #fill the vbox with time entries
        self._update_entries_box()

        #show hide button and hours entry
        self.handle_visible_state()

        self.entries_expander_label.set_text(
            "%s Entries %0.02f hours Total" % (len(self.current['__all']), self.today_total))

    def _clear_lingering_timers(self, count_days = 7):
        start = self.today_day_number - count_days

        #dang it, i feel datelib coming because of 1st and last of year calc, do it simple for now
        for day_number in range(start, self.today_day_number):
            day_data = self.harvest.get_day(day_number, datetime.now().timetuple().tm_year)
            for entry in day_data['day_entries']:
                if entry.has_key('timer_started_at'):
                    self.harvest.toggle_timer(entry['id'])

    def connect_to_harvest(self):
        #check harvest status
        if not self.check_harvest_up():
            return

        #set preference fields data
        self.set_prefs()

        if not self.uri or not self.username or not self.password:
            self.preferences_window.show()
            self.preferences_window.present()
            self.attention = True
            self.running = False
            return False

        try:
            self.harvest = Harvest(self.uri, self.username, self.password)

            self.set_entries()

            #by this time no error means valid login, so lets save it to config
            self.save_config()

            self.set_message_text("%s Logged In" % self.username)
            self.preferences_window.hide()
            self.timetracker_window.show()
            self.timetracker_window.present()
            return True

        except HarvestError as e:
            self.running = False
            self.attention = True
            self.set_message_text("Unable to Connect to Harvest\r\n%s" % e)
            self.warning_message(self.timetracker_window, "Error Connecting!\r\n%s" % e )
            return False
        except Exception as e:
            #catch all other exceptions
            self.running = False
            self.attention = True
            self.set_message_text("Error\r\n%s" % e)
            return False
