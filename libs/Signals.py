import gtk

from datetime import datetime
import gobject
from threading import Thread

class uiSignalHelpers(object):
    def __init__(self, *args, **kwargs):
        super(uiSignalHelpers, self).__init__(*args, **kwargs)
        
    def gtk_widget_show(self, w, e = None):
        w.show()
        return True
        
    def gtk_widget_hide(self, w, e = None):
        w.hide()
        return True

    def information_message(self, widget, message, cb = None):
        self.attention = "INFO: %s" % message
        messagedialog = gtk.MessageDialog(widget, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, message)
        messagedialog.connect("delete-event", lambda w, e: w.hide() or True)
        if cb:
            messagedialog.connect("response", cb)

        messagedialog.set_default_response(gtk.RESPONSE_OK)
        messagedialog.show()
        messagedialog.present()
        return messagedialog


    def error_message(self, widget, message):
        self.attention = "ERROR: %s" % message
        messagedialog = gtk.MessageDialog(widget, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, gtk.BUTTONS_CANCEL, message)
        messagedialog.run()
        messagedialog.destroy()

    def warning_message(self, widget, message):
        self.attention = "WARNING: %s" % message
        messagedialog = gtk.MessageDialog(widget, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, gtk.BUTTONS_OK_CANCEL, message)
        messagedialog.show()
        messagedialog.present()
        messagedialog.run()
        messagedialog.destroy()

    def question_message(self, widget, message, cb = None):
        self.attention = "QUESTION: %s" % message
        messagedialog = gtk.MessageDialog(widget, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, message)
        messagedialog.connect("delete-event", lambda w, e: w.hide() or True)
        if cb:
            messagedialog.connect("response", cb)

        messagedialog.set_default_response(gtk.RESPONSE_YES)
        messagedialog.show()
        messagedialog.present()
        return messagedialog

    def interval_dialog(self, message):
        if not self.interval_dialog_showing:
            if not self.timetracker_window.is_active():
                self.timetracker_window.show()
                self.timetracker_window.present()

            self.interval_dialog_showing = True
            self.message_dialog_instance = self.question_message(self.timetracker_window, message, self.on_interval_dialog)

    def stop_interval_dialog(self, message):
        if not self.stop_interval_dialog_showing:
            if not self.timetracker_window.is_active():
                self.timetracker_window.show()
                self.timetracker_window.present()

            self.stop_interval_dialog_showing = True
            self.stop_interval_dialog_instance = self.information_message(self.timetracker_window, message, self.on_stopped)

    def set_custom_label(self, widget, text):
        #set custom label on stock button
        Label = widget.get_children()[0]
        Label = Label.get_children()[0].get_children()[1]
        Label = Label.set_label(text)

    def window_state(self, widget, state):
        self.timetracker_window_state = state.new_window_state

