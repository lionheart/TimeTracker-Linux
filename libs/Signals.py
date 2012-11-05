import gtk
import os, sys
from time import sleep, time
from datetime import datetime, timedelta
from harvest import Harvest, Daily, HarvestStatus, HarvestError

import ConfigParser
import keyring
import pytz
from base64 import b64encode

class uiSignalHelpers(object):
    def __init__(self, *args, **kwargs):
        super(uiSignalHelpers, self).__init__(*args, **kwargs)
        
    def gtk_widget_show(self, w, e = None):
        w.show()
        return True
        
    def gtk_widget_hide(self, w, e = None):
        w.hide()
        return True

    def information_message(self, widget, message):
        messagedialog = gtk.MessageDialog(widget, 0, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, message)
        messagedialog.run()
        messagedialog.destroy()

    def error_message(self, widget, message):
        messagedialog = gtk.MessageDialog(widget, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_CANCEL, message)
        messagedialog.run()
        messagedialog.destroy()

    def warning_message(self, widget, message):
        messagedialog = gtk.MessageDialog(widget, 0, gtk.MESSAGE_WARNING, gtk.BUTTONS_OK_CANCEL, message)
        messagedialog.run()
        messagedialog.destroy()

    def question_message(self, widget, message):
        messagedialog = gtk.MessageDialog(widget, 0, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, message)
        messagedialog.run()
        messagedialog.destroy()

    def set_custom_label(self, widget, text):
        #set custom label on stock button
        Label = widget.get_children()[0]
        Label = Label.get_children()[0].get_children()[1]
        Label = Label.set_label(text)

    def is_entry_active(self, entry):
        return entry.timer_started_at.replace(tzinfo=pytz.utc) >= entry.updated_at.replace(tzinfo=pytz.utc)

    def set_comboboxes(self, widget, id):
        model = widget.get_model()
        i = 0

        for m in model:
            iter = model.get_iter(i)
            if "%s"%model.get_value(iter, 1) == "%s"%id:
                widget.set_active(i)
                break
            i += 1

class uiSignals(uiSignalHelpers):
    def __init__(self, *args, **kwargs):
        super(uiSignals, self).__init__(*args, **kwargs)
        self.preferences_window.connect('delete-event', lambda w, e: w.hide() or True)
        self.timetracker_window.connect('delete-event', lambda w, e: w.hide() or True)
        self.about_dialog.connect("delete-event", lambda w, e: w.hide() or True)
        self.about_dialog.connect("response", lambda w, e: w.hide() or True)
        self.icon.connect('activate', self.left_click)
        self.icon.connect("popup-menu", self.right_click)

    def on_save_preferences_button_clicked(self, widget):
        uri = self.harvest_url_entry.get_text()
        username = self.harvest_email_entry.get_text()
        password = self.harvest_password_entry.get_text()
        if self.auth(uri, username, password):
            self.preferences_window.hide()
            self.timetracker_window.show()
            self.timetracker_window.present()
        else:
            self.preferences_window.show()
            self.preferences_window.present()

    def on_task_combobox_changed(self, widget):
        pass #print widget

    def on_project_combobox_changed(self, widget):
        pass #print widget

    def on_client_combobox_changed(self, widget):
        pass #print widget

    def show_preferences(self, widget):
        self.preferences_window.show()
        self.preferences_window.present()


    def get_projects(self):
        pass


    def away_for_meeting(self, widget):
        pass


    def check_for_updates(self, widget):
        pass
    def save_username_and_uri(self, uri, username):
       if not self.config.has_option('timetracker_login', "uri"):
           self.config.set('timetracker_login', "uri", uri)

       if not self.config.has_option('timetracker_login', "username"):
           self.config.set('timetracker_login', "username", username)

    def auth(self, uri = None, username = None, password = None):
        #check harvest status
        if not self.check_harvest_up():
            return False

        if not uri and not username and not password:
            uri = self.config.get('auth', 'uri')
            username = self.config.get('auth', 'username')
            password = ''
            print "using auth from config: ", username
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
                s= ""
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
                if self.current.has_key('id') and i[0] == self.current['id']:
                    self.set_custom_label(button, "Continue")
                else:
                    self.set_custom_label(button, "Start")
                edit_button = None
            else:
                button = gtk.Button(stock="gtk-stop")
                edit_button = gtk.Button(stock="gtk-edit")
                self.set_custom_label(edit_button, "Modify")
                edit_button.connect("clicked", self.on_edit_timer_entry, i[0])


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
                        'text': "%s" %(i),
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

            self.hours_entry.set_text("%s"%(self.current['hours']))

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

        self.entries_expander_label.set_text("%s Entries %0.02f hours Total"%(entries_count, total))

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
                self.harvest.headers['Authorization'] = 'Basic '+b64encode('%s:%s' % (EMAIL,PASS))
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
            self.set_message_text("Unable to Connect to Harvest\n%s" %(e))
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

            self.set_message_text("%s Logged In"%(self.username))
            self.preferences_window.hide()
            self.timetracker_window.show()
            self.timetracker_window.present()
            return True

        except HarvestError, e:
            self.logged_in = False
            self.set_message_text("Unable to Connect to Harvest\n%s" %(e))
            return False

        except ValueError, e:
            self.logged_in = False
            self.set_message_text("ValueError\n%s" %(e))
            return False

    def on_timer_toggle_clicked(self, widget, id):
        for entry in self.harvest.toggle_entry(id):
            self.set_entries()


    def get_combobox_selection(self, widget):
            model = widget.get_model()
            active = widget.get_active()
            if active < 0:
                return None
            return model[active][1] #0 is name, 1 is id
    def on_entries_expander_activate(self, widget):
        self.set_entries()

    def on_submit_button_clicked(self, widget):
        self.daily.add({
            "request": {
                'notes': self.get_textview_text(self.notes_textview),
                'hours': self.hours_entry.get_text(),
                'project_id': self.get_combobox_selection(self.project_combobox),
                'task_id': self.get_combobox_selection(self.task_combobox)
            }
        })
        self.set_entries()

    def on_timer_entry_removed(self, widget, entry_id):
        self.daily.delete(entry_id)
        self.set_entries()

    def on_edit_timer_entry(self, widget, entry_id):
        self.daily.update( entry_id, {
            "request": {
                'notes': self.get_textview_text(self.notes_textview),
                'hours': self.hours_entry.get_text(),
                'project_id': self.get_combobox_selection(self.project_combobox),
                'task_id': self.get_combobox_selection(self.task_combobox)
            }
        })

        self.set_entries()
