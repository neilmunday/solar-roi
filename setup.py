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
Solar-ROI setup.py
"""

import pathlib
import sys
import setuptools  # type: ignore

sys.path.append(str(pathlib.Path(__file__).resolve().parents[0] / "src"))

from solarroi import (  # noqa
    ARCHITECTURE,
    DESCRIPTION,
    LONG_DESCRIPTION,
    MAINTAINER,
    NAME,
    VERSION
)

setuptools.setup(
    author="Neil Munday",
    data_files=[
        ("etc", ["solar-roi.conf"])
    ],
    description=DESCRIPTION,
    entry_points={
        "console_scripts": [
            "solar-roi=solarroi.cli:main"
        ],
    },
    install_requires=[
        "setuptools"
    ],
    license="GPLv3",
    long_description=LONG_DESCRIPTION,
    maintainer=MAINTAINER,
    name=NAME,
    packages=setuptools.find_packages(where="src"),
    package_dir={"": "src"},
    platforms=ARCHITECTURE,
    python_requires=">=3.6",
    url="https://github.com/neilmunday/solar-roi",
    version=VERSION
)
