import os
from pathlib import Path

import numpy.testing as npt
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from mmass.mspy import obj_scan, parser_xy


@pytest.fixture
def small_xy_path():
    return str(Path.cwd() / 'tests/data/test_small.xy')


class TestParseXY:
    """Tests for ParseXY class."""

    def test_info(self, tmp_path):
        path = tmp_path / 'test.xy'
        path.touch()
        parser = parser_xy.ParseXY(path)
        info = parser.info()
        assert isinstance(info, dict)
        assert info['title'] == ''
        assert 'operator' in info

    def test_init_failure(self):
        with pytest.raises(OSError, match='File not found!'):
            parser_xy.ParseXY('non_existent_file.xy')

    def test_init_success(self, tmp_path):
        path = tmp_path / 'test.xy'
        path.touch()
        parser = parser_xy.ParseXY(path)
        assert parser.path == path

    @pytest.mark.integration
    def test_integration(self, small_xy_path):
        parser = parser_xy.ParseXY(small_xy_path)
        s = parser.scan()
        assert isinstance(s, obj_scan.Scan)
        assert len(s.profile) == 6
        npt.assert_array_equal(s.profile[0], [100.0, 1000.0])

    def test_makeScan_continuous(self, tmp_path):
        path = tmp_path / 'test.xy'
        path.touch()
        parser = parser_xy.ParseXY(path)
        data = [[100.0, 1000.0], [101.0, 2000.0]]
        s = parser._makeScan(data, dataType='continuous')
        assert isinstance(s, obj_scan.Scan)
        npt.assert_array_equal(s.profile, data)

    def test_makeScan_discrete(self, tmp_path):
        path = tmp_path / 'test.xy'
        path.touch()
        parser = parser_xy.ParseXY(path)
        data = [[100.0, 1000.0], [101.0, 2000.0]]
        s = parser._makeScan(data, dataType='discrete')
        assert isinstance(s, obj_scan.Scan)
        assert s.peaklist is not None
        assert len(s.peaklist.peaks) == 2
        assert s.peaklist.peaks[0].mz == 100.0
        assert s.peaklist.peaks[0].intensity == 1000.0

    def test_parseData_empty(self, tmp_path):
        path = tmp_path / 'test.xy'
        path.write_text('')
        parser = parser_xy.ParseXY(path)
        assert parser._parseData() == []

    def test_parseData_happy_path(self, tmp_path):
        path = tmp_path / 'test.xy'
        content = '# Comment\nm/z intensity\n100.0 1000.0\n101.1\t2000.0\n102.2,3000.0\n103.3;4000.0\n1.0e2 5.0e3\n'
        path.write_text(content)
        parser = parser_xy.ParseXY(path)
        data = parser._parseData()
        assert len(data) == 5
        assert data[0] == [100.0, 1000.0]
        assert data[1] == [101.1, 2000.0]
        assert data[2] == [102.2, 3000.0]
        assert data[3] == [103.3, 4000.0]
        assert data[4] == [100.0, 5000.0]

    def test_parseData_invalid_line(self, tmp_path):
        path = tmp_path / 'test.xy'
        path.write_text('100.0 1000.0\ninvalid line\n')
        parser = parser_xy.ParseXY(path)
        assert parser._parseData() is False

    def test_parseData_ioerror(self, tmp_path, mocker):
        path = tmp_path / 'test.xy'
        path.touch()
        parser = parser_xy.ParseXY(path)
        mocker.patch('pathlib.Path.open', side_effect=OSError)
        assert parser._parseData() is False

    def test_parseData_only_comments(self, tmp_path):
        path = tmp_path / 'test.xy'
        path.write_text('# comment\nm/z header\n')
        parser = parser_xy.ParseXY(path)
        assert parser._parseData() == []

    def test_parseData_single_value(self, tmp_path):
        path = tmp_path / 'test.xy'
        path.write_text('100.0\n')
        parser = parser_xy.ParseXY(path)
        assert parser._parseData() is False

    def test_scan_failure(self, tmp_path):
        path = tmp_path / 'test.xy'
        path.write_text('invalid\n')
        parser = parser_xy.ParseXY(path)
        assert parser.scan() is False

    def test_scan_success(self, tmp_path):
        path = tmp_path / 'test.xy'
        path.write_text('100.0 1000.0\n')
        parser = parser_xy.ParseXY(path)
        s = parser.scan()
        assert isinstance(s, obj_scan.Scan)
        npt.assert_array_equal(s.profile, [[100.0, 1000.0]])


class TestPropertyBased:
    """Property-based tests for XY parsing."""

    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(mz=st.floats(allow_nan=False, allow_infinity=False, min_value=-10000000000.0, max_value=10000000000.0), intensity=st.floats(allow_nan=False, allow_infinity=False, min_value=-10000000000.0, max_value=10000000000.0), sep=st.sampled_from([' ', '\t', ',', ';', ' \t ', ', ', '; ']))
    def test_hypothesis_parseData(self, tmp_path, mz, intensity, sep):
        line = '{}{}{}'.format(format(mz, 'g'), sep, format(intensity, 'g'))
        path = tmp_path / 'test.xy'
        path.write_text(line)
        parser = parser_xy.ParseXY(path)
        data = parser._parseData()
        if data:
            assert len(data) == 1
            assert data[0][0] == pytest.approx(mz, rel=1e-05, abs=1e-05)
            assert data[0][1] == pytest.approx(intensity, rel=1e-05, abs=1e-05)
        else:
            pass

