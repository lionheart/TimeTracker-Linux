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

import dbus
import dbus.service

DBUS_INTERFACE_NAMESPACE = 'net.launchpad.timetrackerapplet.TimeTrackerApplet.TimeTrackerManager'

class TimeTrackerManagerService(dbus.service.Object):
    def __init__(self, bus_name, object_path):
        dbus.service.Object.__init__(self,
                                     dbus.service.BusName(bus_name, bus=dbus.SessionBus()),
                                     object_path)
        self._time_tracker_id_list = []

    def create_and_register_time_tracker_id(self):
        time_tracker_id = str(uuid.uuid4())
        self.register_time_tracker_id(time_tracker_id)
        return time_tracker_id

    def register_time_tracker_id(self, time_tracker_id):
        self._time_tracker_id_list.append(time_tracker_id)

    def unregister_time_tracker_id(self, time_tracker_id):
        self._time_tracker_id_list.remove(time_tracker_id)

    @dbus.service.method(dbus_interface=DBUS_INTERFACE_NAMESPACE, out_signature='as')
    def GetTimeTrackerIDList(self):
        return self._time_tracker_id_list
