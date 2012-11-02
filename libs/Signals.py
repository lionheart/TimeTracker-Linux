import gtk
import os, sys
from datetime import datetime, timedelta
from harvest import Harvest, HarvestError

import getpass
import ConfigParser

import keyring

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

class uiSignals(uiSignalHelpers):
    def __init__(self, *args, **kwargs):
        super(uiSignals, self).__init__(*args, **kwargs)
        self.preferences_window.connect('delete-event', lambda w, e: w.hide() or True)
        self.timetracker_window.connect('delete-event', lambda w, e: w.hide() or True)
        self.icon.connect('activate', self.left_click)
        self.icon.connect("popup-menu", self.right_click)

    def on_save_preferences_button_clicked(self, widget):
        URI = self.harvest_url_entry.get_text()
        EMAIL = self.harvest_email_entry.get_text()
        PASS = self.harvest_password_entry.get_text()
        if URI != "" and EMAIL != "" and PASS != "":
            self.auth(URI, EMAIL, PASS)
            self.preferences_window.hide()
        else:
            self.warning_message(self.preferences_window, "Invalid Login Information")

    def on_task_combobox_changed(self, widget):
        print widget

    def on_project_combobox_changed(self, widget):
        print widget

    def on_client_combobox_changed(self, widget):
        print widget

    def show_preferences(self, widget):
        self.center_windows()
        self.preferences_window.show()


    def get_projects(self):
        pass


    def away_for_meeting(self, widget):
        pass


    def check_for_updates(self, widget):
        pass

    def auth(self, URI, EMAIL, PASS):
    # config file init
        config_file = 'harvest.cfg'
        config = ConfigParser.SafeConfigParser({
            'username': '',
        })
        config.read(config_file)
        if not config.has_section('timetracker_login'):
            config.add_section('timetracker_login')

        if not config.has_option('timetracker_login', "uri"):
            config.set('timetracker_login', "uri", URI)

        if not config.has_option('timetracker_login', "username"):
            config.set('timetracker_login', "username", EMAIL)

        uri = config.get('timetracker_login', 'uri')
        username = config.get('timetracker_login', 'username')
        password = None
        if username != '':
            password = keyring.get_password('timetracker_login', username)

        if password == None or not self.harvest_login(uri, username, password):
            while 1:
                username = raw_input("Username:\n")
                password = getpass.getpass("Password:\n")

                if self.harvest_login(URI, EMAIL, PASS):
                    break
                else:
                    print
                    "Authorization failed."

            # store the username
            config.set('timetracker_login', 'username', EMAIL)
            config.write(open(config_file, 'w'))

            # store the password
            keyring.set_password('timetracker_login', EMAIL, password)

    def harvest_login(self, URI, EMAIL, PASS):
        self.harvest = Harvest(URI, EMAIL, PASS)
        self.users = self.harvest.users()

        total = 0
        dose = 0

        start = datetime.today().replace(hour=0, minute=0, second=0)
        end = start + timedelta(1)
        try:

            try:
                for user in self.harvest.users():
                    for entry in user.entries(start, end):
                        total += entry.hours

                text = '%0.02f' % total
                print text
                projects_liststore = gtk.ListStore(str)
                cell = gtk.CellRendererText()
                self.project_combobox.pack_start(cell)
                self.project_combobox.add_attribute(cell, 'text', 0)


                for project in self.harvest.projects():
                    p = "%s"%(project)
                    projects_liststore.append(p)
                for client in self.harvest.clients():
                    self.clients += [client]
                for task in self.harvest.tasks():
                    self.tasks += [task]
                self.project_combobox.set_model(projects_liststore)
                print self.projects, self.clients, self.tasks
                return True

            except HarvestError, e:
                print 'Retrying in 5 minutes...'
                return False
        except ValueError, e:
            print "unknown url"
            return False
