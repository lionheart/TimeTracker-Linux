serverdir = $(libdir)/bonobo/servers
server_in_files = TimeTrackerApplet.server.in
server_DATA = $(server_in_files:.server.in=.server)

$(server_in_files): $(server_in_files:.server.in=.server.in.in) Makefile
	sed -e "s|\@LIBEXECDIR\@|$(pkglibdir)|" $< > $@

schemasdir = $(GCONF_SCHEMA_FILE_DIR)
schemas_in_files = timetracker-applet.schemas.in
schemas_DATA = $(schemas_in_files:.schemas.in=.schemas)

pkgdata_DATA = \
	TimeTrackerApplet.xml \
	timetracker-applet.glade

EXTRA_DIST = \
	TimeTrackerApplet.server.in.in \
	$(pkgdata_DATA) \
	$(schemas_in_files)
	
CLEANFILES = \
	$(server_DATA) \
	$(server_in_files) \
	$(schemas_DATA)

@INTLTOOL_SERVER_RULE@
@INTLTOOL_SCHEMAS_RULE@

if GCONF_SCHEMAS_INSTALL
install-data-local:
	GCONF_CONFIG_SOURCE=$(GCONF_SCHEMA_CONFIG_SOURCE) \
	$(GCONFTOOL) --makefile-install-rule $(schemas_DATA)
	
uninstall-local:
	GCONF_CONFIG_SOURCE=$(GCONF_SCHEMA_CONFIG_SOURCE) \
	$(GCONFTOOL) --makefile-uninstall-rule $(schemas_DATA)
endif
