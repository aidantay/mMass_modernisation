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
import base64
import contextlib
import copy
import os
import re
import struct
import sys
import time
import xml.dom.minidom
import zlib
from pathlib import Path

import numpy
import wx

from mmass import mspy

# load modules
from . import config

# DOCUMENT STRUCTURE
# ------------------


class document:
    """Document object definition."""

    def __init__(self):
        self.format = "mSD"
        self.title = ""
        self.path = ""

        self.date = ""
        self.operator = ""
        self.contact = ""
        self.institution = ""
        self.instrument = ""
        self.notes = ""

        self.spectrum = mspy.scan()
        self.annotations = []
        self.sequences = []

        self.colour = (0, 0, 255)
        self.style = wx.SOLID
        self.dirty = False
        self.visible = True
        self.flipped = False
        self.offset = [0, 0]

        # undo buffers
        self.undo = None
        self._spectrumBuff = None
        self._annotationsBuff = None
        self._sequencesBuff = None

    # ----

    def backup(self, items=None):
        """Backup current state for undo."""

        self.undo = items

        # delete old
        self._spectrumBuff = None
        self._annotationsBuff = None
        self._sequencesBuff = None

        if not items:
            return

        # store data
        if "spectrum" in items:
            self._spectrumBuff = copy.deepcopy(self.spectrum)
        if "annotations" in items:
            self._annotationsBuff = copy.deepcopy(self.annotations)
        if "sequences" in items:
            self._sequencesBuff = copy.deepcopy(self.sequences)
        if "notations" in items:
            self._annotationsBuff = copy.deepcopy(self.annotations)
            self._sequencesBuff = copy.deepcopy(self.sequences)

    # ----

    def restore(self):
        """Revert to last stored state."""

        # check undo
        if not self.undo:
            return False

        # revert data
        items = self.undo
        if "spectrum" in items:
            self.spectrum = self._spectrumBuff
        if "annotations" in items:
            self.annotations[:] = self._annotationsBuff[:]
        if "sequences" in items:
            self.sequences[:] = self._sequencesBuff[:]
        if "notations" in items:
            self.annotations[:] = self._annotationsBuff[:]
            for x in range(len(self.sequences)):
                self.sequences[x].matches[:] = self._sequencesBuff[x].matches[:]

        # clear buffers
        self.undo = None
        self._spectrumBuff = None
        self._annotationsBuff = None
        self._sequencesBuff = None

        return items

    # ----

    def sortAnnotations(self):
        """Sort annotations by m/z."""

        buff = []
        for item in self.annotations:
            buff.append((item.mz, item))
        buff.sort()

        # remove formula duplicates
        # formulas = []
        # del self.annotations[:]
        # for item in buff:
        #    if not item[1].formula in formulas:
        #        self.annotations.append(item[1])
        #        formulas.append(item[1].formula)

        del self.annotations[:]
        for item in buff:
            self.annotations.append(item[1])

    # ----

    def sortSequences(self):
        """Sort sequences by titles."""

        # get sequences
        sequences = []
        for sequence in self.sequences:
            sequences.append((sequence.title, sequence))
        sequences.sort()

        # update document
        del self.sequences[:]
        for _title, sequence in sequences:
            self.sequences.append(sequence)

    # ----

    def sortSequenceMatches(self):
        """Sort sequence matches by m/z."""

        for sequence in self.sequences:
            buff = []
            for item in sequence.matches:
                buff.append((item.mz, item))
            buff.sort()

            del sequence.matches[:]
            for item in buff:
                sequence.matches.append(item[1])

    # ----

    def msd(self):
        """Make mSD XML."""

        buff = '<?xml version="1.0" encoding="utf-8" ?>\n'
        buff += '<mSD version="2.2">\n\n'

        # format description
        buff += "  <description>\n"
        buff += f"    <title>{self._escape(self.title)}</title>\n"
        buff += f'    <date value="{self._escape(self.date)}" />\n'
        buff += f'    <operator value="{self._escape(self.operator)}" />\n'
        buff += f'    <contact value="{self._escape(self.contact)}" />\n'
        buff += f'    <institution value="{self._escape(self.institution)}" />\n'
        buff += f'    <instrument value="{self._escape(self.instrument)}" />\n'
        buff += f"    <notes>{self._escape(self.notes)}</notes>\n"
        buff += "  </description>\n\n"

        # format spectrum
        precision = config.main["dataPrecision"]
        endian = sys.byteorder
        points = self.spectrum.profile
        mzArray, intArray = self._convertSpectrum(points, precision)
        attributes = f'points="{len(points)}"'
        if self.spectrum.scanNumber is not None:
            attributes += f' scanNumber="{self.spectrum.scanNumber}"'
        if self.spectrum.msLevel is not None:
            attributes += f' msLevel="{self.spectrum.msLevel}"'
        if self.spectrum.retentionTime is not None:
            attributes += f' retentionTime="{self.spectrum.retentionTime}"'
        if self.spectrum.precursorMZ is not None:
            attributes += f' precursorMZ="{self.spectrum.precursorMZ}"'
        if self.spectrum.precursorCharge is not None:
            attributes += f' precursorCharge="{self.spectrum.precursorCharge}"'
        if self.spectrum.polarity is not None:
            attributes += f' polarity="{self.spectrum.polarity}"'

        buff += f"  <spectrum {attributes}>\n"
        if len(points) > 0:
            buff += f'    <mzArray precision="{precision}" compression="zlib" endian="{endian}">{mzArray}</mzArray>\n'
            buff += f'    <intArray precision="{precision}" compression="zlib" endian="{endian}">{intArray}</intArray>\n'
        buff += "  </spectrum>\n\n"

        # format peaklist
        if len(self.spectrum.peaklist):
            buff += "  <peaklist>\n"
            for peak in self.spectrum.peaklist:
                attributes = f'mz="{peak.mz:.6f}" intensity="{peak.ai:.6f}" baseline="{peak.base:.6f}"'
                if peak.sn is not None:
                    attributes += f' sn="{peak.sn:.3f}"'
                if peak.charge is not None:
                    attributes += ' charge="%d"' % peak.charge
                if peak.isotope is not None:
                    attributes += ' isotope="%d"' % peak.isotope
                if peak.fwhm is not None:
                    attributes += f' fwhm="{peak.fwhm:.6f}"'
                if peak.group:
                    attributes += f' group="{self._escape(peak.group)}"'
                buff += f"    <peak {attributes} />\n"
            buff += "  </peaklist>\n\n"

        # format annotations
        if len(self.annotations):
            buff += "  <annotations>\n"
            for annot in self.annotations:
                attributes = f'peakMZ="{annot.mz:.6f}" peakIntensity="{annot.ai:.6f}" peakBaseline="{annot.base:.6f}"'
                if annot.charge is not None:
                    attributes += ' charge="%d"' % annot.charge
                if annot.radical:
                    attributes += ' radical="1"'
                if annot.theoretical is not None:
                    attributes += f' calcMZ="{annot.theoretical:.6f}"'
                if annot.formula is not None:
                    attributes += f' formula="{annot.formula}"'
                buff += f"    <annotation {attributes}>{self._escape(annot.label)}</annotation>\n"
            buff += "  </annotations>\n\n"

        # format sequences
        if len(self.sequences):
            buff += "  <sequences>\n\n"
            for index, sequence in enumerate(self.sequences):
                buff += f'    <sequence index="{index}">\n'
                buff += f"      <title>{self._escape(sequence.title)}</title>\n"
                buff += "      <accession>{}</accession>\n".format(
                    self._escape(sequence.accession)
                )

                attributes = f'type="{sequence.chainType}"'
                if sequence.cyclic:
                    attributes += ' cyclic="1"'
                buff += "      <seq {}>{}</seq>\n".format(
                    attributes, sequence.format("S")
                )

                # save monomers for custom sequences
                if sequence.chainType != "aminoacids":
                    buff += "      <monomers>\n"
                    savedMonomers = []
                    for abbr in sequence.chain:
                        if abbr not in savedMonomers:
                            savedMonomers.append(abbr)
                            formula = mspy.monomers[abbr].formula
                            buff += f'        <monomer abbr="{abbr}" formula="{formula}" />\n'
                    buff += "      </monomers>\n"

                # format modifications
                if len(sequence.modifications):
                    buff += "      <modifications>\n"
                    for mod in sequence.modifications:
                        gainFormula = mspy.modifications[mod[0]].gainFormula
                        lossFormula = mspy.modifications[mod[0]].lossFormula
                        modtype = "fixed"
                        if mod[2] == "v":
                            modtype = "variable"
                        buff += f'        <modification name="{mod[0]}" position="{mod[1]}" type="{modtype}" gainFormula="{gainFormula}" lossFormula="{lossFormula}" />\n'
                    buff += "      </modifications>\n"

                # format matches
                if len(sequence.matches):
                    buff += "      <matches>\n"
                    for match in sequence.matches:
                        attributes = f'peakMZ="{match.mz:.6f}" peakIntensity="{match.ai:.6f}" peakBaseline="{match.base:.6f}"'
                        if match.charge is not None:
                            attributes += ' charge="%d"' % match.charge
                        if match.radical:
                            attributes += ' radical="1"'
                        if match.theoretical is not None:
                            attributes += f' calcMZ="{match.theoretical:.6f}"'
                        if match.formula is not None:
                            attributes += f' formula="{match.formula}"'
                        if match.sequenceRange is not None:
                            attributes += ' sequenceRange="%d-%d"' % tuple(
                                match.sequenceRange
                            )
                        if match.fragmentSerie is not None:
                            attributes += f' fragmentSerie="{match.fragmentSerie}"'
                        if match.fragmentIndex is not None:
                            attributes += f' fragmentIndex="{match.fragmentIndex}"'
                        buff += f"        <match {attributes}>{self._escape(match.label)}</match>\n"
                    buff += "      </matches>\n"

                buff += "    </sequence>\n\n"
            buff += "  </sequences>\n\n"

        buff += "</mSD>\n"

        return buff

    # ----

    def report(self, image=None):
        """Get HTML report."""

        mzFormat = "%0." + repr(config.main["mzDigits"]) + "f"
        intFormat = "%0." + repr(config.main["intDigits"]) + "f"
        ppmFormat = "%0." + repr(config.main["ppmDigits"]) + "f"

        # add header
        buff = REPORT_HEADER

        # add basic file info
        scanNumber = ""
        retentionTime = ""
        msLevel = ""
        precursorMZ = ""
        polarity = "unknown"
        points = len(self.spectrum.profile)
        peaks = len(self.spectrum.peaklist)

        basePeak = self.spectrum.peaklist.basepeak
        if basePeak:
            basePeak = basePeak.intensity

        if self.spectrum.scanNumber is not None:
            scanNumber = self.spectrum.scanNumber
        if self.spectrum.retentionTime is not None:
            retentionTime = self.spectrum.retentionTime
        if self.spectrum.msLevel is not None:
            msLevel = self.spectrum.msLevel
        if self.spectrum.precursorMZ is not None:
            precursorMZ = self.spectrum.precursorMZ

        if self.spectrum.polarity == 1:
            polarity = "positive"
        elif self.spectrum.polarity == -1:
            polarity = "negative"

        buff += f"  <h1>mMass Report: <span>{self.title}</span></h1>\n"
        buff += '  <table id="tableMainInfo">\n'
        buff += "    <tbody>\n"
        buff += f"      <tr><th>Date</th><td>{self.date}</td><th>Scan Number</th><td>{scanNumber}</td></tr>\n"
        buff += f"      <tr><th>Operator</th><td>{self.operator}</td><th>Retention Time</th><td>{retentionTime}</td></tr>\n"
        buff += f"      <tr><th>Contact</th><td>{self.contact}</td><th>MS Level</th><td>{msLevel}</td></tr>\n"
        buff += f"      <tr><th>Institution</th><td>{self.institution}</td><th>Precursor m/z</th><td>{precursorMZ}</td></tr>\n"
        buff += f"      <tr><th>Instrument</th><td>{self.instrument}</td><th>Polarity</th><td>{polarity}</td></tr>\n"
        buff += f"      <tr><th>&nbsp;</th><td>&nbsp;</td><th>Spectrum Points</th><td>{points}</td></tr>\n"
        buff += f"      <tr><th>&nbsp;</th><td>&nbsp;</td><th>Peak List</th><td>{peaks}</td></tr>\n"
        buff += "    </tbody>\n"
        buff += "  </table>\n"

        # show spectrum
        if image:
            buff += f'  <div id="spectrum"><img src="mmass_spectrum.png?{time.time()}" alt="Mass Spectrum" width="600" height="400" /></div>\n'

        # notes
        if self.notes:
            notes = self.notes.replace("\n", "<br />")
            buff += "  <h2>Notes</h2>\n"
            buff += f'  <p id="notes">{notes}</p>\n'

        # annotations
        if self.annotations:
            tableID = "tableAnnotations1"
            buff += "  <h2>Annotations</h2>\n"
            buff += '  <table id="tableAnnotations">\n'
            buff += "    <thead>\n"
            buff += "      <tr>\n"
            buff += (
                '        <th><a href="" onclick="return sortTable(\''
                + tableID
                + '\', 0);" title="Sort by">Meas.&nbsp;m/z</a></th>\n'
            )
            buff += (
                '        <th><a href="" onclick="return sortTable(\''
                + tableID
                + '\', 1);" title="Sort by">Calc.&nbsp;m/z</a></th>\n'
            )
            buff += (
                '        <th><a href="" onclick="return sortTable(\''
                + tableID
                + '\', 2);" title="Sort by">&delta;&nbsp;(Da)</a></th>\n'
            )
            buff += (
                '        <th><a href="" onclick="return sortTable(\''
                + tableID
                + '\', 3);" title="Sort by">&delta;&nbsp;(ppm)</a></th>\n'
            )
            buff += (
                '        <th><a href="" onclick="return sortTable(\''
                + tableID
                + '\', 4);" title="Sort by">Int.</a></th>\n'
            )
            buff += (
                '        <th><a href="" onclick="return sortTable(\''
                + tableID
                + '\', 5);" title="Sort by">Rel.&nbsp;Int.&nbsp;(%)</a></th>\n'
            )
            buff += (
                '        <th><a href="" onclick="return sortTable(\''
                + tableID
                + '\', 6);" title="Sort by">z</a></th>\n'
            )
            buff += (
                '        <th><a href="" onclick="return sortTable(\''
                + tableID
                + '\', 7);" title="Sort by">Annotation</a></th>\n'
            )
            buff += (
                '        <th><a href="" onclick="return sortTable(\''
                + tableID
                + '\', 8);" title="Sort by">Formula</a></th>\n'
            )
            buff += "      </tr>\n"
            buff += "    </thead>\n"
            buff += f'    <tbody id="{tableID}">\n'
            for annot in self.annotations:
                mz = mzFormat % annot.mz
                absIntensity = intFormat % (annot.ai - annot.base)
                relIntensity = ""
                theoretical = ""
                charge = ""
                deltaDa = ""
                deltaPpm = ""
                formula = ""
                label = self._replaceLabelIDs("compounds", annot.label)

                if basePeak:
                    relIntensity = "%0.2f" % (
                        ((annot.ai - annot.base) / basePeak) * 100
                    )
                if annot.theoretical:
                    theoretical = mzFormat % annot.theoretical
                    deltaDa = mzFormat % annot.delta("Da")
                    deltaPpm = ppmFormat % annot.delta("ppm")
                if annot.formula:
                    formula = annot.formula
                if annot.charge:
                    charge = annot.charge
                if annot.radical:
                    charge = str(annot.charge) + " &bull;"

                buff += f'      <tr><td class="right nowrap">{mz}</td><td class="right nowrap">{theoretical}</td><td class="right nowrap">{deltaDa}</td><td class="right nowrap">{deltaPpm}</td><td class="right nowrap">{absIntensity}</td><td class="right nowrap">{relIntensity}</td><td class="center nowrap">{charge}</td><td>{label}</td><td class="nowrap">{formula}</td></tr>\n'
            buff += "    </tbody>\n"
            buff += "  </table>\n"

        # sequences
        if self.sequences:
            for x, sequence in enumerate(self.sequences):
                accession = self._replaceLabelIDs("sequences", sequence.accession)
                mass = sequence.mass()
                moMass = mzFormat % mass[0]
                avMass = mzFormat % mass[1]
                chain = self._formatSequence(sequence)
                coverage = self._getSequenceCoverage(sequence)
                matchedInt = self._getMatchedIntensity(
                    self.spectrum.peaklist, sequence.matches
                )
                tableID = "tableSequenceMatches%d" % x

                cyclic = ""
                if sequence.cyclic:
                    cyclic = " (Cyclic)"

                if accession:
                    buff += f"  <h2>Sequence - <span>{sequence.title}</span> - [{accession}]</h2>\n"
                else:
                    buff += f"  <h2>Sequence - <span>{sequence.title}</span></h2>\n"

                buff += '  <table id="tableSequenceInfo">\n'
                buff += "    <thead>\n"
                buff += "      <tr><th>Accession</th><th>Length</th><th>Mo. Mass</th><th>Av. Mass</th><th>Coverage</th><th>Matched Int.</th></tr>\n"
                buff += "    </thead>\n"
                buff += "    <tbody>\n"
                buff += f'      <tr><td class="right">{accession}</td><td class="right">{len(sequence)}{cyclic}</td><td class="right">{moMass}</td><td class="right">{avMass}</td><td class="right">{coverage}</td><td class="right">{matchedInt}</td></tr>\n'
                buff += (
                    f'      <tr><td colspan="6" class="sequence">{chain}</td></tr>\n'
                )
                buff += "    </tbody>\n"
                buff += "  </table>\n"

                if sequence.modifications:
                    buff += '  <table id="tableSequenceModifications">\n'
                    buff += "    <thead>\n"
                    buff += "      <tr><th>Position</th><th>Modification</th><th>Type</th><th>Mo.&nbsp;Mass</th><th>Av.&nbsp;Mass</th><th>Formula</th></tr>\n"
                    buff += "    </thead>\n"
                    buff += "    <tbody>\n"
                    for mod in self._formatModifications(sequence):
                        buff += '      <tr><td class="nowrap">{}</td><td>{}</td><td>{}</td><td class="right nowrap">{}</td><td class="right nowrap">{}</td><td class="nowrap">{}</td></tr>\n'.format(
                            *mod
                        )
                    buff += "    </tbody>\n"
                    buff += "  </table>\n"

                if sequence.matches:
                    buff += '  <table id="tableSequenceMatches">\n'
                    buff += "    <thead>\n"
                    buff += "      <tr>\n"
                    buff += (
                        '        <th><a href="" onclick="return sortTable(\''
                        + tableID
                        + '\', 0);" title="Sort by">Meas.&nbsp;m/z</a></th>\n'
                    )
                    buff += (
                        '        <th><a href="" onclick="return sortTable(\''
                        + tableID
                        + '\', 1);" title="Sort by">Calc.&nbsp;m/z</a></th>\n'
                    )
                    buff += (
                        '        <th><a href="" onclick="return sortTable(\''
                        + tableID
                        + '\', 2);" title="Sort by">&delta;&nbsp;(Da)</a></th>\n'
                    )
                    buff += (
                        '        <th><a href="" onclick="return sortTable(\''
                        + tableID
                        + '\', 3);" title="Sort by">&delta;&nbsp;(ppm)</a></th>\n'
                    )
                    buff += (
                        '        <th><a href="" onclick="return sortTable(\''
                        + tableID
                        + '\', 4);" title="Sort by">Rel.&nbsp;Int.&nbsp;(%)</a></th>\n'
                    )
                    buff += (
                        '        <th><a href="" onclick="return sortTable(\''
                        + tableID
                        + '\', 5);" title="Sort by">z</a></th>\n'
                    )
                    buff += (
                        '        <th><a href="" onclick="return sortTable(\''
                        + tableID
                        + '\', 6);" title="Sort by">Annotation</a></th>\n'
                    )
                    buff += (
                        '        <th><a href="" onclick="return sortTable(\''
                        + tableID
                        + '\', 7);" title="Sort by">Formula</a></th>\n'
                    )
                    buff += "      </tr>\n"
                    buff += "    </thead>\n"
                    buff += f'    <tbody id="{tableID}">\n'
                    for m in sequence.matches:
                        mz = mzFormat % m.mz
                        relIntensity = ""
                        theoretical = ""
                        charge = ""
                        deltaDa = ""
                        deltaPpm = ""
                        formula = ""

                        if basePeak:
                            relIntensity = "%0.2f" % (
                                ((m.ai - m.base) / basePeak) * 100
                            )
                        if m.theoretical:
                            theoretical = mzFormat % m.theoretical
                            deltaDa = mzFormat % m.delta("Da")
                            deltaPpm = ppmFormat % m.delta("ppm")
                        if m.formula:
                            formula = m.formula
                        if m.charge:
                            charge = m.charge
                        if m.radical:
                            charge = str(m.charge) + " &bull;"

                        buff += f'      <tr><td class="right nowrap">{mz}</td><td class="right nowrap">{theoretical}</td><td class="right nowrap">{deltaDa}</td><td class="right nowrap">{deltaPpm}</td><td class="right nowrap">{relIntensity}</td><td class="center nowrap">{charge}</td><td>{m.label}</td><td class="nowrap">{formula}</td></tr>\n'
                    buff += "    </tbody>\n"
                    buff += "  </table>\n"

        # add footer
        buff += '  <p id="footer">Generated by mMass &bull; Open Source Mass Spectrometry Tool &bull; <a href="http://www.mmass.org/" title="mMass homepage">www.mmass.org</a></p>\n'
        buff += "</body>\n"
        buff += "</html>"

        return buff

    # ----

    def _escape(self, text):
        """Clear special characters such as <> etc."""

        text = text.strip()
        search = ("&", '"', "'", "<", ">")
        replace = ("&amp;", "&quot;", "&#39;", "&lt;", "&gt;")
        for x, item in enumerate(search):
            text = text.replace(item, replace[x])

        return text

    # ----

    def _convertSpectrum(self, spectrum, precision="f"):
        """Convert spectrum data to compressed binary format coded by base64."""

        # get precision
        if precision == 32:
            precision = "f"
        elif precision == 64:
            precision = "d"

        # convert data to binary
        mzArray = b""
        intArray = b""
        for point in spectrum:
            mzArray += struct.pack(precision, point[0])
            intArray += struct.pack(precision, point[1])

        # compress data by gz
        mzArray = zlib.compress(mzArray)
        intArray = zlib.compress(intArray)

        # convert to ascii by base64
        mzArray = base64.b64encode(mzArray).decode("ascii")
        intArray = base64.b64encode(intArray).decode("ascii")

        return mzArray, intArray

    # ----

    def _formatSequence(self, sequence):
        """Format sequence for report."""

        # get coverage
        coverage = len(sequence) * [0]
        for m in sequence.matches:
            if m.sequenceRange:
                for i in range(m.sequenceRange[0] - 1, m.sequenceRange[1]):
                    coverage[i] = 1

        # format sequence
        buff = ""
        for x, monomer in enumerate(sequence):
            attributes = ""

            if sequence.ismodified(x, True):
                attributes += "modified "
            if coverage[x]:
                attributes += "matched "

            if attributes:
                buff += f'<span class="{attributes}">{monomer}</span>'
            else:
                buff += monomer

            if sequence.chainType != "aminoacids" and (x + 1) != len(sequence):
                buff += " | "
            elif not (x + 1) % 10:
                buff += " "

        return buff

    # ----

    def _formatModifications(self, sequence):
        """Format sequence modifications for report."""

        buff = []

        format = "%0." + repr(config.main["mzDigits"]) + "f"
        for mod in sequence.modifications:
            name = mod[0]

            # format position
            if isinstance(mod[1], int):
                position = f"{sequence[mod[1]]} {mod[1] + 1}"
            elif mod[1] == "nTerm":
                position = "N-terminus"
            elif mod[1] == "cTerm":
                position = "C-terminus"
            else:
                position = "All " + mod[1]

            # format type
            modtype = "fixed" if mod[2] == "f" else "variable"

            # format masses
            mass = mspy.modifications[name].mass
            massMo = format % mass[0]
            massAv = format % mass[1]

            # format formula
            formula = mspy.modifications[name].gainFormula
            if mspy.modifications[name].lossFormula:
                formula += " - " + mspy.modifications[name].lossFormula

            # append data
            buff.append((position, name, modtype, massMo, massAv, formula))

        return buff

    # ----

    def _getSequenceCoverage(self, sequence):
        """Get sequence coverage from matches."""

        # get ranges
        ranges = []
        for m in sequence.matches:
            if m.sequenceRange is not None:
                ranges.append(m.sequenceRange)

        # get coverage
        coverage = mspy.coverage(ranges, len(sequence))
        coverage = f"{coverage:.1f} "
        coverage += "%"

        return coverage

    # ----

    def _getMatchedIntensity(self, peaklist, matches):
        """Get total matched intensity."""

        # get total intensity
        totalInt = 0
        buff = {}
        for peak in peaklist:
            totalInt += peak.intensity
            buff[round(peak.mz, 6)] = peak.intensity

        # get matched intensity
        matchedInt = 0
        for item in matches:
            mz = round(item.mz, 6)
            if mz in buff:
                matchedInt += buff[mz]
                del buff[mz]

        # get percentage
        matched = "0.0"
        if totalInt:
            matched = "%.1f" % (100 * matchedInt / totalInt)
        matched += " %"

        return matched

    # ----

    def _replaceLabelIDs(self, section, label):
        """Replace IDs with links in annotations."""

        # replace IDs
        for name in config.replacements[section]:
            self._currentReplacement = (section, name)
            label = re.sub(
                config.replacements[section][name]["pattern"], self._replaceIDs, label
            )

        return label

    # ----

    def _replaceIDs(self, matchobj):
        """Replace IDs to links."""

        section, name = self._currentReplacement
        url = config.replacements[section][name]["url"] % matchobj.group(1)
        return f'<a href="{url}" title="More information...">{matchobj.group(0)}</a>'

    # ----


