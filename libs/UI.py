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
        except KeyError, e:
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
            ashley = re.compile("(?:id=\"([a-zA-Z0-9_]*?)\")+")
            mary_kate = re.compile("(?:class=\"([a-zA-Z0-9_]*?)\")+")
            boobies = {}
            current_boob = ''
            with open(file) as boobs:
                for boob in boobs.readlines():
                    for right in ashley.findall(boob):
                        #print 'r:',right
                        if right:
                            for left in mary_kate.findall(boob):
                                #print 'l:',left
                                if left in self.Gtk_Widget_List:
                                    boobies[right] = []
                                    current_boob = right

                                if not left in self.Gtk_Widget_List  and current_boob:
                                    try:
                                        boobies[current_boob].append( right )
                                    except KeyError:
                                        print 'cb: ',current_boob, 'r:',right, 'l:', left
            return boobies

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

class uiLabel(gtk.Label):
    def __init__(self, *args, **kwargs):
        super(uiLabel, self).__init__(*args, **kwargs)

class uiEntry(gtk.Entry):
    def __init__(self, *args, **kwargs):
        super(uiEntry, self).__init__(*args, **kwargs)

class uiTreeView(gtk.TreeView):
    columns = []
    rows = {}
    def __init__(self, treestore = None):
        if treestore:
            self.treestore = treestore
        else:
            self.treestore = gtk.gtk.TreeStore(str)

        super(uiTreeView, self).__init__(self.treestore)

    def add_columns(self,columns=[], expander_index = -1, edited_callback = None, *args, **kwargs):
        if columns and isinstance(columns, list):
            self.cells = {}
            for i in range(len(columns)):
                def col_edited_cb( cell, path, new_text, model, callback, *a, **k ):
                    callback(cell, path, new_text, model, *a, **k )
                    #if model[path][2] is not new_text:
                        #print "Change '%s' to '%s'" % (model[path][2], new_text)
                        #model[path][2] = new_text
                    #return
                cell_types = kwargs.get('cell_types', [ gtk.CellRendererText ] * len( columns ))
                for cell_type in cell_types:
                    if callable(cell_type):
                        self.cells[ columns[i] ] = cell_type()
                    else:
                        self.cells[ columns[i] ] = cell_type

                cell_background = kwargs.get('cell_background', [ None ] * len( columns ) )
                for cb in range(len(cell_background)):
                    if cell_background[ cb ]:
                        self.cells[ columns[i] ].set_property('cell-background', cell_background[ cb ] )

                cell_foreground = kwargs.get('cell_foreground', [ None ] * len( columns ) )
                for cf in range(len(cell_foreground)):
                    if cell_foreground[ cf ]:
                        self.cells[ columns[i] ].set_property('foreground', cell_foreground[ cf ] )

                cell_editable = kwargs.get('cell_editable', [ False ] * len( columns ) )
                for ce in range(len(cell_editable)):
                    self.cells[ columns[i] ].set_property( 'editable', cell_editable[ ce ] )

                if edited_callback:
                    self.cells[ columns[i] ].connect( 'edited', col_edited_cb, self.treestore, edited_callback, *args, **kwargs )

                setattr(self, 'tvcolumn' + str(i), getattr(gtk, 'TreeViewColumn')(columns[i], self.cells[ columns[i] ]))
                curr_column = getattr(self, 'tvcolumn' + str(i) )
                curr_column.set_sort_column_id(i)
                #curr_column.pack_start(self.cell, True)
                #curr_column.set_attribute(cell, 'text', i)
                curr_column.set_attributes(self.cells[ columns[i] ], text=i, cell_background_set=3)
                self.append_column(curr_column)
                if expander_index >= 0 and i == expander_index:
                    self.set_expander_column(curr_column)

    def add_row(self,fields = [], index = None):
        return self.append_row(fields, index)

    def add_rows(self, rows = []):
        return self.append_rows(rows)

    def append_row(self, fields = [], index = None):
        ts = self.treestore.append(index, fields)
        return ts

    def append_rows(self, rows = []):
        iters = []
        for row in range(len(rows)):
            index, fields = rows[row]
            iters.append(self.append_row(fields, index))

        return iters

    @staticmethod
    def get_store(n = 1, model = gtk.TreeStore, obj = str):
        if n:
            assert type( n ) is IntType, "n is not an integer: %s" % (n)
            assert type(model) is type(gtk.TreeStore) or \
                type(model) is type(gtk.ListStore), \
                "model needs to be gtk.ListStore or gtk.TreeStore instance"
            return model(*((obj,) * n))
        return gtk.TreeStore(obj)

class uiCreator(object):
    def __init__(self, *args, **kwargs):
        super(uiCreator, self).__init__()

    def generic_signal(self, w = None, e = None):
        '''used for the purpose of connecting to a signal if no signal
            is passed as kwargs to create_treeview function
        '''
        pass

    def create_treeview(self, *args, **kwargs):
        container = kwargs.get('container', None)
        container_name = kwargs.get('container_name', None)
        if container and container_name:
            cols = kwargs.get('cols', [str])
            tv_name = ''.join(container_name.split('_box'))
            tv = uiTreeView( uiTreeView.get_store( len( cols ) ) )

            try:
                getattr(self, 'temp_%s' % (container_name) ).remove(getattr(self, '%s_treeview' % ( tv_name )))
                container.remove( getattr(self, 'temp_%s' % (container_name) ) )
            except AttributeError:
                '''first run'''
                pass

            signal_button_press_event = kwargs.get('button_press', self.generic_signal ) #self.on_treeview_button_press_event )
            signal_changed_event = kwargs.get('cursor_changed', self.generic_signal ) #self.set_selected )
            signal_column_edited = kwargs.get('column_edited', self.generic_signal ) #self.on_column_edited )

            setattr(self, '%s_treeview' % ( tv_name ), tv )

            getattr(self, '%s_treeview' % ( tv_name )).connect( 'button-press-event', signal_button_press_event )
            getattr(self, '%s_treeview' % ( tv_name )).add_columns( cols, 0, signal_column_edited, getattr(self, '%s_treeview' % ( tv_name )), [] )
            #getattr(self, '%s_treeview' % ( tv_name )).set_property( 'fixed-height-mode', True )
            getattr(self, '%s_treeview' % ( tv_name )).set_grid_lines( gtk.TREE_VIEW_GRID_LINES_BOTH )
            getattr(self, '%s_treeview' % ( tv_name )).set_reorderable( True )

            setattr(self, 'temp_%s' % ( container_name ), gtk.ScrolledWindow())
            getattr(self, 'temp_%s' % (container_name) ).set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
            getattr(self, 'temp_%s' % (container_name) ).add_with_viewport( getattr(self, '%s_treeview' % ( tv_name )) )

            container.pack_start(getattr(self, 'temp_%s' % (container_name) ))
            container.show_all()
            getattr(self, '%s_treeview' % ( tv_name )).get_selection().connect('changed', signal_changed_event, getattr(self, '%s_treeview' % ( tv_name )) )
            getattr(self, '%s_treeview' % ( tv_name )).connect('cursor-changed', signal_changed_event, getattr(self, '%s_treeview' % ( tv_name )) )
