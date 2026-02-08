"""Confidence scoring and issue detection for player matches."""

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


def calculate_confidence(
    event: Player,
    ref: Player,
    lastname_sim: float,
    firstname_sim: float,
) -> float:
    """Calculate the confidence score for a match.

    Args:
        event: Player from the event file.
        ref: Player from the reference database.
        lastname_sim: Jaro-Winkler similarity for last name (0.0–1.0).
        firstname_sim: Jaro-Winkler similarity for first name (0.0–1.0).

    Returns:
        Confidence score between 0.0 and 1.0.
    """
    score = (
        WEIGHTS['lastname'] * lastname_sim
        + WEIGHTS['firstname'] * firstname_sim
        + WEIGHTS['dob'] * (1.0 if event.dob == ref.dob else 0.0)
        + WEIGHTS['mob'] * (1.0 if event.mob == ref.mob else 0.0)
        + WEIGHTS['yob'] * (1.0 if event.yob == ref.yob else 0.0)
        + WEIGHTS['sex'] * (1.0 if event.sex.upper() == ref.sex.upper() else 0.0)
        + WEIGHTS['association'] * (1.0 if event.association.upper() == ref.association.upper() else 0.0)
    )
    return round(score, 4)


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
