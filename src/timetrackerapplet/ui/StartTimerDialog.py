# Copyright (C) 2010 Kenny Meyer <knny.myer@gmail.com>
# Copyright (C) 2008 Jimmy Do <jimmydo@users.sourceforge.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import gobject
import gtk
import gtk.glade as glade
import pango

from gettext import gettext as _
from shlex import split as shell_tokenize
from subprocess import check_call, CalledProcessError

from timerapplet.logger import logging as log
from DurationChooser import DurationChooser
from ScrollableButtonList import ScrollableButtonList

class StartTimerDialog(gobject.GObject):
    __gsignals__ = {'clicked-start':
                        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
                    'clicked-cancel':
                        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
                    'clicked-manage-presets':
                        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
                    'clicked-save':
                        (gobject.SIGNAL_RUN_LAST,
                         gobject.TYPE_NONE,
                         (gobject.TYPE_STRING,
                          gobject.TYPE_INT,
                          gobject.TYPE_INT,
                          gobject.TYPE_INT,
                          gobject.TYPE_STRING)),
                    'clicked-preset':
                        (gobject.SIGNAL_RUN_LAST,
                         gobject.TYPE_NONE,
                         (gobject.TYPE_PYOBJECT,))}
                    
    def __init__(self, glade_file_name, name_validator_func, presets_store, preset_display_func):
        gobject.GObject.__init__(self)
        
        self._valid_name_func = name_validator_func;
        self._presets_store = presets_store
        self._preset_display_func = preset_display_func
        
        self._presets_list = ScrollableButtonList()
        labels_size_group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        self._duration_chooser = DurationChooser(labels_size_group)
        
        glade_widgets = glade.XML(glade_file_name, 'start_timer_dialog')
        self._dialog = glade_widgets.get_widget('start_timer_dialog')
        self._ok_button = glade_widgets.get_widget('ok_button')
        name_label = glade_widgets.get_widget('name_label')
        self._name_entry = glade_widgets.get_widget('name_entry')
        self._save_button = glade_widgets.get_widget('save_button')
        duration_chooser_container = glade_widgets.get_widget('duration_chooser_container')
        presets_chooser_container = glade_widgets.get_widget('presets_chooser_container')
        self._presets_section = glade_widgets.get_widget('presets_section')
        # The TextEntry control for running a custom command
        self._command_entry = glade_widgets.get_widget('command_entry')
        self._invalid_cmd_label = glade_widgets.get_widget('invalid_command_label')
        
        labels_size_group.add_widget(name_label)
        self._dialog.set_default_response(gtk.RESPONSE_OK)
        duration_chooser_container.pack_start(self._duration_chooser)
        presets_chooser_container.pack_start(self._presets_list)
        
        self._dialog.connect('response', self._on_dialog_response)
        self._dialog.connect('delete-event', self._dialog.hide_on_delete)
        self._duration_chooser.connect('duration-changed', self._on_duration_changed)
        self._name_entry.connect('changed', self._on_name_entry_changed)
        self._save_button.connect('clicked', self._on_save_button_clicked)
        # Check that executable is valid while inserting text
        self._command_entry.connect('changed', self._check_is_valid_command)
        glade_widgets.get_widget('manage_presets_button').connect('clicked',
                                                                  self._on_manage_presets_button_clicked)
        self._presets_store.connect('row-deleted',
                                    lambda model, row_path: self._update_presets_list())
        self._presets_store.connect('row-changed',
                                    lambda model, row_path, row_iter: self._update_presets_list())
        
        self._update_presets_list()
        self._duration_chooser.show()
        self._presets_list.show()

    def show(self):
        if not self._dialog.props.visible:
            self._duration_chooser.clear()
            self._duration_chooser.focus_hours()
            self._name_entry.set_text('')
        self._check_for_valid_start_timer_input()
        self._check_for_valid_save_preset_input()
        self._dialog.present()
        
    def hide(self):
        self._dialog.hide()
        
    def get_name_and_duration(self):
        """Return name and duration in a tuple.
        
        The returned tuple is in this format: (name, hours, minutes, seconds)
        
        """
        return (self._name_entry.get_text().strip(),) + \
    self._duration_chooser.get_duration() + \
    (self._command_entry.get_text().strip(),)
        
    def set_name_and_duration(self, name, hours, minutes, seconds, *args):
        self._name_entry.set_text(name)
        if args[0]:
            self._command_entry.set_text(args[0])
        else:
            # Clear the Command Entry control after switching preset elements
            self._command_entry.set_text('')
        self._duration_chooser.set_duration(hours, minutes, seconds)

    def _update_presets_list(self):
        self._check_for_valid_save_preset_input()

        if len(self._presets_store) == 0:
            self._presets_section.hide()
            
            # Make window shrink
            self._dialog.resize(1, 1)
        else:
            self._presets_section.show()
            
        for button in self._presets_list.get_buttons():
            button.destroy()
            
        row_iter = self._presets_store.get_iter_first()
        while row_iter is not None:
            name = self._preset_display_func(row_iter)
            label = gtk.Label(name)
            label.set_ellipsize(pango.ELLIPSIZE_END)
            button = gtk.Button()
            button.set_relief(gtk.RELIEF_NONE)
            button.add(label)
            self._presets_list.add_button(button)
            
            button.connect('clicked', self._on_preset_button_clicked, self._presets_store.get_path(row_iter))
            
            label.show()
            button.show()
            
            row_iter = self._presets_store.iter_next(row_iter)
    
    def _check_is_valid_command(self, widget, data=None):
        """
        Check that input in the command entry TextBox control is a valid
        executable.
        """
        try:
            data = widget.get_text()
            executable = shell_tokenize(data)[0]
            # Check if command in path, else raise CalledProcessError
            # The idea of using `which` to check if a command is in PATH
            # originated from the Python mailing list.
            check_call(['which', executable])
            self._invalid_cmd_label.set_label('')
        except (ValueError, IndexError, CalledProcessError):
            self._invalid_cmd_label.set_label(_("<b>Command not found.</b>"))
            if data is '':
                self._invalid_cmd_label.set_label('')

    def _non_zero_duration(self):
        (hours, minutes, seconds) = self._duration_chooser.get_duration()
        return (hours > 0 or minutes > 0 or seconds > 0)

    def _check_for_valid_save_preset_input(self):
        self._save_button.props.sensitive = (self._non_zero_duration() and
                                             self._valid_name_func(self._name_entry.get_text()))
    
    def _check_for_valid_start_timer_input(self):
        self._ok_button.props.sensitive = self._non_zero_duration()
    
    def _on_preset_button_clicked(self, button, row_path):
        self.emit('clicked-preset', row_path)

    def _on_manage_presets_button_clicked(self, button):
        self.emit('clicked-manage-presets')
    
    def _on_duration_changed(self, data=None):
        self._check_for_valid_start_timer_input()
        self._check_for_valid_save_preset_input()
    
    def _on_name_entry_changed(self, entry):
        self._check_for_valid_save_preset_input()

    def _on_dialog_response(self, dialog, response_id):
        if response_id == gtk.RESPONSE_OK:
            self._duration_chooser.normalize_fields()
            self.emit('clicked-start')
        elif response_id == gtk.RESPONSE_CANCEL:
            self.emit('clicked-cancel')
        self._dialog.hide()
        
    def _on_save_button_clicked(self, button):
        self._duration_chooser.normalize_fields()
        (hours, minutes, seconds) = self._duration_chooser.get_duration()
        name = self._name_entry.get_text()
        command = self._command_entry.get_text()
        self.emit('clicked-save', name, hours, minutes, seconds, command)
