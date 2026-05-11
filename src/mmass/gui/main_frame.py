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
import copy
import http.client
import importlib.resources
import os
import platform
import random
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import webbrowser
from pathlib import Path

import wx
import wx.aui

from mmass import mspy

# load modules
from . import config, doc, ids, images, libs, mwx
from .dlg_clipboard_editor import DlgClipboardEditor
from .dlg_compounds_editor import DlgCompoundsEditor
from .dlg_enzymes_editor import DlgEnzymesEditor
from .dlg_error import DlgError
from .dlg_mascot_editor import DlgMascotEditor
from .dlg_modifications_editor import DlgModificationsEditor
from .dlg_monomers_editor import DlgMonomersEditor
from .dlg_preferences import DlgPreferences
from .dlg_presets_editor import DlgPresetsEditor
from .dlg_references_editor import DlgReferencesEditor
from .dlg_select_scans import DlgSelectScans
from .dlg_select_sequences import DlgSelectSequences
from .panel_about import PanelAbout
from .panel_calibration import PanelCalibration
from .panel_compare_peaklists import PanelComparePeaklists
from .panel_compounds_search import PanelCompoundsSearch
from .panel_document_export import PanelDocumentExport
from .panel_document_info import PanelDocumentInfo
from .panel_documents import PanelDocuments
from .panel_envelope_fit import PanelEnvelopeFit
from .panel_mascot import PanelMascot
from .panel_mass_calculator import PanelMassCalculator
from .panel_mass_defect_plot import PanelMassDefectPlot
from .panel_mass_filter import PanelMassFilter
from .panel_mass_to_formula import PanelMassToFormula
from .panel_peak_differences import PanelPeakDifferences
from .panel_peaklist import PanelPeaklist
from .panel_periodic_table import PanelPeriodicTable
from .panel_processing import PanelProcessing
from .panel_profound import PanelProfound
from .panel_prospector import PanelProspector
from .panel_sequence import PanelSequence
from .panel_spectrum import DlgSpectrumOffset, DlgViewRange, PanelSpectrum
from .panel_spectrum_generator import PanelSpectrumGenerator

# MAIN FRAME
# ----------


