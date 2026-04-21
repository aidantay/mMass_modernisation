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
import contextlib
import os
import sys
import xml.dom.minidom
from pathlib import Path

# SET VERSION
# -----------

version = "5.5.0"
nightbuild = ""


# SET CONFIG FOLDER
# -----------------

# set config folder for MAC OS X
if sys.platform == "darwin":
    support = Path("~/Library/Application Support/").expanduser()
    userconf = support / "mMass"
    if support.exists() and not userconf.exists():
        with contextlib.suppress(Exception):
            userconf.mkdir()
    confdir = userconf

# set config folder for Linux
elif sys.platform.startswith("linux") or sys.platform.startswith("freebsd"):
    home = Path("~").expanduser()
    userconf = home / ".mmass"
    if home.exists() and not userconf.exists():
        with contextlib.suppress(Exception):
            userconf.mkdir()
    confdir = userconf

# set config folder for Windows
else:
    appdata = os.environ.get("APPDATA")
    if appdata:
        userconf = Path(appdata) / "mMass"
        if not userconf.exists():
            with contextlib.suppress(Exception):
                userconf.mkdir()
        confdir = userconf
    else:
        confdir = Path("~/.mmass").expanduser()

if not Path(confdir).exists():
    try:
        Path(confdir).mkdir(parents=True, exist_ok=True)
    except Exception:
        raise OSError("Configuration folder cannot be created!")


# INIT DEFAULT VALUES
# -------------------

internal = {
    "canvasXrange": None,
}

main = {
    "appWidth": 1050,
    "appHeight": 620,
    "appMaximized": 0,
    "unlockGUI": 0,
    "layout": "default",
    "documentsWidth": 195,
    "documentsHeight": 195,
    "peaklistWidth": 195,
    "peaklistHeight": 195,
    "mzDigits": 4,
    "intDigits": 0,
    "ppmDigits": 1,
    "chargeDigits": 2,
    "dataPrecision": 32,
    "lastDir": "",
    "lastSeqDir": "",
    "errorUnits": "Da",
    "printQuality": 5,
    "useServer": 1,
    "serverPort": 65456,
    "reverseScrolling": 0,
    "macListCtrlGeneric": 1,
    "peaklistColumns": ["mz", "int", "rel", "sn", "z", "fwhm", "resol"],
    "cursorInfo": ["mz", "dist", "ppm", "z"],
    "updatesEnabled": 1,
    "updatesChecked": "",
    "updatesCurrent": version,
    "updatesAvailable": version,
    "compassMode": "Profile",
    "compassFormat": "mzML",
    "compassDeleteFile": 1,
}

recent = []

colours = [
    [16, 71, 185],
    [50, 140, 0],
    [241, 144, 0],
    [76, 199, 197],
    [143, 143, 21],
    [38, 122, 255],
    [38, 143, 73],
    [237, 187, 0],
    [120, 109, 255],
    [179, 78, 0],
    [128, 191, 189],
    [137, 136, 68],
    [200, 136, 18],
    [197, 202, 61],
    [123, 182, 255],
    [69, 67, 138],
    [24, 129, 131],
    [131, 129, 131],
    [69, 126, 198],
    [189, 193, 123],
    [127, 34, 0],
    [76, 78, 76],
    [31, 74, 145],
    [15, 78, 75],
    [79, 26, 81],
]

export = {
    "imageWidth": 750,
    "imageHeight": 500,
    "imageUnits": "px",
    "imageResolution": 72,
    "imageFontsScale": 1,
    "imageDrawingsScale": 1,
    "imageFormat": "PNG",
    "peaklistColumns": ["mz", "int"],
    "peaklistFormat": "ASCII",
    "peaklistSeparator": "tab",
    "spectrumSeparator": "tab",
}

spectrum = {
    "xLabel": "m/z",
    "yLabel": "a.i.",
    "showGrid": 1,
    "showMinorTicks": 1,
    "showLegend": 1,
    "showPosBars": 1,
    "showGel": 1,
    "showGelLegend": 1,
    "showTracker": 1,
    "showNotations": 1,
    "showLabels": 1,
    "showAllLabels": 1,
    "showTicks": 1,
    "showDataPoints": 1,
    "showCursorImage": 1,
    "posBarSize": 7,
    "gelHeight": 19,
    "autoscale": 1,
    "normalize": 0,
    "overlapLabels": 0,
    "checkLimits": 1,
    "labelAngle": 90,
    "labelCharge": 1,
    "labelGroup": 0,
    "labelBgr": 1,
    "labelFontSize": 10,
    "axisFontSize": 10,
    "tickColour": [255, 75, 75],
    "tmpSpectrumColour": [255, 0, 0],
    "notationMarksColour": [0, 255, 0],
    "notationMaxLength": 40,
    "notationMarks": 1,
    "notationLabels": 0,
    "notationMZ": 0,
}

match = {
    "tolerance": 0.2,
    "units": "Da",
    "ignoreCharge": 0,
    "filterAnnotations": 0,
    "filterMatches": 0,
    "filterUnselected": 0,
    "filterIsotopes": 1,
    "filterUnknown": 0,
}

processing = {
    "math": {
        "operation": "normalize",
        "multiplier": 1,
    },
    "crop": {
        "lowMass": 500,
        "highMass": 5000,
    },
    "baseline": {
        "precision": 15,
        "offset": 0.25,
    },
    "smoothing": {
        "method": "SG",
        "windowSize": 0.3,
        "cycles": 2,
    },
    "peakpicking": {
        "snThreshold": 3.0,
        "absIntThreshold": 0,
        "relIntThreshold": 0.0,
        "pickingHeight": 0.75,
        "baseline": 1,
        "smoothing": 1,
        "deisotoping": 1,
        "monoisotopic": 0,
        "removeShoulders": 0,
    },
    "deisotoping": {
        "maxCharge": 1,
        "massTolerance": 0.1,
        "intTolerance": 0.5,
        "isotopeShift": 0.0,
        "removeIsotopes": 1,
        "removeUnknown": 1,
        "labelEnvelope": "1st",
        "envelopeIntensity": "maximum",
        "setAsMonoisotopic": 0,
    },
    "deconvolution": {
        "massType": 0,
        "groupWindow": 0.01,
        "groupPeaks": 1,
        "forceGroupWindow": 0,
    },
    "batch": {
        "swap": 0,
        "math": 0,
        "crop": 0,
        "baseline": 0,
        "smoothing": 0,
        "peakpicking": 0,
        "deisotoping": 0,
        "deconvolution": 0,
    },
}

calibration = {
    "fitting": "quadratic",
    "tolerance": 50,
    "units": "ppm",
    "statCutOff": 800,
}

sequence = {
    "editor": {
        "gridSize": 20,
    },
    "digest": {
        "maxMods": 1,
        "maxCharge": 1,
        "massType": 0,
        "enzyme": "Trypsin",
        "miscl": 1,
        "lowMass": 500,
        "highMass": 5000,
        "retainPos": 0,
        "allowMods": 0,
        "listTemplateAmino": "b.S.a [m]",
        "listTemplateCustom": "b . [ S ] . a [m]",
        "matchTemplateAmino": "h b.S.a [m]",
        "matchTemplateCustom": " h b . [ S ] . a [m]",
    },
    "fragment": {
        "maxMods": 1,
        "maxCharge": 1,
        "massType": 1,
        "fragments": ["a", "b", "y", "-NH3", "-H2O"],
        "maxLosses": 2,
        "filterFragments": 1,
        "listTemplateAmino": "b.S.a [m]",
        "listTemplateCustom": "b . [ S ] . a [m]",
        "matchTemplateAmino": "f h [m]",
        "matchTemplateCustom": "f h [m]",
    },
    "search": {
        "mass": 0,
        "maxMods": 1,
        "charge": 1,
        "massType": 0,
        "enzyme": "Trypsin",
        "semiSpecific": True,
        "tolerance": 0.2,
        "units": "Da",
        "retainPos": 0,
        "listTemplateAmino": "b.S.a [m]",
        "listTemplateCustom": "b . [ S ] . a [m]",
    },
}

massCalculator = {
    "ionseriesAgent": "H",
    "ionseriesAgentCharge": 1,
    "ionseriesPolarity": 1,
    "patternFwhm": 0.1,
    "patternIntensity": 100,
    "patternBaseline": 0,
    "patternShift": 0,
    "patternThreshold": 0.001,
    "patternShowPeaks": 1,
    "patternPeakShape": "gaussian",
}

massfilter = {}

massToFormula = {
    "countLimit": 1000,
    "massLimit": 3000,
    "charge": 1,
    "ionization": "H",
    "tolerance": 1.0,
    "units": "ppm",
    "formulaMin": "",
    "formulaMax": "",
    "autoCHNO": 1,
    "checkPattern": 1,
    "rules": ["HC", "NOPSC", "NOPS", "RDBE", "RDBEInt"],
    "HCMin": 0.1,
    "HCMax": 3,
    "NCMax": 4,
    "OCMax": 3,
    "PCMax": 2,
    "SCMax": 3,
    "RDBEMin": -1,
    "RDBEMax": 40,
    "PubChemScript": "http://pubchem.ncbi.nlm.nih.gov/search/search.cgi",
    "ChemSpiderScript": "http://www.chemspider.com/Search.aspx",
    "METLINScript": "http://metlin.scripps.edu/metabo_list_adv.php",
    "HMDBScript": "http://www.hmdb.ca/search",
    "LipidMAPSScript": "http://www.lipidmaps.org/data/structure/LMSDSearch.php",
}

