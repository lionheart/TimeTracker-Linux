import gtk
import os, sys
from datetime import datetime, timedelta
from harvest import Harvest, HarvestStatus, HarvestError

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
        self.uri = self.harvest_url_entry.get_text()
        self.username = self.harvest_email_entry.get_text()
        self.password = self.harvest_password_entry.get_text()
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
    def save_username_and_uri(self, uri, username):
       if not self.config.has_option('timetracker_login', "uri"):
           self.config.set('timetracker_login', "uri", uri)

       if not self.config.has_option('timetracker_login', "username"):
           self.config.set('timetracker_login', "username", username)

    def auth(self):
    # config file init
        if not self.check_harvest_up():
            return False

        uri = self.config.get('timetracker_login', 'uri')
        username = self.config.get('timetracker_login', 'username')
        password = ''
        if username != '':
            password = keyring.get_password('timetracker_login', username)
        else:
            self.preferences_window.show()

        if password == '' or not self.harvest_login(uri, username, password):
            while not self.logged_in:

                if self.harvest_login(self.harvest_url_entry.get_text(), self.harvest_email_entry.get_text(), self.harvest_password_entry.get_text()):
                    break
                else:
                    self.preferences_window.show()

            # store the username
            config.set('timetracker_login', 'username', EMAIL)
            config.write(open(config_file, 'w'))

            # store the password
            keyring.set_password('timetracker_login', EMAIL, password)
    def check_harvest_up(self):
        if HarvestStatus().status == "down":
            self.warning_message(self.preferences_window, "Harvest Is Down")
            exit(1)

    def create_liststore(self, combobox, items):
        liststore = gtk.ListStore(str, str)
        cell = gtk.CellRendererText()
        combobox.pack_start(cell)
        combobox.add_attribute(cell, 'text', 0)
        combobox.add_attribute(cell, 'text', 0)

        for p in items:
            liststore.append([items[p], p])
        combobox.set_model(liststore)
        combobox.set_active(0)

    def harvest_login(self, URI, EMAIL, PASS):
        print URI, EMAIL, PASS
        try:
            self.harvest = Harvest(URI, EMAIL, PASS)
        except HarvestError:
            self.warning_message(None, "Error Connecting!")
        total = 0
        dose = 0

        start = datetime.today().replace(hour=0, minute=0, second=0)
        end = start + timedelta(1)

        try:
            '''for user in self.harvest.users():
                for entry in user.entries(start, end):
                    total += entry.hours

            text = '%0.02f' % total
            print text

            for project in self.harvest.projects():
                p = "%s"%(project)
                projects_liststore.append(p)
                print p

            for client in self.harvest.clients():
                self.clients += [client]
            for task in self.harvest.tasks():
                self.tasks += [task]
                '''
            projects = {'1': 'Sindulge Harvest', '2': 'Barn.IO', '3': 'TimeTracker', '4': 'WhiteExpress'}
            self.create_liststore(self.project_combobox, projects)
            clients = {'1': 'Sindulge', '2': 'Aurora', '3': 'Me', '4': 'WhiteExpress'}
            self.create_liststore(self.client_combobox, clients)
            tasks = {'1': 'Development', '2': 'Design', '3': 'Project Management', '4': 'Research'}
            self.create_liststore(self.task_combobox, tasks)

            return True

        except HarvestError, e:
            self.warning_message(self.preferences_window, "Unable to Connect to Harvest\n%s" %(e))
            return False

        except ValueError, e:
            self.warning_message(self.preferences_window, "ValueError\n%s" %(e))
            return False

    def on_submit_button_clicked(self, widget):
        print widget