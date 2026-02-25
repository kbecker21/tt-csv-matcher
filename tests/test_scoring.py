"""Tests for core.scoring module."""

from core import Player
from core.scoring import (
    WEIGHTS,
    calculate_confidence,
    calculate_confidence_tolerant,
    detect_issues,
    is_dob_mob_swapped,
    normalize_for_tolerant_comparison,
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

    def test_dob_mob_swap_yields_full_score(self):
        """A detected DoB/MoB swap must not penalize the confidence score."""
        e = _player(dob=6, mob=15)
        r = _player(dob=15, mob=6)
        score = calculate_confidence(e, r, 1.0, 1.0)
        assert score == 1.0

    def test_single_date_mismatch_still_penalized(self):
        """A plain date mismatch (no swap pattern) still reduces the score."""
        e = _player(dob=5)
        r = _player(dob=15)
        score = calculate_confidence(e, r, 1.0, 1.0)
        assert score == 1.0 - WEIGHTS['dob']


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


class TestNormalizeForTolerantComparison:
    """Tests for accent/punctuation-tolerant normalization."""

    def test_accent_removal(self):
        assert normalize_for_tolerant_comparison('José') == 'JOSE'
        assert normalize_for_tolerant_comparison('François') == 'FRANCOIS'
        assert normalize_for_tolerant_comparison('Müller') == 'MULLER'
        assert normalize_for_tolerant_comparison('Señor') == 'SENOR'
        assert normalize_for_tolerant_comparison('Àlex') == 'ALEX'

    def test_umlaut_normalization(self):
        assert normalize_for_tolerant_comparison('ö') == 'O'
        assert normalize_for_tolerant_comparison('ü') == 'U'
        assert normalize_for_tolerant_comparison('ä') == 'A'

    def test_punctuation_removal(self):
        assert normalize_for_tolerant_comparison('Jean-Pierre') == 'JEANPIERRE'
        assert normalize_for_tolerant_comparison('O.Brien') == 'OBRIEN'
        assert normalize_for_tolerant_comparison('van der Berg') == 'VANDERBERG'

    def test_whitespace_removal(self):
        assert normalize_for_tolerant_comparison('  Juan  Carlos ') == 'JUANCARLOS'

    def test_combined(self):
        assert normalize_for_tolerant_comparison('José-María') == 'JOSEMARIA'

    def test_plain_ascii_unchanged(self):
        assert normalize_for_tolerant_comparison('MUELLER') == 'MUELLER'


class TestCalculateConfidenceTolerant:
    """Tests for tolerant confidence scoring."""

    def test_perfect_match_equals_normal(self):
        p = _player()
        normal = calculate_confidence(p, p, 1.0, 1.0)
        tolerant = calculate_confidence_tolerant(p, p, 1.0, 1.0)
        assert tolerant == normal == 1.0

    def test_accent_difference_gives_full_name_score(self):
        e = _player(last_name='José', first_name='François')
        r = _player(last_name='Jose', first_name='Francois')
        tolerant = calculate_confidence_tolerant(e, r, 0.9, 0.85)
        # Normalized names are identical → name similarities = 1.0
        # All other fields match → full score
        assert tolerant == 1.0

    def test_tolerant_higher_than_normal_with_accents(self):
        e = _player(last_name='Müller', first_name='Hans')
        r = _player(last_name='Muller', first_name='Hans')
        normal = calculate_confidence(e, r, 0.95, 1.0)
        tolerant = calculate_confidence_tolerant(e, r, 0.95, 1.0)
        assert tolerant > normal

    def test_hyphen_difference_gives_full_name_score(self):
        e = _player(last_name='Smith', first_name='Jean-Pierre')
        r = _player(last_name='Smith', first_name='Jean Pierre')
        tolerant = calculate_confidence_tolerant(e, r, 1.0, 0.9)
        assert tolerant == 1.0

    def test_unrelated_names_stay_low(self):
        e = _player(last_name='Schmidt', first_name='Hans')
        r = _player(last_name='Meyer', first_name='Karl')
        tolerant = calculate_confidence_tolerant(e, r, 0.5, 0.4)
        normal = calculate_confidence(e, r, 0.5, 0.4)
        # Tolerant may be slightly higher (JW on normalized) but still low
        assert tolerant <= 1.0
        assert tolerant >= normal

    def test_dob_mob_swap_yields_full_score(self):
        """A detected DoB/MoB swap must not penalize the tolerant confidence score."""
        e = _player(dob=6, mob=15)
        r = _player(dob=15, mob=6)
        score = calculate_confidence_tolerant(e, r, 1.0, 1.0)
        assert score == 1.0
