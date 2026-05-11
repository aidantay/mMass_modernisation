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

import contextlib
import re
from copy import deepcopy
from pathlib import Path

# load objects
from . import obj_peak, obj_peaklist, obj_scan


# PARSE MGF DATA
# --------------

class ParseMGF:
    """Parse data from MGF."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._scans = None
        self._scanlist = None

        # check path
        if not self.path.exists():
            raise OSError(f"File not found! --> {self.path}")

    # ----

    def load(self) -> None:
        """Load all scans into memory."""
        self._parseData()

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

    def scanlist(self):
        """Get list of all scans in the document."""
        # use preloaded data if available
        if self._scanlist:
            return self._scanlist

        # parse data
        self._parseData()

        return self._scanlist

    # ----

    def scan(self, scanID=None, dataType=None):
        """Get spectrum from document."""
        # parse file
        if not self._scans:
            self._parseData()

        # check data
        if not self._scans:
            return False

        # check selected scan
        if scanID in self._scans:
            data = self._scans[scanID]
        elif scanID is None:
            data = self._scans[0]

        # return scan
        return self._makeScan(data, dataType)

    # ----

    def _parseData(self) -> bool | None:
        """Parse data."""
        # clear buffers
        self._scans = {}
        self._scanlist = None

        # open document
        try:
            with self.path.open(encoding="utf-8") as document:
                rawData = document.readlines()
        except OSError:
            return False

        headerPattern = re.compile("^([A-Z]+)=(.+)")
        pointPattern = re.compile("[ \t]+")
        currentID = None

        # parse each line
        for line in rawData:
            line = line.strip()

            # discard comments
            if not line or line[0] in ("#", ";", "!", "/"):
                continue

            # append default scan
            if currentID is None or line == "BEGIN IONS":
                currentID = len(self._scans)
                scan = {
                    "title": "",
                    "scanNumber": currentID,
                    "parentScanNumber": None,
                    "msLevel": None,
                    "pointsCount": 0,
                    "polarity": None,
                    "retentionTime": None,
                    "lowMZ": None,
                    "highMZ": None,
                    "basePeakMZ": None,
                    "basePeakIntensity": None,
                    "totIonCurrent": None,
                    "precursorMZ": None,
                    "precursorIntensity": None,
                    "precursorCharge": None,
                    "spectrumType": "unknown",
                    "data": [],
                }
                self._scans[currentID] = scan

            # scan ended, use default scan
            if line == "END IONS":
                currentID = 0
                continue

            # get header data
            parts = headerPattern.match(line)
            if parts:
                if parts.group(1) == "TITLE":
                    self._scans[currentID]["title"] = parts.group(2).strip()
                elif parts.group(1) == "PEPMASS":
                    with contextlib.suppress(BaseException):
                        self._scans[currentID]["precursorMZ"] = float(
                            pointPattern.split(parts.group(2))[0]
                        )
                elif parts.group(1) == "CHARGE":
                    charge = parts.group(2).strip()
                    if charge[-1] in ("+", "-"):
                        charge = charge[-1] + charge[:-1]
                    with contextlib.suppress(BaseException):
                        self._scans[currentID]["precursorCharge"] = int(charge)
                continue

            # append datapoint
            parts = pointPattern.split(line)
            if parts:
                point = [0, 100.0]
                try:
                    point[0] = float(parts[0])
                except ValueError:
                    continue
                with contextlib.suppress(ValueError):
                    point[1] = float(parts[1])
                self._scans[currentID]["data"].append(point)
                self._scans[currentID]["pointsCount"] += 1
                continue

        # make scanlist
        if self._scans:
            self._scanlist = deepcopy(self._scans)
            for scanNumber in self._scanlist:
                del self._scanlist[scanNumber]["data"]
        return None

    # ----

    def _makeScan(self, scanData, dataType):
        """Make scan object from raw data."""
        # parse data as Peaklist (discrete points)
        if dataType == "peaklist" or (
            dataType is None and len(scanData["data"]) < 3000
        ):
            buff = []
            for point in scanData["data"]:
                buff.append(obj_peak.Peak(point[0], point[1]))
            scan = obj_scan.Scan(peaklist=obj_peaklist.Peaklist(buff))

        # parse data as spectrum (continuous line)
        else:
            scan = obj_scan.Scan(profile=scanData["data"])

        # set metadata
        scan.title = scanData["title"]
        scan.scanNumber = scanData["scanNumber"]
        scan.parentScanNumber = scanData["parentScanNumber"]
        scan.msLevel = scanData["msLevel"]
        scan.polarity = scanData["polarity"]
        scan.retentionTime = scanData["retentionTime"]
        scan.totIonCurrent = scanData["totIonCurrent"]
        scan.basePeakMZ = scanData["basePeakMZ"]
        scan.basePeakIntensity = scanData["basePeakIntensity"]
        scan.precursorMZ = scanData["precursorMZ"]
        scan.precursorIntensity = scanData["precursorIntensity"]
        scan.precursorCharge = scanData["precursorCharge"]

        return scan

    # ----
