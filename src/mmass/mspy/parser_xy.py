# -------------------------------------------------------------------------
#     Copyright (C) 2005-2013 Martin Strohalm <www.mmass.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file LICENSE.TXT in the
#     main directory of the program.
# -------------------------------------------------------------------------

# load libs
from __future__ import annotations

import re
from pathlib import Path

# load objects
from . import obj_peak, obj_peaklist, obj_scan


# PARSE SIMPLE ASCII XY
# ---------------------


class ParseXY:
    """Parse data from ASCII XY."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

        # check path
        if not self.path.exists():
            raise OSError(f"File not found! --> {self.path}")

    # ----

    def info(self):
        """Get document info."""
        return {
            "title": "",
            "operator": "",
            "contact": "",
            "institution": "",
            "date": "",
            "instrument": "",
            "notes": "",
        }

    # ----

    def scan(self, dataType="continuous"):
        """Get spectrum from document."""
        # parse file
        data = self._parseData()

        # check data
        if not data:
            return False

        # return scan
        return self._makeScan(data, dataType)

    # ----

    def _parseData(self):
        """Parse data."""
        # open document
        try:
            with self.path.open(encoding="utf-8") as document:
                rawData = document.readlines()
        except OSError:
            return False

        pattern = re.compile("^([-0-9\\.eE+]+)[ \t]*(;|,)?[ \t]*([-0-9\\.eE+]*)$")

        # read lines
        data = []
        for line in rawData:
            line = line.strip()

            # discard comment lines
            if not line or line[0] == "#" or line[0:3] == "m/z":
                continue

            # check pattern
            parts = pattern.match(line)
            if parts:
                try:
                    mass = float(parts.group(1))
                    intensity = float(parts.group(3))
                except ValueError:
                    return False
                data.append([mass, intensity])
            else:
                return False

        return data

    # ----

    def _makeScan(self, scanData, dataType):
        """Make scan object from raw data."""
        # parse data as Peaklist (discrete points)
        if dataType == "discrete":
            buff = []
            for point in scanData:
                buff.append(obj_peak.Peak(point[0], point[1]))
            scan = obj_scan.Scan(peaklist=obj_peaklist.Peaklist(buff))

        # parse data as spectrum (continuous line)
        else:
            scan = obj_scan.Scan(profile=scanData)

        return scan

    # ----
