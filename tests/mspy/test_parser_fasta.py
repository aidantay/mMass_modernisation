import pytest
import os
import mspy.parser_fasta
import mspy.obj_sequence

def test_init_success():
    """Test parseFASTA.__init__ with existing file."""
    path = 'tests/data/test_small.fasta'
    parser = mspy.parser_fasta.parseFASTA(path)
    assert parser.path == path

def test_init_failure():
    """Test parseFASTA.__init__ with non-existent file."""
    path = 'non_existent_file.fasta'
    with pytest.raises(OSError):
        mspy.parser_fasta.parseFASTA(path)

def test_sequences_io_error(mocker):
    """Test parseFASTA.sequences() handling OSError on file open."""
    path = 'tests/data/test_small.fasta'
    parser = mspy.parser_fasta.parseFASTA(path)
    
    # Use builtins.open for Python 3
    mocker.patch('builtins.open', side_effect=OSError)
    
    assert parser.sequences() is False

def test_sequences_valid_parsing():
    """Test parseFASTA.sequences() with valid FASTA file."""
    path = 'tests/data/test_small.fasta'
    parser = mspy.parser_fasta.parseFASTA(path)
    sequences = parser.sequences()
    
    assert len(sequences) == 5
    
    # Verify sequences[0]: P12345, TITLE1, len 20
    assert sequences[0].accession == 'sp|P12345'
    assert sequences[0].title == 'TITLE1'
    assert len(sequences[0]) == 20
    
    # Verify sequences[1]: 123456, TITLE2, len 20 (stripped *)
    assert sequences[1].accession == 'gi|123456'
    assert sequences[1].title == 'TITLE2'
    assert len(sequences[1]) == 20
    
    # Verify sequences[2]: ABC12345, TITLE3, len 10
    assert sequences[2].accession == 'gb|ABC12345'
    assert sequences[2].title == 'TITLE3'
    assert len(sequences[2]) == 10
    
    # Verify sequences[3]: NP_123456, TITLE4, len 10
    assert sequences[3].accession == 'ref|NP_123456'
    assert sequences[3].title == 'TITLE4'
    assert len(sequences[3]) == 10
    
    # Verify sequences[4]: '', SimpleTitle, len 4
    assert sequences[4].accession == ''
    assert sequences[4].title == 'SimpleTitle'
    assert len(sequences[4]) == 4

def test_sequences_edge_cases(tmpdir):
    """Test parseFASTA.sequences() with edge cases and errors."""
    fasta_content = """
; A comment at the start
A line before any header - this should be ignored

>Valid1
ACDEF
; A comment in the middle

>Invalid1
12345
>Valid2
GHIKL

>Invalid2
ABCXYZ123
"""
    fasta_file = tmpdir.join("edge_cases.fasta")
    fasta_file.write(fasta_content)
    
    parser = mspy.parser_fasta.parseFASTA(str(fasta_file))
    sequences = parser.sequences()
    
    # Valid1 and Valid2 should be parsed.
    # Invalid1 and Invalid2 should be skipped due to unknown monomers (KeyError).
    assert len(sequences) == 2
    assert sequences[0].title == 'Valid1'
    assert sequences[1].title == 'Valid2'

def test_sequences_empty_file(tmpdir):
    """Test parseFASTA.sequences() with an empty file."""
    fasta_file = tmpdir.join("empty.fasta")
    fasta_file.write("")
    
    parser = mspy.parser_fasta.parseFASTA(str(fasta_file))
    sequences = parser.sequences()
    assert sequences == []