massDefectPlot = {
    "xAxis": "mz",
    "yAxis": "standard",
    "nominalMass": "floor",
    "kendrickFormula": "CH2",
    "relIntCutoff": 0.0,
    "removeIsotopes": 0,
    "ignoreCharge": 1,
    "showNotations": 0,
    "showAllDocuments": 0,
}

compoundsSearch = {
    "massType": 0,
    "maxCharge": 1,
    "radicals": 0,
    "adducts": ["Na", "K"],
}

peakDifferences = {
    "aminoacids": 1,
    "dipeptides": 0,
    "massType": 0,
    "tolerance": 0.1,
    "consolidate": 0,
}

comparePeaklists = {
    "compare": "peaklists",
    "tolerance": 0.2,
    "units": "Da",
    "ignoreCharge": 0,
    "ratioCheck": 0,
    "ratioDirection": 1,
    "ratioThreshold": 2,
}

spectrumGenerator = {
    "fwhm": 0.1,
    "points": 10,
    "noise": 0,
    "forceFwhm": 0,
    "peakShape": "gaussian",
    "showPeaks": 1,
    "showOverlay": 0,
    "showFlipped": 0,
}

envelopeFit = {
    "loss": "H",
    "gain": "H{2}",
    "fit": "spectrum",
    "scaleMin": 0,
    "scaleMax": 10,
    "charge": 1,
    "fwhm": 0.01,
    "forceFwhm": 0,
    "peakShape": "gaussian",
    "autoAlign": 1,
    "relThreshold": 0.05,
}

mascot = {
    "common": {
        "title": "",
        "userName": "",
        "userEmail": "",
        "server": "Matrix Science",
        "searchType": "pmf",
        "filterAnnotations": 0,
        "filterMatches": 0,
        "filterUnselected": 0,
        "filterIsotopes": 1,
        "filterUnknown": 0,
    },
    "pmf": {
        "database": "SwissProt",
        "taxonomy": "All entries",
        "enzyme": "Trypsin",
        "miscleavages": 1,
        "fixedMods": [],
        "variableMods": [],
        "hiddenMods": 0,
        "proteinMass": "",
        "peptideTol": 0.1,
        "peptideTolUnits": "Da",
        "massType": "Monoisotopic",
        "charge": "1+",
        "decoy": 0,
        "report": "AUTO",
    },
    "sq": {
        "database": "SwissProt",
        "taxonomy": "All entries",
        "enzyme": "Trypsin",
        "miscleavages": 1,
        "fixedMods": [],
        "variableMods": [],
        "hiddenMods": 0,
        "peptideTol": 0.1,
        "peptideTolUnits": "Da",
        "msmsTol": 0.2,
        "msmsTolUnits": "Da",
        "massType": "Average",
        "charge": "1+",
        "instrument": "Default",
        "quantitation": "None",
        "decoy": 0,
        "report": "AUTO",
    },
    "mis": {
        "database": "SwissProt",
        "taxonomy": "All entries",
        "enzyme": "Trypsin",
        "miscleavages": 1,
        "fixedMods": [],
        "variableMods": [],
        "hiddenMods": 0,
        "peptideMass": "",
        "peptideTol": 0.1,
        "peptideTolUnits": "Da",
        "msmsTol": 0.2,
        "msmsTolUnits": "Da",
        "massType": "Average",
        "charge": "1+",
        "instrument": "Default",
        "quantitation": "None",
        "decoy": 0,
        "errorTolerant": 0,
        "report": "AUTO",
    },
}

profound = {
    "script": "http://prowl.rockefeller.edu/prowl-cgi/profound.exe",
    "title": "",
    "database": "NCBI nr",
    "taxonomy": "All taxa",
    "enzyme": "Trypsin",
    "miscleavages": 1,
    "fixedMods": [],
    "variableMods": [],
    "proteinMassLow": 0,
    "proteinMassHigh": 300,
    "proteinPILow": 0,
    "proteinPIHigh": 14,
    "peptideTol": 0.1,
    "peptideTolUnits": "Da",
    "massType": "Monoisotopic",
    "charge": "MH+",
    "ranking": "expect",
    "expectation": 1,
    "candidates": 10,
    "filterAnnotations": 0,
    "filterMatches": 0,
    "filterUnselected": 0,
    "filterIsotopes": 1,
    "filterUnknown": 0,
}

prospector = {
    "common": {
        "title": "",
        "script": "http://prospector.ucsf.edu/prospector/cgi-bin/mssearch.cgi",
        "searchType": "msfit",
        "filterAnnotations": 0,
        "filterMatches": 0,
        "filterUnselected": 0,
        "filterIsotopes": 1,
        "filterUnknown": 0,
    },
    "msfit": {
        "database": "SwissProt",
        "taxonomy": "All",
        "enzyme": "Trypsin",
        "miscleavages": 1,
        "fixedMods": [],
        "variableMods": [],
        "proteinMassLow": 0,
        "proteinMassHigh": 300,
        "proteinPILow": 0,
        "proteinPIHigh": 14,
        "peptideTol": 0.1,
        "peptideTolUnits": "Da",
        "massType": "Monoisotopic",
        "instrument": "MALDI-TOFTOF",
        "minMatches": 4,
        "maxMods": 1,
        "report": 5,
        "pfactor": 0.4,
    },
    "mstag": {
        "database": "SwissProt",
        "taxonomy": "All",
        "enzyme": "Trypsin",
        "miscleavages": 1,
        "fixedMods": [],
        "variableMods": [],
        "peptideMass": "",
        "peptideTol": 0.1,
        "peptideTolUnits": "Da",
        "peptideCharge": "1",
        "msmsTol": 0.2,
        "msmsTolUnits": "Da",
        "massType": "Monoisotopic",
        "instrument": "MALDI-TOFTOF",
        "maxMods": 1,
        "report": 5,
    },
}

links = {
    "mMassHomepage": "http://www.mmass.org/",
    "mMassForum": "http://forum.mmass.org/",
    "mMassTwitter": "http://www.twitter.com/mmassorg/",
    "mMassCite": "http://www.mmass.org/donate/papers.php",
    "mMassDonate": "http://www.mmass.org/donate/",
    "mMassDownload": "http://www.mmass.org/download/",
    "mMassWhatsNew": "http://www.mmass.org/download/history.php",
    "biomedmstools": "http://ms.biomed.cas.cz/MSTools/",
    "blast": "http://www.ebi.ac.uk/Tools/blastall/",
    "clustalw": "http://www.ebi.ac.uk/Tools/clustalw/",
    "deltamass": "http://www.abrf.org/index.cfm/dm.home",
    "emblebi": "http://www.ebi.ac.uk/services/",
    "expasy": "http://www.expasy.org/",
    "fasta": "http://www.ebi.ac.uk/Tools/fasta33/",
    "matrixscience": "http://www.matrixscience.com/",
    "muscle": "http://phylogenomics.berkeley.edu/cgi-bin/muscle/input_muscle.py",
    "ncbi": "http://www.ncbi.nlm.nih.gov/Entrez/",
    "pdb": "http://www.rcsb.org/pdb/",
    "pir": "http://pir.georgetown.edu/",
    "profound": "http://prowl.rockefeller.edu/prowl-cgi/profound.exe",
    "prospector": "http://prospector.ucsf.edu/",
    "unimod": "http://www.unimod.org/",
    "uniprot": "http://www.uniprot.org/",
}

replacements = {
    "sequences": {
        "general": {
            "pattern": r"^([A-Z0-9_]+[\.0-9]*)$",
            "url": "http://www.ncbi.nlm.nih.gov/protein/%s",
        },
        "gi": {
            "pattern": r"^gi\|?([0-9]+[\.0-9]*)$",
            "url": "http://www.ncbi.nlm.nih.gov/protein/%s",
        },
        "gb": {
            "pattern": r"^gb\|?([A-Z]{3}[0-9]{5}[\.0-9]*)$",
            "url": "http://www.ncbi.nlm.nih.gov/protein/%s",
        },
        "sp": {
            "pattern": r"^sp\|?([A-Z][A-Z0-9]+)$",
            "url": "http://www.uniprot.org/uniprot/%s",
        },
        "ref": {
            "pattern": r"^ref\|?([A-Z]{2}_[0-9]+[\.0-9]*)$",
            "url": "http://www.ncbi.nlm.nih.gov/protein/%s",
        },
    },
    "compounds": {
        "PubChemC": {
            "pattern": "CID([0-9]{1,10})",
            "url": "http://pubchem.ncbi.nlm.nih.gov/summary/summary.cgi?cid=%s",
        },
        "LipidMaps": {
            "pattern": "(LM[A-Z]{2}[0-9]{4}[0-9A-Z]{2}[0-9]{2})",
            "url": "http://www.lipidmaps.org/data/LMSDRecord.php?LMID=%s",
        },
        "NORINE": {
            "pattern": "(NOR[0-9]{5})",
            "url": "http://bioinfo.lifl.fr/norine/result.jsp?ID=%s",
        },
    },
}


