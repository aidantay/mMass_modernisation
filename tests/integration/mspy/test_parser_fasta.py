from pathlib import Path

import pytest

from mmass.mspy import parser_fasta


class TestParseFASTA:
    """Tests for ParseFASTA class."""

    def test_init_failure(self):
        """Test ParseFASTA.__init__ with non-existent file."""
        path = 'non_existent_file.fasta'
        with pytest.raises(OSError, match='File not found!'):
            parser_fasta.ParseFASTA(path)

    def test_init_success(self):
        """Test ParseFASTA.__init__ with existing file."""
        path = 'tests/data/test_small.fasta'
        parser = parser_fasta.ParseFASTA(path)
        assert parser.path == Path(path)

    def test_sequences_edge_cases(self, tmpdir):
        """Test ParseFASTA.sequences() with edge cases and errors."""
        fasta_content = '\n; A comment at the start\nA line before any header - this should be ignored\n\n>Valid1\nACDEF\n; A comment in the middle\n\n>Invalid1\n12345\n>Valid2\nGHIKL\n\n>Invalid2\nABCXYZ123\n'
        fasta_file = tmpdir.join('edge_cases.fasta')
        fasta_file.write(fasta_content)
        parser = parser_fasta.ParseFASTA(str(fasta_file))
        sequences = parser.sequences()
        assert len(sequences) == 2
        assert sequences[0].title == 'Valid1'
        assert sequences[1].title == 'Valid2'

    def test_sequences_empty_file(self, tmpdir):
        """Test ParseFASTA.sequences() with an empty file."""
        fasta_file = tmpdir.join('empty.fasta')
        fasta_file.write('')
        parser = parser_fasta.ParseFASTA(str(fasta_file))
        sequences = parser.sequences()
        assert sequences == []

    def test_sequences_io_error(self, mocker):
        """Test ParseFASTA.sequences() handling OSError on file open."""
        path = 'tests/data/test_small.fasta'
        parser = parser_fasta.ParseFASTA(path)
        mocker.patch('pathlib.Path.open', side_effect=OSError)
        assert parser.sequences() is False

    def test_sequences_valid_parsing(self):
        """Test ParseFASTA.sequences() with valid FASTA file."""
        path = 'tests/data/test_small.fasta'
        parser = parser_fasta.ParseFASTA(path)
        sequences = parser.sequences()
        assert len(sequences) == 5
        assert sequences[0].accession == 'sp|P12345'
        assert sequences[0].title == 'TITLE1'
        assert len(sequences[0]) == 20
        assert sequences[1].accession == 'gi|123456'
        assert sequences[1].title == 'TITLE2'
        assert len(sequences[1]) == 20
        assert sequences[2].accession == 'gb|ABC12345'
        assert sequences[2].title == 'TITLE3'
        assert len(sequences[2]) == 10
        assert sequences[3].accession == 'ref|NP_123456'
        assert sequences[3].title == 'TITLE4'
        assert len(sequences[3]) == 10
        assert sequences[4].accession == ''
        assert sequences[4].title == 'SimpleTitle'
        assert len(sequences[4]) == 4

