#!/usr/bin/env python

#C: THIS FILE IS PART OF THE CYLC SUITE ENGINE.
#C: Copyright (C) 2008-2014 Hilary Oliver, NIWA
#C:
#C: This program is free software: you can redistribute it and/or modify
#C: it under the terms of the GNU General Public License as published by
#C: the Free Software Foundation, either version 3 of the License, or
#C: (at your option) any later version.
#C:
#C: This program is distributed in the hope that it will be useful,
#C: but WITHOUT ANY WARRANTY; without even the implied warranty of
#C: MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#C: GNU General Public License for more details.
#C:
#C: You should have received a copy of the GNU General Public License
#C: along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Tasks spawn a sequence of POINTS (P) separated by INTERVALS (I).
Each task may have multiple sequences, e.g. 12-hourly and 6-hourly.
"""
cycling = 'integer'
#cycling = 'iso8601'

if cycling == 'integer':
    from integer import point, interval, sequence
elif cycling == 'iso8601':
    from iso8601 import point, interval, sequence
else:
    raise "CYCLING IMPORT ERROR"

# or use import by name:
# mod = __import__( module_name, fromlist=[class_name] )
# my_class = getattr( mod, class_name )