# ANNOTATION OBJECT
# -----------------


class annotation:
    """Annotation object definition."""

    def __init__(
        self,
        label,
        mz,
        ai,
        base=0.0,
        charge=None,
        radical=None,
        theoretical=None,
        formula=None,
    ):
        self.label = label
        self.mz = mz
        self.ai = ai
        self.base = base
        self.charge = charge
        self.radical = radical
        self.theoretical = theoretical
        self.formula = formula

    # ----

    def delta(self, units):
        """Get error in specified units."""

        if self.theoretical is not None:
            return mspy.delta(self.mz, self.theoretical, units)
        return None

    # ----


# SEQUENCE MATCH OBJECT
# ---------------------


class match:
    """Match object definition."""

    def __init__(
        self,
        label,
        mz,
        ai,
        base=0.0,
        charge=None,
        radical=None,
        theoretical=None,
        formula=None,
    ):
        self.label = label
        self.mz = mz
        self.ai = ai
        self.base = base
        self.charge = charge
        self.radical = radical
        self.theoretical = theoretical
        self.formula = formula

        self.sequenceRange = None
        self.fragmentSerie = None
        self.fragmentIndex = None

    # ----

    def delta(self, units):
        """Get error in specified units."""

        if self.theoretical is not None:
            return mspy.delta(self.mz, self.theoretical, units)
        return None

    # ----


