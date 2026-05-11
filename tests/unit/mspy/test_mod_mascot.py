from pathlib import Path

import pytest

from mmass.mspy import mod_mascot


class TestMascotInit:
    """Tests for mascot.__init__."""

    def test_init_default_path(self):
        """Test mascot initialization with default path."""
        m = mod_mascot.Mascot('testhost.com')
        assert m.server['host'] == 'testhost.com'
        assert m.server['path'] == '/mascot/'
        assert m.server['search'] == 'cgi/nph-mascot.exe'
        assert m.server['result'] == 'cgi/master_results.pl'
        assert m.server['export'] == 'cgi/export_dat_2.pl'
        assert m.server['params'] == 'cgi/get_params.pl'
        assert m.resultsPath is None
        assert m.resultsXML is None
        assert m.hits == {}

    def test_init_custom_path(self):
        """Test mascot initialization with custom path."""
        m = mod_mascot.Mascot('mascot.example.org', path='/search/mascot/')
        assert m.server['host'] == 'mascot.example.org'
        assert m.server['path'] == '/search/mascot/'

    def test_init_export_dict(self):
        """Test that export dict is initialized with correct values."""
        m = mod_mascot.Mascot('testhost.com')
        assert m.export['do_export'] == 1
        assert m.export['export_format'] == 'XML'
        assert m.export['report'] == 'AUTO'
        assert m.export['protein_master'] == 1
        assert m.export['peptide_master'] == 1
        assert m.export['_sigthreshold'] == 0.05
        assert m.export['prot_seq'] == 1


