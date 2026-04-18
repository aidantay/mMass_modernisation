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
import wx

# common
ID_quit = wx.ID_EXIT
ID_about = wx.ID_ABOUT
ID_preferences = wx.ID_PREFERENCES

HK_quit = "\tCtrl+Q"
HK_preferences = ""
if wx.Platform == "__WXMAC__":
    HK_preferences = "\tCtrl+,"

# file
ID_documentNew = wx.NewIdRef()
ID_documentNewFromClipboard = wx.NewIdRef()
ID_documentDuplicate = wx.NewIdRef()
ID_documentOpen = wx.NewIdRef()
ID_documentRecent = wx.NewIdRef()
ID_documentClose = wx.NewIdRef()
ID_documentCloseAll = wx.NewIdRef()
ID_documentSave = wx.NewIdRef()
ID_documentSaveAs = wx.NewIdRef()
ID_documentSaveAll = wx.NewIdRef()
ID_documentExport = wx.NewIdRef()
ID_documentInfo = wx.NewIdRef()
ID_documentPrintSpectrum = wx.NewIdRef()
ID_documentReport = wx.NewIdRef()
ID_documentFlip = wx.NewIdRef()
ID_documentOffset = wx.NewIdRef()
ID_documentClearOffset = wx.NewIdRef()
ID_documentClearOffsets = wx.NewIdRef()
ID_documentColour = wx.NewIdRef()
ID_documentStyle = wx.NewIdRef()
ID_documentStyleSolid = wx.NewIdRef()
ID_documentStyleDot = wx.NewIdRef()
ID_documentStyleDash = wx.NewIdRef()
ID_documentStyleDotDash = wx.NewIdRef()
ID_documentAnnotationEdit = wx.NewIdRef()
ID_documentAnnotationDelete = wx.NewIdRef()
ID_documentAnnotationSendToMassCalculator = wx.NewIdRef()
ID_documentAnnotationSendToMassToFormula = wx.NewIdRef()
ID_documentAnnotationSendToEnvelopeFit = wx.NewIdRef()
ID_documentAnnotationsDelete = wx.NewIdRef()
ID_documentAnnotationsCalibrateBy = wx.NewIdRef()
ID_documentNotationsDelete = wx.NewIdRef()

ID_documentRecent0 = wx.NewIdRef()
ID_documentRecent1 = wx.NewIdRef()
ID_documentRecent2 = wx.NewIdRef()
ID_documentRecent3 = wx.NewIdRef()
ID_documentRecent4 = wx.NewIdRef()
ID_documentRecent5 = wx.NewIdRef()
ID_documentRecent6 = wx.NewIdRef()
ID_documentRecent7 = wx.NewIdRef()
ID_documentRecent8 = wx.NewIdRef()
ID_documentRecent9 = wx.NewIdRef()
ID_documentRecentClear = wx.NewIdRef()

HK_documentNew = "\tCtrl+N"
HK_documentNewFromClipboard = "\tShift+Ctrl+N"
HK_documentOpen = "\tCtrl+O"
HK_documentClose = "\tCtrl+W"
HK_documentCloseAll = "\tShift+Ctrl+W"
HK_documentSave = "\tCtrl+S"
HK_documentSaveAs = "\tShift+Ctrl+S"
HK_documentSaveAll = "\tAlt+Ctrl+S"
HK_documentExport = "\tCtrl+E"
HK_documentInfo = "\tCtrl+I"
HK_documentPrintSpectrum = "\tCtrl+P"
HK_documentReport = "\tShift+Ctrl+R"
HK_documentFlip = "\tAlt+Ctrl+F"

