import gtk
import os, sys
import re
from types import *

class uiBuilder(gtk.Builder):
    Gtk_Widget_List = [
        'GtkWindow', 'GtkDialog', 'GtkFileChooserDialog',
        'GtkAboutDialog', 'GtkColorSelectionDialog', 'GtkFileChooserDialog',
        'GtkFontSelectionDialog', 'GtkInputDialog', 'GtkMessageDialog',
        'GtkRecentChooserDialog', 'GtkAssistant'
    ]
    def __init__(self, *args, **kwargs):
        super(uiBuilder, self).__init__()

    def add_file(self, file):
        try:
            if os.environ["OS"].startswith("Windows"):
                self.add_from_file( file ) #+ "\\builder.ui")
        except KeyError as e:
            self.add_from_file( file ) #+ "/builder.ui")

    def get_widget(self, name = None):
        if name:
            #is name string
            if isinstance(name, basestring):
                setattr(self, name, self.get_object( name ))

    def get_widgets(self, name = None):
        if name:
            #is name dict
            if isinstance(name, dict):
                names = []
                for i in name.keys():
                    if i:
                        names.append(i)
                for i in name.values():
                    if i:
                        if isinstance(i, list):
                            for j in range(len(i)):
                                names.append(i[j])
                        elif isinstance(i, dict):
                            pass
                        else:
                            #else name is a string
                            names.append(i)
                # Get objects (widgets) from the Builder
                for i in range(len(names)):
                    setattr(self, names[i], self.get_object(names[i]))

    def connect_widgets(self, parent):
        self.connect_signals(self)

    def builder_build(self, *args, **kwargs):
        widget_list_dict = kwargs.get('widget_list_dict', {})
        def parse_widgets(file):
            ids = re.compile("(?:id=\"([a-zA-Z0-9_]*?)\")+")
            classes = re.compile("(?:class=\"([a-zA-Z0-9_]*?)\")+")
            components = {}
            current = ''
            with open(file) as lines:
                for line in lines.readlines():
                    for id in ids.findall(line):
                        #print 'r:',id
                        if id:
                            for klass in classes.findall(line):
                                #print 'l:',left
                                if klass in self.Gtk_Widget_List:
                                    components[id] = []
                                    current = id

                                if not klass in self.Gtk_Widget_List  and current:
                                    try:
                                        components[current].append( id )
                                    except KeyError:
                                        print 'cb: ',current, 'r:',id, 'l:', klass
            return components

        file = kwargs.get('builder_file', './data/ui/builder.ui')

        if isinstance(file, list):
            for f in file:
                widget_list_dict.update(parse_widgets(f))
                self.add_file(f)
                self.connect_widgets(self)
            #print widget_list_dict
        elif isinstance(file, str):
            widget_list_dict = parse_widgets(file)
            self.add_file(file)
            self.connect_widgets(self)
        if widget_list_dict:
            self.get_widgets(widget_list_dict)
            return True
        else:
            return False


class uiCreator(object):
    def __init__(self, *args, **kwargs):
        super(uiCreator, self).__init__()

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

    def get_textview_text(self, widget):
        buffer = self.notes_textview.get_buffer()
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())

    def set_comboboxes(self, widget, id):
        '''
        sets the current selected item in the combobox
        '''
        model = widget.get_model()
        i = 0

        for m in model:
            iter = model.get_iter(i)
            if "%s" % model.get_value(iter, 1) == "%s" % id:
                widget.set_active(i)
                break
            i += 1