class TestMascotSearch:
    """Tests for mascot.search."""

    def test_search_success_with_regex_match(self, mocker, sample_search_response):
        """Test successful search with regex match in response."""
        m = mod_mascot.Mascot('testhost.com')
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_search_response.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        result = m.search('test query')
        assert result is True
        assert m.resultsPath == 'F001234567&REPTYPE=peptide'
        assert m.resultsXML is None
        assert m.hits == {}

    def test_search_network_exception(self, mocker):
        """Test search when network exception occurs."""
        m = mod_mascot.Mascot('testhost.com')
        mocker.patch('http.client.HTTPConnection', side_effect=Exception('Connection refused'))
        result = m.search('test query')
        assert result is False
        assert m.resultsPath is None
        assert m.resultsXML is None
        assert m.hits == {}

    def test_search_non_200_status(self, mocker):
        """Test search when server returns non-200 status."""
        m = mod_mascot.Mascot('testhost.com')
        mock_response = mocker.MagicMock()
        mock_response.status = 500
        mock_response.read.return_value = b'Server error'
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        result = m.search('test query')
        assert result is False

    def test_search_no_regex_match(self, mocker, sample_search_response_no_match):
        """Test search when response does not contain regex match."""
        m = mod_mascot.Mascot('testhost.com')
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_search_response_no_match.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        result = m.search('test query')
        assert result is False
        assert m.resultsPath is None

    def test_search_clears_previous_results(self, mocker, sample_search_response):
        """Test that search clears previous results."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsPath = 'old_path'
        m.resultsXML = 'old xml'
        m.hits = {1: {'protein': 'data'}}
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_search_response.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        m.search('test query')
        assert m.resultsXML is None
        assert m.hits == {}

    def test_search_multipart_body_format(self, mocker, sample_search_response):
        """Test that search constructs proper multipart form data."""
        m = mod_mascot.Mascot('testhost.com')
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_search_response.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        query_data = 'BEGIN IONS\nTITLE=test\nEND IONS'
        m.search(query_data)
        mock_conn.send.assert_called_once()
        sent_body = mock_conn.send.call_args[0][0]
        assert b'Content-Disposition: form-data; name="QUE"' in sent_body
        assert query_data.encode('utf-8') in sent_body

    def test_search_http_method_and_path(self, mocker, sample_search_response):
        """Test that search uses correct HTTP method and path."""
        m = mod_mascot.Mascot('testhost.com', path='/custom/')
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_search_response.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        m.search('test')
        assert mock_conn.putrequest.called
        call_args = mock_conn.putrequest.call_args[0]
        assert call_args[0] == 'POST'
        assert '/custom/' in call_args[1]
        assert 'cgi/nph-mascot.exe' in call_args[1]


class TestMascotReport:
    """Tests for mascot.report."""

    def test_report_with_explicit_path(self, mocker):
        """Test report with explicit path parameter."""
        m = mod_mascot.Mascot('testhost.com')
        mock_open = mocker.patch('webbrowser.open')
        m.report(path='F001234567')
        mock_open.assert_called_once()
        url = mock_open.call_args[0][0]
        assert 'http://' in url
        assert 'testhost.com' in url
        assert 'master_results.pl' in url
        assert 'F001234567' in url

    def test_report_with_self_results_path(self, mocker):
        """Test report using self.resultsPath."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsPath = 'F001234567'
        mock_open = mocker.patch('webbrowser.open')
        m.report()
        mock_open.assert_called_once()
        url = mock_open.call_args[0][0]
        assert 'F001234567' in url

    def test_report_no_path_silent_failure(self, mocker):
        """Test report when no path is available (silent failure)."""
        m = mod_mascot.Mascot('testhost.com')
        mock_open = mocker.patch('webbrowser.open')
        m.report(path=None)
        assert not mock_open.called

    def test_report_explicit_path_takes_precedence(self, mocker):
        """Test that explicit path takes precedence over self.resultsPath."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsPath = 'old_path'
        mock_open = mocker.patch('webbrowser.open')
        m.report(path='new_path')
        url = mock_open.call_args[0][0]
        assert 'new_path' in url
        assert 'old_path' not in url


class TestMascotFetchall:
    """Tests for mascot.fetchall."""

    def test_fetchall_no_path_no_results_path(self):
        """Test fetchall returns False when no path available."""
        m = mod_mascot.Mascot('testhost.com')
        result = m.fetchall()
        assert result is False

    def test_fetchall_with_explicit_path(self, mocker, sample_xml_single_hit):
        """Test fetchall with explicit path parameter."""
        m = mod_mascot.Mascot('testhost.com')
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_xml_single_hit.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        result = m.fetchall(path='F001234567')
        assert result is True
        assert m.resultsXML == sample_xml_single_hit.encode('utf-8')
        assert len(m.hits) > 0

    def test_fetchall_with_self_results_path(self, mocker, sample_xml_single_hit):
        """Test fetchall using self.resultsPath."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsPath = 'F001234567'
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_xml_single_hit.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        result = m.fetchall()
        assert result is True
        assert m.resultsXML == sample_xml_single_hit.encode('utf-8')

    def test_fetchall_clears_previous_results(self, mocker, sample_xml_no_hits):
        """Test fetchall clears previous results."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsXML = 'old xml'
        m.hits = {1: {'protein': 'data'}}
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_xml_no_hits.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        m.fetchall(path='F001234567')
        assert m.resultsXML == sample_xml_no_hits.encode('utf-8')
        assert m.hits == {}

    def test_fetchall_network_exception(self, mocker):
        """Test fetchall returns False on network exception."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsPath = 'F001234567'
        mocker.patch('http.client.HTTPConnection', side_effect=Exception('Connection failed'))
        result = m.fetchall()
        assert result is False

    def test_fetchall_non_200_status(self, mocker):
        """Test fetchall returns False on non-200 status."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsPath = 'F001234567'
        mock_response = mocker.MagicMock()
        mock_response.status = 404
        mock_response.read.return_value = b'Not found'
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        result = m.fetchall()
        assert result is False

    def test_fetchall_calls_parse(self, mocker, sample_xml_single_hit):
        """Test fetchall calls parse method with XML data."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsPath = 'F001234567'
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_xml_single_hit.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        m.fetchall()
        assert len(m.hits) == 1
        assert 1 in m.hits

    def test_fetchall_includes_export_params(self, mocker, sample_xml_single_hit):
        """Test fetchall includes all export parameters in request."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsPath = 'F001234567'
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_xml_single_hit.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        m.fetchall()
        mock_conn.request.assert_called_once()
        path = mock_conn.request.call_args[0][1]
        assert 'do_export=1' in path
        assert 'export_format=XML' in path
        assert 'protein_master=1' in path
        assert 'peptide_master=1' in path


class TestMascotParse:
    """Tests for mascot.parse."""

    def test_parse_from_string_data(self, sample_xml_single_hit):
        """Test parse from string data parameter."""
        m = mod_mascot.Mascot('testhost.com')
        result = m.parse(data=sample_xml_single_hit)
        assert result is True
        assert len(m.hits) == 1
        assert 1 in m.hits
        assert 'Q12345' in m.hits[1]

    def test_parse_from_self_results_xml(self, sample_xml_single_hit):
        """Test parse from self.resultsXML."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsXML = sample_xml_single_hit
        result = m.parse()
        assert result is True
        assert len(m.hits) == 1

    def test_parse_from_file_path(self, tmp_path, sample_xml_single_hit):
        """Test parse from file path parameter."""
        m = mod_mascot.Mascot('testhost.com')
        temp_file = tmp_path / 'test.xml'
        temp_file.write_text(sample_xml_single_hit)
        result = m.parse(path=str(temp_file))
        assert result is True
        assert len(m.hits) == 1

    def test_parse_no_args_no_results_xml(self):
        """Test parse returns False when no arguments and no self.resultsXML."""
        m = mod_mascot.Mascot('testhost.com')
        result = m.parse()
        assert result is False

    def test_parse_invalid_xml(self):
        """Test parse returns False on invalid XML."""
        m = mod_mascot.Mascot('testhost.com')
        invalid_xml = '<mascot_search_results><unclosed>'
        result = m.parse(data=invalid_xml)
        assert result is False

    def test_parse_file_not_found(self):
        """Test parse returns False when file not found."""
        m = mod_mascot.Mascot('testhost.com')
        result = m.parse(path='/nonexistent/path/to/file.xml')
        assert result is False

    def test_parse_no_hits(self, sample_xml_no_hits):
        """Test parse with XML containing no hits."""
        m = mod_mascot.Mascot('testhost.com')
        result = m.parse(data=sample_xml_no_hits)
        assert result is True
        assert m.hits == {}

    def test_parse_single_hit_single_protein_single_peptide(self, sample_xml_single_hit):
        """Test parse extracts single hit with one protein and peptide."""
        m = mod_mascot.Mascot('testhost.com')
        m.parse(data=sample_xml_single_hit)
        assert 1 in m.hits
        assert 'Q12345' in m.hits[1]
        protein = m.hits[1]['Q12345']
        assert protein['prot_accession'] == 'Q12345'
        assert protein['prot_desc'] == 'Test Protein Description'
        assert protein['prot_score'] == '95.5'
        assert protein['prot_mass'] == '50000.12'
        assert len(protein['peptides']) == 1
        peptide = protein['peptides'][0]
        assert peptide['query'] == '1'
        assert peptide['rank'] == '1'
        assert peptide['isbold'] == '1'
        assert peptide['pep_seq'] == 'PEPTIDER'
        assert peptide['pep_score'] == '45.3'

    def test_parse_multiple_hits_multiple_proteins_multiple_peptides(self, sample_xml_multiple_hits):
        """Test parse with multiple hits, proteins, and peptides.

        Note: Due to XML DOM getElementsByTagName behavior, all peptides
        within a hit are assigned to each protein in that hit.
        """
        m = mod_mascot.Mascot('testhost.com')
        m.parse(data=sample_xml_multiple_hits)
        assert 1 in m.hits
        assert len(m.hits[1]) == 2
        assert 'Q12345' in m.hits[1]
        assert 'P54321' in m.hits[1]
        protein1 = m.hits[1]['Q12345']
        assert len(protein1['peptides']) == 3
        protein2 = m.hits[1]['P54321']
        assert len(protein2['peptides']) == 3
        assert 2 in m.hits
        assert 'Q99999' in m.hits[2]

    def test_parse_clears_previous_hits(self, sample_xml_multiple_hits, sample_xml_no_hits):
        """Test parse clears previous hits when called with new data."""
        m = mod_mascot.Mascot('testhost.com')
        m.parse(data=sample_xml_multiple_hits)
        assert len(m.hits) == 2
        m.parse(data=sample_xml_no_hits)
        assert m.hits == {}

    def test_parse_clears_results_path_when_path_param(self, tmp_path, sample_xml_single_hit):
        """Test parse clears resultsPath when called with path parameter."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsPath = 'old_path'
        m.resultsXML = 'old xml'
        temp_file = tmp_path / 'test.xml'
        temp_file.write_text(sample_xml_single_hit)
        m.parse(path=str(temp_file))
        assert m.resultsPath is None
        assert m.resultsXML is None

    def test_parse_clears_results_path_when_data_param(self, sample_xml_single_hit):
        """Test parse clears resultsPath when called with data parameter."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsPath = 'old_path'
        m.resultsXML = 'old xml'
        m.parse(data=sample_xml_single_hit)
        assert m.resultsPath is None
        assert m.resultsXML is None

    def test_parse_handles_text_nodes_in_elements(self):
        """Test parse handles text nodes and only processes element nodes."""
        xml_with_text = '<?xml version="1.0" encoding="UTF-8"?>\n<mascot_search_results>\n  <hit number="1">\n    <protein accession="Q12345">\n      <prot_desc>Test Protein</prot_desc>\n      Text content that should be ignored\n      <prot_score>95.5</prot_score>\n    </protein>\n  </hit>\n</mascot_search_results>'
        m = mod_mascot.Mascot('testhost.com')
        result = m.parse(data=xml_with_text)
        assert result is True
        assert 1 in m.hits
        protein = m.hits[1]['Q12345']
        assert protein['prot_desc'] == 'Test Protein'
        assert protein['prot_score'] == '95.5'

    def test_parse_attributes_correctly_extracted(self, sample_xml_multiple_hits):
        """Test that attributes like query, rank, isbold are extracted correctly.

        Note: All peptides in a hit are assigned to each protein in that hit.
        """
        m = mod_mascot.Mascot('testhost.com')
        m.parse(data=sample_xml_multiple_hits)
        protein = m.hits[1]['Q12345']
        assert len(protein['peptides']) == 3
        pep1 = protein['peptides'][0]
        assert pep1['query'] == '1'
        assert pep1['rank'] == '1'
        assert pep1['isbold'] == '1'
        pep2 = protein['peptides'][1]
        assert pep2['query'] == '2'
        assert pep2['rank'] == '1'
        assert pep2['isbold'] == '1'
        pep3 = protein['peptides'][2]
        assert pep3['isbold'] == '0'


