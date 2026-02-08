"""Tests for core.scoring module."""

from core import Player
from core.scoring import (
    WEIGHTS,
    calculate_confidence,
    detect_issues,
    is_dob_mob_swapped,
)


def _player(**kwargs) -> Player:
    """Create a Player with defaults for easy test construction."""
    defaults = dict(
        extern_id='P001', last_name='MUELLER', first_name='Hans',
        sex='M', association='GER', dob=15, mob=6, yob=1985,
    )
    defaults.update(kwargs)
    return Player(**defaults)


class TestWeights:
    """Verify weight configuration."""

    def test_weights_sum_to_one(self):
        assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

    def test_all_keys_present(self):
        expected = {'lastname', 'firstname', 'dob', 'mob', 'yob', 'sex', 'association'}
        assert set(WEIGHTS.keys()) == expected


class TestCalculateConfidence:
    """Tests for confidence score calculation."""

    def test_perfect_match(self):
        p = _player()
        score = calculate_confidence(p, p, 1.0, 1.0)
        assert score == 1.0

    def test_no_match(self):
        e = _player(dob=1, mob=2, yob=2000, sex='F', association='FRA')
        r = _player(dob=15, mob=6, yob=1985, sex='M', association='GER')
        score = calculate_confidence(e, r, 0.0, 0.0)
        assert score == 0.0

    def test_name_only_match(self):
        e = _player(dob=1, mob=2, yob=2000, sex='F', association='FRA')
        r = _player(dob=15, mob=6, yob=1985, sex='M', association='GER')
        score = calculate_confidence(e, r, 1.0, 1.0)
        assert score == WEIGHTS['lastname'] + WEIGHTS['firstname']

    def test_partial_name_similarity(self):
        p = _player()
        score = calculate_confidence(p, p, 0.9, 0.8)
        expected = (
            WEIGHTS['lastname'] * 0.9
            + WEIGHTS['firstname'] * 0.8
            + WEIGHTS['dob'] + WEIGHTS['mob'] + WEIGHTS['yob']
            + WEIGHTS['sex'] + WEIGHTS['association']
        )
        assert abs(score - round(expected, 4)) < 1e-9


class TestIsDobMobSwapped:
    """Tests for DoB/MoB swap detection."""

    def test_swap_detected(self):
        e = _player(dob=6, mob=15)
        r = _player(dob=15, mob=6)
        assert is_dob_mob_swapped(e, r) is True

    def test_no_swap_same_values(self):
        e = _player(dob=6, mob=6)
        r = _player(dob=6, mob=6)
        assert is_dob_mob_swapped(e, r) is False

    def test_no_swap_different_year(self):
        e = _player(dob=6, mob=15, yob=1985)
        r = _player(dob=15, mob=6, yob=1986)
        assert is_dob_mob_swapped(e, r) is False

    def test_no_swap_unrelated_difference(self):
        e = _player(dob=5, mob=3)
        r = _player(dob=15, mob=6)
        assert is_dob_mob_swapped(e, r) is False


class TestDetectIssues:
    """Tests for issue detection."""

    def test_no_issues_on_perfect_match(self):
        p = _player()
        issues = detect_issues(p, p, 'EXACT', 1.0, 1.0)
        assert issues == []

    def test_name_swap_issue(self):
        p = _player()
        issues = detect_issues(p, p, 'NAME_SWAP', 1.0, 1.0)
        assert 'NAME_SWAPPED' in issues

    def test_fuzzy_issues(self):
        p = _player()
        issues = detect_issues(p, p, 'FUZZY', 0.9, 0.85)
        assert 'LASTNAME_FUZZY' in issues
        assert 'FIRSTNAME_FUZZY' in issues

    def test_dob_mob_swap_reported(self):
        e = _player(dob=6, mob=15)
        r = _player(dob=15, mob=6)
        issues = detect_issues(e, r, 'EXACT', 1.0, 1.0)
        assert 'DOB_MOB_SWAPPED' in issues
        # Individual mismatches should NOT be reported for swaps
        assert 'DOB_MISMATCH' not in issues
        assert 'MOB_MISMATCH' not in issues

    def test_individual_dob_mismatch(self):
        e = _player(dob=5)
        r = _player(dob=15)
        issues = detect_issues(e, r, 'EXACT', 1.0, 1.0)
        assert 'DOB_MISMATCH' in issues

    def test_yob_mismatch(self):
        e = _player(yob=1985)
        r = _player(yob=1986)
        issues = detect_issues(e, r, 'EXACT', 1.0, 1.0)
        assert 'YOB_MISMATCH' in issues

    def test_sex_mismatch(self):
        e = _player(sex='M')
        r = _player(sex='F')
        issues = detect_issues(e, r, 'EXACT', 1.0, 1.0)
        assert 'SEX_MISMATCH' in issues

    def test_assoc_mismatch(self):
        e = _player(association='ISR')
        r = _player(association='NZL')
        issues = detect_issues(e, r, 'EXACT', 1.0, 1.0)
        assert 'ASSOC_MISMATCH' in issues