# LOAD AND SAVE CONFIG FILE
# -------------------------


def loadConfig(path=None):
    """Parse config XML and get data."""

    # set default path
    if path is None:
        path = confdir / "config.xml"

    # parse XML
    document = xml.dom.minidom.parse(str(path))

    # main
    mainTags = document.getElementsByTagName("main")
    if mainTags:
        _getParams(mainTags[0], main)

        if not isinstance(main["cursorInfo"], list):
            main["cursorInfo"] = main["cursorInfo"].split(";")

        if not isinstance(main["peaklistColumns"], list):
            main["peaklistColumns"] = main["peaklistColumns"].split(";")

    # recent files
    recentTags = document.getElementsByTagName("recent")
    if recentTags:
        pathTags = recentTags[0].getElementsByTagName("path")
        if pathTags:
            del recent[:]
            for pathTag in pathTags:
                recent.append(pathTag.getAttribute("value"))

    # colours
    coloursTags = document.getElementsByTagName("colours")
    if coloursTags:
        colourTags = coloursTags[0].getElementsByTagName("colour")
        if colourTags:
            del colours[:]
            for colourTag in colourTags:
                col = colourTag.getAttribute("value")
                colours.append([int(c, 16) for c in (col[0:2], col[2:4], col[4:6])])

    # export
    exportTags = document.getElementsByTagName("export")
    if exportTags:
        _getParams(exportTags[0], export)

        if not isinstance(export["peaklistColumns"], list):
            export["peaklistColumns"] = export["peaklistColumns"].split(";")

    # spectrum
    spectrumTags = document.getElementsByTagName("spectrum")
    if spectrumTags:
        _getParams(spectrumTags[0], spectrum)

        if not isinstance(spectrum["tickColour"], list):
            col = spectrum["tickColour"]
            spectrum["tickColour"] = [
                int(c, 16) for c in (col[0:2], col[2:4], col[4:6])
            ]

        if not isinstance(spectrum["tmpSpectrumColour"], list):
            col = spectrum["tmpSpectrumColour"]
            spectrum["tmpSpectrumColour"] = [
                int(c, 16) for c in (col[0:2], col[2:4], col[4:6])
            ]

        if not isinstance(spectrum["notationMarksColour"], list):
            col = spectrum["notationMarksColour"]
            spectrum["notationMarksColour"] = [
                int(c, 16) for c in (col[0:2], col[2:4], col[4:6])
            ]

    # match
    matchTags = document.getElementsByTagName("match")
    if matchTags:
        _getParams(matchTags[0], match)

    # processing
    processingTags = document.getElementsByTagName("processing")
    if processingTags:
        cropTags = processingTags[0].getElementsByTagName("crop")
        if cropTags:
            _getParams(cropTags[0], processing["crop"])

        baselineTags = processingTags[0].getElementsByTagName("baseline")
        if baselineTags:
            _getParams(baselineTags[0], processing["baseline"])

        smoothingTags = processingTags[0].getElementsByTagName("smoothing")
        if smoothingTags:
            _getParams(smoothingTags[0], processing["smoothing"])

        peakpickingTags = processingTags[0].getElementsByTagName("peakpicking")
        if peakpickingTags:
            _getParams(peakpickingTags[0], processing["peakpicking"])

        deisotopingTags = processingTags[0].getElementsByTagName("deisotoping")
        if deisotopingTags:
            _getParams(deisotopingTags[0], processing["deisotoping"])

        deconvolutionTags = processingTags[0].getElementsByTagName("deconvolution")
        if deconvolutionTags:
            _getParams(deconvolutionTags[0], processing["deconvolution"])

    # calibration
    calibrationTags = document.getElementsByTagName("calibration")
    if calibrationTags:
        _getParams(calibrationTags[0], calibration)

    # sequence
    sequenceTags = document.getElementsByTagName("sequence")
    if sequenceTags:
        editorTags = sequenceTags[0].getElementsByTagName("editor")
        if editorTags:
            _getParams(editorTags[0], sequence["editor"])

        digestTags = sequenceTags[0].getElementsByTagName("digest")
        if digestTags:
            _getParams(digestTags[0], sequence["digest"])

        fragmentTags = sequenceTags[0].getElementsByTagName("fragment")
        if fragmentTags:
            _getParams(fragmentTags[0], sequence["fragment"])

        searchTags = sequenceTags[0].getElementsByTagName("search")
        if searchTags:
            _getParams(searchTags[0], sequence["search"])

        if not isinstance(sequence["fragment"]["fragments"], list):
            sequence["fragment"]["fragments"] = sequence["fragment"]["fragments"].split(
                ";"
            )

    # mass calculator
    massCalculatorTags = document.getElementsByTagName("massCalculator")
    if massCalculatorTags:
        _getParams(massCalculatorTags[0], massCalculator)

    # mass to formula
    massToFormulaTags = document.getElementsByTagName("massToFormula")
    if massToFormulaTags:
        _getParams(massToFormulaTags[0], massToFormula)

        if not isinstance(massToFormula["rules"], list):
            massToFormula["rules"] = massToFormula["rules"].split(";")

    # mass defect plot
    massDefectPlotTags = document.getElementsByTagName("massDefectPlot")
    if massDefectPlotTags:
        _getParams(massDefectPlotTags[0], massDefectPlot)

    # compounds search
    compoundsSearchTags = document.getElementsByTagName("compoundsSearch")
    if compoundsSearchTags:
        _getParams(compoundsSearchTags[0], compoundsSearch)

        if not isinstance(compoundsSearch["adducts"], list):
            compoundsSearch["adducts"] = compoundsSearch["adducts"].split(";")

    # peak differences
    peakDifferencesTags = document.getElementsByTagName("peakDifferences")
    if peakDifferencesTags:
        _getParams(peakDifferencesTags[0], peakDifferences)

    # compare peaklists
    comparePeaklistsTags = document.getElementsByTagName("comparePeaklists")
    if comparePeaklistsTags:
        _getParams(comparePeaklistsTags[0], comparePeaklists)

    # spectrum generator
    spectrumGeneratorTags = document.getElementsByTagName("spectrumGenerator")
    if spectrumGeneratorTags:
        _getParams(spectrumGeneratorTags[0], spectrumGenerator)

    # envelope fit
    envelopeFitTags = document.getElementsByTagName("envelopeFit")
    if envelopeFitTags:
        _getParams(envelopeFitTags[0], envelopeFit)

    # mascot
    mascotTags = document.getElementsByTagName("mascot")
    if mascotTags:
        commonTags = mascotTags[0].getElementsByTagName("common")
        if commonTags:
            _getParams(commonTags[0], mascot["common"])

        pmfTags = mascotTags[0].getElementsByTagName("pmf")
        if pmfTags:
            _getParams(pmfTags[0], mascot["pmf"])

        sqTags = mascotTags[0].getElementsByTagName("sq")
        if sqTags:
            _getParams(sqTags[0], mascot["sq"])

        misTags = mascotTags[0].getElementsByTagName("mis")
        if misTags:
            _getParams(misTags[0], mascot["mis"])

        for key in ("pmf", "sq", "mis"):
            if not isinstance(mascot[key]["fixedMods"], list):
                mascot[key]["fixedMods"] = mascot[key]["fixedMods"].split(";")
            if not isinstance(mascot[key]["variableMods"], list):
                mascot[key]["variableMods"] = mascot[key]["variableMods"].split(";")

    # profound
    profoundTags = document.getElementsByTagName("profound")
    if profoundTags:
        _getParams(profoundTags[0], profound)

        if not isinstance(profound["fixedMods"], list):
            profound["fixedMods"] = profound["fixedMods"].split(";")
        if not isinstance(profound["variableMods"], list):
            profound["variableMods"] = profound["variableMods"].split(";")

    # prospector
    prospectorTags = document.getElementsByTagName("prospector")
    if prospectorTags:
        commonTags = prospectorTags[0].getElementsByTagName("common")
        if commonTags:
            _getParams(commonTags[0], prospector["common"])

        msfitTags = prospectorTags[0].getElementsByTagName("msfit")
        if msfitTags:
            _getParams(msfitTags[0], prospector["msfit"])

        mstagTags = prospectorTags[0].getElementsByTagName("mstag")
        if mstagTags:
            _getParams(mstagTags[0], prospector["mstag"])

        for key in ("msfit", "mstag"):
            if not isinstance(prospector[key]["fixedMods"], list):
                prospector[key]["fixedMods"] = prospector[key]["fixedMods"].split(";")
            if not isinstance(prospector[key]["variableMods"], list):
                prospector[key]["variableMods"] = prospector[key]["variableMods"].split(
                    ";"
                )

    # links
    linksTags = document.getElementsByTagName("links")
    if linksTags:
        linkTags = linksTags[0].getElementsByTagName("link")
        for linkTag in linkTags:
            name = linkTag.getAttribute("name")
            value = linkTag.getAttribute("value")
            if name not in (
                "mMassHomepage",
                "mMassForum",
                "mMassTwitter",
                "mMassCite",
                "mMassDonate",
                "mMassDownload",
            ):
                links[name] = value


