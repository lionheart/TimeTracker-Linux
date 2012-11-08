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

    def information_message(self, widget, message):
        self.attention = True
        messagedialog = gtk.MessageDialog(widget, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, message)
        messagedialog.run()
        messagedialog.destroy()

    def error_message(self, widget, message):
        self.attention = True
        messagedialog = gtk.MessageDialog(widget, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, gtk.BUTTONS_CANCEL, message)
        messagedialog.run()
        messagedialog.destroy()

    def warning_message(self, widget, message):
        self.attention = True
        messagedialog = gtk.MessageDialog(widget, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, gtk.BUTTONS_OK_CANCEL, message)
        messagedialog.show()
        messagedialog.present()
        messagedialog.run()
        messagedialog.destroy()

    def question_message(self, widget, message, cb = None):
        self.attention = True
        messagedialog = gtk.MessageDialog(widget, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, message)
        messagedialog.connect("delete-event", lambda w, e: w.hide() or True)
        if cb:
            messagedialog.connect("response", cb)

        messagedialog.set_default_response(gtk.RESPONSE_YES)
        messagedialog.show()
        messagedialog.present()

    def interval_dialog(self, message):
        if not self.interval_dialog_showing:
            if not self.timetracker_window.is_active():
                self.timetracker_window.show()
                self.timetracker_window.present()

            self.interval_dialog_showing = True
            self.question_message(self.timetracker_window, message, self.on_working)

    def set_custom_label(self, widget, text):
        #set custom label on stock button
        Label = widget.get_children()[0]
        Label = Label.get_children()[0].get_children()[1]
        Label = Label.set_label(text)
import inspect

class uiSignals(uiSignalHelpers):
    def __init__(self, *args, **kwargs):
        super(uiSignals, self).__init__(*args, **kwargs)
        self.preferences_window.connect('delete-event', lambda w, e: w.hide() or True)
        self.timetracker_window.connect('delete-event', lambda w, e: w.hide() or True)
        self.timetracker_window.connect('destroy', lambda w, e: w.hide() or True)
        self.about_dialog.connect("delete-event", lambda w, e: w.hide() or True)
        self.about_dialog.connect("response", lambda w, e: w.hide() or True)
        self.icon.connect('activate', self.left_click)
        self.icon.connect("popup-menu", self.right_click)

    def on_show_about_dialog(self, widget):
        self.about_dialog.show()

    def on_working(self, dialog, a): #interval_dialog callback
        if a == gtk.RESPONSE_NO and self.running: #id will be set if running
            self.toggle_current_timer(self.current['id'])
            if not self.timetracker_window.is_active():
                self.timetracker_window.show()
                self.timetracker_window.present()
        else:
            self.timetracker_window.hide()

        self.clear_interval_timer()
        self.start_interval_timer()

        dialog.destroy()

        self.interval_dialog_showing = False


    def on_save_preferences_button_clicked(self, widget):
        self.get_prefs()
        if self.connect_to_harvest():
            self.preferences_window.hide()
            self.timetracker_window.show()
            self.timetracker_window.present()

    def on_task_combobox_changed(self, widget):
        self.current_selected_task_id = self.get_combobox_selection(widget)
        self.current_selected_task_idx = widget.get_active()

    def on_project_combobox_changed(self, widget):
        self.current_selected_project_id = self.get_combobox_selection(widget)
        new_idx = widget.get_active()
        if new_idx != -1 and new_idx != self.current_selected_project_idx: #-1 is sent from pygtk loop or something
            #reset task when new project is selected
            self.current_selected_project_idx = new_idx
            self.current_selected_task_id = None
            self.current_selected_task_idx = 0

    def on_show_preferences(self, widget):
        self.preferences_window.show()
        self.preferences_window.present()

    def on_away_from_desk(self, widget):
        #toggle away state
        self.away_from_desk = True if not self.away_from_desk else False

    def on_check_for_updates(self, widget):
        pass

    def on_top(self, widget):
        self.timetracker_window.set_keep_above(self.always_on_top)

    def on_timer_toggle_clicked(self, widget, id):
        if self.running: #if running it will turn off, lets empty the comboboxes
            self.current_project_id = None
            self.current_task_id = None
            self.refresh_comboboxes()

        #allow to start or stop a timer
        self.toggle_current_timer(id)

    def on_entries_expander_activate(self, widget):
        if not widget.get_expanded():
            self.set_entries()

    def on_submit_button_clicked(self, widget):
        print self.current_project_id, self.current_selected_project_id
        print self.current_task_id, self.current_selected_task_id
        self.away_from_desk = False
        if self.harvest: #we have to be connected
            if self.current_project_id != self.current_selected_project_id \
                or self.current_task_id != self.current_selected_task_id:
                self.harvest.add({
                    'notes': self.get_textview_text(self.notes_textview),
                    'hours': self.current_hours,
                    'project_id': self.get_combobox_selection(self.project_combobox),
                    'task_id': self.get_combobox_selection(self.task_combobox)
                })
            else:
                print 'no'
                pass
        else: #something is wrong we aren't connected
            self.warning_message(self.timetracker_window, "Not Connected to Harvest")
            self.attention = True

        self.set_entries()

    def on_timer_entry_removed(self, widget, entry_id):
        self.away_from_desk = False
        if self.harvest:
            self.harvest.delete(entry_id)
        else:
            self.warning_message(self.timetracker_window, "Not Connected to Harvest")
            self.attention = True

        self.set_entries()

    def on_edit_timer_entry(self, widget, entry_id):
        self.away_from_desk = False

        #should not be required if entry if hidden altogether, since its getting updated all the time
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
            self.attention = True

        self.set_entries()

    def on_stop_timer(self, widget):
        self.toggle_current_timer(self.current['id'])

    def left_click(self, widget):
        self.attention = False
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


        if not self.away_from_desk:
            away = gtk.ImageMenuItem(gtk.STOCK_MEDIA_STOP)
            away.set_label("Away from desk")
        else:
            away = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PLAY)
            away.set_label("Back at desk")

        if not self.away_from_desk:
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
        quit.connect("activate", gtk.main_quit)

        menu.append(away)
        menu.append(updates)
        menu.append(top)
        menu.append(prefs)
        menu.append(about)
        menu.append(quit)

        menu.show_all()

        menu.popup(None, None, gtk.status_icon_position_menu, button, time, self.icon)