class uiSignals(uiSignalHelpers):
    def __init__(self, *args, **kwargs):
        super(uiSignals, self).__init__(*args, **kwargs)
        self.preferences_window.connect('delete-event', lambda w, e: w.hide() or True)
        self.timetracker_window.connect('delete-event', lambda w, e: w.hide() or True)
        self.timetracker_window.connect('destroy', lambda w, e: w.hide() or True)
        self.timetracker_window.connect("window-state-event", self.window_state)
        self.about_dialog.connect("delete-event", lambda w, e: w.hide() or True)
        self.about_dialog.connect("response", lambda w, e: w.hide() or True)
        self.icon.connect('activate', self.left_click)
        self.icon.connect("popup-menu", self.right_click)

    def callback(self, *args, **kwargs): #executed after init, hopefully this will let me inject interrupts
        pass

    def before_init(self):
        pass

    def after_init(self):
        self.project_combobox_handler = self.project_combobox.connect('changed', self.on_project_combobox_changed)
        self.task_combobox_handler = self.task_combobox.connect('changed', self.on_task_combobox_changed)

    def on_show_about_dialog(self, widget):
        self.about_dialog.show()

    def on_interval_dialog(self, dialog, a): #interval_dialog callback
        if a == gtk.RESPONSE_NO and self.running: #id will be set if running
            self.toggle_current_timer(self.current['id'])#stop the timer
            if not self.timetracker_window.is_active():#show timetracker window if not shown
                self.timetracker_window.show()
                self.timetracker_window.present()
        else:
            self.timetracker_window.hide() #hide timetracker and continue task

        #restart interval
        self.clear_interval_timer()
        self.start_interval_timer()
        self.clear_stop_interval_timer()

        dialog.destroy()

        self.attention = None

        self.interval_dialog_showing = False

    def on_stopped(self, dialog):
        if not self.timetracker_window.is_active():
            self.timetracker_window.show()
            self.timetracker_window.present()

        dialog.destroy()

        self.attention = None

        self.stop_interval_dialog_showing = False

    def on_save_preferences_button_clicked(self, widget):
        if self.running: #if running it will turn off, lets empty the comboboxes
            #stop the timer
            #self.toggle_current_timer(self.current_entry_id) #maybe add pref option to kill timer on pref change?
            if self.message_dialog_instance:
                self.message_dialog_instance.hide() #hide the dialog

        self.get_prefs()
        if self.connect_to_harvest():
            self.preferences_window.hide()
            self.timetracker_window.show()
            self.timetracker_window.present()


    def on_task_combobox_changed(self, widget):
        new_idx = widget.get_active()
        if new_idx != -1:
            if new_idx != self.current_selected_task_idx: #-1 is sent from pygtk loop or something
                self.current_selected_task_id = self.get_combobox_selection(widget)
                self.current_selected_task_idx = new_idx
                self.refresh_comboboxes()

    def on_project_combobox_changed(self, widget):
        self.current_selected_project_id = self.get_combobox_selection(widget)
        new_idx = widget.get_active()
        print self.current_selected_project_id, self.current_selected_task_id
        if new_idx != -1:
            #reset task when new project is selected
            self.current_selected_project_idx = new_idx
            self.current_selected_task_id = None
            self.current_selected_task_idx = 0
            self.refresh_comboboxes()

    def on_show_preferences(self, widget):
        self.preferences_window.show()
        self.preferences_window.present()

    def on_away_from_desk(self, widget):
        #toggle away state
        if self.running:
            self.away_from_desk = True if not self.away_from_desk else False

    def on_check_for_updates(self, widget):
        pass

    def on_top(self, widget):
        on_top = True if self.always_on_top else False
        self.timetracker_window.set_keep_above(on_top)

    #not needed anymore for slimmed interface
    def on_timer_toggle_clicked(self, widget, id):
        if self.running: #if running it will turn off, lets empty the comboboxes
            self.current_project_id = None
            self.current_task_id = None
            self.refresh_comboboxes()

        #allow to start or stop a timer
        self.toggle_current_timer(id)

    #not needed anymore for slimmed interface
    def on_entries_expander_activate(self, widget):
        if not widget.get_expanded():
            self.set_entries()

    def on_submit_button_clicked(self, widget):
        print 'project', self.current_project_id, self.current_selected_project_id
        print 'task', self.current_task_id, self.current_selected_task_id
        print 'last', self.last_project_id, self.last_task_id, self.last_entry_id

        self.away_from_desk = False
        self.start_interval_timer()

        self.append_add_entry()

        self.set_entries()

    #not needed anymore for slimmed interface
    def on_timer_entry_removed(self, widget, entry_id):
        self.away_from_desk = False
        if self.harvest:
            self.harvest.delete(entry_id)
        else:
            self.warning_message(self.timetracker_window, "Not Connected to Harvest")

        self.set_entries()

    #not needed anymore for slimmed interface
    def on_edit_timer_entry(self, widget, entry_id):
        self.away_from_desk = False

        hours = self.current_hours

        #if time passed and the user tries to modify time, to prevent accidental modification show warning
        if "%s"%(self.current['hours']) == "%s"%(hours) \
            and self.time_delta > 0.01: #if its been more than six minutes notify user, of potential loss
            self.warning_message(self.timetracker_window, "Are you sure you want to modify this entry?\n\nSome time has passed already, and you will lose time.\n\nMaybe you should stop the timer first, start it again and then modify.")

            return

        if self.harvest:
            self.harvest.update( entry_id, {
                'notes': self.get_textview_text(self.notes_textview),
                'hours': hours,
                'project_id': self.get_combobox_selection(self.project_combobox),
                'task_id': self.get_combobox_selection(self.task_combobox)
            })
        else:
            self.warning_message(self.timetracker_window, "Not Connected to Harvest")
            return self.not_connected()

        self.set_entries()

    def on_stop_timer(self, widget):
        self.toggle_current_timer(self.current_entry_id)


    def on_quit(self, widget):
        if self.running and self.harvest:
            self.harvest.toggle_timer(self.current_entry_id)

        gtk.main_quit()


    def left_click(self, widget):
        self.set_entries()
        self.timetracker_window.show()
        self.timetracker_window.present()

    def right_click(self, widget, button, time):
        #create popup menu
        menu = gtk.Menu()

        if self.running:
            stop_timer = gtk.MenuItem("Stop Timer")
            stop_timer.connect("activate", self.on_stop_timer)
            menu.append(stop_timer)
        elif self.last_entry_id:
            pass

        if not self.away_from_desk:
            away = gtk.ImageMenuItem(gtk.STOCK_NO)
            away.set_label("Away from desk")
        else:
            away = gtk.ImageMenuItem(gtk.STOCK_YES)
            away.set_label("Back at desk")

        if not self.always_on_top:
            top = gtk.ImageMenuItem(gtk.STOCK_YES)
        else:
            top = gtk.ImageMenuItem(gtk.STOCK_NO)
        top.set_label("Always on top")

        updates = gtk.MenuItem("Check for updates")
        prefs = gtk.MenuItem("Preferences")
        about = gtk.MenuItem("About")
        quit = gtk.MenuItem("Quit")

        away.connect("activate", self.on_away_from_desk)
        updates.connect("activate", self.on_check_for_updates)
        top.connect("activate", self.on_top)
        prefs.connect("activate", self.on_show_preferences)
        about.connect("activate", self.on_show_about_dialog)
        quit.connect("activate", self.on_quit)

        menu.append(away)
        menu.append(updates)
        menu.append(top)
        menu.append(prefs)
        menu.append(about)
        menu.append(quit)

        menu.show_all()

        menu.popup(None, None, gtk.status_icon_position_menu, button, time, self.icon)