# MSD FORMAT PARSER
# -----------------


class parseMSD:
    """Parse data from mSD files."""

    def __init__(self, path):
        self.path = path
        self.errors = []
        self._version = None
        self._parsedData = None

        # init new document
        self.document = document()
        self.document.format = "mSD"
        self.document.path = path

    # ----

    def getDocument(self):
        """Get document."""

        self.errors = []

        # parse data
        if not self._parsedData:
            try:
                self._parsedData = xml.dom.minidom.parse(self.path)
                self._version = self._getVersion()
            except Exception:
                return False

        # get data
        if self._version == "1.0":
            self.handleDescription()
            self.handleSpectrum()
            self.handlePeaklist_10()
            self.handleSequences_10()
            _dirName, fileName = os.path.split(self.path)
            self.document.title = fileName[:-4]
        else:
            self.handleDescription()
            self.handleSpectrum()
            self.handlePeaklist()
            self.handleAnnotations()
            self.handleSequences()

        return self.document

    # ----

    def getSequences(self):
        """Get list of available sequences."""

        self.errors = []

        # parse data
        if not self._parsedData:
            try:
                self._parsedData = xml.dom.minidom.parse(self.path)
                self._version = self._getVersion()
            except Exception:
                return False

        # set handler
        if self._version == "1.0":
            handler = self.handleSequence_10
        else:
            handler = self.handleSequence

        # get sequence
        data = []
        sequenceTags = self._parsedData.getElementsByTagName("sequence")
        if sequenceTags:
            for sequenceTag in sequenceTags:
                sequence = handler(sequenceTag)
                if sequence:
                    data.append(sequence)

        return data

    # ----

    # CURRENT HANDLERS

    def handleDescription(self):
        """Get document info."""

        # get description
        descriptionTags = self._parsedData.getElementsByTagName("description")
        if descriptionTags:
            titleTags = descriptionTags[0].getElementsByTagName("title")
            if titleTags:
                self.document.title = self._getNodeText(titleTags[0])

            dateTags = descriptionTags[0].getElementsByTagName("date")
            if dateTags:
                self.document.date = dateTags[0].getAttribute("value")

            operatorTags = descriptionTags[0].getElementsByTagName("operator")
            if operatorTags:
                self.document.operator = operatorTags[0].getAttribute("value")

            contactTags = descriptionTags[0].getElementsByTagName("contact")
            if contactTags:
                self.document.contact = contactTags[0].getAttribute("value")

            institutionTags = descriptionTags[0].getElementsByTagName("institution")
            if institutionTags:
                self.document.institution = institutionTags[0].getAttribute("value")

            instrumentTags = descriptionTags[0].getElementsByTagName("instrument")
            if instrumentTags:
                self.document.instrument = instrumentTags[0].getAttribute("value")

            notesTags = descriptionTags[0].getElementsByTagName("notes")
            if notesTags:
                self.document.notes = self._getNodeText(notesTags[0])

    # ----

    def handleSpectrum(self):
        """Get spectrum data."""

        # get spectrum
        spectrumTags = self._parsedData.getElementsByTagName("spectrum")
        if spectrumTags:
            # get metadata
            scanNumber = spectrumTags[0].getAttribute("scanNumber")
            if scanNumber:
                with contextlib.suppress(ValueError):
                    self.document.spectrum.scanNumber = int(scanNumber)

            msLevel = spectrumTags[0].getAttribute("msLevel")
            if msLevel:
                with contextlib.suppress(ValueError):
                    self.document.spectrum.msLevel = int(msLevel)

            retentionTime = spectrumTags[0].getAttribute("retentionTime")
            if retentionTime:
                with contextlib.suppress(ValueError):
                    self.document.spectrum.retentionTime = float(retentionTime)

            precursorMZ = spectrumTags[0].getAttribute("precursorMZ")
            if precursorMZ:
                with contextlib.suppress(ValueError):
                    self.document.spectrum.precursorMZ = float(precursorMZ)

            precursorCharge = spectrumTags[0].getAttribute("precursorCharge")
            if precursorCharge:
                with contextlib.suppress(ValueError):
                    self.document.spectrum.precursorCharge = int(precursorCharge)

            polarity = spectrumTags[0].getAttribute("polarity")
            if polarity:
                with contextlib.suppress(ValueError):
                    self.document.spectrum.polarity = int(polarity)

            # get mzArray
            mzData = None
            mzArrayTags = spectrumTags[0].getElementsByTagName("mzArray")
            if mzArrayTags:
                compression = False
                if mzArrayTags[0].hasAttribute("compression"):
                    compression = mzArrayTags[0].getAttribute("compression")

                precision = "f"
                if (
                    mzArrayTags[0].hasAttribute("precision")
                    and mzArrayTags[0].getAttribute("precision") == "64"
                ):
                    precision = "d"

                endian = "<"
                if mzArrayTags[0].getAttribute("endian") == "big":
                    endian = ">"

                mzData = self._getNodeText(mzArrayTags[0])
                mzData = self._convertDataPoints(mzData, compression, precision, endian)

            # get intArray
            intData = None
            intArrayTags = spectrumTags[0].getElementsByTagName("intArray")
            if intArrayTags:
                compression = False
                if intArrayTags[0].hasAttribute("compression"):
                    compression = intArrayTags[0].getAttribute("compression")

                precision = "f"
                if (
                    intArrayTags[0].hasAttribute("precision")
                    and intArrayTags[0].getAttribute("precision") == "64"
                ):
                    precision = "d"

                endian = "<"
                if intArrayTags[0].getAttribute("endian") == "big":
                    endian = ">"

                intData = self._getNodeText(intArrayTags[0])
                intData = self._convertDataPoints(
                    intData, compression, precision, endian
                )

            # check data
            if not mzData or not intData:
                return False

            # format data
            mzData = numpy.array(mzData)
            mzData.shape = (-1, 1)

            intData = numpy.array(intData)
            intData.shape = (-1, 1)

            points = numpy.concatenate((mzData, intData), axis=1)
            points = points.copy()

            # add to spectrum
            self.document.spectrum.setprofile(points)
        return None

    # ----

    def handlePeaklist(self):
        """Get peaklist."""

        peaklist = []

        # get peaklist
        peaklistTags = self._parsedData.getElementsByTagName("peaklist")
        if peaklistTags:
            # get peaks
            peakTags = peaklistTags[0].getElementsByTagName("peak")
            for peakTag in peakTags:
                # get data
                try:
                    mz = float(peakTag.getAttribute("mz"))
                    ai = float(peakTag.getAttribute("intensity"))

                    base = 0.0
                    sn = None
                    charge = None
                    isotope = None
                    fwhm = None
                    group = ""

                    if peakTag.hasAttribute("baseline"):
                        base = float(peakTag.getAttribute("baseline"))
                    if peakTag.hasAttribute("sn"):
                        sn = float(peakTag.getAttribute("sn"))
                    if peakTag.hasAttribute("charge"):
                        charge = int(peakTag.getAttribute("charge"))
                    if peakTag.hasAttribute("isotope"):
                        isotope = int(peakTag.getAttribute("isotope"))
                    if peakTag.hasAttribute("fwhm"):
                        fwhm = float(peakTag.getAttribute("fwhm"))
                    if peakTag.hasAttribute("group"):
                        group = peakTag.getAttribute("group")

                except ValueError:
                    self.errors.append("Incorrect peak data.")
                    continue

                # make peak
                peak = mspy.peak(
                    mz=mz,
                    ai=ai,
                    base=base,
                    sn=sn,
                    charge=charge,
                    isotope=isotope,
                    fwhm=fwhm,
                    group=group,
                )
                peaklist.append(peak)

        # add peaklist to document
        peaklist = mspy.peaklist(peaklist)
        self.document.spectrum.setpeaklist(peaklist)

    # ----

    def handleAnnotations(self):
        """Get annotations."""

        # get annotations
        annotationsTags = self._parsedData.getElementsByTagName("annotations")
        if annotationsTags:
            # get annotation
            annotationTags = annotationsTags[0].getElementsByTagName("annotation")
            for annotationTag in annotationTags:
                # get data
                try:
                    label = self._getNodeText(annotationTag)
                    mz = float(annotationTag.getAttribute("peakMZ"))
                    ai = 0.0
                    base = 0.0
                    charge = None
                    radical = None
                    theoretical = None
                    formula = None

                    if annotationTag.hasAttribute("peakIntensity"):
                        ai = float(annotationTag.getAttribute("peakIntensity"))
                    if annotationTag.hasAttribute("peakBaseline"):
                        base = float(annotationTag.getAttribute("peakBaseline"))
                    if annotationTag.hasAttribute("charge"):
                        charge = int(annotationTag.getAttribute("charge"))
                    if annotationTag.hasAttribute("radical"):
                        radical = int(annotationTag.getAttribute("radical"))
                    if annotationTag.hasAttribute("calcMZ"):
                        theoretical = float(annotationTag.getAttribute("calcMZ"))
                    if annotationTag.hasAttribute("formula"):
                        formula = annotationTag.getAttribute("formula")

                    annot = annotation(
                        label=label,
                        mz=mz,
                        ai=ai,
                        base=base,
                        charge=charge,
                        radical=radical,
                        theoretical=theoretical,
                        formula=formula,
                    )

                except ValueError:
                    self.errors.append("Incorrect annotation data.")
                    continue

                # append annotation
                self.document.annotations.append(annot)

            # sort annotations by mz
            self.document.sortAnnotations()

    # ----

    def handleSequences(self):
        """Get sequences."""

        # get sequences
        sequencesTags = self._parsedData.getElementsByTagName("sequences")
        if sequencesTags:
            sequenceTags = sequencesTags[0].getElementsByTagName("sequence")
            for sequenceTag in sequenceTags:
                sequence = self.handleSequence(sequenceTag)
                if sequence:
                    self.document.sequences.append(sequence)

    # ----

    def handleSequence(self, sequenceTag):
        """Get sequence."""

        # get title
        title = ""
        titleTags = sequenceTag.getElementsByTagName("title")
        if titleTags:
            title = self._getNodeText(titleTags[0])

        # get accession
        accession = ""
        accessionTags = sequenceTag.getElementsByTagName("accession")
        if accessionTags:
            accession = self._getNodeText(accessionTags[0])

        # get chain
        chain = ""
        chainType = "aminoacids"
        cyclic = False
        seqTags = sequenceTag.getElementsByTagName("seq")
        if seqTags:
            chain = self._getNodeText(seqTags[0])

            if seqTags[0].hasAttribute("type"):
                chainType = str(seqTags[0].getAttribute("type"))
            if seqTags[0].hasAttribute("cyclic"):
                with contextlib.suppress(ValueError):
                    cyclic = bool(int(seqTags[0].getAttribute("cyclic")))

        # get monomers
        monomerTags = sequenceTag.getElementsByTagName("monomer")
        for monomerTag in monomerTags:
            abbr = monomerTag.getAttribute("abbr")
            formula = monomerTag.getAttribute("formula")
            if abbr not in mspy.monomers:
                self._addMonomer(abbr, formula)

        # make sequence
        try:
            sequence = mspy.sequence(
                chain,
                title=title,
                accession=accession,
                chainType=chainType,
                cyclic=cyclic,
            )
            sequence.matches = []
        except Exception:
            self.errors.append("Unknown monomers in sequence data.")
            return False

        # get modifications
        modificationTags = sequenceTag.getElementsByTagName("modification")
        for modificationTag in modificationTags:
            name = modificationTag.getAttribute("name")
            position = modificationTag.getAttribute("position")
            gainFormula = modificationTag.getAttribute("gainFormula")
            lossFormula = modificationTag.getAttribute("lossFormula")

            with contextlib.suppress(BaseException):
                position = int(position)

            modtype = "f"
            if modificationTag.getAttribute("type") == "variable":
                modtype = "v"

            if name in mspy.modifications:
                sequence.modify(name, position, modtype)
            else:
                if self._addModification(name, gainFormula, lossFormula):
                    sequence.modify(name, position, modtype)

        # get matches
        sequence.matches[:] = self.handleSequenceMatches(sequenceTag)

        return sequence

    # ----

    def handleSequenceMatches(self, sequenceTag):
        """Get sequence amtches."""

        # get matches
        matches = []
        matchTags = sequenceTag.getElementsByTagName("match")
        for matchTag in matchTags:
            try:
                label = self._getNodeText(matchTag)
                mz = float(matchTag.getAttribute("peakMZ"))

                ai = 0.0
                base = 0.0
                charge = None
                radical = None
                theoretical = None
                formula = None
                sequenceRange = None
                fragmentSerie = None
                fragmentIndex = None

                if matchTag.hasAttribute("peakIntensity"):
                    ai = float(matchTag.getAttribute("peakIntensity"))
                if matchTag.hasAttribute("peakBaseline"):
                    base = float(matchTag.getAttribute("peakBaseline"))
                if matchTag.hasAttribute("charge"):
                    charge = int(matchTag.getAttribute("charge"))
                if matchTag.hasAttribute("radical"):
                    radical = int(matchTag.getAttribute("radical"))
                if matchTag.hasAttribute("calcMZ"):
                    theoretical = float(matchTag.getAttribute("calcMZ"))
                if matchTag.hasAttribute("formula"):
                    formula = matchTag.getAttribute("formula")
                if matchTag.hasAttribute("sequenceRange"):
                    sequenceRange = [
                        int(x)
                        for x in matchTag.getAttribute("sequenceRange").split("-")
                    ]
                if matchTag.hasAttribute("fragmentSerie"):
                    fragmentSerie = matchTag.getAttribute("fragmentSerie")
                if matchTag.hasAttribute("fragmentIndex"):
                    fragmentIndex = int(matchTag.getAttribute("fragmentIndex"))

                m = match(
                    label=label,
                    mz=mz,
                    ai=ai,
                    base=base,
                    charge=charge,
                    radical=radical,
                    theoretical=theoretical,
                    formula=formula,
                )
                m.sequenceRange = sequenceRange
                m.fragmentSerie = fragmentSerie
                m.fragmentIndex = fragmentIndex

                matches.append(m)

            except ValueError:
                self.errors.append("Incorrect sequence match data.")
                continue

        return matches

    # ----

    # OLDER VERSIONS

    def handlePeaklist_10(self):
        """Get peaklist from mSD version 1.0."""

        peaklist = []

        # get peaklist
        peaklistTags = self._parsedData.getElementsByTagName("peaklist")
        if peaklistTags:
            # get peaks
            peakTags = peaklistTags[0].getElementsByTagName("peak")
            for peakTag in peakTags:
                # get data
                try:
                    mz = float(peakTag.getAttribute("mass"))
                    ai = float(peakTag.getAttribute("intens"))
                    annot = peakTag.getAttribute("annots")
                except ValueError:
                    self.errors.append("Incorrect peak data.")
                    continue

                # make peak
                peak = mspy.peak(mz=mz, ai=ai)
                peaklist.append(peak)

                # make annotation
                if annot:
                    self.document.annotations.append(
                        annotation(label=annot, mz=mz, ai=ai)
                    )

        # add peaklist to document
        peaklist = mspy.peaklist(peaklist)
        self.document.spectrum.setpeaklist(peaklist)

    # ----

    def handleSequences_10(self):
        """Get sequences from mSD version 1.0."""

        # get sequences
        sequencesTags = self._parsedData.getElementsByTagName("sequences")
        if sequencesTags:
            sequenceTags = sequencesTags[0].getElementsByTagName("sequence")
            for sequenceTag in sequenceTags:
                sequence = self.handleSequence_10(sequenceTag)
                if sequence:
                    self.document.sequences.append(sequence)

    # ----

    def handleSequence_10(self, sequenceTag):
        """Get sequence from mSD version 1.0."""

        # get title
        title = ""
        titleTags = sequenceTag.getElementsByTagName("title")
        if titleTags:
            title = self._getNodeText(titleTags[0])

        # get sequence
        chain = ""
        seqTags = sequenceTag.getElementsByTagName("seq")
        if seqTags:
            chain = self._getNodeText(seqTags[0])

        # make sequence
        try:
            sequence = mspy.sequence(chain, title=title)
            sequence.matches = []
        except Exception:
            self.errors.append("Unknown monomers in sequence data.")
            return False

        # get modifications
        modificationTags = sequenceTag.getElementsByTagName("modification")
        for modificationTag in modificationTags:
            name = modificationTag.getAttribute("name")
            amino = modificationTag.getAttribute("amino")
            position = modificationTag.getAttribute("position")
            gainFormula = modificationTag.getAttribute("gain")
            lossFormula = modificationTag.getAttribute("loss")

            position = int(position) - 1 if position else amino

            if name in mspy.modifications:
                sequence.modify(name, position)
            else:
                if self._addModification(name, gainFormula, lossFormula):
                    sequence.modify(name, position)

        return sequence

    # ----

    # HELPERS

    def _convertDataPoints(self, data, compression, precision="f", endian="<"):
        """Convert spectrum data points."""

        try:
            # convert from base64
            data = base64.b64decode(data)

            # decompress
            if compression:
                data = zlib.decompress(data)

            # convert form binary
            count = len(data) // struct.calcsize(endian + precision)
            return struct.unpack(endian + precision * int(count), data[0 : len(data)])

        except Exception:
            self.errors.append("Incorrect spectrum data.")
            return False

    # ----

    def _getVersion(self):
        """Get mSD format version."""

        # mSD document
        mSDTags = self._parsedData.getElementsByTagName("mSD")
        if mSDTags:
            return mSDTags[0].getAttribute("version")

        # mMassDoc document
        mMassDocTags = self._parsedData.getElementsByTagName("mMassDoc")
        if mMassDocTags:
            return mMassDocTags[0].getAttribute("version")
        return None

    # ----

    def _getNodeText(self, node):
        """Get text from node list."""

        # get text
        buff = ""
        for node in node.childNodes:
            if node.nodeType == node.TEXT_NODE:
                buff += node.data

        # replace back some characters
        search = ("&amp;", "&quot;", "&#39;", "&lt;", "&gt;")
        replace = ("&", '"', "'", "<", ">")
        for x, item in enumerate(search):
            buff = buff.replace(item, replace[x])

        return buff

    # ----

    def _addMonomer(self, abbr, formula, losses=None, name="", category=""):
        """Add monomer to library."""

        # check data
        if losses is None:
            losses = []
        if not abbr or not formula or not re.match(r"^[A-Za-z0-9\-_]*$", abbr):
            return False

        # add new monomer
        try:
            monomer = mspy.monomer(
                abbr=abbr, formula=formula, losses=losses, name=name, category=category
            )
            mspy.monomers[abbr] = monomer
            mspy.saveMonomers(Path(config.confdir) / "monomers.xml")
            return True
        except Exception:
            return False

    # ----

    def _addModification(self, name, gainFormula, lossFormula, aminoSpecifity=""):
        """Add modification to library."""

        # check data
        if not name or not (gainFormula or lossFormula):
            return False

        # add new modification
        try:
            modification = mspy.modification(
                name=name,
                gainFormula=gainFormula,
                lossFormula=lossFormula,
                aminoSpecifity=aminoSpecifity,
            )
            mspy.modifications[name] = modification
            mspy.saveModifications(Path(config.confdir) / "modifications.xml")
            return True
        except Exception:
            return False

    # ----


