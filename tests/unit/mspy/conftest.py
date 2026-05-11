import pytest


@pytest.fixture
def sample_xml_single_hit():
    """Sample XML response with a single hit."""
    return '<?xml version="1.0" encoding="UTF-8"?>\n<mascot_search_results>\n  <hit number="1">\n    <protein accession="Q12345">\n      <prot_desc>Test Protein Description</prot_desc>\n      <prot_score>95.5</prot_score>\n      <prot_mass>50000.12</prot_mass>\n      <peptide query="1" rank="1" isbold="1">\n        <pep_seq>PEPTIDER</pep_seq>\n        <pep_score>45.3</pep_score>\n        <pep_calc_mr>900.45</pep_calc_mr>\n      </peptide>\n    </protein>\n  </hit>\n</mascot_search_results>'

@pytest.fixture
def sample_xml_multiple_hits():
    """Sample XML response with multiple hits, proteins, and peptides."""
    return '<?xml version="1.0" encoding="UTF-8"?>\n<mascot_search_results>\n  <hit number="1">\n    <protein accession="Q12345">\n      <prot_desc>Test Protein 1</prot_desc>\n      <prot_score>95.5</prot_score>\n      <peptide query="1" rank="1" isbold="1">\n        <pep_seq>PEPTIDER</pep_seq>\n        <pep_score>45.3</pep_score>\n      </peptide>\n      <peptide query="2" rank="1" isbold="1">\n        <pep_seq>PEPTIDE2</pep_seq>\n        <pep_score>50.1</pep_score>\n      </peptide>\n    </protein>\n    <protein accession="P54321">\n      <prot_desc>Test Protein 2</prot_desc>\n      <prot_score>75.2</prot_score>\n      <peptide query="3" rank="1" isbold="0">\n        <pep_seq>PROTEIN</pep_seq>\n        <pep_score>30.5</pep_score>\n      </peptide>\n    </protein>\n  </hit>\n  <hit number="2">\n    <protein accession="Q99999">\n      <prot_desc>Test Protein 3</prot_desc>\n      <prot_score>60.0</prot_score>\n      <peptide query="4" rank="1" isbold="1">\n        <pep_seq>SEQUENCE</pep_seq>\n        <pep_score>35.7</pep_score>\n      </peptide>\n    </protein>\n  </hit>\n</mascot_search_results>'

@pytest.fixture
def sample_xml_no_hits():
    """Sample XML response with no hits."""
    return '<?xml version="1.0" encoding="UTF-8"?>\n<mascot_search_results>\n</mascot_search_results>'

@pytest.fixture
def sample_parameters():
    """Sample mascot parameters file content."""
    return '[DB]\nSwissProt\nTrEMBL\n\n[CLE]\nTrypsin\nPepsin\n\n[MODS]\nAcetyl (N-term)\nOxidation (M)\n\n[INSTRUMENT]\nDefault\nESI-Q-TOF\n\n[TAXONOMY]\nAll entries\nHomo sapiens\n\n[HIDDEN_MODS]\nLabel:18O(2)\n\n[OPTIONS]\nNone\nInstrument settings\n\n[QUANTITATION]\nNone\nSILAC\n\n'

@pytest.fixture
def sample_parameters_with_empty_lines():
    """Sample parameters content with extra empty lines."""
    return '[DB]\nSwissProt\n\n[CLE]\nTrypsin\n\n'

@pytest.fixture
def sample_search_response():
    """Sample HTML response from mascot search."""
    return '<html>\n<script>\n  var uQuery=\'123\';\n  var uFG=\'2\';\n  var uErr=0;\n  var uUrl="master_results.pl?file=F001234567&REPTYPE=peptide";\n</script>\n</html>'

@pytest.fixture
def sample_search_response_no_match():
    """Sample HTML response with no regex match."""
    return '<html>\n<body>Server error</body>\n</html>'
