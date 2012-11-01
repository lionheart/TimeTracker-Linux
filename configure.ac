AC_INIT(timetracker-applet, "1.1beta1" , alex@goretoy.com)
AM_INIT_AUTOMAKE
AC_CONFIG_SRCDIR(src/timetracker-applet)
AM_MAINTAINER_MODE

AC_PROG_INTLTOOL([0.35.0])
AM_GLIB_GNU_GETTEXT

AC_PATH_PROG(GCONFTOOL, gconftool-2)
AM_GCONF_SOURCE_2

AM_PATH_PYTHON(2.4)

# check for gtk-doc
GTK_DOC_CHECK([1.14],[--flavour no-tmpl])
AC_CONFIG_MACRO_DIR(m4)

GETTEXT_PACKAGE="timetracker-applet"
AC_SUBST(GETTEXT_PACKAGE)

AC_CONFIG_FILES([
Makefile
data/Makefile
images/Makefile
po/Makefile.in
src/Makefile
src/timetrackerapplet/Makefile
src/timetrackerapplet/controllers/Makefile
src/timetrackerapplet/core/Makefile
src/timetrackerapplet/ui/Makefile])

AC_OUTPUT
