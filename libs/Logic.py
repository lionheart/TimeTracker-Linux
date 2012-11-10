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
        #print 'logic helpers __init__'

    def callback(self, *args, **kwargs): #stub
        super(self, logicHelpers).callback(*args, **kwargs)
        #print 'logic helpers callback'

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
        #print 'logic functions __init__'

    def callback(self, *args, **kwargs): #stub
        super(self, logicFunctions).callback(*args, **kwargs)
        #print 'logic functions callback'

    def init(self, *args, **kwargs):
        #print 'init'
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

        self.today_total_hours = 0 #total hours today
        self.today_total_elapsed_hours = 0 #today_total_hours + elapsed time while running

        self.away_from_desk = False #used to start stop interval timer and display away popup menu item
        self.always_on_top = False #keep timetracker iwndow always on top

        self.attention = None #state/message to set attention icon

        self.interval_dialog_showing = False # whether or not the interval diloag is being displayed

        self.current = {
            '__all': {}, #holds all the current entries for the day
            #merged in to self.current is the current active timer entry
        }

        self.current_entry_id = None #when running this will be set to the current active entry id

        self.current_created_at = None #holds the current task created at date for showing in statusbar

        self.current_hours = 0 #when running this will increment with amount of current hours to post to harvest

        self.current_selected_project_id = None #used for current selection of combobox for project, value
        self.current_selected_task_id = None #used for current selected combobox task item, value
        self.current_selected_project_idx = 0 #used for current selection of combobox for project, index
        self.current_selected_task_idx = 0 #used for current selected combobox task item, index

        self.last_project_id = None #last project worked on
        self.last_task_id = None # last task worked on
        self.last_entry_id = None # last worked on time entry, so we can continue it after having stopped all timers
        self.last_hours = 0 #last hours, for sending to update last timer

        #combobox handlers to block
        self.project_combobox_handler = None
        self.task_combobox_handler = None

        self.config_filename = kwargs.get('config', 'harvest.cfg')

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
        self._process_elapsed_timer()

        self.elapsed_timer_timeout_instance = gobject.timeout_add(1000, self._elapsed_timer)

    def _elapsed_timer(self):
        self._process_elapsed_timer()

        gobject.timeout_add(1000, self._elapsed_timer)

    def _process_elapsed_timer(self):
        self.set_status_icon()
        if self.running:
            self.time_delta = round(round(time() - self.start_time) / 3600, 3)
            self.current['elapsed_hours'] = self.current['hours'] + self.time_delta #amount of time to add real time in app while timer running
            self.today_total_elapsed_hours = float(self.today_total_hours) + float(self.time_delta)

            self._update_elapsed_status()
            self._set_counter_label()

            self.current_hours = "%0.02f" % round(self.current['elapsed_hours'], 2) #set updated current time while running for modify


    def _update_elapsed_status(self):
        sub = 0
        minutes_running = -1
        dt = parse(self.current['updated_at'].replace(tzinfo=pytz.utc).strftime("%Y-%m-%d %H:%M:%S%z"))
        while minutes_running < 0:
            updated_at = dt.astimezone(tzoffset(None, 3600 * sub))
            #updated_at = datetime.fromtimestamp(updated_at.timetuple())
            minutes_running = (time() - mktime(updated_at.timetuple()) + (
                8 * 60 * 60)) / 60  #minutes timer has been running
            sub += 1
        seconds_running = (time() - mktime(updated_at.timetuple()) + (8 * 60 * 60)) % 60
        time_running = "%02d:%02d" % (minutes_running, seconds_running)

        eff_time_it_sux = parse("%s" % (updated_at + timedelta( hours=-8 + sub - 1))).strftime("%H:%M") if self.running else "Idle"

        self.statusbar.push(0, "%s" % ("Working %s started_at %s created_at %s" % (time_running, eff_time_it_sux, self.current_created_at )))

    def _set_counter_label(self):
        self.counter_label.set_text(
            "%s Entries %0.02f hours Total" % (self.entries_count, self.today_total_elapsed_hours))

    def start_interval_timer(self):
        #interval timer for when to popup the window
        if self.running:
            if self.interval_timer_timeout_instance:
                gobject.source_remove(self.interval_timer_timeout_instance)

            self.interval_timer_timeout_instance = gobject.timeout_add(self._interval, self._interval_timer) #start interval to show warning

    def clear_interval_timer(self):
        #clear interval timer, stops the timer so we can restart it again later
        self.interval_timer_timeout_instance = None

    def _interval_timer(self):
        if self.running and not self.away_from_desk and not self.interval_dialog_showing:
            self.call_notify("TimeTracker", "Are you still working on?\n%s" % self.current['text'])
            self.timetracker_window.show()
            self.timetracker_window.present()
            self.interval_dialog_instance = self.interval_dialog("Are you still working on this task?")
            self.start_stop_interval_timer() #start interval to stop the timer

        self.interval_timer_timeout_instance = gobject.timeout_add(self._interval, self._interval_timer) #restart interval, for cases where not running(etc) to keep moving

    def start_stop_interval_timer(self):
        #interval timer for stopping tacking if no response from interval dialog in
        if self.running:
            if self.stop_timer_timeout_instance:
                gobject.source_remove(self.stop_timer_timeout_instance)

            self.stop_timer_timeout_instance = gobject.timeout_add(self._stop_interval, self._stop_timer_interval)

    def _stop_timer_interval(self):
        if self.running: #if running it will turn off, lets empty the comboboxes
            #stop the timer
            self.toggle_current_timer(self.current_entry_id)
            if self.message_dialog_instance:
                self.message_dialog_instance.hide() #hide the dialog

            self.refresh_comboboxes()

            self.running = False

            self.attention = "Timer Stopped!"

            self.statusbar.push(0, "Stop Timer Timeout")

            self.clear_stop_interval_timer()

    def get_notes(self, text = None):
        notes = text if text else ""
        current_time = datetime.time(datetime.now()).strftime("%H:%M")

        if notes != "":
            notes = "%s\n%s: %s" % (notes, current_time, self.get_textview_text(self.notes_textview))
        else:
            notes = "%s: %s" % (current_time, self.get_textview_text(self.notes_textview))
        return notes

    def clear_stop_interval_timer(self):
        self.stop_timer_timeout_instance = None

    def set_prefs(self):
        if self.interval:
            self.interval_entry.set_text("%s" % self.interval)

        if self.stop_interval:
            self.stop_timer_interval_entry.set_text("%s" % self.stop_interval)

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
        self._interval = int(round(3600000 * float(self.interval)))

        self.stop_interval = self.stop_timer_interval_entry.get_text()
        self._stop_interval = int(round(1000 * int(self.stop_interval)))

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
            self.icon.set_tooltip(self.attention)
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
            self._interval = int(round(3600000 * float(self.interval)))

        if not self.config.has_option('prefs', 'stop_interval'):
            is_new = True
            self.config.set('prefs', 'stop_interval',
                '300') #don't stop the timer for 5 minutes after the interval warning message by default
        else:
            self.stop_interval = self.config.get('prefs', 'stop_interval')
            self._stop_interval = int(round(1000 * int(self.stop_interval)))

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

        #get password
        self.password = self.get_password()

        if is_new:
            #write file in case write not exists or options missing
            self.config.write(open(self.config_filename, 'w'))

    def save_config(self):
        if self.interval <=0 or self.interval == '':
            self.interval = 0.33

        self.config.set('auth', 'uri', self.uri)
        self.config.set('auth', 'username', self.username)
        self.config.set('prefs', 'interval', "%s" % self.interval)
        self.config.set('prefs', 'stop_interval', "%s" % self.stop_interval)
        self.config.set('prefs', 'show_countdown', self.bool_to_string(self.show_countdown))
        self.config.set('prefs', 'show_notification', self.bool_to_string(self.show_notification))
        self.config.set('prefs', 'show_timetracker', self.bool_to_string(self.show_timetracker))
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
        #print 'logic __init__'
        #get all the widgets from the glade ui file
        if self.builder_build(widget_list_dict={}, *args, **kwargs):
            #initialize application
            #run before_init to setup callbacks and other junk that may be needed later on
            self.before_init()

            #run the meat of the setup, the application is actually ran from the callback via _run_application()
            self.init()

            #setup any other callbacks and whatnot, this is after all other callback have been connected inside init
            self.after_init()

    def callback(self, *args, **kwargs): #executed after init, lets us inject interrupts
        '''
        execution order:
        logic __init__
            signals before init
            init
            signals after init
        signal helpers __init__
        signals __init__
        logic callback
            logic _run_application
                checking harvest up
        signal helpers callback
        signals callback
        '''
        #print 'logic callback'
        def _handle_callback(*args):
            return self._run_application()

        return kwargs.get("function")( lambda *args, **kwargs: _handle_callback(*args, **kwargs) )

    def quit_gracefully(self): #after all those callbacks and stuff, this function works like a charm, successfully injected interrupts
        print 'quitting'

    def _run_application(self):
        #print 'logic _run_application'
        #call functions to start up app from here
        self.load_config()

        self.set_status_icon()

        self.connect_to_harvest()

        #stop any timers that were started in previous days
        self._clear_lingering_timers(7) #stop all lingering timers for the last week

        self.center_windows(self.timetracker_window, self.preferences_window)

        self.start_interval_timer() #notification interval, and warning message
        self.start_elapsed_timer() #ui interval that does things every second

        self._status_button = StatusButton()
        self._notifier = Notifier('TimeTracker', gtk.STOCK_DIALOG_INFO, self._status_button)

        self.about_dialog.set_logo(gtk.gdk.pixbuf_new_from_file(media_path + "logo.svg"))

        return self

    def check_harvest_up(self):
        #print 'checking harvest up'
        if HarvestStatus().get() == "down":
            self.warning_message(self.timetracker_window, "Harvest Is Down")
            self.attention = "Harvest is Down!"
            return self.not_connected()
        return True

    def refresh_comboboxes(self):
        if self.project_combobox_handler:
            self.project_combobox.handler_block(self.project_combobox_handler)

        self.create_liststore(self.project_combobox, self.projects, self.current_selected_project_idx)

        if self.project_combobox_handler:
            self.project_combobox.handler_unblock(self.project_combobox_handler)

        #repopulate the tasks comboboxes, because they can be different for each project
        if self.current_selected_project_id and self.current_selected_task_idx > -1:
            if self.task_combobox_handler:
                self.task_combobox.handler_block(self.task_combobox_handler)
            self.create_liststore(self.task_combobox, self.tasks[self.current_selected_project_id], self.current_selected_task_idx)
            if self.task_combobox_handler:
                self.task_combobox.handler_unblock(self.task_combobox_handler)

        elif self.current_selected_task_idx > -1:#no current project running, just select the first entry
            if self.task_combobox_handler:
                self.task_combobox.handler_block(self.task_combobox_handler)
            self.create_liststore(self.task_combobox, {}, self.current_selected_task_idx, True, "Select Project First") #select default None option
            if self.task_combobox_handler:
                self.task_combobox.handler_unblock(self.task_combobox_handler)


        self.set_comboboxes(self.project_combobox, self.current_selected_project_id)
        self.set_comboboxes(self.task_combobox, self.current_selected_task_id)

    def not_connected(self):
        self.warning_message(self.timetracker_window, "Not Connected to Harvest")
        self.preferences_window.show()
        self.preferences_window.present()

        if not self.attention:
            self.attention = "Not Connected to Harvest!"
        else:#append any previous message
            self.attention = "Not Connected to Harvest!\r\n%s" % self.attention
        return

    def set_entries(self):
        if not self.harvest:
            return self.not_connected()

        #get data from harvest
        data = self.harvest.get_today()

        self._setup_current_data(data)

        self.attention = None #remove attention state, everything should be fine by now

        if not self.running:
            self.statusbar.push(0, "Stopped")

    def _clear_lingering_timers(self, count_days = 7):
        start = self.today_day_number - count_days

        #get range of count_days before today and stop timers on all those days
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

            self.running = False
            return self.not_connected()

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
            self.attention = "Unable to Connect to Harvest!"
            self.set_message_text("Unable to Connect to Harvest\r\n%s" % e)
            self.warning_message(self.timetracker_window, "Error Connecting!\r\n%s" % e )
            return self.not_connected()
        except Exception as e:
            #catch all other exceptions
            self.running = False
            self.attention = "ERROR: %s" % e
            self.set_message_text("Error\r\n%s" % e)
            return self.not_connected()


    def _setup_current_data(self, harvest_data):
        self.current = {
            '__projects': harvest_data['projects'], #these will be unset at the end, we should
            '__all': harvest_data['day_entries'],
        }

        self.entries_count = len(self.current['__all'])

        #get day entries are for
        self.today_date = harvest_data['for_day']
        self.today_day_number = datetime.strptime(self.today_date, '%Y-%m-%d').timetuple().tm_yday #used to get previous days

        self.today_total_hours = 0 #total hours amount for all entries combined
        self.today_total_elapsed_hours = 0 #today_total_hours + timedelta

        self.running = False

        self.projects = {}
        self.tasks = {}

        #all projects, used for liststore for combobox
        for project in self.current['__projects']:
            project_id = str(project['id'])
            self.projects[project_id] = "%s - %s" % (project['client'], project['name'])
            self.tasks[project_id] = {}
            for task in project['tasks']:
                task_id = str(task['id'])
                self.tasks[project_id][task_id] = "%s" % task['name']

        _updated_at = None #date used to determine the newest entry to use as last entry, a user could on a diff comp use\
        # harvest web app and things go out of sync so we should use the newest updated_at entry

        # reset
        self.current_entry_id = None

        self.current_hours = ""

        self.last_project_id = None
        self.last_task_id = None
        self.last_entry_id = None
        self.last_hours = 0

        #get total hours and set current
        for entry in self.current['__all']:
            #how many hours worked today, used in counter label
            self.today_total_hours += entry['hours']

            #make dates into a datetime object we can use
            entry['created_at'] = datetime.strptime(entry['created_at'], "%Y-%m-%dT%H:%M:%SZ")
            entry['updated_at'] = datetime.strptime(entry['updated_at'], "%Y-%m-%dT%H:%M:%SZ")

            #this should all go away, leave for now
            if not _updated_at:#first time
                _updated_at = entry['updated_at']
            if _updated_at <= entry['updated_at']:
                _updated_at = entry['updated_at']

                self.last_entry_id = entry['id']
                self.last_project_id = entry['project_id']
                self.last_task_id = entry['task_id']
                self.last_hours = "%0.02f" % entry['hours']
                self.last_notes = "%s" % entry['notes'] if entry['notes'] else ""

            #this should go away as much as possible
            if entry.has_key('timer_started_at'):
                entry_id = str(entry['id'])
                project_id = str(entry['project_id'])
                task_id = str(entry['task_id'])

                self.current_entry_id = entry_id
                self.current_selected_project_id = project_id
                self.current_selected_project_idx = self.projects.keys().index(
                    project_id) + 1 #compensate for empty 'select one'
                self.current_selected_task_id = task_id
                self.current_selected_task_idx = self.tasks[project_id].keys().index(
                    task_id) + 1 #compensate for empty 'select one'
                self.current.update(entry) #merge everything into current

                self.current_created_at = entry['created_at'] #set created at date for use in statusbar, as of now

                self.current['text'] = "%s %s %s" % (entry['hours'], entry['task'], entry['project']) #make the text

                self.current_hours = "%0.02f" % round(self.current['hours'], 2) #used in posting to harvest and calculations

                self.running = True
                self.start_time = time()  #start time for determine timedelta every second while running, it can be out of sync when not running who cares

        self.set_textview_text(self.notes_textview, "")

        self.refresh_comboboxes() #setup the comboboxes

    def append_add_entry(self):
        if self.harvest: #we have to be connected
            if self.current_selected_project_id and self.current_selected_task_id:
                self.set_entries() #febreeze the place, mom is coming

                if self.running:
                    got_one = False
                    for entry in self.current['__all']:
                        if (entry['project_id'] == self.current_selected_project_id\
                            and entry['task_id'] == self.current_selected_task_id)\
                            and self.current_hours: #current running time with timedelta added from timer
                            print '1'



                            notes = entry['notes'] if entry.has_key('notes') else None
                            notes = self.get_notes(notes)

                            entry = self.harvest.update(entry['id'], {#append to existing timer
                                 'notes': notes,
                                 'hours': self.current_hours,
                                 'project_id': self.current_selected_project_id,
                                 'task_id': self.current_selected_task_id
                            })

                            got_one = True
                            break

                    if not got_one:
                        #not the same project task as last one, add new entry
                        print '2'

                        entry = self.harvest.add({
                            'notes': self.get_notes(),
                            'hours': "",
                            'project_id': self.current_selected_project_id,
                            'task_id': self.current_selected_task_id
                        })

                    if not entry.has_key('timer_started_at'): #start the timer if adding it hasn't strated it
                        self.harvest.toggle_timer(entry['id'])

                else:
                    got_one = False
                    for entry in self.current['__all']:
                        if (entry['project_id'] == self.current_selected_project_id\
                            and entry['task_id'] == self.current_selected_task_id): #found existing project/task entry for today, just append to it
                            self.harvest.toggle_timer(entry['id'])
                            print '3'

                            notes = entry['notes'] if entry.has_key('notes') else None
                            print self.get_notes(notes)
                            entry = self.harvest.update(entry['id'], {#append to existing timer
                                 'notes': self.get_notes(notes),
                                 'hours': entry['hours'],
                                 'project_id': self.current_selected_project_id,
                                 'task_id': self.current_selected_task_id
                            })

                            got_one = True
                            break

                    if not got_one:
                        #not the same project task as last one, add new entry
                        print '4'
                        entry = self.harvest.add({
                            'notes': self.get_notes(),
                            'hours': "",
                            'project_id': self.current_selected_project_id,
                            'task_id': self.current_selected_task_id
                        })

                    if not entry.has_key('timer_started_at'): #start the timer if adding it hasn't strated it
                        self.harvest.toggle_timer(entry['id'])

            else:
                self.statusbar.push(0, "No Project and Task Selected")
                return False
        else: #something is wrong we aren't connected
            return self.not_connected()
