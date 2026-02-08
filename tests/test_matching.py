"""Tests for core.matching module."""

import pytest

from core import Player, MatchResult
from core.matching import match_players


def _player(**kwargs) -> Player:
    """Create a Player with defaults."""
    defaults = dict(
        extern_id='P001', last_name='MUELLER', first_name='Hans',
        sex='M', association='GER', dob=15, mob=6, yob=1985,
    )
    defaults.update(kwargs)
    return Player(**defaults)


class TestExactMatch:
    """Tests for stage 1: exact matching."""

    def test_exact_match_found(self):
        ref = [_player()]
        event = [_player(extern_id='E001')]
        results = match_players(ref, event)
        assert len(results) == 1
        assert results[0].match_type == 'EXACT'
        assert results[0].confidence == 1.0

    def test_exact_match_case_insensitive(self):
        ref = [_player(last_name='Mueller', first_name='HANS')]
        event = [_player(last_name='MUELLER', first_name='Hans', extern_id='E001')]
        results = match_players(ref, event)
        assert results[0].match_type == 'EXACT'

    def test_exact_match_with_dob_difference(self):
        ref = [_player(dob=15)]
        event = [_player(dob=16, extern_id='E001')]
        results = match_players(ref, event)
        assert results[0].match_type == 'EXACT'
        assert 'DOB_MISMATCH' in results[0].issues


class TestNameSwap:
    """Tests for stage 2: name-swap detection."""

    def test_name_swap_detected(self):
        ref = [_player(last_name='SIMON', first_name='Csaba')]
        event = [_player(last_name='Csaba', first_name='SIMON', extern_id='E001')]
        results = match_players(ref, event)
        assert results[0].match_type == 'NAME_SWAP'
        assert 'NAME_SWAPPED' in results[0].issues


class TestFuzzyMatch:
    """Tests for stage 3: fuzzy matching."""

    def test_fuzzy_match_typo(self):
        ref = [_player(last_name='MUELLER')]
        event = [_player(last_name='MULLER', extern_id='E001')]
        results = match_players(ref, event)
        assert results[0].match_type == 'FUZZY'
        assert 'LASTNAME_FUZZY' in results[0].issues

    def test_no_match_below_threshold(self):
        ref = [_player(last_name='COMPLETELY_DIFFERENT')]
        event = [_player(last_name='XYZ_SOMETHING', extern_id='E001')]
        results = match_players(ref, event)
        assert results[0].match_type == 'NONE'


class TestNoMatch:
    """Tests for stage 4: no match."""

    def test_no_match_empty_ref(self):
        event = [_player(extern_id='E001')]
        results = match_players([], event)
        assert len(results) == 1
        assert results[0].match_type == 'NONE'
        assert results[0].ref_player is None
        assert 'NO_MATCH' in results[0].issues

    def test_no_match_confidence_zero(self):
        results = match_players([], [_player()])
        assert results[0].confidence == 0.0


class TestDobMobSwap:
    """Tests for DoB/MoB swap detection in matched results."""

    def test_dob_mob_swap_flagged_on_exact_match(self):
        ref = [_player(dob=5, mob=2)]
        event = [_player(dob=2, mob=5, extern_id='E001')]
        results = match_players(ref, event)
        assert results[0].match_type == 'EXACT'
        assert 'DOB_MOB_SWAPPED' in results[0].issues


class TestIntegrationWithRealData:
    """Integration tests with actual CSV data files."""

    def test_total_results_count(self, ref_players, evc2025_players):
        results = match_players(ref_players, evc2025_players)
        assert len(results) == len(evc2025_players)

    def test_match_type_distribution(self, ref_players, evc2025_players):
        results = match_players(ref_players, evc2025_players)
        counts = {}
        for r in results:
            counts[r.match_type] = counts.get(r.match_type, 0) + 1

        # Expected approximate counts from CLAUDE.md
        assert counts.get('EXACT', 0) > 1300
        assert counts.get('NAME_SWAP', 0) >= 8
        assert counts.get('NONE', 0) > 0

    def test_dob_mob_swap_count(self, ref_players, evc2025_players):
        results = match_players(ref_players, evc2025_players)
        swap_count = sum(
            1 for r in results if 'DOB_MOB_SWAPPED' in r.issues
        )
        # At least 8 from exact name matches; more possible via fuzzy matches
        assert swap_count >= 8

    def test_all_results_have_event_player(self, ref_players, evc2025_players):
        results = match_players(ref_players, evc2025_players)
        for r in results:
            assert r.event_player is not None

    def test_matched_results_have_ref_player(self, ref_players, evc2025_players):
        results = match_players(ref_players, evc2025_players)
        for r in results:
            if r.match_type != 'NONE':
                assert r.ref_player is not None