# view
ID_viewGrid = wx.NewIdRef()
ID_viewMinorTicks = wx.NewIdRef()
ID_viewLegend = wx.NewIdRef()
ID_viewPosBars = wx.NewIdRef()
ID_viewGel = wx.NewIdRef()
ID_viewGelLegend = wx.NewIdRef()
ID_viewTracker = wx.NewIdRef()
ID_viewDataPoints = wx.NewIdRef()
ID_viewLabels = wx.NewIdRef()
ID_viewTicks = wx.NewIdRef()
ID_viewLabelCharge = wx.NewIdRef()
ID_viewLabelGroup = wx.NewIdRef()
ID_viewLabelBgr = wx.NewIdRef()
ID_viewLabelAngle = wx.NewIdRef()
ID_viewAllLabels = wx.NewIdRef()
ID_viewOverlapLabels = wx.NewIdRef()
ID_viewCheckLimits = wx.NewIdRef()
ID_viewNotations = wx.NewIdRef()
ID_viewNotationMarks = wx.NewIdRef()
ID_viewNotationLabels = wx.NewIdRef()
ID_viewNotationMz = wx.NewIdRef()
ID_viewAutoscale = wx.NewIdRef()
ID_viewNormalize = wx.NewIdRef()
ID_viewRange = wx.NewIdRef()
ID_viewCanvasProperties = wx.NewIdRef()

ID_viewSpectrumRulerMz = wx.NewIdRef()
ID_viewSpectrumRulerDist = wx.NewIdRef()
ID_viewSpectrumRulerPpm = wx.NewIdRef()
ID_viewSpectrumRulerZ = wx.NewIdRef()
ID_viewSpectrumRulerCursorMass = wx.NewIdRef()
ID_viewSpectrumRulerParentMass = wx.NewIdRef()
ID_viewSpectrumRulerArea = wx.NewIdRef()

ID_viewPeaklistColumnMz = wx.NewIdRef()
ID_viewPeaklistColumnAi = wx.NewIdRef()
ID_viewPeaklistColumnInt = wx.NewIdRef()
ID_viewPeaklistColumnBase = wx.NewIdRef()
ID_viewPeaklistColumnRel = wx.NewIdRef()
ID_viewPeaklistColumnSn = wx.NewIdRef()
ID_viewPeaklistColumnZ = wx.NewIdRef()
ID_viewPeaklistColumnMass = wx.NewIdRef()
ID_viewPeaklistColumnFwhm = wx.NewIdRef()
ID_viewPeaklistColumnResol = wx.NewIdRef()
ID_viewPeaklistColumnGroup = wx.NewIdRef()

HK_viewPosBars = "\tAlt+Ctrl+P"
HK_viewGel = "\tAlt+Ctrl+G"
HK_viewLabels = "\tAlt+Ctrl+L"
HK_viewTicks = "\tAlt+Ctrl+T"
HK_viewLabelAngle = "\tAlt+Ctrl+H"
HK_viewAllLabels = "\tAlt+Ctrl+Shift+L"
HK_viewOverlapLabels = "\tAlt+Ctrl+O"
HK_viewAutoscale = "\tAlt+Ctrl+A"
HK_viewNormalize = "\tAlt+Ctrl+N"
HK_viewRange = "\tAlt+Ctrl+R"
HK_viewCanvasProperties = "\tCtrl+J"

# processing
ID_processingUndo = wx.NewIdRef()
ID_processingPeakpicking = wx.NewIdRef()
ID_processingDeisotoping = wx.NewIdRef()
ID_processingDeconvolution = wx.NewIdRef()
ID_processingBaseline = wx.NewIdRef()
ID_processingSmoothing = wx.NewIdRef()
ID_processingCrop = wx.NewIdRef()
ID_processingMath = wx.NewIdRef()
ID_processingBatch = wx.NewIdRef()
ID_toolsSwapData = wx.NewIdRef()

HK_processingUndo = "\tCtrl+Z"
HK_processingPeakpicking = "\tCtrl+F"
HK_processingDeisotoping = "\tCtrl+D"
HK_processingDeconvolution = ""
HK_processingSmoothing = "\tCtrl+G"
HK_processingBaseline = "\tCtrl+B"

# sequence
ID_sequenceNew = wx.NewIdRef()
ID_sequenceImport = wx.NewIdRef()
ID_sequenceEditor = wx.NewIdRef()
ID_sequenceModifications = wx.NewIdRef()
ID_sequenceDigest = wx.NewIdRef()
ID_sequenceFragment = wx.NewIdRef()
ID_sequenceSearch = wx.NewIdRef()
ID_sequenceSendToMassCalculator = wx.NewIdRef()
ID_sequenceSendToEnvelopeFit = wx.NewIdRef()
ID_sequenceDelete = wx.NewIdRef()
ID_sequenceSort = wx.NewIdRef()
ID_sequenceMatchEdit = wx.NewIdRef()
ID_sequenceMatchDelete = wx.NewIdRef()
ID_sequenceMatchSendToMassCalculator = wx.NewIdRef()
ID_sequenceMatchSendToEnvelopeFit = wx.NewIdRef()
ID_sequenceMatchesDelete = wx.NewIdRef()
ID_sequenceMatchesCalibrateBy = wx.NewIdRef()

