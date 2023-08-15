#
#  This file is part of Solar-ROI.
#
#  Solar-ROI is a utility to calculate the return on investment (ROI)
#  of a solar panel system that uses GivEnergy equipment and Octopus
#  Energy as the energy provider for import and export tariffs. 
#
#   Copyright (C) 2023 Neil Munday (neil@mundayweb.com)
#
#  Solar-ROI is free software: you can redistribute it and/or modify it
#  under the terms of the GNU General Public License as published by the
#  Free Software Foundation, either version 3 of the License, or (at
#  your option) any later version.
#
#  Solar-ROI is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Slurm-Mail.  If not, see <http://www.gnu.org/licenses/>.
#

"""
Solar-ROI global variables.
"""

import pathlib

conf_file = pathlib.Path("/etc/solar-roi.conf")

# properties
ARCHITECTURE = "any"
EMAIL = "neil@mundayweb.com"
DESCRIPTION = "Provides ROI data for GivEnergy solar panel systems that use Octopus Energy."
LONG_DESCRIPTION = "Provides ROI data for GivEnergy solar panel systems that use Octopus Energy."
MAINTAINER = "Neil Munday"
NAME = "solarroi"
VERSION = "1.0"
URL = "https://www.github.com/neilmunday/solar-roi"