# REPORT
# ------

REPORT_HEADER = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">

<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="cs" lang="cs">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8" />
  <meta name="author" content="Created by mMass - Open Source Mass Spectrometry Tool; www.mmass.org" />
  <title>mMass Report</title>
  <style type="text/css">
  <!--
    body{margin: 5%; font-size: 8.5pt; font-family: Arial, Verdana, Geneva, Helvetica, sans-serif;}
    h1{font-size: 1.5em; text-align: center; margin: 1em 0; border-bottom: 3px double #000;}
    h1 span{font-style: italic;}
    h2{font-size: 1.2em; text-align: left; margin: 2em 0 1em 0; border-bottom: 1px solid #000;}
    h2 span{font-style: italic;}
    table{border-collapse: collapse; margin: 1.5em auto; width: 100%; background-color: #fff;}
    thead{display: table-header-group;}
    th,td{font-size: .75em; border: 1px solid #aaa; padding: .3em; vertical-align: top; text-align: left;}
    html>body th, html>body td{font-size: .9em;}
    th{text-align: center; color: #000; background-color: #ccc;}
    th a{text-align: center; color: #000; background-color: #ccc; text-decoration: none;}
    #tableMainInfo th{text-align: right; width: 15%;}
    #tableMainInfo td{text-align: left;}
    #spectrum{text-align: center;}
    #footer{font-size: .8em; font-style: italic; text-align: center; color: #aaa; margin: 2em 0 1em 0; padding-top: 0.5em; border-top: 1px solid #000;}
    .left{text-align: left;}
    .right{text-align: right;}
    .center{text-align: center;}
    .nowrap{white-space:nowrap;}
    .sequence{font-size: 1.1em; font-family: monospace;}
    .modified{color: #f00; font-weight: bold;}
    .matched{text-decoration: underline;}
  -->
  </style>
  <script type="text/javascript">
    // This script was adapted from the original script by Mike Hall (www.brainjar.com)
    //<![CDATA[

    // for IE
    if (document.ELEMENT_NODE == null) {
      document.ELEMENT_NODE = 1;
      document.TEXT_NODE = 3;
    }

    // sort table
    function sortTable(id, col) {

      // get table
      var tblEl = document.getElementById(id);

      // init sorter
      if (tblEl.reverseSort == null) {
        tblEl.reverseSort = new Array();
      }

      // reverse sorting
      if (col == tblEl.lastColumn) {
        tblEl.reverseSort[col] = !tblEl.reverseSort[col];
      }

      // remember current column
      tblEl.lastColumn = col;

      // sort table
      var tmpEl;
      var i, j;
      var minVal, minIdx;
      var testVal;
      var cmp;

      for (i = 0; i < tblEl.rows.length - 1; i++) {
        minIdx = i;
        minVal = getTextValue(tblEl.rows[i].cells[col]);

        // walk in other rows
        for (j = i + 1; j < tblEl.rows.length; j++) {
          testVal = getTextValue(tblEl.rows[j].cells[col]);
          cmp = compareValues(minVal, testVal);

          // reverse sorting
          if (tblEl.reverseSort[col]) {
            cmp = -cmp;
          }

          // set new minimum
          if (cmp > 0) {
            minIdx = j;
            minVal = testVal;
          }
        }

        // move row before
        if (minIdx > i) {
          tmpEl = tblEl.removeChild(tblEl.rows[minIdx]);
          tblEl.insertBefore(tmpEl, tblEl.rows[i]);
        }
      }

      return false;
    }

    // get node text
    function getTextValue(el) {
      var i;
      var s;

      // concatenate values of text nodes
      s = "";
      for (i = 0; i < el.childNodes.length; i++) {
        if (el.childNodes[i].nodeType == document.TEXT_NODE) {
          s += el.childNodes[i].nodeValue;
        } else if (el.childNodes[i].nodeType == document.ELEMENT_NODE && el.childNodes[i].tagName == "BR") {
          s += " ";
        } else {
          s += getTextValue(el.childNodes[i]);
        }
      }

      return s;
    }

    // compare values
    function compareValues(v1, v2) {
      var f1, f2;

      // lowercase values
      v1 = v1.toLowerCase()
      v2 = v2.toLowerCase()

      // try to convert values to floats
      f1 = parseFloat(v1);
      f2 = parseFloat(v2);
      if (!isNaN(f1) && !isNaN(f2)) {
        v1 = f1;
        v2 = f2;
      }

      // compare values
      if (v1 == v2) {
        return 0;
      } else if (v1 > v2) {
        return 1;
      } else {
        return -1;
      }
    }

    //]]>
  </script>
</head>

<body>
"""
