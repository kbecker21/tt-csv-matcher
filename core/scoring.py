"""Confidence scoring and issue detection for player matches."""

import unicodedata

from rapidfuzz.distance import JaroWinkler

from core import Player

WEIGHTS: dict[str, float] = {
    'lastname': 0.30,
    'firstname': 0.25,
    'dob': 0.10,
    'mob': 0.10,
    'yob': 0.15,
    'sex': 0.05,
    'association': 0.05,
}


def is_dob_mob_swapped(event: Player, ref: Player) -> bool:
    """Check if day and month of birth are swapped between event and ref.

    Only flags a swap when day != month (otherwise swapping is a no-op).

    Args:
        event: Player from the event file.
        ref: Player from the reference database.

    Returns:
        True if DoB and MoB appear to be swapped.
    """
    return (
        event.dob == ref.mob
        and event.mob == ref.dob
        and event.yob == ref.yob
        and event.dob != event.mob  # Guard: only flag when swap changes values
    )


def calculate_confidence(
    event: Player,
    ref: Player,
    lastname_sim: float,
    firstname_sim: float,
) -> float:
    """Calculate the confidence score for a match.

    A detected DoB/MoB swap is treated as a correct match (same as NAME_SWAP),
    so both dob and mob contribute their full weight to the score.

    Args:
        event: Player from the event file.
        ref: Player from the reference database.
        lastname_sim: Jaro-Winkler similarity for last name (0.0–1.0).
        firstname_sim: Jaro-Winkler similarity for first name (0.0–1.0).

    Returns:
        Confidence score between 0.0 and 1.0.
    """
    dob_swapped = is_dob_mob_swapped(event, ref)
    score = (
        WEIGHTS['lastname'] * lastname_sim
        + WEIGHTS['firstname'] * firstname_sim
        + WEIGHTS['dob'] * (1.0 if event.dob == ref.dob or dob_swapped else 0.0)
        + WEIGHTS['mob'] * (1.0 if event.mob == ref.mob or dob_swapped else 0.0)
        + WEIGHTS['yob'] * (1.0 if event.yob == ref.yob else 0.0)
        + WEIGHTS['sex'] * (1.0 if event.sex.upper() == ref.sex.upper() else 0.0)
        + WEIGHTS['association'] * (1.0 if event.association.upper() == ref.association.upper() else 0.0)
    )
    return round(score, 4)


def normalize_for_tolerant_comparison(text: str) -> str:
    """Normalize text for tolerant name comparison.

    Removes accents/diacritics via NFD decomposition, strips spaces,
    hyphens, dots, commas and semicolons, then uppercases.

    Args:
        text: Raw name string.

    Returns:
        Normalized string for comparison.
    """
    # NFD decomposition: split base characters from combining marks
    decomposed = unicodedata.normalize('NFD', text)
    # Remove combining marks (category 'Mn')
    stripped = ''.join(ch for ch in decomposed if unicodedata.category(ch) != 'Mn')
    # Remove whitespace and punctuation characters
    for ch in (' ', '-', '.', ',', ';'):
        stripped = stripped.replace(ch, '')
    return stripped.upper()


def calculate_confidence_tolerant(
    event: Player,
    ref: Player,
    lastname_sim: float,
    firstname_sim: float,
) -> float:
    """Calculate tolerant confidence score using accent-/punctuation-normalized names.

    If normalized names are identical, similarity is set to 1.0.
    Otherwise falls back to Jaro-Winkler on the normalized forms.

    Args:
        event: Player from the event file.
        ref: Player from the reference database.
        lastname_sim: Original Jaro-Winkler similarity for last name.
        firstname_sim: Original Jaro-Winkler similarity for first name.

    Returns:
        Tolerant confidence score between 0.0 and 1.0.
    """
    norm_event_ln = normalize_for_tolerant_comparison(event.last_name)
    norm_ref_ln = normalize_for_tolerant_comparison(ref.last_name)
    norm_event_fn = normalize_for_tolerant_comparison(event.first_name)
    norm_ref_fn = normalize_for_tolerant_comparison(ref.first_name)

    if norm_event_ln == norm_ref_ln:
        ln_sim_t = 1.0
    else:
        ln_sim_t = max(lastname_sim, JaroWinkler.similarity(norm_event_ln, norm_ref_ln))

    if norm_event_fn == norm_ref_fn:
        fn_sim_t = 1.0
    else:
        fn_sim_t = max(firstname_sim, JaroWinkler.similarity(norm_event_fn, norm_ref_fn))

    dob_swapped = is_dob_mob_swapped(event, ref)
    score = (
        WEIGHTS['lastname'] * ln_sim_t
        + WEIGHTS['firstname'] * fn_sim_t
        + WEIGHTS['dob'] * (1.0 if event.dob == ref.dob or dob_swapped else 0.0)
        + WEIGHTS['mob'] * (1.0 if event.mob == ref.mob or dob_swapped else 0.0)
        + WEIGHTS['yob'] * (1.0 if event.yob == ref.yob else 0.0)
        + WEIGHTS['sex'] * (1.0 if event.sex.upper() == ref.sex.upper() else 0.0)
        + WEIGHTS['association'] * (1.0 if event.association.upper() == ref.association.upper() else 0.0)
    )
    return round(score, 4)


def detect_issues(
    event: Player,
    ref: Player,
    match_type: str,
    lastname_sim: float,
    firstname_sim: float,
) -> list[str]:
    """Detect all issues between an event player and a reference player.

    Args:
        event: Player from the event file.
        ref: Player from the reference database.
        match_type: Type of match (EXACT, NAME_SWAP, FUZZY).
        lastname_sim: Jaro-Winkler similarity for last name (0.0–1.0).
        firstname_sim: Jaro-Winkler similarity for first name (0.0–1.0).

    Returns:
        List of issue codes.
    """
    issues: list[str] = []

    if match_type == 'NAME_SWAP':
        issues.append('NAME_SWAPPED')

    if lastname_sim < 1.0 and match_type == 'FUZZY':
        issues.append('LASTNAME_FUZZY')

    if firstname_sim < 1.0 and match_type == 'FUZZY':
        issues.append('FIRSTNAME_FUZZY')

    # DoB/MoB swap detection
    if is_dob_mob_swapped(event, ref):
        issues.append('DOB_MOB_SWAPPED')
    else:
        # Only report individual mismatches if NOT a swap
        if event.dob != ref.dob:
            issues.append('DOB_MISMATCH')
        if event.mob != ref.mob:
            issues.append('MOB_MISMATCH')

    if event.yob != ref.yob:
        issues.append('YOB_MISMATCH')

    if event.sex.upper() != ref.sex.upper():
        issues.append('SEX_MISMATCH')

    if event.association.upper() != ref.association.upper():
        issues.append('ASSOC_MISMATCH')

    return issues
