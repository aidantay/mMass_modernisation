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
from pathlib import Path

# load stopper
from .parser_mgf import ParseMGF
from .parser_mzdata import ParseMZData
from .parser_mzml import ParseMZML
from .parser_mzxml import ParseMZXML

# load parsers
from .parser_xy import ParseXY

# UTILITIES
# ---------


def load(path: str | Path, scanID: int | None = None, dataType: str = "continuous"):
    """Load scan from given document."""
    # check path
    p = Path(path)
    if not p.exists():
        raise OSError("File not found! --> " + str(p))

    # get extension
    extension = p.suffix.lower()

    # get document type
    docType = None
    if extension == ".mzdata":
        docType = "mzData"
    elif extension == ".mzxml":
        docType = "mzXML"
    elif extension == ".mzml":
        docType = "mzML"
    elif extension == ".mgf":
        docType = "MGF"
    elif extension in (".xy", ".txt", ".asc"):
        docType = "XY"
    elif extension == ".xml":
        with p.open(encoding="utf-8", errors="ignore") as doc:
            data = doc.read(500)
            if "<mzData" in data:
                docType = "mzData"
            elif "<mzXML" in data:
                docType = "mzXML"
            elif "<mzML" in data:
                docType = "mzML"

    # check document type
    if not docType:
        raise ValueError("Unknown document type! --> " + str(p))

    # load document data
    if docType == "mzData":
        parser = ParseMZData(p)
        scan = parser.scan(scanID)
    elif docType == "mzXML":
        parser = ParseMZXML(p)
        scan = parser.scan(scanID)
    elif docType == "mzML":
        parser = ParseMZML(p)
        scan = parser.scan(scanID)
    elif docType == "MGF":
        parser = ParseMGF(p)
        scan = parser.scan(scanID)
    elif docType == "XY":
        parser = ParseXY(p)
        scan = parser.scan(dataType)

    return scan


# ----


def save(data: list[list[float]], path: str | Path) -> None:
    buff = ""
    for point in data:
        buff += f"{point[0]:f}\t{point[1]:f}\n"

    with Path(path).open("wb") as save_file:
        save_file.write(buff.encode("utf-8"))


# ----
