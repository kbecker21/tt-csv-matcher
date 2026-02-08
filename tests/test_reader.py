"""Tests for core.reader module."""

import tempfile
from pathlib import Path

import pytest

from core import Player
from core.reader import detect_encoding, normalize_whitespace, read_players


class TestDetectEncoding:
    """Tests for encoding detection."""

    def test_utf16le_bom(self, data_dir):
        assert detect_encoding(data_dir / 'Reference.csv') == 'utf-16-le'

    def test_utf8_fallback(self, tmp_path):
        f = tmp_path / 'test.csv'
        f.write_text('hello', encoding='utf-8')
        assert detect_encoding(f) == 'utf-8-sig'


class TestNormalizeWhitespace:
    """Tests for whitespace normalization."""

    def test_strips_leading_trailing(self):
        assert normalize_whitespace('  hello  ') == 'hello'

    def test_collapses_multiple_spaces(self):
        assert normalize_whitespace('  Juan  Carlos ') == 'Juan Carlos'

    def test_handles_tabs_and_newlines(self):
        assert normalize_whitespace('a\t\nb') == 'a b'

    def test_unicode_whitespace(self):
        # U+2006 = Six-Per-Em Space
        assert normalize_whitespace('a\u2006b') == 'a b'

    def test_empty_string(self):
        assert normalize_whitespace('') == ''


class TestReadPlayers:
    """Tests for reading player CSV files."""

    def test_reference_count(self, ref_players):
        assert len(ref_players) == 5940

    def test_evc2025_count(self, evc2025_players):
        assert len(evc2025_players) == 2502

    def test_player_types(self, ref_players):
        p = ref_players[0]
        assert isinstance(p, Player)
        assert isinstance(p.last_name, str)
        assert isinstance(p.dob, int)
        assert isinstance(p.mob, int)
        assert isinstance(p.yob, int)

    def test_first_player_reference(self, ref_players):
        p = ref_players[0]
        assert p.extern_id == '10000-P000'
        assert p.last_name == 'MUSTERMANN'
        assert p.first_name == 'MAX'
        assert p.sex == 'M'
        assert p.association == 'GER'
        assert p.dob == 1
        assert p.mob == 1
        assert p.yob == 1971

    def test_special_characters_preserved(self, ref_players):
        # LAGERLÖF should keep the Ö
        names = {p.last_name.upper() for p in ref_players}
        assert 'LAGERLÖF' in names

    def test_no_empty_last_names(self, ref_players):
        for p in ref_players:
            assert p.last_name != '', f"Empty last name for {p.extern_id}"

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            read_players('nonexistent.csv')

    def test_missing_columns_raises(self, tmp_path):
        f = tmp_path / 'bad.csv'
        f.write_text('Col1\tCol2\na\tb\n', encoding='utf-8')
        with pytest.raises(ValueError, match='Fehlende Spalten'):
            read_players(f)