class MainFrame(wx.Frame):
    def __init__(self, parent, id, title) -> None:
        wx.Frame.__init__(
            self,
            parent,
            -1,
            title,
            size=(800, 500),
            style=wx.DEFAULT_FRAME_STYLE,
        )

        # init error handler
        sys.excepthook = self.onError

        # init images
        images.loadImages()

        # set icon
        icons = wx.IconBundle()
        icons.AddIcon(images.lib["icon16"])
        icons.AddIcon(images.lib["icon32"])
        icons.AddIcon(images.lib["icon48"])
        icons.AddIcon(images.lib["icon128"])
        icons.AddIcon(images.lib["icon256"])
        self.SetIcons(icons)

        # init basics
        self.documents = []
        self.currentDocument = None
        self.currentDocumentXML = None
        self.currentSequence = None

        self.documentsSoloCurrent = None
        self.documentsSoloPrevious = {}
        self.usedColours = []

        self.bufferedScanlists = {}

        self.processingDocumentQueue = False
        self.tmpDocumentQueue = []
        self.tmpScanlist = None
        self.tmpSequenceList = None
        self.tmpCompassXport = None
        self.tmpLibrarySaved = None

        # make GUI
        self.makeMenubar()
        self.SetMenuBar(self.menubar)

        self.makeToolbar()
        self.SetToolBar(self.toolbar)
        self.toolbar.Realize()

        self.makeGUI()
        self.updateControls()

        # set size
        maximize = config.main["appMaximized"]
        self.SetSize((config.main["appWidth"], config.main["appHeight"]))
        self.SetMinSize((855, 500))
        if maximize:
            self.Maximize()

        # bind events
        self.DragAcceptFiles(True)
        self.Bind(wx.EVT_CLOSE, self.onQuit)
        self.Bind(wx.EVT_SIZE, self.onSize)
        self.Bind(wx.EVT_DROP_FILES, self.onDocumentDropped)

        # show app
        self.Layout()
        self.Centre(wx.BOTH)
        self.Show(True)

        # check for available updates
        self.checkVersions()

    # ----

    def makeMenubar(self) -> None:
        """Make main application menubar."""
        # init menubar
        self.menubar = wx.MenuBar()

        # init recent documents
        self.menuRecent = wx.Menu()
        self.updateRecentFiles()

        # file
        document = wx.Menu()
        document.Append(ids.ID_documentNew, "New" + ids.HK_documentNew, "")
        document.Append(
            ids.ID_documentNewFromClipboard,
            "New from Clipboard" + ids.HK_documentNewFromClipboard,
            "",
        )
        document.Append(ids.ID_documentOpen, "Open..." + ids.HK_documentOpen, "")
        document.Append(ids.ID_documentRecent, "Open Recent", self.menuRecent)
        document.AppendSeparator()
        document.Append(ids.ID_documentClose, "Close" + ids.HK_documentClose, "")
        document.Append(ids.ID_documentCloseAll, "Close All" + ids.HK_documentCloseAll, "")
        document.Append(ids.ID_documentSave, "Save" + ids.HK_documentSave, "")
        document.Append(ids.ID_documentSaveAs, "Save As..." + ids.HK_documentSaveAs, "")
        document.Append(ids.ID_documentSaveAll, "Save All" + ids.HK_documentSaveAll, "")
        document.AppendSeparator()
        document.Append(ids.ID_documentExport, "Export..." + ids.HK_documentExport, "")
        document.AppendSeparator()
        document.Append(
            ids.ID_documentPrintSpectrum, "Print Spectrum..." + ids.HK_documentPrintSpectrum, ""
        )
        document.Append(ids.ID_documentReport, "Analysis Report..." + ids.HK_documentReport, "")
        if wx.Platform == "__WXMAC__":
            document.AppendSeparator()
        document.Append(ids.ID_documentInfo, "Document Info..." + ids.HK_documentInfo, "")
        document.AppendSeparator()
        document.Append(ids.ID_preferences, "Preferences..." + ids.HK_preferences, "")
        document.AppendSeparator()
        document.Append(ids.ID_quit, "Quit" + ids.HK_quit, "Quit mMass")

        self.Bind(wx.EVT_MENU, self.onDocumentNew, id=ids.ID_documentNew)
        self.Bind(
            wx.EVT_MENU, self.onDocumentNewFromClipboard, id=ids.ID_documentNewFromClipboard
        )
        self.Bind(wx.EVT_MENU, self.onDocumentOpen, id=ids.ID_documentOpen)
        self.Bind(wx.EVT_MENU, self.onDocumentClose, id=ids.ID_documentClose)
        self.Bind(wx.EVT_MENU, self.onDocumentCloseAll, id=ids.ID_documentCloseAll)
        self.Bind(wx.EVT_MENU, self.onDocumentSave, id=ids.ID_documentSave)
        self.Bind(wx.EVT_MENU, self.onDocumentSave, id=ids.ID_documentSaveAs)
        self.Bind(wx.EVT_MENU, self.onDocumentSaveAll, id=ids.ID_documentSaveAll)
        self.Bind(wx.EVT_MENU, self.onDocumentExport, id=ids.ID_documentExport)
        self.Bind(wx.EVT_MENU, self.onDocumentInfo, id=ids.ID_documentInfo)
        self.Bind(
            wx.EVT_MENU, self.onDocumentPrintSpectrum, id=ids.ID_documentPrintSpectrum
        )
        self.Bind(wx.EVT_MENU, self.onDocumentReport, id=ids.ID_documentReport)
        self.Bind(wx.EVT_MENU, self.onPreferences, id=ids.ID_preferences)
        self.Bind(wx.EVT_MENU, self.onQuit, id=ids.ID_quit)

        self.menubar.Append(document, "File")

        # view
        view = wx.Menu()

        viewCanvas = wx.Menu()
        viewCanvas.Append(ids.ID_viewLegend, "Legend", "", wx.ITEM_CHECK)
        viewCanvas.Append(ids.ID_viewGrid, "Gridlines", "", wx.ITEM_CHECK)
        viewCanvas.Append(ids.ID_viewMinorTicks, "Minor Ticks", "", wx.ITEM_CHECK)
        viewCanvas.Append(ids.ID_viewDataPoints, "Data Points", "", wx.ITEM_CHECK)
        viewCanvas.AppendSeparator()
        viewCanvas.Append(
            ids.ID_viewPosBars, "Position Bars" + ids.HK_viewPosBars, "", wx.ITEM_CHECK
        )
        viewCanvas.AppendSeparator()
        viewCanvas.Append(ids.ID_viewGel, "Gel View" + ids.HK_viewGel, "", wx.ITEM_CHECK)
        viewCanvas.Append(ids.ID_viewGelLegend, "Gel View Legend", "", wx.ITEM_CHECK)
        viewCanvas.AppendSeparator()
        viewCanvas.Append(ids.ID_viewTracker, "Cursor Tracker", "", wx.ITEM_CHECK)
        viewCanvas.Append(ids.ID_viewCheckLimits, "Check Limits", "", wx.ITEM_CHECK)
        view.Append(-1, "Spectrum Canvas", viewCanvas)

        viewLabels = wx.Menu()
        title = ("Show Labels", "Hide Labels")
        viewLabels.Append(
            ids.ID_viewLabels,
            title[bool(config.spectrum["showLabels"])] + ids.HK_viewLabels,
            "",
        )
        title = ("Show Ticks", "Hide Ticks")
        viewLabels.Append(
            ids.ID_viewTicks, title[bool(config.spectrum["showTicks"])] + ids.HK_viewTicks, ""
        )
        viewLabels.AppendSeparator()
        viewLabels.Append(ids.ID_viewLabelCharge, "Charge", "", wx.ITEM_CHECK)
        viewLabels.Append(ids.ID_viewLabelGroup, "Group", "", wx.ITEM_CHECK)
        viewLabels.Append(ids.ID_viewLabelBgr, "Background", "", wx.ITEM_CHECK)
        viewLabels.AppendSeparator()
        title = ("Vertical Labels", "Horizontal Labels")
        viewLabels.Append(
            ids.ID_viewLabelAngle,
            title[bool(config.spectrum["labelAngle"])] + ids.HK_viewLabelAngle,
            "",
        )
        viewLabels.AppendSeparator()
        viewLabels.Append(
            ids.ID_viewOverlapLabels,
            "Allow Overlapping" + ids.HK_viewOverlapLabels,
            "",
            wx.ITEM_CHECK,
        )
        viewLabels.Append(
            ids.ID_viewAllLabels,
            "Labels in All Documents" + ids.HK_viewAllLabels,
            "",
            wx.ITEM_CHECK,
        )
        view.Append(-1, "Peak Labels", viewLabels)

        viewNotations = wx.Menu()
        title = ("Show Notations", "Hide Notations")
        viewNotations.Append(
            ids.ID_viewNotations, title[bool(config.spectrum["showNotations"])], ""
        )
        viewNotations.AppendSeparator()
        viewNotations.Append(ids.ID_viewNotationMarks, "Marks", "", wx.ITEM_CHECK)
        viewNotations.Append(ids.ID_viewNotationLabels, "Labels", "", wx.ITEM_CHECK)
        viewNotations.Append(ids.ID_viewNotationMz, "m/z", "", wx.ITEM_CHECK)
        view.Append(-1, "Notations", viewNotations)

        viewSpectrumRuler = wx.Menu()
        viewSpectrumRuler.Append(ids.ID_viewSpectrumRulerMz, "m/z", "", wx.ITEM_CHECK)
        viewSpectrumRuler.Append(
            ids.ID_viewSpectrumRulerDist, "Distance", "", wx.ITEM_CHECK
        )
        viewSpectrumRuler.Append(ids.ID_viewSpectrumRulerPpm, "ppm", "", wx.ITEM_CHECK)
        viewSpectrumRuler.Append(ids.ID_viewSpectrumRulerZ, "Charge", "", wx.ITEM_CHECK)
        viewSpectrumRuler.Append(
            ids.ID_viewSpectrumRulerCursorMass, "Neutral Mass (Cursor)", "", wx.ITEM_CHECK
        )
        viewSpectrumRuler.Append(
            ids.ID_viewSpectrumRulerParentMass, "Neutral Mass (Parent)", "", wx.ITEM_CHECK
        )
        viewSpectrumRuler.Append(ids.ID_viewSpectrumRulerArea, "Area", "", wx.ITEM_CHECK)
        view.Append(-1, "Spectrum Ruler", viewSpectrumRuler)

        viewPeaklistColumns = wx.Menu()
        viewPeaklistColumns.Append(ids.ID_viewPeaklistColumnMz, "m/z", "", wx.ITEM_CHECK)
        viewPeaklistColumns.Append(ids.ID_viewPeaklistColumnAi, "a.i.", "", wx.ITEM_CHECK)
        viewPeaklistColumns.Append(
            ids.ID_viewPeaklistColumnInt, "Intensity", "", wx.ITEM_CHECK
        )
        viewPeaklistColumns.Append(
            ids.ID_viewPeaklistColumnBase, "Baseline", "", wx.ITEM_CHECK
        )
        viewPeaklistColumns.Append(
            ids.ID_viewPeaklistColumnRel, "Rel. Intensity", "", wx.ITEM_CHECK
        )
        viewPeaklistColumns.Append(ids.ID_viewPeaklistColumnSn, "s/n", "", wx.ITEM_CHECK)
        viewPeaklistColumns.Append(ids.ID_viewPeaklistColumnZ, "Charge", "", wx.ITEM_CHECK)
        viewPeaklistColumns.Append(ids.ID_viewPeaklistColumnMass, "Mass", "", wx.ITEM_CHECK)
        viewPeaklistColumns.Append(ids.ID_viewPeaklistColumnFwhm, "FWHM", "", wx.ITEM_CHECK)
        viewPeaklistColumns.Append(
            ids.ID_viewPeaklistColumnResol, "Resolution", "", wx.ITEM_CHECK
        )
        viewPeaklistColumns.Append(
            ids.ID_viewPeaklistColumnGroup, "Group", "", wx.ITEM_CHECK
        )
        view.Append(-1, "Peak List Columns", viewPeaklistColumns)

        view.AppendSeparator()
        view.Append(
            ids.ID_viewAutoscale,
            "Autoscale Intensity" + ids.HK_viewAutoscale,
            "",
            wx.ITEM_CHECK,
        )
        view.Append(
            ids.ID_viewNormalize,
            "Normalize Intensity" + ids.HK_viewNormalize,
            "",
            wx.ITEM_CHECK,
        )
        view.AppendSeparator()
        view.Append(ids.ID_viewRange, "Set Mass Range..." + ids.HK_viewRange, "")
        view.AppendSeparator()
        view.Append(ids.ID_documentFlip, "Flip Spectrum" + ids.HK_documentFlip, "")
        view.Append(ids.ID_documentOffset, "Offset Spectrum...", "")
        view.Append(ids.ID_documentClearOffsets, "Clear All Offsets", "")
        view.AppendSeparator()
        view.Append(
            ids.ID_viewCanvasProperties,
            "Canvas Properties..." + ids.HK_viewCanvasProperties,
            "",
        )

        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewLegend)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewGrid)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewMinorTicks)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewDataPoints)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewPosBars)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewGel)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewGelLegend)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewTracker)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewCheckLimits)

        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewLabels)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewTicks)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewLabelCharge)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewLabelGroup)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewLabelBgr)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewLabelAngle)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewOverlapLabels)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewAllLabels)

        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewNotations)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewNotationMarks)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewNotationLabels)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewNotationMz)

        self.Bind(wx.EVT_MENU, self.onViewSpectrumRuler, id=ids.ID_viewSpectrumRulerMz)
        self.Bind(wx.EVT_MENU, self.onViewSpectrumRuler, id=ids.ID_viewSpectrumRulerDist)
        self.Bind(wx.EVT_MENU, self.onViewSpectrumRuler, id=ids.ID_viewSpectrumRulerPpm)
        self.Bind(wx.EVT_MENU, self.onViewSpectrumRuler, id=ids.ID_viewSpectrumRulerZ)
        self.Bind(
            wx.EVT_MENU, self.onViewSpectrumRuler, id=ids.ID_viewSpectrumRulerCursorMass
        )
        self.Bind(
            wx.EVT_MENU, self.onViewSpectrumRuler, id=ids.ID_viewSpectrumRulerParentMass
        )
        self.Bind(wx.EVT_MENU, self.onViewSpectrumRuler, id=ids.ID_viewSpectrumRulerArea)

        self.Bind(wx.EVT_MENU, self.onViewPeaklistColumns, id=ids.ID_viewPeaklistColumnMz)
        self.Bind(wx.EVT_MENU, self.onViewPeaklistColumns, id=ids.ID_viewPeaklistColumnAi)
        self.Bind(wx.EVT_MENU, self.onViewPeaklistColumns, id=ids.ID_viewPeaklistColumnInt)
        self.Bind(wx.EVT_MENU, self.onViewPeaklistColumns, id=ids.ID_viewPeaklistColumnBase)
        self.Bind(wx.EVT_MENU, self.onViewPeaklistColumns, id=ids.ID_viewPeaklistColumnRel)
        self.Bind(wx.EVT_MENU, self.onViewPeaklistColumns, id=ids.ID_viewPeaklistColumnSn)
        self.Bind(wx.EVT_MENU, self.onViewPeaklistColumns, id=ids.ID_viewPeaklistColumnZ)
        self.Bind(wx.EVT_MENU, self.onViewPeaklistColumns, id=ids.ID_viewPeaklistColumnMass)
        self.Bind(wx.EVT_MENU, self.onViewPeaklistColumns, id=ids.ID_viewPeaklistColumnFwhm)
        self.Bind(
            wx.EVT_MENU, self.onViewPeaklistColumns, id=ids.ID_viewPeaklistColumnResol
        )
        self.Bind(
            wx.EVT_MENU, self.onViewPeaklistColumns, id=ids.ID_viewPeaklistColumnGroup
        )

        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewAutoscale)
        self.Bind(wx.EVT_MENU, self.onView, id=ids.ID_viewNormalize)
        self.Bind(wx.EVT_MENU, self.onViewRange, id=ids.ID_viewRange)
        self.Bind(wx.EVT_MENU, self.onDocumentFlip, id=ids.ID_documentFlip)
        self.Bind(wx.EVT_MENU, self.onDocumentOffset, id=ids.ID_documentOffset)
        self.Bind(wx.EVT_MENU, self.onDocumentOffset, id=ids.ID_documentClearOffsets)
        self.Bind(wx.EVT_MENU, self.onViewCanvasProperties, id=ids.ID_viewCanvasProperties)

        self.menubar.Append(view, "View")

        self.menubar.Check(ids.ID_viewLegend, bool(config.spectrum["showLegend"]))
        self.menubar.Check(ids.ID_viewGrid, bool(config.spectrum["showGrid"]))
        self.menubar.Check(ids.ID_viewMinorTicks, bool(config.spectrum["showMinorTicks"]))
        self.menubar.Check(ids.ID_viewDataPoints, bool(config.spectrum["showDataPoints"]))
        self.menubar.Check(ids.ID_viewPosBars, bool(config.spectrum["showPosBars"]))
        self.menubar.Check(ids.ID_viewGel, bool(config.spectrum["showGel"]))
        self.menubar.Check(ids.ID_viewGelLegend, bool(config.spectrum["showGelLegend"]))
        self.menubar.Check(ids.ID_viewTracker, bool(config.spectrum["showTracker"]))
        self.menubar.Check(ids.ID_viewCheckLimits, bool(config.spectrum["checkLimits"]))

        self.menubar.Check(ids.ID_viewLabelCharge, bool(config.spectrum["labelCharge"]))
        self.menubar.Check(ids.ID_viewLabelGroup, bool(config.spectrum["labelGroup"]))
        self.menubar.Check(ids.ID_viewLabelBgr, bool(config.spectrum["labelBgr"]))
        self.menubar.Check(ids.ID_viewOverlapLabels, bool(config.spectrum["overlapLabels"]))
        self.menubar.Check(ids.ID_viewAllLabels, bool(config.spectrum["showAllLabels"]))

        self.menubar.Check(ids.ID_viewNotationMarks, bool(config.spectrum["notationMarks"]))
        self.menubar.Check(
            ids.ID_viewNotationLabels, bool(config.spectrum["notationLabels"])
        )
        self.menubar.Check(ids.ID_viewNotationMz, bool(config.spectrum["notationMZ"]))

        self.menubar.Check(
            ids.ID_viewSpectrumRulerMz, bool("mz" in config.main["cursorInfo"])
        )
        self.menubar.Check(
            ids.ID_viewSpectrumRulerDist, bool("dist" in config.main["cursorInfo"])
        )
        self.menubar.Check(
            ids.ID_viewSpectrumRulerPpm, bool("ppm" in config.main["cursorInfo"])
        )
        self.menubar.Check(
            ids.ID_viewSpectrumRulerZ, bool("z" in config.main["cursorInfo"])
        )
        self.menubar.Check(
            ids.ID_viewSpectrumRulerCursorMass, bool("cmass" in config.main["cursorInfo"])
        )
        self.menubar.Check(
            ids.ID_viewSpectrumRulerParentMass, bool("pmass" in config.main["cursorInfo"])
        )
        self.menubar.Check(
            ids.ID_viewSpectrumRulerArea, bool("area" in config.main["cursorInfo"])
        )

        self.menubar.Check(
            ids.ID_viewPeaklistColumnMz, bool("mz" in config.main["peaklistColumns"])
        )
        self.menubar.Check(
            ids.ID_viewPeaklistColumnAi, bool("ai" in config.main["peaklistColumns"])
        )
        self.menubar.Check(
            ids.ID_viewPeaklistColumnBase, bool("base" in config.main["peaklistColumns"])
        )
        self.menubar.Check(
            ids.ID_viewPeaklistColumnInt, bool("int" in config.main["peaklistColumns"])
        )
        self.menubar.Check(
            ids.ID_viewPeaklistColumnRel, bool("rel" in config.main["peaklistColumns"])
        )
        self.menubar.Check(
            ids.ID_viewPeaklistColumnSn, bool("sn" in config.main["peaklistColumns"])
        )
        self.menubar.Check(
            ids.ID_viewPeaklistColumnZ, bool("z" in config.main["peaklistColumns"])
        )
        self.menubar.Check(
            ids.ID_viewPeaklistColumnMass, bool("mass" in config.main["peaklistColumns"])
        )
        self.menubar.Check(
            ids.ID_viewPeaklistColumnFwhm, bool("fwhm" in config.main["peaklistColumns"])
        )
        self.menubar.Check(
            ids.ID_viewPeaklistColumnResol, bool("resol" in config.main["peaklistColumns"])
        )
        self.menubar.Check(
            ids.ID_viewPeaklistColumnGroup, bool("group" in config.main["peaklistColumns"])
        )

        self.menubar.Check(ids.ID_viewAutoscale, bool(config.spectrum["autoscale"]))
        self.menubar.Check(ids.ID_viewNormalize, bool(config.spectrum["normalize"]))

        # processing
        processing = wx.Menu()
        processing.Append(ids.ID_processingUndo, "Undo" + ids.HK_processingUndo, "")
        processing.AppendSeparator()
        processing.Append(
            ids.ID_processingPeakpicking, "Peak Picking..." + ids.HK_processingPeakpicking, ""
        )
        processing.Append(
            ids.ID_processingDeisotoping, "Deisotoping..." + ids.HK_processingDeisotoping, ""
        )
        processing.Append(
            ids.ID_processingDeconvolution,
            "Deconvolution..." + ids.HK_processingDeconvolution,
            "",
        )
        processing.AppendSeparator()
        processing.Append(
            ids.ID_processingBaseline, "Correct Baseline..." + ids.HK_processingBaseline, ""
        )
        processing.Append(
            ids.ID_processingSmoothing, "Smooth Spectrum..." + ids.HK_processingSmoothing, ""
        )
        processing.Append(ids.ID_processingCrop, "Crop...", "")
        processing.Append(ids.ID_processingMath, "Math Operations...", "")
        processing.AppendSeparator()
        processing.Append(ids.ID_processingBatch, "Batch Processing...", "")
        processing.AppendSeparator()
        processing.Append(
            ids.ID_toolsCalibration, "Calibration..." + ids.HK_toolsCalibration, ""
        )
        processing.AppendSeparator()
        processing.Append(ids.ID_toolsSwapData, "Swap Data", "")

        self.Bind(wx.EVT_MENU, self.onToolsUndo, id=ids.ID_processingUndo)
        self.Bind(wx.EVT_MENU, self.onToolsProcessing, id=ids.ID_processingPeakpicking)
        self.Bind(wx.EVT_MENU, self.onToolsProcessing, id=ids.ID_processingDeisotoping)
        self.Bind(wx.EVT_MENU, self.onToolsProcessing, id=ids.ID_processingDeconvolution)
        self.Bind(wx.EVT_MENU, self.onToolsProcessing, id=ids.ID_processingBaseline)
        self.Bind(wx.EVT_MENU, self.onToolsProcessing, id=ids.ID_processingSmoothing)
        self.Bind(wx.EVT_MENU, self.onToolsProcessing, id=ids.ID_processingCrop)
        self.Bind(wx.EVT_MENU, self.onToolsProcessing, id=ids.ID_processingMath)
        self.Bind(wx.EVT_MENU, self.onToolsProcessing, id=ids.ID_processingBatch)
        self.Bind(wx.EVT_MENU, self.onToolsCalibration, id=ids.ID_toolsCalibration)
        self.Bind(wx.EVT_MENU, self.onToolsSwapData, id=ids.ID_toolsSwapData)

        self.menubar.Append(processing, "Processing")

        # sequence
        sequence = wx.Menu()
        sequence.Append(ids.ID_sequenceNew, "New...", "")
        sequence.Append(ids.ID_sequenceImport, "Import...", "")
        sequence.AppendSeparator()
        sequence.Append(ids.ID_sequenceEditor, "Edit sequence...", "")
        sequence.Append(ids.ID_sequenceModifications, "Edit Modifications...", "")
        sequence.AppendSeparator()
        sequence.Append(ids.ID_sequenceDigest, "Digest Protein...", "")
        sequence.Append(ids.ID_sequenceFragment, "Fragment Peptide...", "")
        sequence.Append(ids.ID_sequenceSearch, "Mass Search...", "")
        sequence.AppendSeparator()
        sequence.Append(ids.ID_sequenceSendToMassCalculator, "Show Isotopic Pattern...", "")
        sequence.Append(ids.ID_sequenceSendToEnvelopeFit, "Send to Envelope Fit...", "")
        sequence.AppendSeparator()
        sequence.Append(ids.ID_sequenceMatchesCalibrateBy, "Calibrate by Matches...", "")
        sequence.AppendSeparator()
        sequence.Append(ids.ID_sequenceMatchesDelete, "Delete All Matches", "")
        sequence.Append(ids.ID_sequenceDelete, "Delete Sequence", "")
        sequence.AppendSeparator()
        sequence.Append(ids.ID_sequenceSort, "Sort by Titles", "")

        self.Bind(wx.EVT_MENU, self.onSequenceNew, id=ids.ID_sequenceNew)
        self.Bind(wx.EVT_MENU, self.onSequenceImport, id=ids.ID_sequenceImport)
        self.Bind(wx.EVT_MENU, self.onToolsSequence, id=ids.ID_sequenceEditor)
        self.Bind(wx.EVT_MENU, self.onToolsSequence, id=ids.ID_sequenceModifications)
        self.Bind(wx.EVT_MENU, self.onToolsSequence, id=ids.ID_sequenceDigest)
        self.Bind(wx.EVT_MENU, self.onToolsSequence, id=ids.ID_sequenceFragment)
        self.Bind(wx.EVT_MENU, self.onToolsSequence, id=ids.ID_sequenceSearch)
        self.Bind(
            wx.EVT_MENU,
            self.onSequenceSendToMassCalculator,
            id=ids.ID_sequenceSendToMassCalculator,
        )
        self.Bind(
            wx.EVT_MENU,
            self.onSequenceSendToEnvelopeFit,
            id=ids.ID_sequenceSendToEnvelopeFit,
        )
        self.Bind(
            wx.EVT_MENU,
            self.onSequenceMatchesCalibrateBy,
            id=ids.ID_sequenceMatchesCalibrateBy,
        )
        self.Bind(
            wx.EVT_MENU, self.onSequenceMatchesDelete, id=ids.ID_sequenceMatchesDelete
        )
        self.Bind(wx.EVT_MENU, self.onSequenceDelete, id=ids.ID_sequenceDelete)
        self.Bind(wx.EVT_MENU, self.onSequenceSort, id=ids.ID_sequenceSort)

        self.menubar.Append(sequence, "Sequence")

        # tools
        tools = wx.Menu()
        tools.Append(ids.ID_toolsRuler, "Spectrum Ruler" + ids.HK_toolsRuler, "", wx.ITEM_RADIO)
        tools.Append(
            ids.ID_toolsLabelPeak, "Label Peak" + ids.HK_toolsLabelPeak, "", wx.ITEM_RADIO
        )
        tools.Append(
            ids.ID_toolsLabelPoint, "Label Point" + ids.HK_toolsLabelPoint, "", wx.ITEM_RADIO
        )
        tools.Append(
            ids.ID_toolsLabelEnvelope,
            "Label Envelope" + ids.HK_toolsLabelEnvelope,
            "",
            wx.ITEM_RADIO,
        )
        tools.Append(
            ids.ID_toolsDeleteLabel, "Delete Label" + ids.HK_toolsDeleteLabel, "", wx.ITEM_RADIO
        )
        tools.Append(ids.ID_toolsOffset, "Offset Spectrum", "", wx.ITEM_RADIO)
        tools.AppendSeparator()
        tools.Append(
            ids.ID_toolsPeriodicTable, "Periodic Table" + ids.HK_toolsPeriodicTable, ""
        )
        tools.Append(
            ids.ID_toolsMassCalculator, "Mass Calculator" + ids.HK_toolsMassCalculator, ""
        )
        tools.Append(
            ids.ID_toolsMassToFormula, "Mass to Formula" + ids.HK_toolsMassToFormula, ""
        )
        tools.Append(
            ids.ID_toolsMassDefectPlot, "Mass Defect Plot" + ids.HK_toolsMassDefectPlot, ""
        )
        tools.AppendSeparator()
        tools.Append(ids.ID_toolsMassFilter, "Mass Filter" + ids.HK_toolsMassFilter, "")
        tools.Append(
            ids.ID_toolsCompoundsSearch, "Compounds Search" + ids.HK_toolsCompoundsSearch, ""
        )
        tools.Append(
            ids.ID_toolsPeakDifferences, "Peak Differences" + ids.HK_toolsPeakDifferences, ""
        )
        tools.Append(
            ids.ID_toolsComparePeaklists,
            "Compare Peak Lists" + ids.HK_toolsComparePeaklists,
            "",
        )
        tools.Append(
            ids.ID_toolsSpectrumGenerator,
            "Spectrum Generator" + ids.HK_toolsSpectrumGenerator,
            "",
        )
        tools.AppendSeparator()
        tools.Append(ids.ID_toolsEnvelopeFit, "Envelope Fit" + ids.HK_toolsEnvelopeFit, "")
        tools.AppendSeparator()
        tools.Append(ids.ID_mascotPMF, "Mascot PMF", "")
        tools.Append(ids.ID_mascotMIS, "Mascot MS/MS Search", "")
        tools.Append(ids.ID_mascotSQ, "Mascot Sequence Query", "")
        tools.AppendSeparator()
        tools.Append(ids.ID_toolsProfound, "ProFound Search", "")
        tools.AppendSeparator()
        tools.Append(ids.ID_prospectorMSFit, "Protein Prospector MS-Fit", "")
        tools.Append(ids.ID_prospectorMSTag, "Protein Prospector MS-Tag", "")

        self.Bind(wx.EVT_MENU, self.onToolsSpectrum, id=ids.ID_toolsRuler)
        self.Bind(wx.EVT_MENU, self.onToolsSpectrum, id=ids.ID_toolsLabelPeak)
        self.Bind(wx.EVT_MENU, self.onToolsSpectrum, id=ids.ID_toolsLabelPoint)
        self.Bind(wx.EVT_MENU, self.onToolsSpectrum, id=ids.ID_toolsLabelEnvelope)
        self.Bind(wx.EVT_MENU, self.onToolsSpectrum, id=ids.ID_toolsDeleteLabel)
        self.Bind(wx.EVT_MENU, self.onToolsSpectrum, id=ids.ID_toolsOffset)
        self.Bind(wx.EVT_MENU, self.onToolsPeriodicTable, id=ids.ID_toolsPeriodicTable)
        self.Bind(wx.EVT_MENU, self.onToolsMassCalculator, id=ids.ID_toolsMassCalculator)
        self.Bind(wx.EVT_MENU, self.onToolsMassToFormula, id=ids.ID_toolsMassToFormula)
        self.Bind(wx.EVT_MENU, self.onToolsMassDefectPlot, id=ids.ID_toolsMassDefectPlot)
        self.Bind(wx.EVT_MENU, self.onToolsMassFilter, id=ids.ID_toolsMassFilter)
        self.Bind(wx.EVT_MENU, self.onToolsCompoundsSearch, id=ids.ID_toolsCompoundsSearch)
        self.Bind(wx.EVT_MENU, self.onToolsPeakDifferences, id=ids.ID_toolsPeakDifferences)
        self.Bind(
            wx.EVT_MENU, self.onToolsComparePeaklists, id=ids.ID_toolsComparePeaklists
        )
        self.Bind(
            wx.EVT_MENU, self.onToolsSpectrumGenerator, id=ids.ID_toolsSpectrumGenerator
        )
        self.Bind(wx.EVT_MENU, self.onToolsEnvelopeFit, id=ids.ID_toolsEnvelopeFit)
        self.Bind(wx.EVT_MENU, self.onToolsMascot, id=ids.ID_mascotPMF)
        self.Bind(wx.EVT_MENU, self.onToolsMascot, id=ids.ID_mascotMIS)
        self.Bind(wx.EVT_MENU, self.onToolsMascot, id=ids.ID_mascotSQ)
        self.Bind(wx.EVT_MENU, self.onToolsProfound, id=ids.ID_toolsProfound)
        self.Bind(wx.EVT_MENU, self.onToolsProspector, id=ids.ID_prospectorMSFit)
        self.Bind(wx.EVT_MENU, self.onToolsProspector, id=ids.ID_prospectorMSTag)

        self.menubar.Append(tools, "Tools")

        self.menubar.Check(ids.ID_toolsRuler, True)

        # libraries
        libraries = wx.Menu()
        libraries.Append(ids.ID_libraryCompounds, "Compounds...", "")
        libraries.Append(ids.ID_libraryModifications, "Modifications...", "")
        libraries.Append(ids.ID_libraryMonomers, "Monomers...", "")
        libraries.Append(ids.ID_libraryEnzymes, "Enzymes...", "")
        libraries.Append(ids.ID_libraryReferences, "Reference Masses...", "")
        libraries.Append(ids.ID_libraryMascot, "Mascot Servers...", "")
        libraries.AppendSeparator()
        libraries.Append(ids.ID_libraryPresets, "Presets...", "")

        self.Bind(wx.EVT_MENU, self.onLibraryEdit, id=ids.ID_libraryCompounds)
        self.Bind(wx.EVT_MENU, self.onLibraryEdit, id=ids.ID_libraryModifications)
        self.Bind(wx.EVT_MENU, self.onLibraryEdit, id=ids.ID_libraryMonomers)
        self.Bind(wx.EVT_MENU, self.onLibraryEdit, id=ids.ID_libraryEnzymes)
        self.Bind(wx.EVT_MENU, self.onLibraryEdit, id=ids.ID_libraryReferences)
        self.Bind(wx.EVT_MENU, self.onLibraryEdit, id=ids.ID_libraryMascot)
        self.Bind(wx.EVT_MENU, self.onLibraryEdit, id=ids.ID_libraryPresets)

        self.menubar.Append(libraries, "Libraries")

        # links
        links = wx.Menu()

        linksMSTools = wx.Menu()
        linksMSTools.Append(ids.ID_linksExpasy, "ExPASy", "")
        linksMSTools.Append(ids.ID_linksMatrixScience, "Matrix Science", "")
        linksMSTools.Append(ids.ID_linksProspector, "Protein Prospector", "")
        linksMSTools.Append(ids.ID_linksProfound, "ProFound", "")
        linksMSTools.Append(ids.ID_linksBiomedMSTools, "Biomed MS Tools", "")
        links.Append(-1, "MS Tools", linksMSTools)

        linksModifications = wx.Menu()
        linksModifications.Append(ids.ID_linksUniMod, "UniMod", "")
        linksModifications.Append(ids.ID_linksDeltaMass, "Delta Mass", "")
        links.Append(-1, "Modifications", linksModifications)

        linksSequenceDB = wx.Menu()
        linksSequenceDB.Append(ids.ID_linksUniProt, "UniProt", "")
        linksSequenceDB.Append(ids.ID_linksExpasy, "ExPASy", "")
        linksSequenceDB.Append(ids.ID_linksEMBLEBI, "EMBL EBI", "")
        linksSequenceDB.Append(ids.ID_linksPIR, "PIR", "")
        linksSequenceDB.Append(ids.ID_linksNCBI, "NCBI", "")
        links.Append(-1, "Sequence Databases", linksSequenceDB)

        linksSequenceTools = wx.Menu()
        linksSequenceTools.Append(ids.ID_linksBLAST, "BLAST", "")
        linksSequenceTools.Append(ids.ID_linksClustalW, "ClustalW", "")
        linksSequenceTools.Append(ids.ID_linksFASTA, "FASTA", "")
        linksSequenceTools.Append(ids.ID_linksMUSCLE, "MUSCLE", "")
        links.Append(-1, "Sequence Tools", linksSequenceTools)

        linksStructures = wx.Menu()
        linksStructures.Append(ids.ID_linksPDB, "RCSB PDB", "")
        links.Append(-1, "Protein Structures", linksStructures)

        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksExpasy)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksMatrixScience)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksProspector)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksProfound)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksBiomedMSTools)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksUniMod)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksDeltaMass)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksUniProt)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksExpasy)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksEMBLEBI)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksPIR)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksNCBI)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksBLAST)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksClustalW)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksFASTA)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksMUSCLE)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_linksPDB)

        self.menubar.Append(links, "Links")

        # window
        window = wx.Menu()
        if wx.Platform != "__WXMAC__":
            window.Append(ids.ID_windowMaximize, "Maximize", "")
            window.Append(ids.ID_windowMinimize, "Minimize", "")
            window.AppendSeparator()

        window.Append(ids.ID_windowLayout1, "Default" + ids.HK_windowLayout1, "", wx.ITEM_RADIO)
        window.Append(
            ids.ID_windowLayout2, "Documents Bottom" + ids.HK_windowLayout2, "", wx.ITEM_RADIO
        )
        window.Append(
            ids.ID_windowLayout3, "Peaklist Bottom" + ids.HK_windowLayout3, "", wx.ITEM_RADIO
        )
        window.Append(
            ids.ID_windowLayout4, "Wide Spectrum" + ids.HK_windowLayout4, "", wx.ITEM_RADIO
        )

        self.Bind(wx.EVT_MENU, self.onWindowMaximize, id=ids.ID_windowMaximize)
        self.Bind(wx.EVT_MENU, self.onWindowIconize, id=ids.ID_windowMinimize)
        self.Bind(wx.EVT_MENU, self.onWindowLayout, id=ids.ID_windowLayout1)
        self.Bind(wx.EVT_MENU, self.onWindowLayout, id=ids.ID_windowLayout2)
        self.Bind(wx.EVT_MENU, self.onWindowLayout, id=ids.ID_windowLayout3)
        self.Bind(wx.EVT_MENU, self.onWindowLayout, id=ids.ID_windowLayout4)

        self.menubar.Append(window, "&Window")

        # help
        help = wx.Menu()
        help.Append(ids.ID_helpUserGuide, "User's Guide..." + ids.HK_helpUserGuide, "")
        help.AppendSeparator()
        help.Append(ids.ID_helpHomepage, "Homepage...", "")
        help.Append(ids.ID_helpForum, "Support Forum...", "")
        help.Append(ids.ID_helpTwitter, "Twitter Account...", "")
        help.AppendSeparator()
        help.Append(ids.ID_helpCite, "Papers to Cite...", "")
        help.Append(ids.ID_helpDonate, "Make a Donation...", "")
        help.AppendSeparator()
        help.Append(ids.ID_helpUpdate, "Check for Update", "")
        if wx.Platform != "__WXMAC__":
            help.AppendSeparator()
        help.Append(ids.ID_helpAbout, "About mMass", "")

        self.Bind(wx.EVT_MENU, self.onHelpUserGuide, id=ids.ID_helpUserGuide)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_helpHomepage)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_helpForum)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_helpTwitter)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_helpCite)
        self.Bind(wx.EVT_MENU, self.onLibraryLink, id=ids.ID_helpDonate)
        self.Bind(wx.EVT_MENU, self.onHelpUpdate, id=ids.ID_helpUpdate)
        self.Bind(wx.EVT_MENU, self.onHelpAbout, id=ids.ID_helpAbout)

        self.menubar.Append(help, "&Help")

    # ----

    def makeToolbar(self) -> None:
        """Make main application toolbar."""
        # init toolbar
        self.toolbar = self.CreateToolBar(mwx.MAIN_TOOLBAR_STYLE)
        self.toolbar.SetToolBitmapSize(mwx.MAIN_TOOLBAR_TOOLSIZE)
        self.toolbar.SetFont(wx.SMALL_FONT)

        # document
        if wx.Platform != "__WXMAC__":
            self.toolbar.AddTool(
                ids.ID_documentOpen,
                "Open",
                images.lib["toolsOpen"],
                shortHelp="Open document...",
            )
            self.toolbar.AddTool(
                ids.ID_documentSave,
                "Save",
                images.lib["toolsSave"],
                shortHelp="Save document",
            )
            self.toolbar.AddTool(
                ids.ID_documentPrintSpectrum,
                "Print",
                images.lib["toolsPrint"],
                shortHelp="Print spectrum...",
            )

            self.toolbar.Bind(wx.EVT_TOOL, self.onDocumentOpen, id=ids.ID_documentOpen)
            self.toolbar.Bind(wx.EVT_TOOL, self.onDocumentSave, id=ids.ID_documentSave)
            self.toolbar.Bind(
                wx.EVT_TOOL, self.onDocumentPrintSpectrum, id=ids.ID_documentPrintSpectrum
            )

            self.toolbar.AddSeparator()

        # tools
        self.toolbar.AddTool(
            ids.ID_toolsProcessing,
            "Processing",
            images.lib["toolsProcessing"],
            shortHelp="Data processing...",
        )
        self.toolbar.AddTool(
            ids.ID_toolsCalibration,
            "Calibration",
            images.lib["toolsCalibration"],
            shortHelp="Re-calibrate data...",
        )

        if wx.Platform != "__WXMAC__":
            self.toolbar.AddSeparator()

        self.toolbar.AddTool(
            ids.ID_toolsSequence,
            "Sequence",
            images.lib["toolsSequence"],
            shortHelp="Sequence editor...",
        )

        if wx.Platform != "__WXMAC__":
            self.toolbar.AddSeparator()

        self.toolbar.AddTool(
            ids.ID_toolsPeriodicTable,
            "Elements",
            images.lib["toolsPeriodicTable"],
            shortHelp="Periodic Table...",
        )
        self.toolbar.AddTool(
            ids.ID_toolsMassCalculator,
            "Masscalc",
            images.lib["toolsMassCalculator"],
            shortHelp="Mass calculator...",
        )
        self.toolbar.AddTool(
            ids.ID_toolsMassToFormula,
            "Formulator",
            images.lib["toolsMassToFormula"],
            shortHelp="Mass to formula...",
        )
        self.toolbar.AddTool(
            ids.ID_toolsMassDefectPlot,
            "Mass Defect",
            images.lib["toolsMassDefectPlot"],
            shortHelp="Mass defect plot...",
        )

        if wx.Platform != "__WXMAC__":
            self.toolbar.AddSeparator()

        self.toolbar.AddTool(
            ids.ID_toolsMassFilter,
            "Mass Filter",
            images.lib["toolsMassFilter"],
            shortHelp="Mass filter...",
        )
        self.toolbar.AddTool(
            ids.ID_toolsCompoundsSearch,
            "Compounds",
            images.lib["toolsCompoundsSearch"],
            shortHelp="Compounds search...",
        )
        self.toolbar.AddTool(
            ids.ID_toolsPeakDifferences,
            "Differences",
            images.lib["toolsPeakDifferences"],
            shortHelp="Peak differences...",
        )
        self.toolbar.AddTool(
            ids.ID_toolsComparePeaklists,
            "Compare",
            images.lib["toolsComparePeaklists"],
            shortHelp="Compare peak lists...",
        )
        self.toolbar.AddTool(
            ids.ID_toolsSpectrumGenerator,
            "Generator",
            images.lib["toolsSpectrumGenerator"],
            shortHelp="Generate mass spectrum...",
        )
        self.toolbar.AddTool(
            ids.ID_toolsEnvelopeFit,
            "Envelope Fit",
            images.lib["toolsEnvelopeFit"],
            shortHelp="Calculate atom exchange...",
        )

        if wx.Platform != "__WXMAC__":
            self.toolbar.AddSeparator()

        self.toolbar.AddTool(
            ids.ID_toolsMascot,
            "Mascot",
            images.lib["toolsMascot"],
            shortHelp="Mascot search...",
        )
        self.toolbar.AddTool(
            ids.ID_toolsProfound,
            "ProFound",
            images.lib["toolsProfound"],
            shortHelp="ProFound search...",
        )

        self.toolbar.Bind(wx.EVT_TOOL, self.onToolsProcessing, id=ids.ID_toolsProcessing)
        self.toolbar.Bind(wx.EVT_TOOL, self.onToolsCalibration, id=ids.ID_toolsCalibration)
        self.toolbar.Bind(wx.EVT_TOOL, self.onToolsSequence, id=ids.ID_toolsSequence)
        self.toolbar.Bind(
            wx.EVT_TOOL, self.onToolsPeriodicTable, id=ids.ID_toolsPeriodicTable
        )
        self.toolbar.Bind(
            wx.EVT_TOOL, self.onToolsMassCalculator, id=ids.ID_toolsMassCalculator
        )
        self.toolbar.Bind(
            wx.EVT_TOOL, self.onToolsMassToFormula, id=ids.ID_toolsMassToFormula
        )
        self.toolbar.Bind(
            wx.EVT_TOOL, self.onToolsMassDefectPlot, id=ids.ID_toolsMassDefectPlot
        )
        self.toolbar.Bind(wx.EVT_TOOL, self.onToolsMassFilter, id=ids.ID_toolsMassFilter)
        self.toolbar.Bind(
            wx.EVT_TOOL, self.onToolsCompoundsSearch, id=ids.ID_toolsCompoundsSearch
        )
        self.toolbar.Bind(
            wx.EVT_TOOL, self.onToolsPeakDifferences, id=ids.ID_toolsPeakDifferences
        )
        self.toolbar.Bind(
            wx.EVT_TOOL, self.onToolsComparePeaklists, id=ids.ID_toolsComparePeaklists
        )
        self.toolbar.Bind(
            wx.EVT_TOOL, self.onToolsSpectrumGenerator, id=ids.ID_toolsSpectrumGenerator
        )
        self.toolbar.Bind(wx.EVT_TOOL, self.onToolsEnvelopeFit, id=ids.ID_toolsEnvelopeFit)
        self.toolbar.Bind(wx.EVT_TOOL, self.onToolsMascot, id=ids.ID_toolsMascot)
        self.toolbar.Bind(wx.EVT_TOOL, self.onToolsProfound, id=ids.ID_toolsProfound)

        if wx.Platform != "__WXMAC__":
            self.toolbar.AddSeparator()

        self.toolbar.AddTool(
            ids.ID_toolsDocumentInfo,
            "Notes",
            images.lib["toolsDocumentInfo"],
            shortHelp="Document information and notes...",
        )
        self.toolbar.AddTool(
            ids.ID_toolsDocumentReport,
            "Report",
            images.lib["toolsDocumentReport"],
            shortHelp="Analysis report",
        )
        self.toolbar.AddTool(
            ids.ID_toolsDocumentExport,
            "Export",
            images.lib["toolsDocumentExport"],
            shortHelp="Export data...",
        )

        self.toolbar.Bind(wx.EVT_TOOL, self.onDocumentInfo, id=ids.ID_toolsDocumentInfo)
        self.toolbar.Bind(wx.EVT_TOOL, self.onDocumentReport, id=ids.ID_toolsDocumentReport)
        self.toolbar.Bind(wx.EVT_TOOL, self.onDocumentExport, id=ids.ID_toolsDocumentExport)

    # ----

    def makeGUI(self) -> None:
        """Init all gui elements."""
        # make documents panel
        self.documentsPanel = PanelDocuments(self, self.documents)

        # make spectrum panel
        self.spectrumPanel = PanelSpectrum(self, self.documents)

        # make peaklist panel
        self.peaklistPanel = PanelPeaklist(self)

        # init other tools
        self.processingPanel = None
        self.calibrationPanel = None
        self.periodicTablePanel = None
        self.massCalculatorPanel = None
        self.massToFormulaPanel = None
        self.massDefectPlotPanel = None
        self.massFilterPanel = None
        self.compoundsSearchPanel = None
        self.peakDifferencesPanel = None
        self.comparePeaklistsPanel = None
        self.spectrumGeneratorPanel = None
        self.envelopeFitPanel = None
        self.sequencePanel = None
        self.mascotPanel = None
        self.profoundPanel = None
        self.prospectorPanel = None
        self.documentInfoPanel = None
        self.documentExportPanel = None

        # manage frames
        self.AUIManager = wx.aui.AuiManager()
        self.AUIManager.SetManagedWindow(self)
        self.AUIManager.SetDockSizeConstraint(0.5, 0.5)

        self.AUIManager.AddPane(
            self.documentsPanel,
            wx.aui.AuiPaneInfo()
            .Name("documents")
            .Left()
            .MinSize((195, 100))
            .Caption("Opened Documents")
            .CaptionVisible(False)
            .Gripper(config.main["unlockGUI"])
            .GripperTop(True)
            .CloseButton(False)
            .PaneBorder(False),
        )

        self.AUIManager.AddPane(
            self.spectrumPanel,
            wx.aui.AuiPaneInfo()
            .Name("plot")
            .CentrePane()
            .MinSize((300, 100))
            .Caption("Spectrum Viewer")
            .CaptionVisible(False)
            .CloseButton(False)
            .PaneBorder(False),
        )

        self.AUIManager.AddPane(
            self.peaklistPanel,
            wx.aui.AuiPaneInfo()
            .Name("peaklist")
            .Right()
            .MinSize((195, 100))
            .Caption("Current Peak List")
            .CaptionVisible(False)
            .Gripper(config.main["unlockGUI"])
            .GripperTop(True)
            .CloseButton(False)
            .PaneBorder(False),
        )

        # show panels
        self.documentsPanel.Show(True)
        self.spectrumPanel.Show(True)
        self.peaklistPanel.Show(True)

        # set frame manager properties
        artProvider = self.AUIManager.GetArtProvider()
        artProvider.SetColour(
            wx.aui.AUI_DOCKART_SASH_COLOUR, self.documentsPanel.GetBackgroundColour()
        )
        artProvider.SetColour(
            wx.aui.AUI_DOCKART_INACTIVE_CAPTION_COLOUR,
            self.documentsPanel.GetBackgroundColour(),
        )
        artProvider.SetMetric(wx.aui.AUI_DOCKART_SASH_SIZE, mwx.SASH_SIZE)
        artProvider.SetMetric(wx.aui.AUI_DOCKART_GRIPPER_SIZE, mwx.GRIPPER_SIZE)
        if mwx.SASH_COLOUR:
            self.SetOwnBackgroundColour(mwx.SASH_COLOUR)
            artProvider.SetColour(wx.aui.AUI_DOCKART_SASH_COLOUR, mwx.SASH_COLOUR)

        # set last layout
        self.onWindowLayout(layout=config.main["layout"])

    # ----

    # COMMON EVENTS

    def onQuit(self, evt) -> None:
        """Close all documents and quit application."""
        # close all documents
        if not self.onDocumentCloseAll():
            return

        # save panels' sizes
        config.main["documentsWidth"], config.main["documentsHeight"] = (
            self.documentsPanel.GetSize()
        )
        config.main["peaklistWidth"], config.main["peaklistHeight"] = (
            self.peaklistPanel.GetSize()
        )

        # save config
        config.saveConfig()

        # quit application
        evt.Skip()
        self.Destroy()

    # ----

    def onSize(self, evt) -> None:
        """Remember application frame size."""
        # get frame size
        config.main["appMaximized"] = int(self.IsMaximized())
        if not self.IsMaximized():
            size = self.GetSize()
            config.main["appWidth"] = size[0]
            config.main["appHeight"] = size[1]

        evt.Skip()

    # ----

    def onError(self, type, value, tb) -> None:
        """Catch exception and show error report."""
        # get exception
        exception = traceback.format_exception(type, value, tb)
        exception = "\n".join(exception)

        # show error message
        wx.Bell()
        dlg = DlgError(self, exception)
        dlg.ShowModal()
        dlg.Destroy()

    # ----

    def onPreferences(self, evt) -> None:
        """Show mMass preferences."""
        dlg = DlgPreferences(self)
        dlg.ShowModal()
        dlg.Destroy()

    # ----

    def onServerCommand(self, command) -> None:
        """Process command from TCP server."""
        # strip command
        command = command.strip()

        # close app
        if command.lower() in ["exit", "quit"]:
            wx.CallAfter(self.Close)
            return

        # open document
        if command and command not in ["mmass.exe", "mmass.py"]:
            wx.CallAfter(self.onDocumentOpen, None, command)
            return

    # ----

    # DOCUMENT

    def onDocumentLoaded(self, select=True) -> None:
        """Update GUI after document loaded."""
        # clear visibility history
        self.documentsSoloCurrent = None
        self.documentsSoloPrevious = {}

        # append document
        self.spectrumPanel.appendLastSpectrum()
        self.documentsPanel.appendLastDocument()

        # select document
        if select:
            self.documentsPanel.selectDocument(-1)

        # update compare panel
        if self.comparePeaklistsPanel:
            self.comparePeaklistsPanel.setData(self.documents)

        # update processing panel
        if self.processingPanel:
            self.processingPanel.updateAvailableDocuments()

        # update mass defect plot panel
        if self.massDefectPlotPanel:
            self.massDefectPlotPanel.updateDocuments()

    # ----

    def onDocumentSelected(self, docIndex) -> None:
        """Set current document."""
        # get document and application title
        if docIndex is not None:
            docData = self.documents[docIndex]
            title = f"mMass - {docData.title}"
            if docData.dirty:
                title += " *"
        else:
            docData = None
            title = "mMass"

        # update app title
        self.SetTitle(title)

        # update panels
        if docIndex != self.currentDocument:
            # set current document
            self.currentDocument = docIndex
            self.currentSequence = None

            # update spectrum panel
            self.spectrumPanel.selectSpectrum(docIndex, refresh=False)

            # update peaklist panel
            self.peaklistPanel.setData(docData)

            # update processing panel
            if self.processingPanel:
                self.processingPanel.setData(docData)

            # update calibration panel
            if self.calibrationPanel:
                self.calibrationPanel.setData(docData)

            # update mass to formula panel
            if self.massToFormulaPanel:
                self.massToFormulaPanel.setData(docData)

            # update mass defect plot panel
            if self.massDefectPlotPanel:
                self.massDefectPlotPanel.setData(docData)

            # update mass filter panel
            if self.massFilterPanel:
                self.massFilterPanel.setData(docData)

            # update compounds panel
            if self.compoundsSearchPanel:
                self.compoundsSearchPanel.setData(docData)

            # update differences panel
            if self.peakDifferencesPanel:
                self.peakDifferencesPanel.setData(docData)

            # update spectrum generator panel
            if self.spectrumGeneratorPanel:
                self.spectrumGeneratorPanel.setData(docData)

            # update envelope fit panel
            if self.envelopeFitPanel:
                self.envelopeFitPanel.setData(docData)

            # update sequence panel
            if self.sequencePanel:
                self.sequencePanel.setData(None)

            # update mascot panel
            if self.mascotPanel:
                self.mascotPanel.setData(docData)

            # update profound panel
            if self.profoundPanel:
                self.profoundPanel.setData(docData)

            # update prospector panel
            if self.prospectorPanel:
                self.prospectorPanel.setData(docData)

            # update document info panel
            if self.documentInfoPanel:
                self.documentInfoPanel.setData(docData)

            # update menubar and toolbar
            self.updateControls()

    # ----

    def onDocumentChanged(self, items=()) -> None:
        """Document content has changed."""
        # check selection
        if self.currentDocument is None:
            return

        # update spectrum panel
        if "spectrum" in items:
            self.spectrumPanel.updateSpectrum(self.currentDocument)

        # update peaklist panel
        if "spectrum" in items:
            self.peaklistPanel.updatePeakList()

        # update title-dependent panels
        if "doctitle" in items:
            self.spectrumPanel.updateSpectrumProperties(self.currentDocument)

            # update processing panel
            if self.processingPanel:
                self.processingPanel.updateAvailableDocuments()

        # update documents panel
        if "notations" in items:
            self.documentsPanel.updateAnnotations(self.currentDocument)
            for seqIndex in range(len(self.documents[self.currentDocument].sequences)):
                self.documentsPanel.updateSequenceMatches(
                    self.currentDocument, seqIndex
                )
        if "annotations" in items:
            self.documentsPanel.updateAnnotations(self.currentDocument, expand=True)
        if "sequences" in items:
            self.documentsPanel.updateSequences(self.currentDocument)
        if "seqtitle" in items:
            self.documentsPanel.updateSequenceTitle(
                self.currentDocument, self.currentSequence
            )
        if "matches" in items:
            self.documentsPanel.updateSequenceMatches(
                self.currentDocument, self.currentSequence, expand=True
            )

        # update notation marks
        if (
            "notations" in items
            or "annotations" in items
            or "sequences" in items
            or "matches" in items
        ):
            self.updateNotationMarks()

        # update data-dependent panels
        if "spectrum" in items:
            docData = self.documents[self.currentDocument]

            # update document info panel
            if self.documentInfoPanel:
                self.documentInfoPanel.setData(docData)

            # update mascot panel
            if self.mascotPanel:
                self.mascotPanel.setData(docData)

            # update profound panel
            if self.profoundPanel:
                self.profoundPanel.setData(docData)

            # update prospector panel
            if self.prospectorPanel:
                self.prospectorPanel.setData(docData)

            # update differences panel
            if self.peakDifferencesPanel:
                self.peakDifferencesPanel.setData(docData)

            # update spectrum generator panel
            if self.spectrumGeneratorPanel:
                self.spectrumGeneratorPanel.setData(docData)

            # update envelope fit panel
            if self.envelopeFitPanel:
                self.envelopeFitPanel.setData(docData)

            # update mass defect plot panel
            if self.massDefectPlotPanel:
                self.massDefectPlotPanel.setData(docData)

            # update sequence panel
            if self.sequencePanel:
                self.sequencePanel.clearMatches()

            # update compounds panel
            if self.compoundsSearchPanel:
                self.compoundsSearchPanel.clearMatches()

            # update mass filter panel
            if self.massFilterPanel:
                self.massFilterPanel.clearMatches()

        # update compare peaklists tool
        if (
            "spectrum" in items
            or "notations" in items
            or "annotations" in items
            or "sequences" in items
            or "matches" in items
        ) and self.comparePeaklistsPanel:
            self.comparePeaklistsPanel.setData(self.documents)

        # disable undo
        if "sequence" in items:
            self.documents[self.currentDocument].backup(None)

        # set document status
        self.documents[self.currentDocument].dirty = True
        self.documentsPanel.updateDocumentTitle(self.currentDocument)

        # update app title
        title = f"mMass - {self.documents[self.currentDocument].title} *"
        self.SetTitle(title)

        # update controls
        self.updateControls()

    # ----

    def onDocumentChangedMulti(self, indexes=None, items=()) -> None:
        """Multiple documents content has changed (not all changes are covered!!!)."""
        # check selection
        if indexes is None:
            indexes = []
        if not indexes:
            return

        # set documents dirty
        for docIndex in indexes:
            self.documents[docIndex].dirty = True
            self.documentsPanel.updateDocumentTitle(docIndex)

        # update spectrum panel
        if "spectrum" in items:
            for docIndex in indexes:
                self.spectrumPanel.updateSpectrum(docIndex, refresh=False)

        # update documents panel
        if "notations" in items or "annotations" in items:
            for docIndex in indexes:
                self.documentsPanel.updateAnnotations(docIndex)
        if "notations" in items or "matches" in items:
            for docIndex in indexes:
                for seqIndex in range(len(self.documents[docIndex].sequences)):
                    self.documentsPanel.updateSequenceMatches(docIndex, seqIndex)

        # update compare peaklists panel
        if self.comparePeaklistsPanel:
            self.comparePeaklistsPanel.setData(self.documents)

        # update current document
        if self.currentDocument in indexes:
            docData = self.documents[self.currentDocument]

            # update peaklist panel
            self.peaklistPanel.updatePeakList()

            # update document info panel
            if self.documentInfoPanel:
                self.documentInfoPanel.setData(docData)

            # update mascot panel
            if self.mascotPanel:
                self.mascotPanel.setData(docData)

            # update profound panel
            if self.profoundPanel:
                self.profoundPanel.setData(docData)

            # update prospector panel
            if self.prospectorPanel:
                self.prospectorPanel.setData(docData)

            # update differences panel
            if self.peakDifferencesPanel:
                self.peakDifferencesPanel.setData(docData)

            # update spectrum generator panel
            if self.spectrumGeneratorPanel:
                self.spectrumGeneratorPanel.setData(docData)

            # update envelope fit panel
            if self.envelopeFitPanel:
                self.envelopeFitPanel.setData(docData)

            # update mass defect plot panel
            if self.massDefectPlotPanel:
                self.massDefectPlotPanel.setData(docData)

            # update sequence panel
            if self.sequencePanel:
                self.sequencePanel.clearMatches()

            # update compounds panel
            if self.compoundsSearchPanel:
                self.compoundsSearchPanel.clearMatches()

            # update mass filter panel
            if self.massFilterPanel:
                self.massFilterPanel.clearMatches()

            # update notation marks
            self.updateNotationMarks(refresh=False)

            # update app title
            title = f"mMass - {self.documents[self.currentDocument].title} *"
            self.SetTitle(title)

            # update controls
            self.updateControls()

        # update spectrum
        self.spectrumPanel.refresh()

    # ----

    def onDocumentNew(self, evt=None, document=None, select=True) -> None:
        """Create blank document."""
        # make document
        if document is None:
            document = doc.Document()
            document.title = "Blank Document"

        # set colour
        document.colour = self.getFreeColour()

        # append document
        self.documents.append(document)

        # update gui
        self.onDocumentLoaded(select)

    # ----

    def onDocumentNewFromClipboard(self, evt=None) -> None:
        """Make new document from clipboard data."""
        # get data from clipboard
        success = False
        data = wx.TextDataObject()
        if wx.TheClipboard.Open():
            success = wx.TheClipboard.GetData(data)
            wx.TheClipboard.Close()
        if not success:
            wx.Bell()
            return

        # get raw data
        rawData = data.GetText()
        if not rawData:
            wx.Bell()
            return

        # parse clipboard data
        while not self.importDocumentFromClipboard(rawData, dataType="profile"):
            dlg = DlgClipboardEditor(self, rawData)
            if dlg.ShowModal() == wx.ID_OK:
                rawData = dlg.data
                dlg.Destroy()
            else:
                dlg.Destroy()
                return

    # ----

    def onDocumentDuplicate(self, evt=None) -> bool | None:
        """Duplicate selected document."""
        # check document
        if self.currentDocument is None:
            wx.Bell()
            return False

        # get selected document
        docData = copy.deepcopy(self.documents[self.currentDocument])

        # update document
        docData.format = "mSD"
        docData.path = ""
        docData.dirty = True

        # append new document
        self.onDocumentNew(document=docData)
        return None

    # ----

    def onDocumentOpen(self, evt=None, path=None) -> None:
        """Open document."""
        # add path to queue
        if path:
            self.tmpDocumentQueue.append(path)

        # open dialog if no path specified
        else:
            lastDir = ""
            if Path(config.main["lastDir"]).exists():
                lastDir = config.main["lastDir"]
            wildcard = "All supported formats|fid;*.msd;*.baf;*.yep;*.mzData;*.mzdata*;*.mzXML;*.mzxml;*.mzML;*.mzml;*.xml;*.XML;*.mgf;*.MGF;*.txt;*.xy;*.asc|All files|*.*"
            dlg = wx.FileDialog(
                self,
                "Open Document",
                lastDir,
                "",
                wildcard=wildcard,
                style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST,
            )
            if dlg.ShowModal() == wx.ID_OK:
                paths = dlg.GetPaths()
                dlg.Destroy()
                self.tmpDocumentQueue += list(paths)
            else:
                dlg.Destroy()
                return

        # import documents in queue
        self.importDocumentQueue()

    # ----

    def onDocumentDropped(self, evt=None, paths=None) -> None:
        """Open dropped documents."""
        # get paths
        if evt is not None:
            paths = evt.GetFiles()

        # open documents
        if paths:
            self.tmpDocumentQueue += list(paths)
            wx.CallAfter(self.importDocumentQueue)

    # ----

    def onDocumentRecent(self, evt) -> None:
        """Open recent document."""
        # get index
        indexes = {
            ids.ID_documentRecent0: 0,
            ids.ID_documentRecent1: 1,
            ids.ID_documentRecent2: 2,
            ids.ID_documentRecent3: 3,
            ids.ID_documentRecent4: 4,
            ids.ID_documentRecent5: 5,
            ids.ID_documentRecent6: 6,
            ids.ID_documentRecent7: 7,
            ids.ID_documentRecent8: 8,
            ids.ID_documentRecent9: 9,
        }

        # open file
        self.onDocumentOpen(path=config.recent[indexes[evt.GetId()]])

    # ----

    def onDocumentClearRecent(self, evt) -> None:
        """Clear recent items."""
        del config.recent[:]
        self.updateRecentFiles()

    # ----

    def onDocumentClose(
        self, evt=None, docIndex=None, review=True, selectPrevious=True
    ) -> bool:
        """Close current document."""
        # check document
        if docIndex is None:
            docIndex = self.currentDocument
        if docIndex is None:
            wx.Bell()
            return False

        # save unsaved document
        if review and self.documents[docIndex].dirty:
            # ensure selected
            if docIndex != self.currentDocument:
                if not self.documents[docIndex].visible:
                    self.onDocumentEnable(docIndex)
                self.documentsPanel.selectDocument(docIndex)

            # ask to save
            title = f'Do you want to save the changes you made in\nthe document "{self.documents[docIndex].title}"?'
            message = "Your changes will be lost if you don't save them."
            buttons = [
                (ids.ID_dlgDontSave, "Don't Save", 120, False, 40),
                (ids.ID_dlgCancel, "Cancel", 80, False, 15),
                (ids.ID_dlgSave, "Save", 80, True, 0),
            ]
            dlg = mwx.DlgMessage(self, title, message, buttons)
            ID = dlg.ShowModal()
            if ids.ID_dlgDontSave == ID:
                pass
            elif ids.ID_dlgSave == ID:
                if not self.onDocumentSave():
                    return False
            else:
                return False

        # unblock colour
        colour = self.documents[docIndex].colour
        if colour in self.usedColours:
            del self.usedColours[self.usedColours.index(colour)]

        # clear visibility history
        self.documentsSoloCurrent = None
        self.documentsSoloPrevious = {}

        # delete document
        self.documentsPanel.selectDocument(None)
        self.documentsPanel.deleteDocument(docIndex)
        self.spectrumPanel.deleteSpectrum(docIndex)
        del self.documents[docIndex]

        # select previous visible document
        if selectPrevious:
            while docIndex > 0:
                docIndex -= 1
                if self.documents[docIndex].visible:
                    self.documentsPanel.selectDocument(docIndex)
                    break

        # update compare panel
        if self.comparePeaklistsPanel:
            self.comparePeaklistsPanel.setData(self.documents)

        # update processing panel
        if self.processingPanel:
            self.processingPanel.updateAvailableDocuments()

        # update mass defect plot panel
        if self.massDefectPlotPanel:
            self.massDefectPlotPanel.updateDocuments()

        # update menubar and toolbar
        self.updateControls()

        # unchanged or saved document
        return True

    # ----

    def onDocumentCloseAll(self, evt=None) -> bool:
        """Close all documents."""
        # close panels
        if self.processingPanel:
            self.processingPanel.Close()
        if self.calibrationPanel:
            self.calibrationPanel.Close()
        if self.periodicTablePanel:
            self.periodicTablePanel.Close()
        if self.massCalculatorPanel:
            self.massCalculatorPanel.Close()
        if self.massToFormulaPanel:
            self.massToFormulaPanel.Close()
        if self.massDefectPlotPanel:
            self.massDefectPlotPanel.Close()
        if self.massFilterPanel:
            self.massFilterPanel.Close()
        if self.compoundsSearchPanel:
            self.compoundsSearchPanel.Close()
        if self.peakDifferencesPanel:
            self.peakDifferencesPanel.Close()
        if self.comparePeaklistsPanel:
            self.comparePeaklistsPanel.Close()
        if self.spectrumGeneratorPanel:
            self.spectrumGeneratorPanel.Close()
        if self.envelopeFitPanel:
            self.envelopeFitPanel.Close()
        if self.sequencePanel:
            self.sequencePanel.Close()
        if self.mascotPanel:
            self.mascotPanel.Close()
        if self.profoundPanel:
            self.profoundPanel.Close()
        if self.prospectorPanel:
            self.prospectorPanel.Close()
        if self.documentInfoPanel:
            self.documentInfoPanel.Close()
        if self.documentExportPanel:
            self.documentExportPanel.Close()

        # get number of unsaved documents
        count = 0
        for document in self.documents:
            if document.dirty:
                count += 1

        # save unsaved documents
        review = True
        if count > 1:
            title = (
                f"You have {count} mMass documents with unsaved changes. Do you\nwant to review these changes before quitting?"
            )
            message = (
                "If you don't review your documents, all your changes will be lost."
            )
            buttons = [
                (ids.ID_dlgDiscard, "Discard Changes", 150, False, 40),
                (ids.ID_dlgCancel, "Cancel", 80, False, 15),
                (ids.ID_dlgReview, "Review Changes...", 160, True, 0),
            ]
            dlg = mwx.DlgMessage(self, title, message, buttons)
            ID = dlg.ShowModal()
            if ids.ID_dlgDiscard == ID:
                review = False
            elif ids.ID_dlgReview == ID:
                review = True
            else:
                return False

        # close documents
        while self.documents:
            docIndex = len(self.documents) - 1
            if not self.onDocumentClose(
                docIndex=docIndex, review=review, selectPrevious=False
            ):
                return False

        return True

    # ----

    def onDocumentSave(self, evt=None, docIndex=None) -> bool:
        """Save current document."""
        # check document
        if docIndex is None:
            docIndex = self.currentDocument
        if docIndex is None:
            wx.Bell()
            return False

        # get document
        document = self.documents[docIndex]
        path = document.path

        # check doctype and ask to save
        if (
            not path
            or document.format != "mSD"
            or (evt and evt.GetId() == ids.ID_documentSaveAs)
        ):
            # ensure document is selected
            if docIndex != self.currentDocument:
                if not self.documents[docIndex].visible:
                    self.onDocumentEnable(docIndex)
                self.documentsPanel.selectDocument(docIndex)

            # ask for name
            fileName = document.title + ".msd"
            dlg = wx.FileDialog(
                self,
                "Save",
                config.main["lastDir"],
                fileName,
                "mMass Spectrum Document|*.msd",
                wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            )
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                config.main["lastDir"] = str(Path(path).parent)
                dlg.Destroy()
            else:
                dlg.Destroy()
                return False

        # init processing gauge
        gauge = mwx.GaugePanel(self, "Formating data...")
        gauge.show()

        # get document XML
        process = threading.Thread(
            target=self.runDocumentSave, kwargs={"docIndex": docIndex}
        )
        process.start()
        while process.is_alive():
            gauge.pulse()

        # save file
        failed = True
        if self.currentDocumentXML:
            gauge.setLabel("Saving data...")
            try:
                Path(path).write_text(self.currentDocumentXML, encoding="utf-8")
                failed = False
            except OSError:
                failed = True
        else:
            failed = True

        # close processing gauge
        gauge.close()

        # processing failed
        if failed:
            wx.Bell()

            # ensure document is selected
            if docIndex != self.currentDocument:
                if not self.documents[docIndex].visible:
                    self.onDocumentEnable(docIndex)
                self.documentsPanel.selectDocument(docIndex)

            # show error message
            dlg = mwx.DlgMessage(
                self,
                title="Unable to save the document.",
                message="Please ensure that you have sufficient permissions\nto write into the document folder.",
            )
            dlg.ShowModal()
            dlg.Destroy()
            return False

        # update document meta
        document.format = "mSD"
        document.path = path
        document.dirty = False

        # update document title
        self.documentsPanel.updateDocumentTitle(docIndex)

        # update app title
        if docIndex == self.currentDocument:
            title = f"mMass - {self.documents[docIndex].title}"
            self.SetTitle(title)
            self.updateControls()

        # update recent files
        self.updateRecentFiles(path)

        # document saved
        return True

    # ----

    def onDocumentSaveAll(self, evt=None) -> None:
        """Save all documents."""
        # save documents
        for docIndex, document in enumerate(self.documents):
            if document.dirty:
                self.onDocumentSave(docIndex=docIndex)

    # ----

    def onDocumentPrintSpectrum(self, evt) -> bool | None:
        """Print spectrum."""
        # get spectrum printout
        printout = self.spectrumPanel.getPrintout(
            config.main["printQuality"], "mMass Spectrum"
        )

        # set printer defaults
        printData = wx.PrintData()
        printData.SetOrientation(wx.LANDSCAPE)
        printData.SetQuality(wx.PRINT_QUALITY_MEDIUM)
        pageSetup = wx.PageSetupDialogData()
        pageSetup.SetPrintData(printData)
        dlgPrintData = wx.PrintDialogData(pageSetup.GetPrintData())
        dlgPrintData.SetMinPage(1)
        dlgPrintData.SetMaxPage(1)
        printer = wx.Printer(dlgPrintData)

        # print
        if printer.Print(self, printout):
            printData = wx.PrintData(printer.GetPrintDialogData().GetPrintData())
            pageSetup.SetPrintData(printData)

        # printing failed
        elif printer.GetLastError() == wx.PRINTER_ERROR:
            dlg = mwx.DlgMessage(
                self,
                title="Unable to print the spectrum.",
                message="Unknown error occured while printing.",
            )
            dlg.ShowModal()
            dlg.Destroy()
            return False
        return None

    # ----

    def onDocumentReport(self, evt) -> None:
        """Print report."""
        # check document
        if self.currentDocument is None:
            wx.Bell()
            return

        # make report
        try:
            # get tmp folder
            tmpDir = Path(tempfile.gettempdir())
            imagePath = str(tmpDir / "mmass_spectrum.png")
            reportPath = tmpDir / "mmass_report.html"

            # make spetrum file
            reportBitmap = self.spectrumPanel.getBitmap(600, 400, None)
            reportImage = reportBitmap.ConvertToImage()
            reportImage.SetOption(wx.IMAGE_OPTION_QUALITY, "100")
            reportImage.SetOption(wx.IMAGE_OPTION_RESOLUTION, "72")
            reportImage.SetOption(wx.IMAGE_OPTION_RESOLUTIONX, "72")
            reportImage.SetOption(wx.IMAGE_OPTION_RESOLUTIONY, "72")
            reportImage.SetOption(wx.IMAGE_OPTION_RESOLUTIONUNIT, "1")
            reportImage.SaveFile(imagePath, wx.BITMAP_TYPE_PNG)

            # make report file
            reportHTML = self.documents[self.currentDocument].report(image=imagePath)
            reportPath.write_text(reportHTML, encoding="utf-8")

            # show report
            path = f"file://{reportPath}?{time.time()}"
            webbrowser.open(path, autoraise=1)

        except OSError:
            wx.Bell()
            dlg = mwx.DlgMessage(
                self,
                title="Unable to create the report.",
                message="Unknown error occured while creating the report.",
            )
            dlg.ShowModal()
            dlg.Destroy()
            return

    # ----

    def onDocumentExport(self, evt=None) -> None:
        """Show export panel."""
        # destroy panel
        if self.documentExportPanel and evt:
            self.documentExportPanel.Close()
            return

        # show panel
        if not self.documentExportPanel:
            self.documentExportPanel = PanelDocumentExport(self)
            self.documentExportPanel.Centre()
            self.documentExportPanel.Show(True)

        self.documentExportPanel.Raise()

    # ----

    def onDocumentInfo(self, evt=None) -> None:
        """Show document information panel."""
        # check document
        if not self.documentInfoPanel and self.currentDocument is None:
            wx.Bell()
            return

        # destroy panel
        if self.documentInfoPanel and evt:
            self.documentInfoPanel.Close()
            return

        # show panel
        if not self.documentInfoPanel:
            self.documentInfoPanel = PanelDocumentInfo(self)
            self.documentInfoPanel.Centre()
            self.documentInfoPanel.Show(True)

        # set current document
        if self.currentDocument is not None:
            self.documentInfoPanel.setData(self.documents[self.currentDocument])
            self.documentInfoPanel.Raise()
        else:
            self.documentInfoPanel.setData(None)
            self.documentInfoPanel.Raise()

    # ----

    def onDocumentSelect(self, evt=None, docIndex=None) -> None:
        """Select document."""
        self.documentsPanel.selectDocument(docIndex)

    # ----

    def onDocumentEnable(self, docIndex) -> None:
        """Enable/disable selected document."""
        # clear visibility history
        self.documentsSoloCurrent = None
        self.documentsSoloPrevious = {}

        # set document visibility
        self.documents[docIndex].visible = not self.documents[docIndex].visible

        # update documents panel
        self.documentsPanel.enableDocument(docIndex, self.documents[docIndex].visible)

        # update spectrum panel
        self.spectrumPanel.updateSpectrumProperties(
            docIndex, refresh=(docIndex != self.currentDocument)
        )

        # unselect current document
        if docIndex == self.currentDocument:
            self.documentsPanel.selectDocument(None)

        # update compare panel
        if self.comparePeaklistsPanel:
            self.comparePeaklistsPanel.setData(self.documents)

        # update mass defect plot panel
        if self.massDefectPlotPanel:
            self.massDefectPlotPanel.updateDocuments()

    # ----

    def onDocumentSolo(self, docIndex) -> None:
        """Disable all documents except one."""
        # remeber current visibility
        if self.documentsSoloCurrent is None:
            self.documentsSoloPrevious = {}
            for x, document in enumerate(self.documents):
                self.documentsSoloPrevious[x] = document.visible

        # new solo
        if docIndex != self.documentsSoloCurrent:
            # disable all documents
            for x, document in enumerate(self.documents):
                document.visible = False
                self.documentsPanel.enableDocument(x, False)
                self.spectrumPanel.updateSpectrumProperties(x, refresh=False)

            # enable the one
            self.documentsSoloCurrent = docIndex
            self.documents[docIndex].visible = True
            self.documentsPanel.enableDocument(docIndex, True)
            self.spectrumPanel.updateSpectrumProperties(docIndex, refresh=True)

            # select the one
            self.documentsPanel.selectDocument(docIndex)

        # revert to previous visibility
        else:
            # apply previous visibility
            for x, document in enumerate(self.documents):
                if x in self.documentsSoloPrevious:
                    document.visible = self.documentsSoloPrevious[x]
                    self.documentsPanel.enableDocument(x, document.visible)
                    self.spectrumPanel.updateSpectrumProperties(x, refresh=False)

            # refresh spectrum panel
            self.spectrumPanel.refresh()

            # select current document if visible
            if self.documents[docIndex].visible:
                self.documentsPanel.selectDocument(docIndex)
            else:
                self.documentsPanel.selectDocument(None)

            # clear visibility history
            self.documentsSoloCurrent = None
            self.documentsSoloPrevious = {}

        # update compare panel
        if self.comparePeaklistsPanel:
            self.comparePeaklistsPanel.setData(self.documents)

    # ----

    def onDocumentFlip(self, evt) -> None:
        """Flip spectrum vertically."""
        # check document
        if self.currentDocument is None:
            wx.Bell()
            return

        # set document flipping
        self.documents[self.currentDocument].flipped = not self.documents[
            self.currentDocument
        ].flipped

        # update spectrum panel
        self.spectrumPanel.updateSpectrumProperties(self.currentDocument)

    # ----

    def onDocumentOffset(self, evt) -> None:
        """Offset spectrum."""
        # set offset for current document
        if evt.GetId() == ids.ID_documentOffset and self.currentDocument is not None:
            if config.spectrum["normalize"]:
                wx.Bell()
                return
            dlg = DlgSpectrumOffset(self, self.documents[self.currentDocument].offset)
            if dlg.ShowModal() == wx.ID_OK:
                offset = dlg.getData()
                dlg.Destroy()
                self.documents[self.currentDocument].offset = offset
                self.spectrumPanel.updateSpectrumProperties(self.currentDocument)
            else:
                dlg.Destroy()

        # clear offset for current document
        elif evt.GetId() == ids.ID_documentClearOffset and self.currentDocument is not None:
            self.documents[self.currentDocument].offset = [0, 0]
            self.spectrumPanel.updateSpectrumProperties(self.currentDocument)

        # clear offset for all documents
        elif evt.GetId() == ids.ID_documentClearOffsets:
            for x, document in enumerate(self.documents):
                document.offset = [0, 0]
                self.spectrumPanel.updateSpectrumProperties(x, refresh=False)
            self.spectrumPanel.refresh()

        # no document
        else:
            wx.Bell()
            return

    # ----

    def onDocumentColour(self, evt) -> None:
        """Change document colour."""
        # check document
        if self.currentDocument is None:
            wx.Bell()
            return

        # get current colour
        oldColour = self.documents[self.currentDocument].colour
        currentColour = wx.ColourData()
        currentColour.SetColour(oldColour)

        # show dialog and get colour
        dlg = wx.ColourDialog(self, currentColour)
        dlg.GetColourData().SetChooseFull(True)
        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetColourData()
            newColour = list(data.GetColour().Get())
            dlg.Destroy()
        else:
            return

        # update used colours
        if oldColour in self.usedColours:
            del self.usedColours[self.usedColours.index(oldColour)]
        self.usedColours.append(newColour)

        # set colour to document
        self.documents[self.currentDocument].colour = newColour

        # update documents panel
        self.documentsPanel.updateDocumentColour(self.currentDocument)

        # update spectrum panel
        self.spectrumPanel.updateSpectrumProperties(self.currentDocument)

        # update compare panel
        if self.comparePeaklistsPanel:
            self.comparePeaklistsPanel.setData(self.documents)

        # update processing panel
        if self.processingPanel:
            self.processingPanel.updateAvailableDocuments()

        # update mass defect plot panel
        if self.massDefectPlotPanel:
            self.massDefectPlotPanel.updateDocuments()

    # ----

    def onDocumentStyle(self, evt) -> None:
        """Change document style."""
        # check document
        if self.currentDocument is None:
            wx.Bell()
            return

        # set document style
        if evt.GetId() == ids.ID_documentStyleDot:
            self.documents[self.currentDocument].style = wx.DOT
        elif evt.GetId() == ids.ID_documentStyleDash:
            self.documents[self.currentDocument].style = wx.SHORT_DASH
        elif evt.GetId() == ids.ID_documentStyleDotDash:
            self.documents[self.currentDocument].style = wx.DOT_DASH
        else:
            self.documents[self.currentDocument].style = wx.SOLID

        # update spectrum panel
        self.spectrumPanel.updateSpectrumProperties(self.currentDocument)

    # ----

    def onDocumentNotationsDelete(self, evt=None) -> None:
        """Delete all annotations and sequence matches."""
        # check selection
        if self.currentDocument is None:
            return

        # backup annotations and matches
        self.documents[self.currentDocument].backup("notations")

        # delete annotations
        del self.documents[self.currentDocument].annotations[:]

        # delete sequence matches
        for seqIndex in range(len(self.documents[self.currentDocument].sequences)):
            del self.documents[self.currentDocument].sequences[seqIndex].matches[:]

        # update GUI
        self.onDocumentChanged(items=("notations"))

    # ----

    def onDocumentAnnotationsDelete(self, evt=None, annotIndex=None) -> None:
        """Delete annotations."""
        # check selection
        if self.currentDocument is None:
            return

        # delete annotations
        self.documents[self.currentDocument].backup("annotations")
        if annotIndex is not None:
            del self.documents[self.currentDocument].annotations[annotIndex]
        else:
            del self.documents[self.currentDocument].annotations[:]

        # update GUI
        self.onDocumentChanged(items=("annotations"))

    # ----

    def onDocumentAnnotationsCalibrateBy(self, evt=None) -> None:
        """Use annotations for calibration."""
        # check selection
        if self.currentDocument is None:
            return

        # get annotations
        annotations = []
        for annotation in self.documents[self.currentDocument].annotations:
            if annotation.theoretical is not None:
                annotations.append(
                    [annotation.label, annotation.theoretical, annotation.mz]
                )
        if not annotations:
            wx.Bell()
            return

        # show calibration panel
        self.onToolsCalibration(references=annotations)

    # ----

    # VIEW

    def onView(self, evt) -> None:
        """Update view parameters in the spectrum."""
        # get ID
        ID = evt.GetId()

        # set new params
        if ids.ID_viewLegend == ID:
            values = (1, 0)
            config.spectrum["showLegend"] = values[bool(config.spectrum["showLegend"])]
            self.menubar.Check(ids.ID_viewLegend, bool(config.spectrum["showLegend"]))

        elif ids.ID_viewGrid == ID:
            values = (1, 0)
            config.spectrum["showGrid"] = values[bool(config.spectrum["showGrid"])]
            self.menubar.Check(ids.ID_viewGrid, bool(config.spectrum["showGrid"]))

        elif ids.ID_viewMinorTicks == ID:
            values = (1, 0)
            config.spectrum["showMinorTicks"] = values[
                bool(config.spectrum["showMinorTicks"])
            ]
            self.menubar.Check(
                ids.ID_viewMinorTicks, bool(config.spectrum["showMinorTicks"])
            )

        elif ids.ID_viewDataPoints == ID:
            values = (1, 0)
            config.spectrum["showDataPoints"] = values[
                bool(config.spectrum["showDataPoints"])
            ]
            self.menubar.Check(
                ids.ID_viewDataPoints, bool(config.spectrum["showDataPoints"])
            )

        elif ids.ID_viewPosBars == ID:
            values = (1, 0)
            config.spectrum["showPosBars"] = values[
                bool(config.spectrum["showPosBars"])
            ]
            self.menubar.Check(ids.ID_viewPosBars, bool(config.spectrum["showPosBars"]))

        elif ids.ID_viewGel == ID:
            values = (1, 0)
            config.spectrum["showGel"] = values[bool(config.spectrum["showGel"])]
            self.menubar.Check(ids.ID_viewGel, bool(config.spectrum["showGel"]))

        elif ids.ID_viewGelLegend == ID:
            values = (1, 0)
            config.spectrum["showGelLegend"] = values[
                bool(config.spectrum["showGelLegend"])
            ]
            self.menubar.Check(ids.ID_viewGelLegend, bool(config.spectrum["showGelLegend"]))

        elif ids.ID_viewTracker == ID:
            values = (1, 0)
            config.spectrum["showTracker"] = values[
                bool(config.spectrum["showTracker"])
            ]
            self.menubar.Check(ids.ID_viewTracker, bool(config.spectrum["showTracker"]))

        elif ids.ID_viewLabels == ID:
            values = (1, 0)
            title = ("Show Labels", "Hide Labels")
            config.spectrum["showLabels"] = values[bool(config.spectrum["showLabels"])]
            self.menubar.SetLabel(
                ids.ID_viewLabels,
                title[bool(config.spectrum["showLabels"])] + ids.HK_viewLabels,
            )

        elif ids.ID_viewTicks == ID:
            values = (1, 0)
            title = ("Show Ticks", "Hide Ticks")
            config.spectrum["showTicks"] = values[bool(config.spectrum["showTicks"])]
            self.menubar.SetLabel(
                ids.ID_viewTicks, title[bool(config.spectrum["showTicks"])] + ids.HK_viewTicks
            )

        elif ids.ID_viewLabelCharge == ID:
            values = (1, 0)
            config.spectrum["labelCharge"] = values[
                bool(config.spectrum["labelCharge"])
            ]
            self.menubar.Check(ids.ID_viewLabelCharge, bool(config.spectrum["labelCharge"]))

        elif ids.ID_viewLabelGroup == ID:
            values = (1, 0)
            config.spectrum["labelGroup"] = values[bool(config.spectrum["labelGroup"])]
            self.menubar.Check(ids.ID_viewLabelGroup, bool(config.spectrum["labelGroup"]))

        elif ids.ID_viewLabelBgr == ID:
            values = (1, 0)
            config.spectrum["labelBgr"] = values[bool(config.spectrum["labelBgr"])]
            self.menubar.Check(ids.ID_viewLabelBgr, bool(config.spectrum["labelBgr"]))

        elif ids.ID_viewLabelAngle == ID:
            values = (90, 0)
            title = ("Vertical Labels", "Horizontal Labels")
            config.spectrum["labelAngle"] = values[bool(config.spectrum["labelAngle"])]
            self.menubar.SetLabel(
                ids.ID_viewLabelAngle,
                title[bool(config.spectrum["labelAngle"])] + ids.HK_viewLabelAngle,
            )

        elif ids.ID_viewOverlapLabels == ID:
            values = (1, 0)
            config.spectrum["overlapLabels"] = values[
                bool(config.spectrum["overlapLabels"])
            ]
            self.menubar.Check(
                ids.ID_viewOverlapLabels, bool(config.spectrum["overlapLabels"])
            )

        elif ids.ID_viewCheckLimits == ID:
            values = (1, 0)
            config.spectrum["checkLimits"] = values[
                bool(config.spectrum["checkLimits"])
            ]
            self.menubar.Check(ids.ID_viewCheckLimits, bool(config.spectrum["checkLimits"]))

        elif ids.ID_viewAllLabels == ID:
            values = (1, 0)
            config.spectrum["showAllLabels"] = values[
                bool(config.spectrum["showAllLabels"])
            ]
            self.menubar.Check(ids.ID_viewAllLabels, bool(config.spectrum["showAllLabels"]))

        elif ids.ID_viewNotations == ID:
            values = (1, 0)
            title = ("Show Notations", "Hide Notations")
            config.spectrum["showNotations"] = values[
                bool(config.spectrum["showNotations"])
            ]
            self.menubar.SetLabel(
                ids.ID_viewNotations, title[bool(config.spectrum["showNotations"])]
            )

        elif ids.ID_viewNotationMarks == ID:
            values = (1, 0)
            config.spectrum["notationMarks"] = values[
                bool(config.spectrum["notationMarks"])
            ]
            self.menubar.Check(
                ids.ID_viewNotationMarks, bool(config.spectrum["notationMarks"])
            )

        elif ids.ID_viewNotationLabels == ID:
            values = (1, 0)
            config.spectrum["notationLabels"] = values[
                bool(config.spectrum["notationLabels"])
            ]
            self.menubar.Check(
                ids.ID_viewNotationLabels, bool(config.spectrum["notationLabels"])
            )

        elif ids.ID_viewNotationMz == ID:
            values = (1, 0)
            config.spectrum["notationMZ"] = values[bool(config.spectrum["notationMZ"])]
            self.menubar.Check(ids.ID_viewNotationMz, bool(config.spectrum["notationMZ"]))

        elif ids.ID_viewAutoscale == ID:
            values = (1, 0)
            config.spectrum["autoscale"] = values[bool(config.spectrum["autoscale"])]
            self.menubar.Check(ids.ID_viewAutoscale, bool(config.spectrum["autoscale"]))

        elif ids.ID_viewNormalize == ID:
            values = (1, 0)
            config.spectrum["normalize"] = values[bool(config.spectrum["normalize"])]
            self.menubar.Check(ids.ID_viewNormalize, bool(config.spectrum["normalize"]))

        # update spectrum
        self.spectrumPanel.updateCanvasProperties(ID)
        self.spectrumPanel.spectrumCanvas.SetFocus()

        # update spectrum generator panel
        if self.spectrumGeneratorPanel:
            self.spectrumGeneratorPanel.updateCanvasProperties()

        # update envelope fit panel
        if self.envelopeFitPanel:
            self.envelopeFitPanel.updateCanvasProperties()

    # ----

    def onViewSpectrumRuler(self, evt) -> None:
        """Show / hide cursor info values."""
        # get ID
        ID = evt.GetId()

        # set items
        items = {
            ids.ID_viewSpectrumRulerMz: "mz",
            ids.ID_viewSpectrumRulerDist: "dist",
            ids.ID_viewSpectrumRulerPpm: "ppm",
            ids.ID_viewSpectrumRulerZ: "z",
            ids.ID_viewSpectrumRulerCursorMass: "cmass",
            ids.ID_viewSpectrumRulerParentMass: "pmass",
            ids.ID_viewSpectrumRulerArea: "area",
        }

        # change config
        item = items[ID]
        if item in config.main["cursorInfo"]:
            del config.main["cursorInfo"][config.main["cursorInfo"].index(item)]
        else:
            config.main["cursorInfo"].append(item)

        # update menubar
        self.menubar.Check(ID, bool(item in config.main["cursorInfo"]))

    # ----

    def onViewPeaklistColumns(self, evt) -> None:
        """Show / hide peaklist columns."""
        # get ID
        ID = evt.GetId()

        # set items
        items = {
            ids.ID_viewPeaklistColumnMz: "mz",
            ids.ID_viewPeaklistColumnAi: "ai",
            ids.ID_viewPeaklistColumnInt: "int",
            ids.ID_viewPeaklistColumnBase: "base",
            ids.ID_viewPeaklistColumnRel: "rel",
            ids.ID_viewPeaklistColumnSn: "sn",
            ids.ID_viewPeaklistColumnZ: "z",
            ids.ID_viewPeaklistColumnMass: "mass",
            ids.ID_viewPeaklistColumnFwhm: "fwhm",
            ids.ID_viewPeaklistColumnResol: "resol",
            ids.ID_viewPeaklistColumnGroup: "group",
        }

        # change config
        item = items[ID]
        columns = config.main["peaklistColumns"][:]
        if item in columns:
            del columns[columns.index(item)]
        else:
            columns.append(item)

        # ensure at least one item is present and right order
        if len(columns) > 0:
            config.main["peaklistColumns"] = []
            if "mz" in columns:
                config.main["peaklistColumns"].append("mz")
            if "ai" in columns:
                config.main["peaklistColumns"].append("ai")
            if "int" in columns:
                config.main["peaklistColumns"].append("int")
            if "base" in columns:
                config.main["peaklistColumns"].append("base")
            if "rel" in columns:
                config.main["peaklistColumns"].append("rel")
            if "sn" in columns:
                config.main["peaklistColumns"].append("sn")
            if "z" in columns:
                config.main["peaklistColumns"].append("z")
            if "mass" in columns:
                config.main["peaklistColumns"].append("mass")
            if "fwhm" in columns:
                config.main["peaklistColumns"].append("fwhm")
            if "resol" in columns:
                config.main["peaklistColumns"].append("resol")
            if "group" in columns:
                config.main["peaklistColumns"].append("group")
        else:
            wx.Bell()

        # update menubar
        self.menubar.Check(ID, bool(item in config.main["peaklistColumns"]))

        # update peaklist
        self.peaklistPanel.updatePeaklistColumns()

    # ----

    def onViewCanvasProperties(self, evt) -> None:
        """Show spectrum canvas properties dialog."""
        self.spectrumPanel.onCanvasProperties()

    # ----

    def onViewRange(self, evt) -> None:
        """Set current ranges for spectrum canvas."""
        # get current range
        if not config.internal["canvasXrange"]:
            massRange = self.spectrumPanel.getCurrentRange()
            minX = f"{massRange[0]:.0f}"
            maxX = f"{massRange[1]:.0f}"
            massRange = (minX, maxX)
        else:
            massRange = config.internal["canvasXrange"]

        # show range dialog
        dlg = DlgViewRange(self, massRange)
        if dlg.ShowModal() == wx.ID_OK:
            massRange = dlg.data
            dlg.Destroy()
        else:
            dlg.Destroy()
            return

        # set new range
        self.spectrumPanel.setCanvasRange(xAxis=massRange)
        config.internal["canvasXrange"] = massRange

    # ----

    # MAIN TOOLS

    def onToolsUndo(self, evt) -> None:
        """Undo last operation."""
        # check document
        if self.currentDocument is None:
            wx.Bell()
            return

        # undo last operation
        items = self.documents[self.currentDocument].restore()
        if not items:
            wx.Bell()
            return

        # update gui
        self.onDocumentChanged(items=items)

    # ----

    def onToolsSpectrum(self, evt) -> None:
        """Toggle spectrum tools."""
        # get ID
        ID = evt.GetId()

        # set tool in menubar
        if ids.ID_toolsRuler == ID:
            self.menubar.Check(ids.ID_toolsRuler, True)
            tool = "ruler"
        elif ids.ID_toolsLabelPeak == ID:
            tool = "labelpeak"
            self.menubar.Check(ids.ID_toolsLabelPeak, True)
        elif ids.ID_toolsLabelPoint == ID:
            tool = "labelpoint"
            self.menubar.Check(ids.ID_toolsLabelPoint, True)
        elif ids.ID_toolsLabelEnvelope == ID:
            self.menubar.Check(ids.ID_toolsLabelEnvelope, True)
            tool = "labelenvelope"
        elif ids.ID_toolsDeleteLabel == ID:
            tool = "deletelabel"
            self.menubar.Check(ids.ID_toolsDeleteLabel, True)
        elif ids.ID_toolsOffset == ID:
            self.menubar.Check(ids.ID_toolsOffset, True)
            tool = "offset"

        # set tool in spectrum
        self.spectrumPanel.setCurrentTool(tool)
        self.spectrumPanel.spectrumCanvas.SetFocus()

    # ----

    def onToolsProcessing(self, evt=None) -> None:
        """Show processing tools panel."""
        # check document
        if not self.processingPanel and not self.documents:
            wx.Bell()
            return

        # destroy panel
        if self.processingPanel and evt and evt.GetId() == ids.ID_toolsProcessing:
            self.processingPanel.Close()
            return

        # init panel
        if not self.processingPanel:
            self.processingPanel = PanelProcessing(self)

        # show selected tool
        tool = "peakpicking"
        if evt and evt.GetId() == ids.ID_processingPeakpicking:
            tool = "peakpicking"
        elif evt and evt.GetId() == ids.ID_processingDeisotoping:
            tool = "deisotoping"
        elif evt and evt.GetId() == ids.ID_processingDeconvolution:
            tool = "deconvolution"
        elif evt and evt.GetId() == ids.ID_processingBaseline:
            tool = "baseline"
        elif evt and evt.GetId() == ids.ID_processingSmoothing:
            tool = "smoothing"
        elif evt and evt.GetId() == ids.ID_processingCrop:
            tool = "crop"
        elif evt and evt.GetId() == ids.ID_processingMath:
            tool = "math"
        elif evt and evt.GetId() == ids.ID_processingBatch:
            tool = "batch"

        self.processingPanel.onToolSelected(tool=tool)
        self.processingPanel.Centre()
        self.processingPanel.Show(True)

        # get current document
        docData = None
        if self.currentDocument is not None:
            docData = self.documents[self.currentDocument]

        # set data
        self.processingPanel.setData(docData)
        self.processingPanel.Raise()

    # ----

    def onToolsSequence(self, evt=None) -> None:
        """Show sequence tools panel."""
        # check document
        if not self.sequencePanel and self.currentDocument is None:
            wx.Bell()
            return

        # select first sequence in document or make new
        if (
            not self.sequencePanel
            and self.currentDocument is not None
            and self.currentSequence is None
            and evt
            and evt.GetId() == ids.ID_toolsSequence
        ):
            if self.documents[self.currentDocument].sequences:
                self.documentsPanel.selectSequence(self.currentDocument, 0)
            else:
                self.onSequenceNew()
                return

        # disable tools if no sequence selected
        if (
            not self.sequencePanel
            and self.currentSequence is None
            and evt
            and evt.GetId() != ids.ID_toolsSequence
        ):
            wx.Bell()
            return

        # destroy panel
        if self.sequencePanel and evt and evt.GetId() == ids.ID_toolsSequence:
            self.sequencePanel.Close()
            return

        # init panel
        if not self.sequencePanel:
            self.sequencePanel = PanelSequence(self)

        # show selected tool
        tool = "editor"
        if evt and evt.GetId() == ids.ID_sequenceEditor:
            tool = "editor"
        elif evt and evt.GetId() == ids.ID_sequenceModifications:
            tool = "modifications"
        elif evt and evt.GetId() == ids.ID_sequenceDigest:
            tool = "digest"
        elif evt and evt.GetId() == ids.ID_sequenceFragment:
            tool = "fragment"
        elif evt and evt.GetId() == ids.ID_sequenceSearch:
            tool = "search"

        self.sequencePanel.onToolSelected(tool=tool)
        self.sequencePanel.Centre()
        self.sequencePanel.Show(True)

        # get current document sequence
        seqData = None
        if self.currentDocument is not None and self.currentSequence is not None:
            seqData = self.documents[self.currentDocument].sequences[
                self.currentSequence
            ]

        # set data
        self.sequencePanel.setData(seqData)
        self.sequencePanel.Raise()

    # ----

    def onToolsCalibration(self, evt=None, references=None) -> None:
        """Show calibration tools panel."""
        # check document
        if not self.calibrationPanel and self.currentDocument is None:
            wx.Bell()
            return

        # destroy panel
        if self.calibrationPanel and evt:
            self.calibrationPanel.Close()
            return

        # init panel
        if not self.calibrationPanel:
            self.calibrationPanel = PanelCalibration(self)
            self.calibrationPanel.Centre()
            self.calibrationPanel.Show(True)

        # get current document
        docData = None
        if self.currentDocument is not None:
            docData = self.documents[self.currentDocument]

        # set data
        self.calibrationPanel.setData(docData, references)
        self.calibrationPanel.Raise()

    # ----

    def onToolsPeriodicTable(self, evt=None) -> None:
        """Show periodic table panel."""
        # destroy panel
        if self.periodicTablePanel and evt:
            self.periodicTablePanel.Close()
            return

        # show periodic table
        if not self.periodicTablePanel:
            self.periodicTablePanel = PanelPeriodicTable(self)
            self.periodicTablePanel.Centre()
            self.periodicTablePanel.Show(True)

        # show panel
        self.periodicTablePanel.Raise()

    # ----

    def onToolsMassCalculator(
        self,
        evt=None,
        formula=None,
        charge=None,
        agentFormula="H",
        agentCharge=1,
        fwhm=None,
    ) -> None:
        """Show mass calculation tool panel."""
        # destroy panel
        if self.massCalculatorPanel and evt:
            self.massCalculatorPanel.Close()
            return

        # init panel
        if not self.massCalculatorPanel:
            self.massCalculatorPanel = PanelMassCalculator(self)
            self.massCalculatorPanel.Centre()
            self.massCalculatorPanel.Show(True)

        # set no formula
        if formula is None:
            self.massCalculatorPanel.setData(None)
            self.massCalculatorPanel.Raise()

        # set current formula
        else:
            fwhm = None
            intensity = None
            baseline = None

            # try to approximate intensity and baseline
            if (
                self.currentDocument is not None
                and charge is not None
                and self.documents[self.currentDocument].spectrum.hasprofile()
            ):
                compound = mspy.Compound(formula)
                mz = compound.mz(
                    charge=charge, agentFormula=agentFormula, agentCharge=agentCharge
                )[0]
                peak = mspy.labelpeak(
                    signal=self.documents[self.currentDocument].spectrum.profile,
                    mz=mz,
                    pickingHeight=0.95,
                )
                if peak:
                    intensity = peak.ai
                    baseline = peak.base
                    fwhm = peak.fwhm

            # set data
            self.massCalculatorPanel.setData(
                formula=formula,
                charge=charge,
                agentFormula=agentFormula,
                agentCharge=agentCharge,
                fwhm=fwhm,
                intensity=intensity,
                baseline=baseline,
            )

            # raise panel
            self.massCalculatorPanel.Raise()

    # ----

    def onToolsMassToFormula(
        self,
        evt=None,
        mass=None,
        charge=None,
        tolerance=None,
        units=None,
        agentFormula=None,
    ) -> None:
        """Show mass to formula tool panel."""
        # destroy panel
        if self.massToFormulaPanel and evt:
            self.massToFormulaPanel.Close()
            return

        # init panel
        if not self.massToFormulaPanel:
            self.massToFormulaPanel = PanelMassToFormula(self)
            self.massToFormulaPanel.Centre()
            self.massToFormulaPanel.Show(True)

        # get current document
        docData = None
        if self.currentDocument is not None:
            docData = self.documents[self.currentDocument]

        # set data
        self.massToFormulaPanel.setData(
            document=docData,
            mass=mass,
            charge=charge,
            tolerance=tolerance,
            units=units,
            agentFormula=agentFormula,
        )
        self.massToFormulaPanel.Raise()

    # ----

    def onToolsMassDefectPlot(self, evt=None) -> None:
        """Docstring for onToolsMassDefectPlot."""
        # check document
        if not self.massDefectPlotPanel and self.currentDocument is None:
            wx.Bell()
            return

        # destroy panel
        if self.massDefectPlotPanel and evt:
            self.massDefectPlotPanel.Close()
            return

        # init panel
        if not self.massDefectPlotPanel:
            self.massDefectPlotPanel = PanelMassDefectPlot(self)
            self.massDefectPlotPanel.Centre()
            self.massDefectPlotPanel.Show(True)

        # get current document
        docData = None
        if self.currentDocument is not None:
            docData = self.documents[self.currentDocument]

        # set data
        self.massDefectPlotPanel.setData(docData)
        self.massDefectPlotPanel.Raise()

    # ----

    def onToolsMassFilter(self, evt=None) -> None:
        """Show mass filter tool panel."""
        # check document
        if not self.massFilterPanel and self.currentDocument is None:
            wx.Bell()
            return

        # destroy panel
        if self.massFilterPanel and evt:
            self.massFilterPanel.Close()
            return

        # init panel
        if not self.massFilterPanel:
            self.massFilterPanel = PanelMassFilter(self)
            self.massFilterPanel.Centre()
            self.massFilterPanel.Show(True)

        # get current document
        docData = None
        if self.currentDocument is not None:
            docData = self.documents[self.currentDocument]

        # set data
        self.massFilterPanel.setData(docData)
        self.massFilterPanel.Raise()

    # ----

    def onToolsCompoundsSearch(self, evt=None) -> None:
        """Show compounds search tool panel."""
        # check document
        if not self.compoundsSearchPanel and self.currentDocument is None:
            wx.Bell()
            return

        # destroy panel
        if self.compoundsSearchPanel and evt:
            self.compoundsSearchPanel.Close()
            return

        # init panel
        if not self.compoundsSearchPanel:
            self.compoundsSearchPanel = PanelCompoundsSearch(self)
            self.compoundsSearchPanel.Centre()
            self.compoundsSearchPanel.Show(True)

        # get current document
        docData = None
        if self.currentDocument is not None:
            docData = self.documents[self.currentDocument]

        # set data
        self.compoundsSearchPanel.setData(docData)
        self.compoundsSearchPanel.Raise()

    # ----

    def onToolsPeakDifferences(self, evt=None) -> None:
        """Show differences tool panel."""
        # check document
        if not self.peakDifferencesPanel and self.currentDocument is None:
            wx.Bell()
            return

        # destroy panel
        if self.peakDifferencesPanel and evt:
            self.peakDifferencesPanel.Close()
            return

        # init panel
        if not self.peakDifferencesPanel:
            self.peakDifferencesPanel = PanelPeakDifferences(self)
            self.peakDifferencesPanel.Centre()
            self.peakDifferencesPanel.Show(True)

        # get current document
        docData = None
        if self.currentDocument is not None:
            docData = self.documents[self.currentDocument]

        # set current document
        self.peakDifferencesPanel.setData(docData)
        self.peakDifferencesPanel.Raise()

    # ----

    def onToolsComparePeaklists(self, evt=None) -> None:
        """Show compare peaklists tool panel."""
        # check documents
        if not self.comparePeaklistsPanel and not self.documents:
            wx.Bell()
            return

        # destroy panel
        if self.comparePeaklistsPanel and evt:
            self.comparePeaklistsPanel.Close()
            return

        # init panel
        if not self.comparePeaklistsPanel:
            self.comparePeaklistsPanel = PanelComparePeaklists(self)
            self.comparePeaklistsPanel.Centre()
            self.comparePeaklistsPanel.Show(True)
            with contextlib.suppress(BaseException):
                wx.SafeYield()

        # set documents
        self.comparePeaklistsPanel.setData(self.documents)
        self.comparePeaklistsPanel.Raise()

    # ----

    def onToolsSpectrumGenerator(self, evt=None) -> None:
        """Show spectrum generator tool panel."""
        # check document
        if not self.spectrumGeneratorPanel and self.currentDocument is None:
            wx.Bell()
            return

        # destroy panel
        if self.spectrumGeneratorPanel and evt:
            self.spectrumGeneratorPanel.Close()
            return

        # init panel
        if not self.spectrumGeneratorPanel:
            self.spectrumGeneratorPanel = PanelSpectrumGenerator(self)
            self.spectrumGeneratorPanel.Centre()
            self.spectrumGeneratorPanel.Show(True)

        # get current document
        docData = None
        if self.currentDocument is not None:
            docData = self.documents[self.currentDocument]

        # set data
        self.spectrumGeneratorPanel.setData(docData)
        self.spectrumGeneratorPanel.Raise()

    # ----

    def onToolsEnvelopeFit(
        self, evt=None, formula=None, sequence=None, charge=None, scale=None
    ) -> None:
        """Show envelope fit panel."""
        # check document
        if not self.envelopeFitPanel and self.currentDocument is None:
            wx.Bell()
            return

        # destroy panel
        if self.envelopeFitPanel and evt:
            self.envelopeFitPanel.Close()
            return

        # init panel
        if not self.envelopeFitPanel:
            self.envelopeFitPanel = PanelEnvelopeFit(self)
            self.envelopeFitPanel.Centre()
            self.envelopeFitPanel.Show(True)

        # get current document
        docData = None
        if self.currentDocument is not None:
            docData = self.documents[self.currentDocument]

        # get data from sequence
        if sequence is not None:
            formula = sequence.formula()
            if (
                scale is None
                and config.envelopeFit["loss"] == "H"
                and config.envelopeFit["gain"] == "H{2}"
            ):
                scale = (0, len(sequence) - sequence.count("P") - 1)

        # set data
        self.envelopeFitPanel.setData(
            document=docData, formula=formula, charge=charge, scale=scale
        )
        self.envelopeFitPanel.Raise()

    # ----

    def onToolsMascot(self, evt=None) -> None:
        """Show Mascot search panel."""
        # check document
        if not self.mascotPanel and self.currentDocument is None:
            wx.Bell()
            return

        # destroy panel
        if self.mascotPanel and evt and evt.GetId() == ids.ID_toolsMascot:
            self.mascotPanel.Close()
            return

        # init panel
        if not self.mascotPanel:
            self.mascotPanel = PanelMascot(self)

        # show selected tool
        tool = "pmf"
        if evt and evt.GetId() == ids.ID_mascotPMF:
            tool = "pmf"
        elif evt and evt.GetId() == ids.ID_mascotMIS:
            tool = "mis"
        elif evt and evt.GetId() == ids.ID_mascotSQ:
            tool = "sq"
        elif (
            self.currentDocument is not None
            and self.documents[self.currentDocument].spectrum.precursorMZ
        ):
            tool = "mis"

        self.mascotPanel.onToolSelected(tool=tool)
        self.mascotPanel.Centre()
        self.mascotPanel.Show(True)
        with contextlib.suppress(BaseException):
            wx.SafeYield()
        self.mascotPanel.updateServerParams()

        # get current document
        docData = None
        if self.currentDocument is not None:
            docData = self.documents[self.currentDocument]

        # set data
        self.mascotPanel.setData(docData)
        self.mascotPanel.Raise()

    # ----

    def onToolsProfound(self, evt=None) -> None:
        """Show ProFound search panel."""
        # check document
        if not self.profoundPanel and self.currentDocument is None:
            wx.Bell()
            return

        # destroy panel
        if self.profoundPanel and evt and evt.GetId() == ids.ID_toolsProfound:
            self.profoundPanel.Close()
            return

        # init panel
        if not self.profoundPanel:
            self.profoundPanel = PanelProfound(self)
            self.profoundPanel.onToolSelected(tool="pmf")
            self.profoundPanel.Centre()
            self.profoundPanel.Show(True)

        # get current document
        docData = None
        if self.currentDocument is not None:
            docData = self.documents[self.currentDocument]

        # set data
        self.profoundPanel.setData(docData)
        self.profoundPanel.Raise()

    # ----

    def onToolsProspector(self, evt=None) -> None:
        """Show MS-Fit search panel."""
        # check document
        if not self.prospectorPanel and self.currentDocument is None:
            wx.Bell()
            return

        # destroy panel
        if self.prospectorPanel and evt and evt.GetId() == ids.ID_toolsProspector:
            self.prospectorPanel.Close()
            return

        # init panel
        if not self.prospectorPanel:
            self.prospectorPanel = PanelProspector(self)

        # show selected tool
        tool = "msfit"
        if evt and evt.GetId() == ids.ID_prospectorMSFit:
            tool = "msfit"
        elif (evt and evt.GetId() == ids.ID_prospectorMSTag) or (
            self.currentDocument is not None
            and self.documents[self.currentDocument].spectrum.precursorMZ
        ):
            tool = "mstag"

        self.prospectorPanel.onToolSelected(tool=tool)
        self.prospectorPanel.Centre()
        self.prospectorPanel.Show(True)

        # get current document
        docData = None
        if self.currentDocument is not None:
            docData = self.documents[self.currentDocument]

        # set data
        self.prospectorPanel.setData(docData)
        self.prospectorPanel.Raise()

    # ----

    def onToolsSwapData(self, evt=None) -> None:
        """Swap peaklist and spectrum data."""
        # check document
        if self.currentDocument is None:
            wx.Bell()
            return

        # ask to process
        title = "Do you really want to swap peaklist and spectrum data?"
        message = "All the annotations and sequence matches will be lost."
        buttons = [
            (wx.ID_CANCEL, "Cancel", 80, False, 15),
            (wx.ID_OK, "Swap", 80, True, 0),
        ]
        dlg = mwx.DlgMessage(self, title, message, buttons)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        dlg.Destroy()

        # backup data
        self.documents[self.currentDocument].backup(("spectrum", "notations"))

        # swap data
        self.documents[self.currentDocument].spectrum.swap()

        # delete annotations
        del self.documents[self.currentDocument].annotations[:]

        # delete sequence matches
        for sequence in self.documents[self.currentDocument].sequences:
            del sequence.matches[:]

        # update GUI
        self.onDocumentChanged(items=("spectrum", "notations"))

    # ----

    # SEQUENCE

    def onSequenceSelected(self, seqIndex) -> None:
        """Set current sequence."""
        # get sequence
        if seqIndex is not None:
            seqData = self.documents[self.currentDocument].sequences[seqIndex]
        else:
            seqData = None

        # update panels
        if seqIndex != self.currentSequence:
            # set current sequence
            self.currentSequence = seqIndex

            # update sequence panel
            if self.sequencePanel:
                self.sequencePanel.setData(seqData)

            # update menubar and toolbar
            self.updateControls()

    # ----

    def onSequenceNew(self, evt=None, seqData=None) -> None:
        """Append new sequence to current document."""
        # check selection
        if self.currentDocument is None:
            wx.Bell()
            return

        # create new sequence
        if not seqData:
            seqData = mspy.Sequence("", title="Untitled Sequence")
            seqData.matches = []

        # append sequence
        self.documents[self.currentDocument].sequences.append(seqData)

        # update documents panel
        self.documentsPanel.appendLastSequence(self.currentDocument)
        self.documentsPanel.selectSequence(self.currentDocument, -1)

        # set document status
        self.onDocumentChanged()

        # show sequence panel
        self.onToolsSequence()

    # ----

    def onSequenceImport(self, evt=None, path=None) -> None:
        """Import sequence from file to current document."""
        # check selection
        if self.currentDocument is None:
            wx.Bell()
            return

        # open dialog if no path specified
        if not path:
            lastDir = ""
            if Path(config.main["lastSeqDir"]).exists():
                lastDir = config.main["lastSeqDir"]
            elif Path(config.main["lastDir"]).exists():
                lastDir = config.main["lastDir"]
            wildcard = (
                "All supported formats|*.msd;*.fa;*.fsa;*.faa;*.fasta;|All files|*.*"
            )
            dlg = wx.FileDialog(
                self,
                "Import Sequence",
                lastDir,
                "",
                wildcard=wildcard,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            )
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                dlg.Destroy()
            else:
                dlg.Destroy()
                return

        # check path
        if Path(path).exists():
            config.main["lastSeqDir"] = str(Path(path).parent)
        else:
            wx.Bell()
            return

        # get document type
        docType = self.getDocumentType(path)
        if not docType:
            wx.Bell()
            dlg = mwx.DlgMessage(
                self,
                title="Unable to open the document.",
                message="Document type or structure can't be recognized. Selected format\nis probably unsupported.",
            )
            dlg.ShowModal()
            dlg.Destroy()
            return

        # select sequences to open
        sequences = self.askForSequences(path, docType)
        if not sequences:
            return

        # append sequences
        for sequence in sequences:
            sequence.matches = []
            self.onSequenceNew(seqData=sequence)

    # ----

    def onSequenceDelete(self, evt=None) -> None:
        """Delete current sequence."""
        # check selection
        docIndex = self.currentDocument
        seqIndex = self.currentSequence
        if self.currentDocument is None or self.currentSequence is None:
            return

        # update sequence panel
        if self.sequencePanel:
            self.sequencePanel.setData(None)

        # update documents panel
        self.documentsPanel.deleteSequence(self.currentDocument, self.currentSequence)

        # delete sequence from document
        self.documents[docIndex].backup("sequences")
        del self.documents[docIndex].sequences[seqIndex]
        self.currentSequence = None

        # set document status
        self.onDocumentChanged()

    # ----

    def onSequenceMatchesDelete(self, evt=None, matchIndex=None) -> None:
        """Delete sequence matches."""
        # check selection
        if self.currentDocument is None or self.currentSequence is None:
            return

        # delete matches
        self.documents[self.currentDocument].backup("sequences")
        if matchIndex is not None:
            del (
                self.documents[self.currentDocument]
                .sequences[self.currentSequence]
                .matches[matchIndex]
            )
        else:
            del (
                self.documents[self.currentDocument]
                .sequences[self.currentSequence]
                .matches[:]
            )

        # update GUI
        self.onDocumentChanged(items=("matches"))

    # ----

    def onSequenceMatchesCalibrateBy(self, evt=None) -> None:
        """Use sequence matches for calibration."""
        # check selection
        if self.currentDocument is None or self.currentSequence is None:
            return

        # get matches
        matches = []
        for match in (
            self.documents[self.currentDocument].sequences[self.currentSequence].matches
        ):
            matches.append([match.label, match.theoretical, match.mz])
        if not matches:
            wx.Bell()
            return

        # show calibration panel
        self.onToolsCalibration(references=matches)

    # ----

    def onSequenceSort(self, evt=None) -> None:
        """Sort current sequences by title."""
        # check selection
        if self.currentDocument is None:
            return

        # update document
        self.documents[self.currentDocument].backup("sequences")
        self.documents[self.currentDocument].sortSequences()

        # update sequence panel
        if self.sequencePanel:
            self.sequencePanel.setData(None)

        # update documents panel
        self.currentSequence = None

        # set document status
        self.onDocumentChanged(items=("sequences"))

    # ----

    def onSequenceSendToMassCalculator(self, evt) -> None:
        """Show isotopic pattern of current sequence."""
        # check selection
        if self.currentDocument is None or self.currentSequence is None:
            wx.Bell()
            return

        # get data
        seqData = self.documents[self.currentDocument].sequences[self.currentSequence]
        formula = seqData.formula()

        # send data to Mass Calculator
        self.onToolsMassCalculator(formula=formula)

    # ----

    def onSequenceSendToEnvelopeFit(self, evt) -> None:
        """Send current sequence to envelope fit tool."""
        # check selection
        if self.currentDocument is None or self.currentSequence is None:
            wx.Bell()
            return

        # get data
        seqData = self.documents[self.currentDocument].sequences[self.currentSequence]

        # send data to envelope fit
        self.onToolsEnvelopeFit(sequence=seqData)

    # ----

    # LIBRARIES

    def onLibraryEdit(self, evt) -> None:
        """Edit library."""
        # set library to edit
        if evt.GetId() == ids.ID_libraryCompounds:
            library = "compounds"
            dlg = DlgCompoundsEditor(self)

        elif evt.GetId() == ids.ID_libraryModifications:
            library = "modifications"
            dlg = DlgModificationsEditor(self)

        elif evt.GetId() == ids.ID_libraryMonomers:
            library = "monomers"
            dlg = DlgMonomersEditor(self)

        elif evt.GetId() == ids.ID_libraryEnzymes:
            library = "enzymes"
            dlg = DlgEnzymesEditor(self)

        elif evt.GetId() == ids.ID_libraryReferences:
            library = "references"
            dlg = DlgReferencesEditor(self)

        elif evt.GetId() == ids.ID_libraryMascot:
            library = "mascot"
            dlg = DlgMascotEditor(self)

        elif evt.GetId() == ids.ID_libraryPresets:
            library = "presets"
            dlg = DlgPresetsEditor(self)

        # close related panels
        if library == "compounds" and self.compoundsSearchPanel:
            self.compoundsSearchPanel.Close()
        elif library in ("modifications", "monomers", "enzymes") and self.sequencePanel:
            self.sequencePanel.Close()
        elif library == "references":
            if self.calibrationPanel:
                self.calibrationPanel.Close()
            if self.massFilterPanel:
                self.massFilterPanel.Close()
        elif library == "mascot" and self.mascotPanel:
            self.mascotPanel.Close()

        # show editor
        dlg.ShowModal()
        dlg.Destroy()

        # init processing gauge
        gauge = mwx.GaugePanel(self, "Saving library...")
        gauge.show()

        # run process
        process = threading.Thread(
            target=self.runLibrarySave, kwargs={"library": library}
        )
        process.start()
        while process.is_alive():
            gauge.pulse()
        gauge.close()

        # data not saved
        if not self.tmpLibrarySaved:
            wx.Bell()
            dlg = mwx.DlgMessage(
                self,
                title="Library cannot be saved.",
                message="Please ensure that you have sufficient permissions\nto write into mMass configuration folder.",
            )
            dlg.ShowModal()
            dlg.Destroy()

    # ----

    def onLibraryLink(self, evt) -> None:
        """Open selected webpage."""
        # set link
        links = {
            ids.ID_helpHomepage: "mMassHomepage",
            ids.ID_helpForum: "mMassForum",
            ids.ID_helpTwitter: "mMassTwitter",
            ids.ID_helpCite: "mMassCite",
            ids.ID_helpDonate: "mMassDonate",
            ids.ID_linksBiomedMSTools: "biomedmstools",
            ids.ID_linksBLAST: "blast",
            ids.ID_linksClustalW: "clustalw",
            ids.ID_linksDeltaMass: "deltamass",
            ids.ID_linksEMBLEBI: "emblebi",
            ids.ID_linksExpasy: "expasy",
            ids.ID_linksFASTA: "fasta",
            ids.ID_linksMatrixScience: "matrixscience",
            ids.ID_linksMUSCLE: "muscle",
            ids.ID_linksNCBI: "ncbi",
            ids.ID_linksPDB: "pdb",
            ids.ID_linksPIR: "pir",
            ids.ID_linksProfound: "profound",
            ids.ID_linksProspector: "prospector",
            ids.ID_linksUniMod: "unimod",
            ids.ID_linksUniProt: "uniprot",
        }
        link = config.links[links[evt.GetId()]]

        # open webpage
        with contextlib.suppress(BaseException):
            webbrowser.open(link, autoraise=1)

    # ----

    # WINDOW

    def onWindowMaximize(self, evt) -> None:
        """Maximize app."""
        self.Maximize()

    # ----

    def onWindowIconize(self, evt) -> None:
        """Iconize app."""
        self.Iconize()

    # ----

    def onWindowLayout(self, evt=None, layout=None) -> None:
        """Apply selected window layout."""
        # documents bottom
        if layout == "layout2" or (evt and evt.GetId() == ids.ID_windowLayout2):
            config.main["layout"] = "layout2"
            self.menubar.Check(ids.ID_windowLayout2, True)
            self.AUIManager.GetPane("documents").Show().Bottom().Layer(0).Row(
                0
            ).Position(0).MinSize((100, 195)).BestSize((100, 195))
            self.AUIManager.GetPane("peaklist").Show().Right().Layer(0).Row(0).Position(
                0
            ).MinSize((195, 100)).BestSize((195, 100))

        # peaklist bottom
        elif layout == "layout3" or (evt and evt.GetId() == ids.ID_windowLayout3):
            config.main["layout"] = "layout3"
            self.menubar.Check(ids.ID_windowLayout3, True)
            self.AUIManager.GetPane("documents").Show().Left().Layer(0).Row(0).Position(
                0
            ).MinSize((195, 100)).BestSize((195, 100))
            self.AUIManager.GetPane("peaklist").Show().Bottom().Layer(0).Row(
                0
            ).Position(0).MinSize((100, 195)).BestSize((100, 195))

        # documents and peaklist bottom
        elif layout == "layout4" or (evt and evt.GetId() == ids.ID_windowLayout4):
            config.main["layout"] = "layout4"
            self.menubar.Check(ids.ID_windowLayout4, True)
            self.AUIManager.GetPane("documents").Show().Bottom().Layer(0).Row(
                0
            ).Position(0).MinSize((100, 195)).BestSize((100, 195))
            self.AUIManager.GetPane("peaklist").Show().Bottom().Layer(0).Row(
                0
            ).Position(1).MinSize((100, 195)).BestSize((100, 195))

        # default
        else:
            config.main["layout"] = "default"
            self.menubar.Check(ids.ID_windowLayout1, True)
            self.AUIManager.GetPane("documents").Show().Left().Layer(0).Row(0).Position(
                0
            ).MinSize((195, 100)).BestSize((195, 100))
            self.AUIManager.GetPane("peaklist").Show().Right().Layer(0).Row(0).Position(
                0
            ).MinSize((195, 100)).BestSize((195, 100))

        # set last size
        if layout:
            self.AUIManager.GetPane("documents").BestSize(
                (config.main["documentsWidth"], config.main["documentsHeight"])
            )
            self.AUIManager.GetPane("peaklist").BestSize(
                (config.main["peaklistWidth"], config.main["peaklistHeight"])
            )

        # apply changes
        self.AUIManager.Update()

    # ----

    # HELP

    def onHelpUserGuide(self, evt) -> None:
        """Open User's Guide PDF."""
        # get path
        try:
            guide_ref = importlib.resources.files("mmass").joinpath("User Guide.pdf")
            with importlib.resources.as_file(guide_ref) as guide_path:
                path = str(guide_path)

                # try to open pdf
                if wx.Platform == "__WXMSW__":
                    os.startfile(path)
                else:
                    try:
                        subprocess.Popen(["xdg-open", path])
                    except Exception:
                        subprocess.Popen(["open", path])
        except Exception:
            wx.Bell()
            dlg = mwx.DlgMessage(
                self,
                title="Unable to open User's Guide.",
                message="Please make sure that you have an application associated\nwith the PDF format, and that the User Guide is available.",
            )
            dlg.ShowModal()
            dlg.Destroy()
            return

    # ----

    def onHelpUpdate(self, evt=None) -> None:
        """Check for available updates."""
        # check for available updates
        if not self.getAvailableUpdates():
            wx.Bell()
            title = "Update Error!"
            message = "An error occured in retrieving update information.\nPlease try again later."
            buttons = [(wx.ID_CANCEL, "Cancel Update", -1, True, 0)]
            dlg = mwx.DlgMessage(self, title, message, buttons)
            dlg.ShowModal()
            dlg.Destroy()
            return

        # newer version is available
        if config.main["updatesAvailable"] != config.version or config.nightbuild:
            if config.nightbuild:
                title = "Different stable version of mMass is available."
                message = "Version {} is the latest stable version available for download.\nYou are currently using test version {} ({}).".format(
                    config.main["updatesAvailable"],
                    config.version,
                    config.nightbuild,
                )
            else:
                title = "A newer version of mMass is available from mMass.org"
                message = "Version {} is now available for download.\nYou are currently using version {}.".format(
                    config.main["updatesAvailable"], config.version
                )
            buttons = [
                (ids.ID_helpWhatsNew, "What's New", -1, False, 15),
                (wx.ID_CANCEL, "Ask Again Later", -1, False, 15),
                (ids.ID_helpDownload, "Upgrade Now", -1, True, 0),
            ]
            dlg = mwx.DlgMessage(self, title, message, buttons)
            response = dlg.ShowModal()
            dlg.Destroy()
            if response == ids.ID_helpDownload:
                with contextlib.suppress(BaseException):
                    webbrowser.open(config.links["mMassDownload"], autoraise=1)
            elif response == ids.ID_helpWhatsNew:
                with contextlib.suppress(BaseException):
                    webbrowser.open(config.links["mMassWhatsNew"], autoraise=1)

        # you are up to date
        else:
            title = "You're up to date!"
            message = (
                f"mMass {config.version} is currently the newest version available."
            )
            dlg = mwx.DlgMessage(self, title, message)
            dlg.ShowModal()
            dlg.Destroy()

    # ----

    def onHelpAbout(self, evt) -> None:
        """Show About mMass panel."""
        about = PanelAbout(self)
        about.Centre()
        about.Show()
        about.SetFocus()

    # ----

    # DOCUMENT IMPORT

    def importDocumentQueue(self) -> None:
        """Open dropped documents."""
        # queue is already running
        if self.processingDocumentQueue:
            return

        # process all files in queue
        self.processingDocumentQueue = True
        while self.tmpDocumentQueue:
            self.importDocument(path=self.tmpDocumentQueue[0])

        # release processing flag
        self.processingDocumentQueue = False

    # ----

    def importDocument(self, path) -> None:
        """Open document."""
        # remove path from queue
        if path in self.tmpDocumentQueue:
            i = self.tmpDocumentQueue.index(path)
            del self.tmpDocumentQueue[i]

        # check path
        if Path(path).exists():
            config.main["lastDir"] = str(Path(path).parent)
        else:
            wx.Bell()
            dlg = mwx.DlgMessage(
                self,
                title="Document doesn't exists.",
                message="Specified document path cannot be found or is temporarily\nunavailable.",
            )
            dlg.ShowModal()
            dlg.Destroy()
            return

        # get document type
        docType = self.getDocumentType(path)
        if not docType:
            wx.Bell()
            dlg = mwx.DlgMessage(
                self,
                title="Unable to open the document.",
                message="Document type or structure can't be recognized. Selected format\nis probably unsupported.",
            )
            dlg.ShowModal()
            dlg.Destroy()
            return

        # import sequences from FASTA
        if docType == "FASTA":
            self.onSequenceImport(path=path)
            return

        # convert Bruker format
        compassUsed = False
        if docType == "bruker":
            compassUsed = True
            docType = config.main["compassFormat"]
            path = self.convertBrukerData(path)
            if not path:
                return

        # select scans from multiscan documents
        scans = [None]
        if docType in ("mzXML", "mzData", "mzML", "MGF"):
            scans = self.askForScans(path, docType)
            if not scans:
                return

        # open document
        status = True
        for scan in scans:
            before = len(self.documents)

            # init processing gauge
            gauge = mwx.GaugePanel(self, "Reading data...")
            gauge.show()

            # load document
            process = threading.Thread(
                target=self.runDocumentParser,
                kwargs={"path": path, "docType": docType, "scan": mspy.Scan},
            )
            process.start()
            while process.is_alive():
                gauge.pulse()

            # append document
            if before < len(self.documents):
                self.onDocumentLoaded(select=True)
                status *= True
            else:
                status *= False

            # close processing gauge
            gauge.close()

        # delete compass file
        if compassUsed and config.main["compassDeleteFile"]:
            with contextlib.suppress(BaseException):
                Path(path).unlink()

        # update recent files
        if status and (not compassUsed or not config.main["compassDeleteFile"]):
            self.updateRecentFiles(path)

        # processing failed
        if not status:
            wx.Bell()
            dlg = mwx.DlgMessage(
                self,
                title="Unable to open the document.",
                message="There were some errors while reading selected document\nor it contains no data.",
            )
            dlg.ShowModal()
            dlg.Destroy()

    # ----

    def importDocumentFromClipboard(self, rawData, dataType="profile") -> bool:
        """Parse data and make new document."""
        before = len(self.documents)

        # init processing gauge
        gauge = mwx.GaugePanel(self, "Reading data...")
        gauge.show()

        # load document
        process = threading.Thread(
            target=self.runDocumentXYParser,
            kwargs={"rawData": rawData, "dataType": dataType},
        )
        process.start()
        while process.is_alive():
            gauge.pulse()

        # append document
        if before < len(self.documents):
            self.onDocumentLoaded(select=True)
            gauge.close()
            return True
        gauge.close()
        return False

    # ----

    def convertBrukerData(self, path):
        """Convert Bruker data."""
        self.tmpCompassXport = False

        # check platform
        if wx.Platform != "__WXMSW__":
            wx.Bell()
            dlg = mwx.DlgMessage(
                self,
                title="Unable to convert data.",
                message="Unfortunately, it is not possible to use Bruker's CompassXport tool\non this platform.",
            )
            dlg.ShowModal()
            dlg.Destroy()
            return False

        # convert data
        gauge = mwx.GaugePanel(self, "Converting data...")
        gauge.show()
        process = threading.Thread(target=self.runCompassXport, kwargs={"path": path})
        process.start()
        while process.is_alive():
            gauge.pulse()
        gauge.close()

        # unable to convert data
        if not self.tmpCompassXport:
            wx.Bell()
            dlg = mwx.DlgMessage(
                self,
                title="Unable to convert data.",
                message="Make sure the Bruker's CompassXport tool is installed\non this computer.",
            )
            dlg.ShowModal()
            dlg.Destroy()
            return False

        return self.tmpCompassXport

    # ----

    def runCompassXport(self, path) -> None:
        """Convert Bruker data using CompassXport tool."""
        self.tmpCompassXport = False

        # get data path
        p = Path(path)
        if p.is_dir():
            for dir_path, _, filenames in p.walk():
                if "Analysis.baf" in filenames:
                    path = str(dir_path / "Analysis.baf")
                    break
                if "analysis.baf" in filenames:
                    path = str(dir_path / "analysis.baf")
                    break
                if "Analysis.yep" in filenames:
                    path = str(dir_path / "Analysis.yep")
                    break
                if "analysis.yep" in filenames:
                    path = str(dir_path / "analysis.yep")
                    break
                if "fid" in filenames:
                    path = str(dir_path / "fid")
                    break
                if "FID" in filenames:
                    path = str(dir_path / "FID")
                    break

        # set params
        choices = {"Line": 0, "Profile": 1}
        raw = choices[config.main["compassMode"]]
        choices = {"mzXML": 0, "mzData": 1, "mzML": 2}
        mode = choices[config.main["compassFormat"]]

        # convert data
        try:
            output = str(
                Path(path).parent / ("Analysis." + config.main["compassFormat"])
            )
            retcode = subprocess.call(
                [
                    "CompassXport.exe",
                    "-a",
                    path,
                    "-o",
                    output,
                    "-raw",
                    str(raw),
                    "-mode",
                    str(mode),
                ],
                shell=True,
            )
            if retcode == 0:
                self.tmpCompassXport = output
                return
        except Exception:
            return

    # ----

    def runDocumentParser(self, path, docType, scan=None) -> None:
        """Load spectrum document."""
        document = False
        spectrum = False

        # get data data
        if docType == "mSD":
            parser = doc.ParseMSD(path)
            document = parser.getDocument()
        elif docType == "mzData":
            parser = mspy.ParseMZData(path)
            spectrum = parser.scan(scan)
        elif docType == "mzXML":
            parser = mspy.ParseMZXML(path)
            spectrum = parser.scan(scan)
        elif docType == "mzML":
            parser = mspy.ParseMZML(path)
            spectrum = parser.scan(scan)
        elif docType == "MGF":
            parser = mspy.ParseMGF(path)
            spectrum = parser.scan(scan)
        elif docType == "XY":
            parser = mspy.ParseXY(path)
            spectrum = parser.scan()
        else:
            return

        # make document for non-mSD formats
        if spectrum:
            # init document
            document = doc.Document()
            document.format = docType
            document.path = path
            document.spectrum = spectrum

            # get info
            info = parser.info()
            if info:
                document.title = info["title"]
                document.operator = info["operator"]
                document.contact = info["contact"]
                document.institution = info["institution"]
                document.date = info["date"]
                document.instrument = info["instrument"]
                document.notes = info["notes"]

            # set date if empty
            if not document.date and docType != "mSD":
                document.date = time.ctime(Path(path).stat().st_ctime)

            # set title if empty
            if not document.title:
                if document.spectrum.title != "":
                    document.title = document.spectrum.title
                else:
                    p = Path(path)
                    if p.stem.lower() == "analysis":
                        document.title = p.parent.name
                    else:
                        document.title = p.stem

            # add scan number to title
            if scan:
                document.title += f" [{scan}]"

        # finalize and append document
        if document:
            document.colour = self.getFreeColour()
            document.sortAnnotations()
            document.sortSequenceMatches()
            self.documents.append(document)

            # precalculate baseline
            if document.spectrum.hasprofile():
                document.spectrum.baseline(
                    window=(1.0 / config.processing["baseline"]["precision"]),
                    offset=config.processing["baseline"]["offset"],
                )

    # ----

    def runDocumentXYParser(self, rawData, dataType="profile") -> None:
        """Parse XY data and make new document."""
        pattern = re.compile("^([-0-9\\.eE+]+)[ \t]*(;|,)?[ \t]*([-0-9\\.eE+]*)$")

        # read lines
        data = []
        for line in rawData.splitlines():
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
                    return
                data.append([mass, intensity])
            else:
                return

        # finalize data
        if dataType == "peaklist":
            spectrum = mspy.Scan(peaklist=data)
        else:
            spectrum = mspy.Scan(profile=data)

        # add new document
        document = doc.Document()
        document.title = "Clipboard Data"
        document.format = "mSD"
        document.path = ""
        document.dirty = True
        document.spectrum = spectrum
        document.colour = self.getFreeColour()
        self.documents.append(document)

        # precalculate baseline
        document.spectrum.baseline(
            window=(1.0 / config.processing["baseline"]["precision"]),
            offset=config.processing["baseline"]["offset"],
        )

    # ----

    def runDocumentSave(self, docIndex) -> None:
        """Save current document."""
        # get XML data for selected document
        self.currentDocumentXML = self.documents[docIndex].msd()

    # ----

    def runLibrarySave(self, library) -> None:
        """Save selected library."""
        self.tmpLibrarySaved = False

        # set process
        if library == "compounds":
            self.tmpLibrarySaved = libs.saveCompounds()
        elif library == "modifications":
            self.tmpLibrarySaved = mspy.saveModifications(
                str(Path(config.confdir) / "modifications.xml")
            )
        elif library == "monomers":
            self.tmpLibrarySaved = mspy.saveMonomers(
                str(Path(config.confdir) / "monomers.xml")
            )
        elif library == "enzymes":
            self.tmpLibrarySaved = mspy.saveEnzymes(
                str(Path(config.confdir) / "enzymes.xml")
            )
        elif library == "references":
            self.tmpLibrarySaved = libs.saveReferences()
        elif library == "mascot":
            self.tmpLibrarySaved = libs.saveMascot()
        elif library == "presets":
            self.tmpLibrarySaved = libs.savePresets()

    # ----

    def getDocumentType(self, path) -> str | bool:
        """Get document type."""
        # get filename and extension
        p = Path(path)
        fileName = p.name.lower()
        p.stem.lower()
        extension = p.suffix.lower()

        # get document type by filename or extension
        if extension == ".msd":
            return "mSD"
        if fileName == "fid" or extension in (".baf", ".yep"):
            return "bruker"
        if extension == ".mzdata":
            return "mzData"
        if extension == ".mzxml":
            return "mzXML"
        if extension == ".mzml":
            return "mzML"
        if extension == ".mgf":
            return "MGF"
        if extension in (".xy", ".txt", ".asc"):
            return "XY"
        if extension in (".fa", ".fsa", ".faa", ".fasta"):
            return "FASTA"
        if (p := Path(path)).is_dir():
            for _, _, filenames in p.walk():
                names = [i.lower() for i in filenames]
                if "fid" in names or "analysis.baf" in names or "analysis.yep" in names:
                    return "bruker"

        # get document type for xml files
        if extension == ".xml":
            data = Path(path).read_text(encoding="utf-8", errors="ignore")[:500]
            if "<mzData" in data:
                return "mzData"
            if "<mzXML" in data:
                return "mzXML"
            if "<mzML" in data:
                return "mzML"

        # unknown document type
        return False

    # ----

    def getDocumentScanList(self, path, docType) -> None:
        """Get scans from document."""
        modified = Path(path).stat().st_mtime

        # try to load from buffer
        if (
            path in self.bufferedScanlists
            and modified == self.bufferedScanlists[path][0]
        ):
            self.tmpScanlist = self.bufferedScanlists[path][1]
            return

        # set parser
        if docType == "mzData":
            parser = mspy.ParseMZData(path)
        elif docType == "mzXML":
            parser = mspy.ParseMZXML(path)
        elif docType == "mzML":
            parser = mspy.ParseMZML(path)
        elif docType == "MGF":
            parser = mspy.ParseMGF(path)
        else:
            return

        # load scans
        self.tmpScanlist = parser.scanlist()

        # remember scan list
        if self.tmpScanlist:
            self.bufferedScanlists[path] = (modified, self.tmpScanlist)

    # ----

    def getDocumentSequences(self, path, docType) -> None:
        """Get sequences from document."""
        # get sequences
        if docType == "mSD":
            parser = doc.ParseMSD(path)
            self.tmpSequenceList = parser.getSequences()
        elif docType == "FASTA":
            parser = mspy.ParseFASTA(path)
            self.tmpSequenceList = parser.sequences()
        else:
            return

    # ----

    def askForScans(self, path, docType):
        """Select scans to import."""
        self.tmpScanlist = None

        # get scan list
        gauge = mwx.GaugePanel(self, "Gathering scan list...")
        gauge.show()
        process = threading.Thread(
            target=self.getDocumentScanList, kwargs={"path": path, "docType": docType}
        )
        process.start()
        while process.is_alive():
            gauge.pulse()
        gauge.close()

        # unable to load scan list
        if not self.tmpScanlist:
            wx.Bell()
            dlg = mwx.DlgMessage(
                self,
                title="Unable to open the document.",
                message="Selected document is damaged or contains no data.",
            )
            dlg.ShowModal()
            dlg.Destroy()
            return False

        # select scans to open
        if len(self.tmpScanlist) > 1:
            dlg = DlgSelectScans(self, self.tmpScanlist)
            if dlg.ShowModal() == wx.ID_OK:
                selected = dlg.selected
                dlg.Destroy()
                return selected
            dlg.Destroy()
            return None
        return [None]

    # ----

    def askForSequences(self, path, docType):
        """Select sequences to import."""
        self.tmpSequenceList = None

        # get scan list
        gauge = mwx.GaugePanel(self, "Gathering sequences...")
        gauge.show()
        process = threading.Thread(
            target=self.getDocumentSequences, kwargs={"path": path, "docType": docType}
        )
        process.start()
        while process.is_alive():
            gauge.pulse()
        gauge.close()

        # no sequences found
        if self.tmpSequenceList == []:
            wx.Bell()
            dlg = mwx.DlgMessage(
                self,
                title="No sequence found.",
                message="Selected document doesn't contain any valid sequence.",
            )
            dlg.ShowModal()
            dlg.Destroy()
            return None

        # unable to load sequences
        if not self.tmpSequenceList:
            wx.Bell()
            dlg = mwx.DlgMessage(
                self,
                title="Unable to open the document.",
                message="Document type or structure can't be recognized. Selected format\nis probably unsupported.",
            )
            dlg.ShowModal()
            dlg.Destroy()
            return False

        # select sequences to open
        if len(self.tmpSequenceList) > 1:
            dlg = DlgSelectSequences(self, self.tmpSequenceList)
            if dlg.ShowModal() == wx.ID_OK:
                selected = dlg.selected
                dlg.Destroy()
                return selected
            dlg.Destroy()
            return None
        return self.tmpSequenceList

    # ----

    # UTILITIES

    def updateTmpSpectrum(self, points, flipped=False, refresh=True) -> None:
        """Update tmp spectrum in canvas."""
        self.spectrumPanel.updateTmpSpectrum(points, flipped=flipped, refresh=refresh)

    # ----

    def updateNotationMarks(self, refresh=True) -> None:
        """Highlight annotations and sequence matches in canvas."""
        # get current selection
        selected = self.documentsPanel.getSelectedItemType()

        # hide annotation marks
        if not selected or self.currentDocument is None:
            self.spectrumPanel.updateNotationMarks(None, refresh=refresh)
            return

        points = []

        # get all
        if selected == "document":
            document = self.documents[self.currentDocument]
            points += [[a.mz, a.ai, a.label] for a in document.annotations]
            for sequence in document.sequences:
                points += [[m.mz, m.ai, m.label] for m in sequence.matches]

        # get annotations
        elif selected in ("annotations", "annotation"):
            document = self.documents[self.currentDocument]
            points += [[a.mz, a.ai, a.label] for a in document.annotations]

        # get sequence matches
        elif selected in ("sequence", "match") and self.currentSequence is not None:
            sequence = self.documents[self.currentDocument].sequences[
                self.currentSequence
            ]
            points += [[m.mz, m.ai, m.label] for m in sequence.matches]

        # sort points
        points.sort()

        # update spectrum panel
        self.spectrumPanel.updateNotationMarks(points, refresh=refresh)

    # ----

    def updateMassPoints(self, points) -> None:
        """Highlight specified points in the spectrum."""
        self.spectrumPanel.highlightPoints(points)

    # ----

    def updateControls(self) -> None:
        """Update menubar and toolbar items state."""
        # skip for Mac since it doesn't work correctly... why???
        if wx.Platform == "__WXMAC__":
            return

        # document
        if self.currentDocument is None:
            enable = False
            document = None
        else:
            enable = True
            document = self.documents[self.currentDocument]

        # update menubar
        self.menubar.Enable(ids.ID_documentClose, enable)
        self.menubar.Enable(ids.ID_documentCloseAll, bool(self.documents))
        self.menubar.Enable(ids.ID_documentSave, enable)
        self.menubar.Enable(ids.ID_documentSaveAs, enable)
        self.menubar.Enable(ids.ID_documentSaveAll, bool(self.documents))
        self.menubar.Enable(ids.ID_documentExport, bool(self.documents))
        self.menubar.Enable(ids.ID_documentReport, enable)
        self.menubar.Enable(ids.ID_documentInfo, enable)
        self.menubar.Enable(ids.ID_documentFlip, enable)
        self.menubar.Enable(
            ids.ID_documentOffset, bool(enable and not config.spectrum["normalize"])
        )
        self.menubar.Enable(ids.ID_processingUndo, bool(enable and document.undo))
        self.menubar.Enable(ids.ID_processingPeakpicking, enable)
        self.menubar.Enable(ids.ID_processingDeisotoping, enable)
        self.menubar.Enable(ids.ID_processingDeconvolution, enable)
        self.menubar.Enable(ids.ID_processingBaseline, enable)
        self.menubar.Enable(ids.ID_processingSmoothing, enable)
        self.menubar.Enable(ids.ID_processingCrop, enable)
        self.menubar.Enable(ids.ID_processingMath, enable)
        self.menubar.Enable(ids.ID_processingBatch, bool(self.documents))
        self.menubar.Enable(ids.ID_toolsSwapData, enable)
        self.menubar.Enable(ids.ID_sequenceNew, enable)
        self.menubar.Enable(ids.ID_sequenceImport, enable)
        self.menubar.Enable(ids.ID_sequenceSort, enable)
        self.menubar.Enable(ids.ID_toolsCalibration, enable)
        self.menubar.Enable(ids.ID_processingDeconvolution, enable)
        self.menubar.Enable(ids.ID_toolsMassFilter, enable)
        self.menubar.Enable(ids.ID_toolsCompoundsSearch, enable)
        self.menubar.Enable(ids.ID_toolsPeakDifferences, enable)
        self.menubar.Enable(ids.ID_toolsComparePeaklists, bool(self.documents))
        self.menubar.Enable(ids.ID_toolsSpectrumGenerator, enable)
        self.menubar.Enable(ids.ID_toolsEnvelopeFit, enable)
        self.menubar.Enable(ids.ID_toolsMassDefectPlot, enable)
        self.menubar.Enable(ids.ID_mascotPMF, enable)
        self.menubar.Enable(ids.ID_mascotSQ, enable)
        self.menubar.Enable(ids.ID_mascotMIS, enable)
        self.menubar.Enable(ids.ID_toolsProfound, enable)
        self.menubar.Enable(ids.ID_prospectorMSFit, enable)
        self.menubar.Enable(ids.ID_prospectorMSTag, enable)

        # update toolbar
        if wx.Platform != "__WXMAC__":
            self.toolbar.EnableTool(ids.ID_documentSave, bool(enable and document.dirty))
        self.toolbar.EnableTool(ids.ID_toolsProcessing, bool(self.documents))
        self.toolbar.EnableTool(ids.ID_toolsCalibration, enable)
        self.toolbar.EnableTool(ids.ID_toolsMassFilter, enable)
        self.toolbar.EnableTool(ids.ID_toolsSequence, enable)
        self.toolbar.EnableTool(ids.ID_toolsCompoundsSearch, enable)
        self.toolbar.EnableTool(ids.ID_toolsPeakDifferences, enable)
        self.toolbar.EnableTool(ids.ID_toolsComparePeaklists, bool(self.documents))
        self.toolbar.EnableTool(ids.ID_toolsSpectrumGenerator, enable)
        self.toolbar.EnableTool(ids.ID_toolsEnvelopeFit, enable)
        self.toolbar.EnableTool(ids.ID_toolsMassDefectPlot, enable)
        self.toolbar.EnableTool(ids.ID_toolsMascot, enable)
        self.toolbar.EnableTool(ids.ID_toolsProfound, enable)
        self.toolbar.EnableTool(ids.ID_toolsDocumentExport, bool(self.documents))
        self.toolbar.EnableTool(ids.ID_toolsDocumentInfo, enable)
        self.toolbar.EnableTool(ids.ID_toolsDocumentReport, enable)

        # sequence
        if self.currentDocument is None or self.currentSequence is None:
            enable = False
            sequence = None
        else:
            enable = True
            sequence = self.documents[self.currentDocument].sequences[
                self.currentSequence
            ]

        # update menubar
        self.menubar.Enable(ids.ID_sequenceEditor, enable)
        self.menubar.Enable(ids.ID_sequenceModifications, enable)
        self.menubar.Enable(ids.ID_sequenceDigest, enable)
        self.menubar.Enable(ids.ID_sequenceFragment, enable)
        self.menubar.Enable(ids.ID_sequenceSearch, enable)
        self.menubar.Enable(ids.ID_sequenceSendToMassCalculator, enable)
        self.menubar.Enable(ids.ID_sequenceSendToEnvelopeFit, enable)
        self.menubar.Enable(
            ids.ID_sequenceMatchesCalibrateBy, bool(enable and sequence.matches)
        )
        self.menubar.Enable(ids.ID_sequenceMatchesDelete, bool(enable and sequence.matches))
        self.menubar.Enable(ids.ID_sequenceDelete, enable)

    # ----

    def updateRecentFiles(self, path=None) -> None:
        """Update recent files."""
        # update config
        if path:
            if path in config.recent:
                del config.recent[config.recent.index(path)]
            config.recent.insert(0, path)
            while len(config.recent) > 10:
                del config.recent[-1]

        # delete old items from menu
        for item in self.menuRecent.GetMenuItems():
            self.menuRecent.Delete(item.GetId())

        # add new items to menu
        for i, path in enumerate(config.recent):
            ID = eval("ids.ID_documentRecent" + str(i))
            self.menuRecent.Insert(i, ID, path, "Open Document")
            self.Bind(wx.EVT_MENU, self.onDocumentRecent, id=ID)
            if not Path(path).exists():
                self.menuRecent.Enable(ID, False)

        # append clear
        if config.recent:
            self.menuRecent.AppendSeparator()
        self.menuRecent.Append(
            ids.ID_documentRecentClear, "Clear Menu", "Clear recent items"
        )
        self.Bind(wx.EVT_MENU, self.onDocumentClearRecent, id=ids.ID_documentRecentClear)

    # ----

    def getFreeColour(self):
        """Get free colour from config or generate random."""
        # get colour from config
        for colour in config.colours:
            if colour not in self.usedColours:
                self.usedColours.append(colour)
                return colour

        # generate random colour
        i = 0
        while True:
            i += 1
            colour = [
                random.randrange(0, 255),
                random.randrange(0, 255),
                random.randrange(0, 255),
            ]
            if colour not in self.usedColours or i == 10000:
                self.usedColours.append(colour)
                return colour

    # ----

    def getAvailableUpdates(self) -> bool:
        """Check for available updates."""
        # get latest version available
        socket.setdefaulttimeout(5)
        conn = http.client.HTTPConnection("www.mmass.org")
        try:
            conn.connect()
            url = f"/update.php?version={config.version}&platform={platform.platform()}"
            conn.request("GET", url)
            response = conn.getresponse()
        except Exception:
            return False

        if response.status == 200:
            data = response.read()
            conn.close()
        else:
            conn.close()
            return False

        # check version
        if re.match(r"^([0-9]{1,2})\.([0-9]{1,2})\.([0-9]{1,2})$", data):
            config.main["updatesAvailable"] = data
            config.main["updatesChecked"] = time.strftime("%Y%m%d", time.localtime())
            return True
        return False

    # ----

    def getCurrentSpectrumPoints(self, currentView=False):
        """Get spectrum profile from current document."""
        # check document
        if self.currentDocument is None:
            return None

        # get spectrum
        points = self.documents[self.currentDocument].spectrum.profile

        # get current view selection
        if currentView:
            minX, maxX = self.spectrumPanel.getCurrentRange()
            points = mspy.crop(points, minX, maxX)

        return points

    # ----

    def getCurrentPeaklist(self, filters=""):
        """Get peaklist from current document."""
        # check document
        if self.currentDocument is None:
            return None

        peaklist = []
        blacklist = []
        whitelist = self.documents[self.currentDocument].spectrum.peaklist

        # get selection
        if "S" in filters:
            whitelist = self.peaklistPanel.getSelectedPeaks()

        # get annotations
        if "A" in filters:
            for annotation in self.documents[self.currentDocument].annotations:
                blacklist.append(round(annotation.mz, 6))

        # get matches
        if "M" in filters:
            for sequence in self.documents[self.currentDocument].sequences:
                for match in sequence.matches:
                    blacklist.append(round(match.mz, 6))

        # get peaklist
        for peak in whitelist:
            if (
                ("X" in filters and peak.charge is None)
                or ("I" in filters and peak.isotope not in (0, None))
                or (
                    ("A" in filters or "M" in filters)
                    and round(peak.mz, 6) in blacklist
                )
            ):
                continue
            peaklist.append(peak)

        # finalize peaklist
        return mspy.Peaklist(peaklist)

    # ----

    def getSpectrumBitmap(self, width, height, printerScale):
        """Get bitmap from current spectrum canvas."""
        return self.spectrumPanel.getBitmap(width, height, printerScale)

    # ----

    def getUsedMonomers(self):
        """Search all sequences for used monomers."""
        # get monomers
        monomers = []
        for document in self.documents:
            for sequence in document.sequences:
                for monomer in sequence:
                    monomers.append(monomer)

        return monomers

    # ----

    def getUsedModifications(self):
        """Search all sequences for used modifications."""
        # get modifications
        modifications = []
        for document in self.documents:
            for sequence in document.sequences:
                for mod in sequence.modifications:
                    modifications.append(mod[0])

        return modifications

    # ----

    def checkVersions(self) -> None:
        """Check mMass version and available updates."""
        # skip testing versions
        if config.nightbuild:
            return

        # first run
        if config.main["updatesCurrent"] != config.version:
            config.main["updatesCurrent"] = config.version
            config.main["updatesAvailable"] = ""
            config.main["updatesChecked"] = ""

        # updates are available
        elif (
            config.main["updatesEnabled"]
            and config.main["updatesAvailable"]
            and config.main["updatesAvailable"] != config.version
        ):
            title = "A newer version of mMass is available from mMass.org"
            message = "Version {} is now available for download.\nYou are currently using version {}.".format(
                config.main["updatesAvailable"], config.version
            )
            buttons = [
                (ids.ID_helpWhatsNew, "What's New", -1, False, 15),
                (wx.ID_CANCEL, "Ask Again Later", -1, False, 15),
                (ids.ID_helpDownload, "Upgrade Now", -1, True, 0),
            ]
            dlg = mwx.DlgMessage(self, title, message, buttons)
            response = dlg.ShowModal()
            dlg.Destroy()
            if response == ids.ID_helpDownload:
                with contextlib.suppress(BaseException):
                    webbrowser.open(config.links["mMassDownload"], autoraise=1)
            elif response == ids.ID_helpWhatsNew:
                with contextlib.suppress(BaseException):
                    webbrowser.open(config.links["mMassWhatsNew"], autoraise=1)

        # check for updates
        if config.main["updatesEnabled"] and config.main[
            "updatesChecked"
        ] != time.strftime("%Y%m%d", time.localtime()):
            process = threading.Thread(target=self.getAvailableUpdates)
            process.start()

    # ----
