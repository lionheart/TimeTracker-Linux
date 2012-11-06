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
            self.inteval_dialog_showing = True
            self.question_message(self.timetracker_window, message, self.on_working)

    def set_custom_label(self, widget, text):
        #set custom label on stock button
        Label = widget.get_children()[0]
        Label = Label.get_children()[0].get_children()[1]
        Label = Label.set_label(text)

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

    def on_show_about_dialog(self, widget):
        self.about_dialog.show()

    def on_working(self, dialog, a): #interval_dialog callback
        if a == gtk.RESPONSE_NO:
            self.toggle_current_timer(self.current['id'])
        else:
            pass

        self.interval_dialog_showing = False
        dialog.destroy()

    def on_save_preferences_button_clicked(self, widget):
        uri = self.harvest_url_entry.get_text()
        username = self.harvest_email_entry.get_text()
        password = self.harvest_password_entry.get_text()
        self.interval = self.interval_entry.get_text()
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
        self.toggle_current_timer(id)

    def get_combobox_selection(self, widget):
            model = widget.get_model()
            active = widget.get_active()
            if active < 0:
                return None
            return model[active][1] #0 is name, 1 is id
    def on_entries_expander_activate(self, widget):
        if not widget.get_expanded():
            self.set_entries()

    def on_submit_button_clicked(self, widget):
        self.away_from_desk = False
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
        self.away_from_desk = False
        self.daily.delete(entry_id)
        self.set_entries()

    def on_edit_timer_entry(self, widget, entry_id):
        self.away_from_desk = False

        #should not be required if entry if hidden altogether, since its getting updated all the time
        hours = self.hours_entry.get_text()
        #if time passed and the user tries to modify time, to prevent accidental modification show warning
        if "%s"%(self.current['hours']) == "%s"%(hours) \
            and self.time_delta > 0.01: #if its been more than six minutes notify user, of potential loss
            self.warning_message(self.timetracker_window, "Are you sure you want to modify this entry?\n\nSome time has passed already, and you will lose time.\n\nMaybe you should stop the timer first, start it again and then modify.")

            return

        self.daily.update( entry_id, {
            "request": {
                'notes': self.get_textview_text(self.notes_textview),
                'hours': hours,
                'project_id': self.get_combobox_selection(self.project_combobox),
                'task_id': self.get_combobox_selection(self.task_combobox)
            }
        })

        self.set_entries()


    def left_click(self, widget):
        self.attention = False
        self.set_entries()
        self.timetracker_window.show()
        self.timetracker_window.present()

    def right_click(self, widget, button, time):
        self.attention = False
        #create popup menu
        menu = gtk.Menu()
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