# ----


def saveConfig(path=None):
    """Make and save config XML."""

    # set default path
    if path is None:
        path = confdir / "config.xml"

    buff = '<?xml version="1.0" encoding="utf-8" ?>\n'
    buff += '<mMassConfig version="1.0">\n\n'

    # main
    buff += "  <main>\n"
    buff += f'    <param name="appWidth" value="{main["appWidth"]}" type="int" />\n'
    buff += f'    <param name="appHeight" value="{main["appHeight"]}" type="int" />\n'
    buff += f'    <param name="appMaximized" value="{int(bool(main["appMaximized"]))}" type="int" />\n'
    buff += (
        f'    <param name="layout" value="{_escape(main["layout"])}" type="str" />\n'
    )
    buff += f'    <param name="documentsWidth" value="{main["documentsWidth"]}" type="int" />\n'
    buff += f'    <param name="documentsHeight" value="{main["documentsHeight"]}" type="int" />\n'
    buff += f'    <param name="peaklistWidth" value="{main["peaklistWidth"]}" type="int" />\n'
    buff += f'    <param name="peaklistHeight" value="{main["peaklistHeight"]}" type="int" />\n'
    buff += f'    <param name="reverseScrolling" value="{int(bool(main["reverseScrolling"]))}" type="int" />\n'
    buff += f'    <param name="macListCtrlGeneric" value="{int(bool(main["macListCtrlGeneric"]))}" type="int" />\n'
    buff += f'    <param name="cursorInfo" value="{";".join(main["cursorInfo"])}" type="str" />\n'
    buff += f'    <param name="peaklistColumns" value="{";".join(main["peaklistColumns"])}" type="str" />\n'
    buff += f'    <param name="mzDigits" value="{main["mzDigits"]}" type="int" />\n'
    buff += f'    <param name="intDigits" value="{main["intDigits"]}" type="int" />\n'
    buff += f'    <param name="ppmDigits" value="{main["ppmDigits"]}" type="int" />\n'
    buff += (
        f'    <param name="chargeDigits" value="{main["chargeDigits"]}" type="int" />\n'
    )
    buff += (
        f'    <param name="lastDir" value="{_escape(main["lastDir"])}" type="str" />\n'
    )
    buff += f'    <param name="lastSeqDir" value="{_escape(main["lastSeqDir"])}" type="str" />\n'
    buff += f'    <param name="errorUnits" value="{_escape(main["errorUnits"])}" type="str" />\n'
    buff += (
        f'    <param name="printQuality" value="{main["printQuality"]}" type="int" />\n'
    )
    buff += f'    <param name="useServer" value="{int(bool(main["useServer"]))}" type="int" />\n'
    buff += f'    <param name="serverPort" value="{main["serverPort"]}" type="int" />\n'
    buff += f'    <param name="updatesEnabled" value="{int(bool(main["updatesEnabled"]))}" type="int" />\n'
    buff += f'    <param name="updatesChecked" value="{_escape(main["updatesChecked"])}" type="str" />\n'
    buff += f'    <param name="updatesCurrent" value="{_escape(main["updatesCurrent"])}" type="str" />\n'
    buff += f'    <param name="updatesAvailable" value="{_escape(main["updatesAvailable"])}" type="str" />\n'
    buff += f'    <param name="compassMode" value="{_escape(main["compassMode"])}" type="str" />\n'
    buff += f'    <param name="compassFormat" value="{_escape(main["compassFormat"])}" type="str" />\n'
    buff += f'    <param name="compassDeleteFile" value="{int(bool(main["compassDeleteFile"]))}" type="int" />\n'
    buff += "  </main>\n\n"

    # recent files
    buff += "  <recent>\n"
    for item in recent:
        buff += f'    <path value="{_escape(item)}" />\n'
    buff += "  </recent>\n\n"

    # colours
    buff += "  <colours>\n"
    for item in colours:
        buff += '    <colour value="{:02x}{:02x}{:02x}" />\n'.format(*tuple(item))
    buff += "  </colours>\n\n"

    # export
    buff += "  <export>\n"
    buff += '    <param name="imageWidth" value="{:.1f}" type="float" />\n'.format(
        export["imageWidth"]
    )
    buff += '    <param name="imageHeight" value="{:.1f}" type="float" />\n'.format(
        export["imageHeight"]
    )
    buff += '    <param name="imageUnits" value="{}" type="str" />\n'.format(
        export["imageUnits"]
    )
    buff += f'    <param name="imageResolution" value="{export["imageResolution"]}" type="int" />\n'
    buff += f'    <param name="imageFontsScale" value="{export["imageFontsScale"]}" type="int" />\n'
    buff += f'    <param name="imageDrawingsScale" value="{export["imageDrawingsScale"]}" type="int" />\n'
    buff += '    <param name="imageFormat" value="{}" type="str" />\n'.format(
        export["imageFormat"]
    )
    buff += '    <param name="peaklistColumns" value="{}" type="str" />\n'.format(
        ";".join(export["peaklistColumns"])
    )
    buff += '    <param name="peaklistFormat" value="{}" type="str" />\n'.format(
        export["peaklistFormat"]
    )
    buff += '    <param name="peaklistSeparator" value="{}" type="str" />\n'.format(
        export["peaklistSeparator"]
    )
    buff += '    <param name="spectrumSeparator" value="{}" type="str" />\n'.format(
        export["spectrumSeparator"]
    )
    buff += "  </export>\n\n"

    # spectrum
    buff += "  <spectrum>\n"
    buff += '    <param name="xLabel" value="{}" type="unicode" />\n'.format(
        _escape(spectrum["xLabel"])
    )
    buff += '    <param name="yLabel" value="{}" type="unicode" />\n'.format(
        _escape(spectrum["yLabel"])
    )
    buff += f'    <param name="showGrid" value="{int(bool(spectrum["showGrid"]))}" type="int" />\n'
    buff += f'    <param name="showMinorTicks" value="{int(bool(spectrum["showMinorTicks"]))}" type="int" />\n'
    buff += f'    <param name="showLegend" value="{int(bool(spectrum["showLegend"]))}" type="int" />\n'
    buff += f'    <param name="showPosBars" value="{int(bool(spectrum["showPosBars"]))}" type="int" />\n'
    buff += f'    <param name="showGel" value="{int(bool(spectrum["showGel"]))}" type="int" />\n'
    buff += f'    <param name="showGelLegend" value="{int(bool(spectrum["showGelLegend"]))}" type="int" />\n'
    buff += f'    <param name="showTracker" value="{int(bool(spectrum["showTracker"]))}" type="int" />\n'
    buff += f'    <param name="showNotations" value="{int(bool(spectrum["showNotations"]))}" type="int" />\n'
    buff += f'    <param name="showDataPoints" value="{int(bool(spectrum["showDataPoints"]))}" type="int" />\n'
    buff += f'    <param name="showLabels" value="{int(bool(spectrum["showLabels"]))}" type="int" />\n'
    buff += f'    <param name="showAllLabels" value="{int(bool(spectrum["showAllLabels"]))}" type="int" />\n'
    buff += f'    <param name="showTicks" value="{int(bool(spectrum["showTicks"]))}" type="int" />\n'
    buff += f'    <param name="showCursorImage" value="{int(bool(spectrum["showCursorImage"]))}" type="int" />\n'
    buff += (
        f'    <param name="posBarSize" value="{spectrum["posBarSize"]}" type="int" />\n'
    )
    buff += (
        f'    <param name="gelHeight" value="{spectrum["gelHeight"]}" type="int" />\n'
    )
    buff += f'    <param name="autoscale" value="{int(bool(spectrum["autoscale"]))}" type="int" />\n'
    buff += f'    <param name="overlapLabels" value="{int(bool(spectrum["overlapLabels"]))}" type="int" />\n'
    buff += f'    <param name="checkLimits" value="{int(bool(spectrum["checkLimits"]))}" type="int" />\n'
    buff += (
        f'    <param name="labelAngle" value="{spectrum["labelAngle"]}" type="int" />\n'
    )
    buff += f'    <param name="labelCharge" value="{int(bool(spectrum["labelCharge"]))}" type="int" />\n'
    buff += f'    <param name="labelGroup" value="{int(bool(spectrum["labelGroup"]))}" type="int" />\n'
    buff += f'    <param name="labelBgr" value="{int(bool(spectrum["labelBgr"]))}" type="int" />\n'
    buff += f'    <param name="labelFontSize" value="{spectrum["labelFontSize"]}" type="int" />\n'
    buff += f'    <param name="axisFontSize" value="{spectrum["axisFontSize"]}" type="int" />\n'
    buff += '    <param name="tickColour" value="{:02x}{:02x}{:02x}" type="str" />\n'.format(
        *tuple(spectrum["tickColour"])
    )
    buff += '    <param name="tmpSpectrumColour" value="{:02x}{:02x}{:02x}" type="str" />\n'.format(
        *tuple(spectrum["tmpSpectrumColour"])
    )
    buff += '    <param name="notationMarksColour" value="{:02x}{:02x}{:02x}" type="str" />\n'.format(
        *tuple(spectrum["notationMarksColour"])
    )
    buff += f'    <param name="notationMaxLength" value="{spectrum["notationMaxLength"]}" type="int" />\n'
    buff += f'    <param name="notationMarks" value="{int(bool(spectrum["notationMarks"]))}" type="int" />\n'
    buff += f'    <param name="notationLabels" value="{int(bool(spectrum["notationLabels"]))}" type="int" />\n'
    buff += f'    <param name="notationMZ" value="{int(bool(spectrum["notationMZ"]))}" type="int" />\n'
    buff += "  </spectrum>\n\n"

    # match
    buff += "  <match>\n"
    buff += '    <param name="tolerance" value="{:f}" type="float" />\n'.format(
        match["tolerance"]
    )
    buff += '    <param name="units" value="{}" type="str" />\n'.format(match["units"])
    buff += f'    <param name="ignoreCharge" value="{int(bool(match["ignoreCharge"]))}" type="int" />\n'
    buff += f'    <param name="filterAnnotations" value="{int(bool(match["filterAnnotations"]))}" type="int" />\n'
    buff += f'    <param name="filterMatches" value="{int(bool(match["filterMatches"]))}" type="int" />\n'
    buff += f'    <param name="filterUnselected" value="{int(bool(match["filterUnselected"]))}" type="int" />\n'
    buff += f'    <param name="filterIsotopes" value="{int(bool(match["filterIsotopes"]))}" type="int" />\n'
    buff += f'    <param name="filterUnknown" value="{int(bool(match["filterUnknown"]))}" type="int" />\n'
    buff += "  </match>\n\n"

    # processing
    buff += "  <processing>\n"
    buff += "    <crop>\n"
    buff += f'      <param name="lowMass" value="{processing["crop"]["lowMass"]}" type="int" />\n'
    buff += f'      <param name="highMass" value="{processing["crop"]["highMass"]}" type="int" />\n'
    buff += "    </crop>\n"
    buff += "    <baseline>\n"
    buff += f'      <param name="precision" value="{processing["baseline"]["precision"]}" type="int" />\n'
    buff += '      <param name="offset" value="{:f}" type="float" />\n'.format(
        processing["baseline"]["offset"]
    )
    buff += "    </baseline>\n"
    buff += "    <smoothing>\n"
    buff += '      <param name="method" value="{}" type="str" />\n'.format(
        processing["smoothing"]["method"]
    )
    buff += '      <param name="windowSize" value="{:f}" type="float" />\n'.format(
        processing["smoothing"]["windowSize"]
    )
    buff += f'      <param name="cycles" value="{processing["smoothing"]["cycles"]}" type="int" />\n'
    buff += "    </smoothing>\n"
    buff += "    <peakpicking>\n"
    buff += '      <param name="snThreshold" value="{:f}" type="float" />\n'.format(
        processing["peakpicking"]["snThreshold"]
    )
    buff += '      <param name="absIntThreshold" value="{:f}" type="float" />\n'.format(
        processing["peakpicking"]["absIntThreshold"]
    )
    buff += '      <param name="relIntThreshold" value="{:f}" type="float" />\n'.format(
        processing["peakpicking"]["relIntThreshold"]
    )
    buff += '      <param name="pickingHeight" value="{:f}" type="float" />\n'.format(
        processing["peakpicking"]["pickingHeight"]
    )
    buff += f'      <param name="baseline" value="{int(bool(processing["peakpicking"]["baseline"]))}" type="int" />\n'
    buff += f'      <param name="smoothing" value="{int(bool(processing["peakpicking"]["smoothing"]))}" type="int" />\n'
    buff += f'      <param name="deisotoping" value="{int(bool(processing["peakpicking"]["deisotoping"]))}" type="int" />\n'
    buff += f'      <param name="removeShoulders" value="{int(bool(processing["peakpicking"]["removeShoulders"]))}" type="int" />\n'
    buff += "    </peakpicking>\n"
    buff += "    <deisotoping>\n"
    buff += f'      <param name="maxCharge" value="{processing["deisotoping"]["maxCharge"]}" type="int" />\n'
    buff += '      <param name="massTolerance" value="{:f}" type="float" />\n'.format(
        processing["deisotoping"]["massTolerance"]
    )
    buff += '      <param name="intTolerance" value="{:f}" type="float" />\n'.format(
        processing["deisotoping"]["intTolerance"]
    )
    buff += f'      <param name="removeIsotopes" value="{int(bool(processing["deisotoping"]["removeIsotopes"]))}" type="int" />\n'
    buff += f'      <param name="removeUnknown" value="{int(bool(processing["deisotoping"]["removeUnknown"]))}" type="int" />\n'
    buff += '      <param name="labelEnvelope" value="{}" type="str" />\n'.format(
        processing["deisotoping"]["labelEnvelope"]
    )
    buff += '      <param name="envelopeIntensity" value="{}" type="str" />\n'.format(
        processing["deisotoping"]["envelopeIntensity"]
    )
    buff += f'      <param name="setAsMonoisotopic" value="{int(bool(processing["deisotoping"]["setAsMonoisotopic"]))}" type="int" />\n'
    buff += "    </deisotoping>\n"
    buff += "    <deconvolution>\n"
    buff += f'      <param name="massType" value="{processing["deconvolution"]["massType"]}" type="int" />\n'
    buff += '      <param name="groupWindow" value="{:f}" type="float" />\n'.format(
        processing["deconvolution"]["groupWindow"]
    )
    buff += f'      <param name="groupPeaks" value="{int(bool(processing["deconvolution"]["groupPeaks"]))}" type="int" />\n'
    buff += f'      <param name="forceGroupWindow" value="{int(bool(processing["deconvolution"]["forceGroupWindow"]))}" type="int" />\n'
    buff += "    </deconvolution>\n"
    buff += "    <batch>\n"
    buff += f'      <param name="math" value="{int(bool(processing["batch"]["math"]))}" type="int" />\n'
    buff += f'      <param name="crop" value="{int(bool(processing["batch"]["crop"]))}" type="int" />\n'
    buff += f'      <param name="baseline" value="{int(bool(processing["batch"]["baseline"]))}" type="int" />\n'
    buff += f'      <param name="smoothing" value="{int(bool(processing["batch"]["smoothing"]))}" type="int" />\n'
    buff += f'      <param name="peakpicking" value="{int(bool(processing["batch"]["peakpicking"]))}" type="int" />\n'
    buff += f'      <param name="deisotoping" value="{int(bool(processing["batch"]["deisotoping"]))}" type="int" />\n'
    buff += f'      <param name="deconvolution" value="{int(bool(processing["batch"]["deconvolution"]))}" type="int" />\n'
    buff += "    </batch>\n"
    buff += "  </processing>\n\n"

    # calibration
    buff += "  <calibration>\n"
    buff += '    <param name="fitting" value="{}" type="str" />\n'.format(
        calibration["fitting"]
    )
    buff += '    <param name="tolerance" value="{:f}" type="float" />\n'.format(
        calibration["tolerance"]
    )
    buff += '    <param name="units" value="{}" type="str" />\n'.format(
        calibration["units"]
    )
    buff += f'    <param name="statCutOff" value="{calibration["statCutOff"]}" type="int" />\n'
    buff += "  </calibration>\n\n"

    # sequence
    buff += "  <sequence>\n"
    buff += "    <editor>\n"
    buff += f'      <param name="gridSize" value="{sequence["editor"]["gridSize"]}" type="int" />\n'
    buff += "    </editor>\n"
    buff += "    <digest>\n"
    buff += f'      <param name="maxMods" value="{sequence["digest"]["maxMods"]}" type="int" />\n'
    buff += f'      <param name="maxCharge" value="{sequence["digest"]["maxCharge"]}" type="int" />\n'
    buff += f'      <param name="massType" value="{sequence["digest"]["massType"]}" type="int" />\n'
    buff += '      <param name="enzyme" value="{}" type="unicode" />\n'.format(
        _escape(sequence["digest"]["enzyme"])
    )
    buff += f'      <param name="miscl" value="{sequence["digest"]["miscl"]}" type="int" />\n'
    buff += f'      <param name="lowMass" value="{sequence["digest"]["lowMass"]}" type="int" />\n'
    buff += f'      <param name="highMass" value="{sequence["digest"]["highMass"]}" type="int" />\n'
    buff += f'      <param name="retainPos" value="{int(bool(sequence["digest"]["retainPos"]))}" type="int" />\n'
    buff += f'      <param name="allowMods" value="{int(bool(sequence["digest"]["allowMods"]))}" type="int" />\n'
    buff += "    </digest>\n"
    buff += "    <fragment>\n"
    buff += f'      <param name="maxMods" value="{sequence["fragment"]["maxMods"]}" type="int" />\n'
    buff += f'      <param name="maxCharge" value="{sequence["fragment"]["maxCharge"]}" type="int" />\n'
    buff += f'      <param name="massType" value="{sequence["fragment"]["massType"]}" type="int" />\n'
    buff += '      <param name="fragments" value="{}" type="str" />\n'.format(
        ";".join(sequence["fragment"]["fragments"])
    )
    buff += f'      <param name="maxLosses" value="{sequence["fragment"]["maxLosses"]}" type="int" />\n'
    buff += f'      <param name="filterFragments" value="{int(bool(sequence["fragment"]["filterFragments"]))}" type="int" />\n'
    buff += "    </fragment>\n"
    buff += "    <search>\n"
    buff += f'      <param name="maxMods" value="{sequence["search"]["maxMods"]}" type="int" />\n'
    buff += f'      <param name="charge" value="{sequence["search"]["charge"]}" type="int" />\n'
    buff += f'      <param name="massType" value="{sequence["search"]["massType"]}" type="int" />\n'
    buff += '      <param name="enzyme" value="{}" type="unicode" />\n'.format(
        _escape(sequence["search"]["enzyme"])
    )
    buff += f'      <param name="semiSpecific" value="{int(bool(sequence["search"]["semiSpecific"]))}" type="int" />\n'
    buff += '    <param name="tolerance" value="{:f}" type="float" />\n'.format(
        sequence["search"]["tolerance"]
    )
    buff += '    <param name="units" value="{}" type="str" />\n'.format(
        sequence["search"]["units"]
    )
    buff += f'      <param name="retainPos" value="{int(bool(sequence["search"]["retainPos"]))}" type="int" />\n'
    buff += "    </search>\n"
    buff += "  </sequence>\n\n"

    # mass calculator
    buff += "  <massCalculator>\n"
    buff += '    <param name="ionseriesAgent" value="{}" type="str" />\n'.format(
        massCalculator["ionseriesAgent"]
    )
    buff += f'    <param name="ionseriesAgentCharge" value="{massCalculator["ionseriesAgentCharge"]}" type="int" />\n'
    buff += f'    <param name="ionseriesPolarity" value="{massCalculator["ionseriesPolarity"]}" type="int" />\n'
    buff += '    <param name="patternFwhm" value="{:f}" type="float" />\n'.format(
        massCalculator["patternFwhm"]
    )
    buff += '    <param name="patternThreshold" value="{:f}" type="float" />\n'.format(
        massCalculator["patternThreshold"]
    )
    buff += f'    <param name="patternShowPeaks" value="{int(bool(massCalculator["patternShowPeaks"]))}" type="int" />\n'
    buff += '    <param name="patternPeakShape" value="{}" type="unicode" />\n'.format(
        _escape(massCalculator["patternPeakShape"])
    )
    buff += "  </massCalculator>\n\n"

    # mass to formula
    buff += "  <massToFormula>\n"
    buff += f'    <param name="countLimit" value="{massToFormula["countLimit"]}" type="int" />\n'
    buff += f'    <param name="massLimit" value="{massToFormula["massLimit"]}" type="int" />\n'
    buff += (
        f'    <param name="charge" value="{massToFormula["charge"]}" type="int" />\n'
    )
    buff += '    <param name="ionization" value="{}" type="str" />\n'.format(
        massToFormula["ionization"]
    )
    buff += '    <param name="tolerance" value="{:f}" type="float" />\n'.format(
        massToFormula["tolerance"]
    )
    buff += '    <param name="units" value="{}" type="str" />\n'.format(
        massToFormula["units"]
    )
    buff += '    <param name="formulaMin" value="{}" type="str" />\n'.format(
        massToFormula["formulaMin"]
    )
    buff += '    <param name="formulaMax" value="{}" type="str" />\n'.format(
        massToFormula["formulaMax"]
    )
    buff += f'    <param name="autoCHNO" value="{int(bool(massToFormula["autoCHNO"]))}" type="int" />\n'
    buff += f'    <param name="checkPattern" value="{int(bool(massToFormula["checkPattern"]))}" type="int" />\n'
    buff += '    <param name="rules" value="{}" type="str" />\n'.format(
        ";".join(massToFormula["rules"])
    )
    buff += '    <param name="HCMin" value="{:f}" type="float" />\n'.format(
        massToFormula["HCMin"]
    )
    buff += '    <param name="HCMax" value="{:f}" type="float" />\n'.format(
        massToFormula["HCMax"]
    )
    buff += '    <param name="NCMax" value="{:f}" type="float" />\n'.format(
        massToFormula["NCMax"]
    )
    buff += '    <param name="OCMax" value="{:f}" type="float" />\n'.format(
        massToFormula["OCMax"]
    )
    buff += '    <param name="PCMax" value="{:f}" type="float" />\n'.format(
        massToFormula["PCMax"]
    )
    buff += '    <param name="SCMax" value="{:f}" type="float" />\n'.format(
        massToFormula["SCMax"]
    )
    buff += '    <param name="RDBEMin" value="{:f}" type="float" />\n'.format(
        massToFormula["RDBEMin"]
    )
    buff += '    <param name="RDBEMax" value="{:f}" type="float" />\n'.format(
        massToFormula["RDBEMax"]
    )
    buff += "  </massToFormula>\n\n"

    # mass defect plot
    buff += "  <massDefectPlot>\n"
    buff += '    <param name="yAxis" value="{}" type="str" />\n'.format(
        massDefectPlot["yAxis"]
    )
    buff += '    <param name="nominalMass" value="{}" type="str" />\n'.format(
        massDefectPlot["nominalMass"]
    )
    buff += '    <param name="kendrickFormula" value="{}" type="str" />\n'.format(
        massDefectPlot["kendrickFormula"]
    )
    buff += '    <param name="relIntCutoff" value="{:f}" type="float" />\n'.format(
        massDefectPlot["relIntCutoff"]
    )
    buff += f'    <param name="removeIsotopes" value="{int(bool(massDefectPlot["removeIsotopes"]))}" type="int" />\n'
    buff += f'    <param name="ignoreCharge" value="{int(bool(massDefectPlot["ignoreCharge"]))}" type="int" />\n'
    buff += f'    <param name="showNotations" value="{int(bool(massDefectPlot["showNotations"]))}" type="int" />\n'
    buff += "  </massDefectPlot>\n\n"

    # compounds search
    buff += "  <compoundsSearch>\n"
    buff += f'    <param name="massType" value="{compoundsSearch["massType"]}" type="int" />\n'
    buff += f'    <param name="maxCharge" value="{compoundsSearch["maxCharge"]}" type="int" />\n'
    buff += f'    <param name="radicals" value="{int(bool(compoundsSearch["radicals"]))}" type="int" />\n'
    buff += '    <param name="adducts" value="{}" type="str" />\n'.format(
        ";".join(compoundsSearch["adducts"])
    )
    buff += "  </compoundsSearch>\n\n"

    # peak differences
    buff += "  <peakDifferences>\n"
    buff += f'    <param name="aminoacids" value="{int(bool(peakDifferences["aminoacids"]))}" type="int" />\n'
    buff += f'    <param name="dipeptides" value="{int(bool(peakDifferences["dipeptides"]))}" type="int" />\n'
    buff += '    <param name="tolerance" value="{:f}" type="float" />\n'.format(
        peakDifferences["tolerance"]
    )
    buff += f'    <param name="massType" value="{peakDifferences["massType"]}" type="int" />\n'
    buff += f'    <param name="consolidate" value="{int(bool(peakDifferences["consolidate"]))}" type="int" />\n'
    buff += "  </peakDifferences>\n\n"

    # compare peaklists
    buff += "  <comparePeaklists>\n"
    buff += '    <param name="tolerance" value="{:f}" type="float" />\n'.format(
        comparePeaklists["tolerance"]
    )
    buff += '    <param name="units" value="{}" type="str" />\n'.format(
        comparePeaklists["units"]
    )
    buff += f'    <param name="ignoreCharge" value="{int(bool(comparePeaklists["ignoreCharge"]))}" type="int" />\n'
    buff += f'    <param name="ratioCheck" value="{int(bool(comparePeaklists["ratioCheck"]))}" type="int" />\n'
    buff += f'    <param name="ratioDirection" value="{comparePeaklists["ratioDirection"]}" type="int" />\n'
    buff += '    <param name="ratioThreshold" value="{:f}" type="float" />\n'.format(
        comparePeaklists["ratioThreshold"]
    )
    buff += "  </comparePeaklists>\n\n"

    # spectrum generator
    buff += "  <spectrumGenerator>\n"
    buff += '    <param name="fwhm" value="{:f}" type="float" />\n'.format(
        spectrumGenerator["fwhm"]
    )
    buff += f'    <param name="points" value="{spectrumGenerator["points"]}" type="int" />\n'
    buff += '    <param name="noise" value="{:f}" type="float" />\n'.format(
        spectrumGenerator["noise"]
    )
    buff += f'    <param name="forceFwhm" value="{int(bool(spectrumGenerator["forceFwhm"]))}" type="int" />\n'
    buff += '    <param name="peakShape" value="{}" type="unicode" />\n'.format(
        _escape(spectrumGenerator["peakShape"])
    )
    buff += f'    <param name="showPeaks" value="{int(bool(spectrumGenerator["showPeaks"]))}" type="int" />\n'
    buff += f'    <param name="showOverlay" value="{int(bool(spectrumGenerator["showOverlay"]))}" type="int" />\n'
    buff += "  </spectrumGenerator>\n\n"

    # envelope fit
    buff += "  <envelopeFit>\n"
    buff += '    <param name="fit" value="{}" type="str" />\n'.format(
        envelopeFit["fit"]
    )
    buff += '    <param name="fwhm" value="{:f}" type="float" />\n'.format(
        envelopeFit["fwhm"]
    )
    buff += f'    <param name="forceFwhm" value="{int(bool(envelopeFit["forceFwhm"]))}" type="int" />\n'
    buff += '    <param name="peakShape" value="{}" type="unicode" />\n'.format(
        _escape(envelopeFit["peakShape"])
    )
    buff += f'    <param name="autoAlign" value="{int(bool(envelopeFit["autoAlign"]))}" type="int" />\n'
    buff += '    <param name="relThreshold" value="{:f}" type="float" />\n'.format(
        envelopeFit["relThreshold"]
    )
    buff += "  </envelopeFit>\n\n"

    # mascot
    buff += "  <mascot>\n"
    buff += "    <common>\n"
    buff += '      <param name="server" value="{}" type="unicode" />\n'.format(
        _escape(mascot["common"]["server"])
    )
    buff += '      <param name="searchType" value="{}" type="str" />\n'.format(
        mascot["common"]["searchType"]
    )
    buff += '      <param name="userName" value="{}" type="unicode" />\n'.format(
        _escape(mascot["common"]["userName"])
    )
    buff += '      <param name="userEmail" value="{}" type="unicode" />\n'.format(
        _escape(mascot["common"]["userEmail"])
    )
    buff += f'      <param name="filterAnnotations" value="{int(bool(mascot["common"]["filterAnnotations"]))}" type="int" />\n'
    buff += f'      <param name="filterMatches" value="{int(bool(mascot["common"]["filterMatches"]))}" type="int" />\n'
    buff += f'      <param name="filterUnselected" value="{int(bool(mascot["common"]["filterUnselected"]))}" type="int" />\n'
    buff += f'      <param name="filterIsotopes" value="{int(bool(mascot["common"]["filterIsotopes"]))}" type="int" />\n'
    buff += f'      <param name="filterUnknown" value="{int(bool(mascot["common"]["filterUnknown"]))}" type="int" />\n'
    buff += "    </common>\n"
    buff += "    <pmf>\n"
    buff += '      <param name="database" value="{}" type="unicode" />\n'.format(
        mascot["pmf"]["database"]
    )
    buff += '      <param name="taxonomy" value="{}" type="unicode" />\n'.format(
        mascot["pmf"]["taxonomy"]
    )
    buff += '      <param name="enzyme" value="{}" type="unicode" />\n'.format(
        mascot["pmf"]["enzyme"]
    )
    buff += '      <param name="miscleavages" value="{}" type="unicode" />\n'.format(
        mascot["pmf"]["miscleavages"]
    )
    buff += '      <param name="fixedMods" value="{}" type="unicode" />\n'.format(
        ";".join(mascot["pmf"]["fixedMods"])
    )
    buff += '      <param name="variableMods" value="{}" type="unicode" />\n'.format(
        ";".join(mascot["pmf"]["variableMods"])
    )
    buff += f'      <param name="hiddenMods" value="{int(bool(mascot["pmf"]["hiddenMods"]))}" type="int" />\n'
    buff += '      <param name="proteinMass" value="{}" type="unicode" />\n'.format(
        mascot["pmf"]["proteinMass"]
    )
    buff += '      <param name="peptideTol" value="{}" type="unicode" />\n'.format(
        mascot["pmf"]["peptideTol"]
    )
    buff += '      <param name="peptideTolUnits" value="{}" type="unicode" />\n'.format(
        mascot["pmf"]["peptideTolUnits"]
    )
    buff += '      <param name="massType" value="{}" type="unicode" />\n'.format(
        mascot["pmf"]["massType"]
    )
    buff += '      <param name="charge" value="{}" type="unicode" />\n'.format(
        mascot["pmf"]["charge"]
    )
    buff += f'      <param name="decoy" value="{int(bool(mascot["pmf"]["decoy"]))}" type="int" />\n'
    buff += '      <param name="report" value="{}" type="unicode" />\n'.format(
        mascot["pmf"]["report"]
    )
    buff += "    </pmf>\n"
    # mascot
    buff += "    <sq>\n"
    buff += '      <param name="database" value="{}" type="unicode" />\n'.format(
        mascot["sq"]["database"]
    )
    buff += '      <param name="taxonomy" value="{}" type="unicode" />\n'.format(
        mascot["sq"]["taxonomy"]
    )
    buff += '      <param name="enzyme" value="{}" type="unicode" />\n'.format(
        mascot["sq"]["enzyme"]
    )
    buff += '      <param name="miscleavages" value="{}" type="unicode" />\n'.format(
        mascot["sq"]["miscleavages"]
    )
    buff += '      <param name="fixedMods" value="{}" type="unicode" />\n'.format(
        ";".join(mascot["sq"]["fixedMods"])
    )
    buff += '      <param name="variableMods" value="{}" type="unicode" />\n'.format(
        ";".join(mascot["sq"]["variableMods"])
    )
    buff += f'      <param name="hiddenMods" value="{int(bool(mascot["sq"]["hiddenMods"]))}" type="int" />\n'
    buff += '      <param name="peptideTol" value="{}" type="unicode" />\n'.format(
        mascot["sq"]["peptideTol"]
    )
    buff += '      <param name="peptideTolUnits" value="{}" type="unicode" />\n'.format(
        mascot["sq"]["peptideTolUnits"]
    )
    buff += '      <param name="msmsTol" value="{}" type="unicode" />\n'.format(
        mascot["sq"]["msmsTol"]
    )
    buff += '      <param name="msmsTolUnits" value="{}" type="unicode" />\n'.format(
        mascot["sq"]["msmsTolUnits"]
    )
    buff += '      <param name="massType" value="{}" type="unicode" />\n'.format(
        mascot["sq"]["massType"]
    )
    buff += '      <param name="charge" value="{}" type="unicode" />\n'.format(
        mascot["sq"]["charge"]
    )
    buff += '      <param name="instrument" value="{}" type="unicode" />\n'.format(
        mascot["sq"]["instrument"]
    )
    buff += '      <param name="quantitation" value="{}" type="unicode" />\n'.format(
        mascot["sq"]["quantitation"]
    )
    buff += f'      <param name="decoy" value="{int(bool(mascot["sq"]["decoy"]))}" type="int" />\n'
    buff += '      <param name="report" value="{}" type="unicode" />\n'.format(
        mascot["sq"]["report"]
    )
    buff += "    </sq>\n"
    buff += "    <mis>\n"
    buff += '      <param name="database" value="{}" type="unicode" />\n'.format(
        mascot["mis"]["database"]
    )
    buff += '      <param name="taxonomy" value="{}" type="unicode" />\n'.format(
        mascot["mis"]["taxonomy"]
    )
    buff += '      <param name="enzyme" value="{}" type="unicode" />\n'.format(
        mascot["mis"]["enzyme"]
    )
    buff += '      <param name="miscleavages" value="{}" type="unicode" />\n'.format(
        mascot["mis"]["miscleavages"]
    )
    buff += '      <param name="fixedMods" value="{}" type="unicode" />\n'.format(
        ";".join(mascot["mis"]["fixedMods"])
    )
    buff += '      <param name="variableMods" value="{}" type="unicode" />\n'.format(
        ";".join(mascot["mis"]["variableMods"])
    )
    buff += f'      <param name="hiddenMods" value="{int(bool(mascot["mis"]["hiddenMods"]))}" type="int" />\n'
    buff += '      <param name="peptideTol" value="{}" type="unicode" />\n'.format(
        mascot["mis"]["peptideTol"]
    )
    buff += '      <param name="peptideTolUnits" value="{}" type="unicode" />\n'.format(
        mascot["mis"]["peptideTolUnits"]
    )
    buff += '      <param name="msmsTol" value="{}" type="unicode" />\n'.format(
        mascot["mis"]["msmsTol"]
    )
    buff += '      <param name="msmsTolUnits" value="{}" type="unicode" />\n'.format(
        mascot["mis"]["msmsTolUnits"]
    )
    buff += '      <param name="massType" value="{}" type="unicode" />\n'.format(
        mascot["mis"]["massType"]
    )
    buff += '      <param name="charge" value="{}" type="unicode" />\n'.format(
        mascot["mis"]["charge"]
    )
    buff += '      <param name="instrument" value="{}" type="unicode" />\n'.format(
        mascot["mis"]["instrument"]
    )
    buff += '      <param name="quantitation" value="{}" type="unicode" />\n'.format(
        mascot["mis"]["quantitation"]
    )
    buff += f'      <param name="errorTolerant" value="{int(bool(mascot["mis"]["errorTolerant"]))}" type="int" />\n'
    buff += f'      <param name="decoy" value="{int(bool(mascot["mis"]["decoy"]))}" type="int" />\n'
    buff += '      <param name="report" value="{}" type="unicode" />\n'.format(
        mascot["mis"]["report"]
    )
    buff += "    </mis>\n"
    buff += "  </mascot>\n\n"

    # profound
    buff += "  <profound>\n"
    buff += '    <param name="script" value="{}" type="unicode" />\n'.format(
        _escape(profound["script"])
    )
    buff += '    <param name="database" value="{}" type="unicode" />\n'.format(
        profound["database"]
    )
    buff += '    <param name="taxonomy" value="{}" type="unicode" />\n'.format(
        profound["taxonomy"]
    )
    buff += '    <param name="enzyme" value="{}" type="unicode" />\n'.format(
        profound["enzyme"]
    )
    buff += '    <param name="miscleavages" value="{}" type="unicode" />\n'.format(
        profound["miscleavages"]
    )
    buff += '    <param name="fixedMods" value="{}" type="unicode" />\n'.format(
        ";".join(profound["fixedMods"])
    )
    buff += '    <param name="variableMods" value="{}" type="unicode" />\n'.format(
        ";".join(profound["variableMods"])
    )
    buff += '    <param name="proteinMassLow" value="{:f}" type="float" />\n'.format(
        profound["proteinMassLow"]
    )
    buff += '    <param name="proteinMassHigh" value="{:f}" type="float" />\n'.format(
        profound["proteinMassHigh"]
    )
    buff += f'    <param name="proteinPILow" value="{profound["proteinPILow"]}" type="int" />\n'
    buff += f'    <param name="proteinPIHigh" value="{profound["proteinPIHigh"]}" type="int" />\n'
    buff += '    <param name="peptideTol" value="{:f}" type="float" />\n'.format(
        profound["peptideTol"]
    )
    buff += '    <param name="peptideTolUnits" value="{}" type="unicode" />\n'.format(
        profound["peptideTolUnits"]
    )
    buff += '    <param name="massType" value="{}" type="unicode" />\n'.format(
        profound["massType"]
    )
    buff += '    <param name="charge" value="{}" type="unicode" />\n'.format(
        profound["charge"]
    )
    buff += '    <param name="ranking" value="{}" type="unicode" />\n'.format(
        profound["ranking"]
    )
    buff += '    <param name="expectation" value="{:f}" type="float" />\n'.format(
        profound["expectation"]
    )
    buff += (
        f'    <param name="candidates" value="{profound["candidates"]}" type="int" />\n'
    )
    buff += f'    <param name="filterAnnotations" value="{int(bool(profound["filterAnnotations"]))}" type="int" />\n'
    buff += f'    <param name="filterMatches" value="{int(bool(profound["filterMatches"]))}" type="int" />\n'
    buff += f'    <param name="filterUnselected" value="{int(bool(profound["filterUnselected"]))}" type="int" />\n'
    buff += f'    <param name="filterIsotopes" value="{int(bool(profound["filterIsotopes"]))}" type="int" />\n'
    buff += f'    <param name="filterUnknown" value="{int(bool(profound["filterUnknown"]))}" type="int" />\n'
    buff += "  </profound>\n\n"

    # protein prospector
    buff += "  <prospector>\n"
    buff += "    <common>\n"
    buff += '      <param name="script" value="{}" type="unicode" />\n'.format(
        _escape(prospector["common"]["script"])
    )
    buff += '      <param name="searchType" value="{}" type="str" />\n'.format(
        prospector["common"]["searchType"]
    )
    buff += f'      <param name="filterAnnotations" value="{int(bool(prospector["common"]["filterAnnotations"]))}" type="int" />\n'
    buff += f'      <param name="filterMatches" value="{int(bool(prospector["common"]["filterMatches"]))}" type="int" />\n'
    buff += f'      <param name="filterUnselected" value="{int(bool(prospector["common"]["filterUnselected"]))}" type="int" />\n'
    buff += f'      <param name="filterIsotopes" value="{int(bool(prospector["common"]["filterIsotopes"]))}" type="int" />\n'
    buff += f'      <param name="filterUnknown" value="{int(bool(prospector["common"]["filterUnknown"]))}" type="int" />\n'
    buff += "    </common>\n"
    buff += "    <msfit>\n"
    buff += '      <param name="database" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["database"]
    )
    buff += '      <param name="taxonomy" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["taxonomy"]
    )
    buff += '      <param name="enzyme" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["enzyme"]
    )
    buff += '      <param name="miscleavages" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["miscleavages"]
    )
    buff += '      <param name="fixedMods" value="{}" type="unicode" />\n'.format(
        ";".join(prospector["msfit"]["fixedMods"])
    )
    buff += '      <param name="variableMods" value="{}" type="unicode" />\n'.format(
        ";".join(prospector["msfit"]["variableMods"])
    )
    buff += '      <param name="proteinMassLow" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["proteinMassLow"]
    )
    buff += '      <param name="proteinMassHigh" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["proteinMassHigh"]
    )
    buff += '      <param name="proteinPILow" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["proteinPILow"]
    )
    buff += '      <param name="proteinPIHigh" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["proteinPIHigh"]
    )
    buff += '      <param name="peptideTol" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["peptideTol"]
    )
    buff += '      <param name="peptideTolUnits" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["peptideTolUnits"]
    )
    buff += '      <param name="massType" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["massType"]
    )
    buff += '      <param name="instrument" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["instrument"]
    )
    buff += '      <param name="minMatches" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["minMatches"]
    )
    buff += '      <param name="maxMods" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["maxMods"]
    )
    buff += '      <param name="report" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["report"]
    )
    buff += '      <param name="pfactor" value="{}" type="unicode" />\n'.format(
        prospector["msfit"]["pfactor"]
    )
    buff += "    </msfit>\n"
    buff += "    <mstag>\n"
    buff += '      <param name="database" value="{}" type="unicode" />\n'.format(
        prospector["mstag"]["database"]
    )
    buff += '      <param name="taxonomy" value="{}" type="unicode" />\n'.format(
        prospector["mstag"]["taxonomy"]
    )
    buff += '      <param name="enzyme" value="{}" type="unicode" />\n'.format(
        prospector["mstag"]["enzyme"]
    )
    buff += '      <param name="miscleavages" value="{}" type="unicode" />\n'.format(
        prospector["mstag"]["miscleavages"]
    )
    buff += '      <param name="fixedMods" value="{}" type="unicode" />\n'.format(
        ";".join(prospector["mstag"]["fixedMods"])
    )
    buff += '      <param name="variableMods" value="{}" type="unicode" />\n'.format(
        ";".join(prospector["mstag"]["variableMods"])
    )
    buff += '      <param name="peptideTol" value="{}" type="unicode" />\n'.format(
        prospector["mstag"]["peptideTol"]
    )
    buff += '      <param name="peptideTolUnits" value="{}" type="unicode" />\n'.format(
        prospector["mstag"]["peptideTolUnits"]
    )
    buff += '      <param name="peptideCharge" value="{}" type="unicode" />\n'.format(
        prospector["mstag"]["peptideCharge"]
    )
    buff += '      <param name="msmsTol" value="{}" type="unicode" />\n'.format(
        prospector["mstag"]["msmsTol"]
    )
    buff += '      <param name="msmsTolUnits" value="{}" type="unicode" />\n'.format(
        prospector["mstag"]["msmsTolUnits"]
    )
    buff += '      <param name="massType" value="{}" type="unicode" />\n'.format(
        prospector["mstag"]["massType"]
    )
    buff += '      <param name="instrument" value="{}" type="unicode" />\n'.format(
        prospector["mstag"]["instrument"]
    )
    buff += '      <param name="maxMods" value="{}" type="unicode" />\n'.format(
        prospector["mstag"]["maxMods"]
    )
    buff += '      <param name="report" value="{}" type="unicode" />\n'.format(
        prospector["mstag"]["report"]
    )
    buff += "    </mstag>\n"
    buff += "  </prospector>\n\n"

    # links
    buff += "  <links>\n"
    for name in links:
        if name not in (
            "mMassHomepage",
            "mMassForum",
            "mMassTwitter",
            "mMassCite",
            "mMassDonate",
            "mMassDownload",
        ):
            buff += (
                f'    <link name="{_escape(name)}" value="{_escape(links[name])}" />\n'
            )
    buff += "  </links>\n\n"

    buff += "</mMassConfig>"

    # save config file
    try:
        with Path(path).open("w", encoding="utf-8") as save:
            save.write(buff)
        return True
    except Exception:
        return False


# ----


def _getParams(sectionTag, section):
    """Get params from nodes."""

    if sectionTag:
        paramTags = sectionTag.getElementsByTagName("param")
        if paramTags and paramTags:
            for paramTag in paramTags:
                name = paramTag.getAttribute("name")
                value = paramTag.getAttribute("value")
                valueType = paramTag.getAttribute("type")
                if name in section:
                    if valueType == "unicode":
                        valueType = "str"
                    if valueType in ("str", "float", "int"):
                        with contextlib.suppress(BaseException):
                            section[name] = eval(valueType + "(value)")


# ----


def _escape(text):
    """Clear special characters such as <> etc."""

    text = text.strip()
    search = ("&", '"', "'", "<", ">")
    replace = ("&amp;", "&quot;", "&apos;", "&lt;", "&gt;")
    for x, item in enumerate(search):
        text = text.replace(item, replace[x])

    return text


# ----


try:
    loadConfig()
except OSError:
    saveConfig()
