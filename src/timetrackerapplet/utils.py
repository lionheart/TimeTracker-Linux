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

from gettext import gettext as _

def is_valid_preset_name(name_str, preset_store, allowed_names=()):
    if len(name_str) == 0:
        return False
        
    name_str = name_str.lower()
    for allowed in allowed_names:
        if name_str == allowed.lower():
            return True
    
    return not preset_store.preset_name_exists_case_insensitive(name_str)
                
def seconds_to_hms(total_seconds):
    (hours, remaining_seconds) = divmod(total_seconds, 3600)
    (minutes, seconds) = divmod(remaining_seconds, 60)
    return (hours, minutes, seconds)
    
def hms_to_seconds(hours, minutes, seconds):
    return hours * 3600 + minutes * 60 + seconds
    
def get_preset_display_text(presets_store, row_iter):
    (name, hours, minutes, seconds, command) = presets_store.get_preset(row_iter)
    
    # <preset name> (HH:MM:SS)
    return _('%s (%02d:%02d:%02d)') % (name, hours, minutes, seconds)