class TestMascotSave:
    """Tests for mascot.save."""

    def test_save_no_results_xml(self, tmp_path):
        """Test save returns False when no resultsXML."""
        m = mod_mascot.Mascot('testhost.com')
        temp_path = str(tmp_path / 'test.xml')
        result = m.save(temp_path)
        assert result is False

    def test_save_successful_write(self, tmp_path, sample_xml_single_hit):
        """Test successful save of results XML to file."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsXML = sample_xml_single_hit
        temp_path = str(tmp_path / 'test.xml')
        result = m.save(temp_path)
        assert result is True
        with Path(temp_path).open() as f:
            content = f.read()
        assert 'mascot_search_results' in content or 'mascot_search_results' in content.decode('utf-8', errors='ignore')

    def test_save_io_error(self, mocker, sample_xml_single_hit):
        """Test save returns False on IOError."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsXML = sample_xml_single_hit
        mocker.patch('builtins.open', side_effect=OSError('Permission denied'))
        result = m.save('/some/path/file.xml')
        assert result is False

    def test_save_file_builtin_error(self, mocker, sample_xml_single_hit):
        """Test save handles file builtin errors."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsXML = sample_xml_single_hit
        mocker.patch('builtins.open', side_effect=OSError('Disk full'))
        result = m.save('/nonexistent/path/file.xml')
        assert result is False


class TestMascotParameters:
    """Tests for mascot.parameters."""

    def test_parameters_success_basic(self, mocker, sample_parameters):
        """Test successful parameters retrieval."""
        m = mod_mascot.Mascot('testhost.com')
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_parameters.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        result = m.parameters()
        assert isinstance(result, dict)
        assert 'DB' in result
        assert 'CLE' in result
        assert 'MODS' in result
        assert 'SwissProt' in result['DB']
        assert 'TrEMBL' in result['DB']

    def test_parameters_network_exception(self, mocker):
        """Test parameters returns False on network exception."""
        m = mod_mascot.Mascot('testhost.com')
        mocker.patch('http.client.HTTPConnection', side_effect=Exception('Connection error'))
        result = m.parameters()
        assert result is False

    def test_parameters_default_sections_exist(self, mocker):
        """Test that parameters dict contains pre-populated default sections."""
        m = mod_mascot.Mascot('testhost.com')
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b''
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        result = m.parameters()
        assert 'TAXONOMY' in result
        assert 'INSTRUMENT' in result
        assert 'QUANTITATION' in result
        assert 'OPTIONS' in result
        assert 'All entries' in result['TAXONOMY']
        assert 'Default' in result['INSTRUMENT']
        assert 'None' in result['QUANTITATION']
        assert 'None' in result['OPTIONS']

    def test_parameters_empty_lines_skipped(self, mocker, sample_parameters_with_empty_lines):
        """Test that empty lines in parameter file are skipped."""
        m = mod_mascot.Mascot('testhost.com')
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_parameters_with_empty_lines.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        result = m.parameters()
        assert 'DB' in result
        assert 'SwissProt' in result['DB']
        assert '' not in result['DB']

    def test_parameters_multiple_entries_per_section(self, mocker, sample_parameters):
        """Test parameters parses multiple entries per section."""
        m = mod_mascot.Mascot('testhost.com')
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_parameters.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        result = m.parameters()
        assert len(result['CLE']) >= 2
        assert 'Trypsin' in result['CLE']
        assert 'Pepsin' in result['CLE']
        assert len(result['MODS']) >= 2
        assert 'Acetyl (N-term)' in result['MODS']
        assert 'Oxidation (M)' in result['MODS']

    def test_parameters_section_header_regex(self, mocker):
        """Test parameters correctly identifies section headers."""
        m = mod_mascot.Mascot('testhost.com')
        param_text = '[VALID_SECTION_NAME]\nEntry1\nEntry2\n[ANOTHER_SECTION]\nEntry3'
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = param_text.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        result = m.parameters()
        assert 'VALID_SECTION_NAME' in result
        assert 'ANOTHER_SECTION' in result
        assert 'Entry1' in result['VALID_SECTION_NAME']
        assert 'Entry3' in result['ANOTHER_SECTION']

    def test_parameters_uses_get_method(self, mocker, sample_parameters):
        """Test parameters uses GET method."""
        m = mod_mascot.Mascot('testhost.com')
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_parameters.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        m.parameters()
        mock_conn.request.assert_called_once()
        assert mock_conn.request.call_args[0][0] == 'GET'

    def test_parameters_correct_url_path(self, mocker, sample_parameters):
        """Test parameters uses correct URL path."""
        m = mod_mascot.Mascot('testhost.com', path='/custom/')
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_parameters.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        m.parameters()
        path = mock_conn.request.call_args[0][1]
        assert '/custom/' in path
        assert 'get_params.pl' in path


class TestMascotIntegration:
    """Integration tests combining multiple methods."""

    def test_search_and_fetchall_workflow(self, mocker, sample_xml_single_hit, sample_search_response):
        """Test typical workflow of search followed by fetchall."""
        m = mod_mascot.Mascot('testhost.com')
        search_response = mocker.MagicMock()
        search_response.status = 200
        search_response.read.return_value = sample_search_response.encode('utf-8')
        fetchall_response = mocker.MagicMock()
        fetchall_response.status = 200
        fetchall_response.read.return_value = sample_xml_single_hit.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.side_effect = [search_response, fetchall_response]
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        search_result = m.search('test query')
        assert search_result is True
        fetchall_result = m.fetchall()
        assert fetchall_result is True
        assert len(m.hits) > 0

    def test_fetchall_parse_save_workflow(self, tmp_path, mocker, sample_xml_single_hit):
        """Test workflow of fetchall, parse, and save."""
        m = mod_mascot.Mascot('testhost.com')
        m.resultsPath = 'F001234567'
        mock_response = mocker.MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = sample_xml_single_hit.encode('utf-8')
        mock_conn = mocker.MagicMock()
        mock_conn.getresponse.return_value = mock_response
        mocker.patch('http.client.HTTPConnection', return_value=mock_conn)
        fetchall_result = m.fetchall()
        assert fetchall_result is True
        temp_file = tmp_path / 'test.xml'
        temp_path = str(temp_file)
        save_result = m.save(temp_path)
        assert save_result is True
        assert temp_file.exists()
        with temp_file.open() as f:
            content = f.read()
        assert len(content) > 0

    def test_parse_then_report_workflow(self, mocker, sample_xml_single_hit):
        """Test workflow of parsing data and then opening report."""
        m = mod_mascot.Mascot('testhost.com')
        m.parse(data=sample_xml_single_hit)
        assert len(m.hits) > 0
        mock_open = mocker.patch('webbrowser.open')
        m.report(path='F001234567')
        assert mock_open.called