# tools
ID_toolsProcessing = wx.NewIdRef()
ID_toolsCalibration = wx.NewIdRef()
ID_toolsSequence = wx.NewIdRef()
ID_toolsRuler = wx.NewIdRef()
ID_toolsLabelPeak = wx.NewIdRef()
ID_toolsLabelPoint = wx.NewIdRef()
ID_toolsLabelEnvelope = wx.NewIdRef()
ID_toolsDeleteLabel = wx.NewIdRef()
ID_toolsOffset = wx.NewIdRef()
ID_toolsPeriodicTable = wx.NewIdRef()
ID_toolsMassCalculator = wx.NewIdRef()
ID_toolsMassToFormula = wx.NewIdRef()
ID_toolsMassDefectPlot = wx.NewIdRef()
ID_toolsMassFilter = wx.NewIdRef()
ID_toolsCompoundsSearch = wx.NewIdRef()
ID_toolsPeakDifferences = wx.NewIdRef()
ID_toolsComparePeaklists = wx.NewIdRef()
ID_toolsSpectrumGenerator = wx.NewIdRef()
ID_toolsEnvelopeFit = wx.NewIdRef()
ID_toolsMascot = wx.NewIdRef()
ID_toolsProfound = wx.NewIdRef()
ID_toolsProspector = wx.NewIdRef()
ID_toolsDocumentInfo = wx.NewIdRef()
ID_toolsDocumentReport = wx.NewIdRef()
ID_toolsDocumentExport = wx.NewIdRef()

HK_toolsCalibration = "\tCtrl+R"
HK_toolsRuler = "\tShift+Ctrl+H"
HK_toolsLabelPeak = "\tShift+Ctrl+P"
HK_toolsLabelPoint = "\tShift+Ctrl+I"
HK_toolsLabelEnvelope = "\tShift+Ctrl+E"
HK_toolsDeleteLabel = "\tShift+Ctrl+X"
HK_toolsPeriodicTable = "\tShift+Ctrl+T"
HK_toolsMassCalculator = "\tShift+Ctrl+M"
HK_toolsMassToFormula = "\tShift+Ctrl+B"
HK_toolsMassDefectPlot = "\tShift+Ctrl+O"
HK_toolsMassFilter = "\tShift+Ctrl+F"
HK_toolsCompoundsSearch = "\tShift+Ctrl+U"
HK_toolsPeakDifferences = "\tShift+Ctrl+D"
HK_toolsComparePeaklists = "\tShift+Ctrl+C"
HK_toolsSpectrumGenerator = "\tShift+Ctrl+G"
HK_toolsEnvelopeFit = "\tShift+Ctrl+V"

# library
ID_libraryCompounds = wx.NewIdRef()
ID_libraryModifications = wx.NewIdRef()
ID_libraryMonomers = wx.NewIdRef()
ID_libraryEnzymes = wx.NewIdRef()
ID_libraryReferences = wx.NewIdRef()
ID_libraryMascot = wx.NewIdRef()
ID_libraryPresets = wx.NewIdRef()

# links
ID_linksBiomedMSTools = wx.NewIdRef()
ID_linksBLAST = wx.NewIdRef()
ID_linksClustalW = wx.NewIdRef()
ID_linksDeltaMass = wx.NewIdRef()
ID_linksEMBLEBI = wx.NewIdRef()
ID_linksExpasy = wx.NewIdRef()
ID_linksFASTA = wx.NewIdRef()
ID_linksMatrixScience = wx.NewIdRef()
ID_linksMUSCLE = wx.NewIdRef()
ID_linksNCBI = wx.NewIdRef()
ID_linksPDB = wx.NewIdRef()
ID_linksPIR = wx.NewIdRef()
ID_linksProfound = wx.NewIdRef()
ID_linksProspector = wx.NewIdRef()
ID_linksUniMod = wx.NewIdRef()
ID_linksUniProt = wx.NewIdRef()

