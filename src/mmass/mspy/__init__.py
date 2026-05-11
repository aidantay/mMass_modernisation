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

# load building blocks
from .blocks import (
    Element,
    Enzyme,
    Fragment,
    Modification,
    Monomer,
    blocksdir,
    elements,
    enzymes,
    fragments,
    loadEnzymes,
    loadModifications,
    loadMonomers,
    modifications,
    monomers,
    saveEnzymes,
    saveModifications,
    saveMonomers,
    xml,
)

# load modules
from .mod_basics import (
    ELECTRON_MASS,
    delta,
    frules,
    math,
    md,
    mz,
    nominalmass,
    rdbe,
)
from .mod_calibration import calibration
from .mod_envfit import (
    EnvFit,
    mod_calibration,
    mod_pattern,
    mod_peakpicking,
    mod_signal,
    obj_compound,
    obj_peaklist,
)
from .mod_formulator import calculations, formulator, mod_basics
from .mod_mascot import Mascot, http, webbrowser
from .mod_pattern import (
    gaussian,
    gausslorentzian,
    lorentzian,
    matchpattern,
    pattern,
    profile,
)
from .mod_peakpicking import (
    AVERAGE_AMINO,
    AVERAGE_BASE,
    ISOTOPE_DISTANCE,
    averagine,
    copy,
    deconvolute,
    deisotope,
    envcentroid,
    envmono,
    labelpeak,
    labelpoint,
    labelscan,
    obj_peak,
    patternLookupTable,
)
from .mod_proteo import (
    coverage,
    digest,
    fragmentgains,
    fragmentlosses,
    fragmentserie,
    itertools,
    obj_sequence,
)
from .mod_signal import (
    area,
    baseline,
    basepeak,
    boundaries,
    centroid,
    combine,
    crop,
    intensity,
    interpolate,
    locate,
    maxima,
    movaver,
    multiply,
    noise,
    normalize,
    offset,
    overlay,
    savgol,
    smooth,
    subbase,
    subtract,
    width,
)
from .mod_stopper import CHECK_FORCE_QUIT, STOPPER, ForceQuitError, Stopper, start, stop
from .mod_utils import load, save

# load objects
from .obj_compound import Compound
from .obj_peak import Peak
from .obj_peaklist import Peaklist
from .obj_scan import (
    Scan,
)
from .obj_sequence import (
    Sequence,
    blocks,
)
from .parser_fasta import ParseFASTA
from .parser_mgf import ParseMGF
from .parser_mzdata import ParseMZData
from .parser_mzml import ParseMZML
from .parser_mzxml import ParseMZXML

# load parsers
from .parser_xy import ParseXY