# window
ID_windowMaximize = wx.NewIdRef()
ID_windowMinimize = wx.NewIdRef()
ID_windowLayout1 = wx.NewIdRef()
ID_windowLayout2 = wx.NewIdRef()
ID_windowLayout3 = wx.NewIdRef()
ID_windowLayout4 = wx.NewIdRef()

HK_windowLayout1 = "\tF5"
HK_windowLayout2 = "\tF6"
HK_windowLayout3 = "\tF7"
HK_windowLayout4 = "\tF8"

# help
ID_helpAbout = wx.ID_ABOUT
ID_helpHomepage = wx.NewIdRef()
ID_helpForum = wx.NewIdRef()
ID_helpTwitter = wx.NewIdRef()
ID_helpCite = wx.NewIdRef()
ID_helpDonate = wx.NewIdRef()
ID_helpUpdate = wx.NewIdRef()
ID_helpUserGuide = wx.NewIdRef()
ID_helpDownload = wx.NewIdRef()
ID_helpWhatsNew = wx.NewIdRef()

HK_helpUserGuide = "\tF1"

# peaklist panel
ID_peaklistAnnotate = wx.NewIdRef()
ID_peaklistSendToMassToFormula = wx.NewIdRef()

# match panel
ID_matchErrors = wx.NewIdRef()
ID_matchSummary = wx.NewIdRef()

# calibration panel
ID_calibrationReferences = wx.NewIdRef()
ID_calibrationErrors = wx.NewIdRef()

# mass calculator panel
ID_massCalculatorSummary = wx.NewIdRef()
ID_massCalculatorIonSeries = wx.NewIdRef()
ID_massCalculatorPattern = wx.NewIdRef()
ID_massCalculatorCollapse = wx.NewIdRef()

# mass to formula panel
ID_massToFormulaSearchPubChem = wx.NewIdRef()
ID_massToFormulaSearchChemSpider = wx.NewIdRef()
ID_massToFormulaSearchMETLIN = wx.NewIdRef()
ID_massToFormulaSearchHMDB = wx.NewIdRef()
ID_massToFormulaSearchLipidMaps = wx.NewIdRef()

# coumpounds search panel
ID_compoundsSearchCompounds = wx.NewIdRef()
ID_compoundsSearchFormula = wx.NewIdRef()

# mascot panel
ID_mascotPMF = wx.NewIdRef()
ID_mascotMIS = wx.NewIdRef()
ID_mascotSQ = wx.NewIdRef()
ID_mascotQuery = wx.NewIdRef()

# profound panel
ID_profoundPMF = wx.NewIdRef()
ID_profoundQuery = wx.NewIdRef()

# prospector panel
ID_prospectorMSFit = wx.NewIdRef()
ID_prospectorMSTag = wx.NewIdRef()
ID_prospectorQuery = wx.NewIdRef()

# info panel
ID_documentInfoSummary = wx.NewIdRef()
ID_documentInfoSpectrum = wx.NewIdRef()
ID_documentInfoNotes = wx.NewIdRef()

# export panel
ID_documentExportImage = wx.NewIdRef()
ID_documentExportPeaklist = wx.NewIdRef()
ID_documentExportSpectrum = wx.NewIdRef()

# dialog buttons
ID_dlgDontSave = wx.NewIdRef()
ID_dlgSave = wx.NewIdRef()
ID_dlgCancel = wx.NewIdRef()
ID_dlgDiscard = wx.NewIdRef()
ID_dlgReview = wx.NewIdRef()
ID_dlgReplace = wx.NewIdRef()
ID_dlgReplaceAll = wx.NewIdRef()
ID_dlgSkip = wx.NewIdRef()
ID_dlgAppend = wx.NewIdRef()

# list pop-up menu
ID_listViewAll = wx.NewIdRef()
ID_listViewMatched = wx.NewIdRef()
ID_listViewUnmatched = wx.NewIdRef()
ID_listCopy = wx.NewIdRef()
ID_listCopySequence = wx.NewIdRef()
ID_listCopyFormula = wx.NewIdRef()
ID_listSendToMassCalculator = wx.NewIdRef()
ID_listSendToEnvelopeFit = wx.NewIdRef()
