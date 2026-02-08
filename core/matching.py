"""Multi-stage matching engine for player records."""

import logging
from collections import defaultdict

from rapidfuzz.distance import JaroWinkler

from core import Player, MatchResult
from core.scoring import calculate_confidence, calculate_confidence_tolerant, detect_issues

log = logging.getLogger(__name__)

# Default fuzzy thresholds (0–1 scale)
DEFAULT_LASTNAME_THRESHOLD = 0.85
DEFAULT_FIRSTNAME_THRESHOLD = 0.80


def _normalize_key(value: str) -> str:
    """Normalize a name for hash-index lookup."""
    return value.strip().upper()


def _build_name_index(players: list[Player]) -> dict[tuple[str, str], list[Player]]:
    """Build a hash index for exact name matching (last_name, first_name)."""
    index: dict[tuple[str, str], list[Player]] = defaultdict(list)
    for p in players:
        key = (_normalize_key(p.last_name), _normalize_key(p.first_name))
        index[key].append(p)
    return dict(index)


def _build_swap_index(players: list[Player]) -> dict[tuple[str, str], list[Player]]:
    """Build a hash index for name-swap matching (first_name, last_name)."""
    index: dict[tuple[str, str], list[Player]] = defaultdict(list)
    for p in players:
        key = (_normalize_key(p.first_name), _normalize_key(p.last_name))
        index[key].append(p)
    return dict(index)


def _pick_best_candidate(
    event: Player,
    candidates: list[Player],
    match_type: str,
    lastname_sim: float,
    firstname_sim: float,
) -> MatchResult:
    """Pick the best candidate from a list based on confidence score."""
    best_result: MatchResult | None = None
    best_confidence = -1.0

    for ref in candidates:
        ln_sim = lastname_sim
        fn_sim = firstname_sim

        # For name-swap, the similarities are swapped too
        if match_type == 'NAME_SWAP':
            ln_sim = 1.0
            fn_sim = 1.0

        confidence = calculate_confidence(event, ref, ln_sim, fn_sim)
        if confidence > best_confidence:
            best_confidence = confidence
            issues = detect_issues(event, ref, match_type, ln_sim, fn_sim)
            conf_tolerant = calculate_confidence_tolerant(event, ref, ln_sim, fn_sim)
            best_result = MatchResult(
                event_player=event,
                ref_player=ref,
                match_type=match_type,
                confidence=confidence,
                confidence_tolerant=conf_tolerant,
                issues=issues,
            )

    assert best_result is not None
    return best_result


def _try_fuzzy_match(
    event: Player,
    ref_players: list[Player],
    lastname_threshold: float,
    firstname_threshold: float,
) -> MatchResult | None:
    """Try to find a fuzzy match for an event player.

    Args:
        event: Player from the event file.
        ref_players: All reference players.
        lastname_threshold: Minimum similarity for last name (0–1).
        firstname_threshold: Minimum similarity for first name (0–1).

    Returns:
        Best MatchResult if a fuzzy match is found, None otherwise.
    """
    event_ln = _normalize_key(event.last_name)
    event_fn = _normalize_key(event.first_name)

    best_result: MatchResult | None = None
    best_confidence = -1.0

    for ref in ref_players:
        ref_ln = _normalize_key(ref.last_name)
        ref_fn = _normalize_key(ref.first_name)

        ln_sim = JaroWinkler.similarity(event_ln, ref_ln)
        fn_sim = JaroWinkler.similarity(event_fn, ref_fn)

        if ln_sim >= lastname_threshold and fn_sim >= firstname_threshold:
            confidence = calculate_confidence(event, ref, ln_sim, fn_sim)
            if confidence > best_confidence:
                best_confidence = confidence
                issues = detect_issues(event, ref, 'FUZZY', ln_sim, fn_sim)
                conf_tolerant = calculate_confidence_tolerant(event, ref, ln_sim, fn_sim)
                best_result = MatchResult(
                    event_player=event,
                    ref_player=ref,
                    match_type='FUZZY',
                    confidence=confidence,
                    confidence_tolerant=conf_tolerant,
                    issues=issues,
                )

    return best_result


def match_players(
    ref_players: list[Player],
    event_players: list[Player],
    fuzzy_threshold: float = 0.85,
) -> list[MatchResult]:
    """Match event players against the reference database.

    Uses a multi-stage approach:
    1. Exact name match (hash lookup)
    2. Name-swap detection (hash lookup)
    3. Fuzzy matching (brute-force with Jaro-Winkler)
    4. Unmatched → NONE

    Args:
        ref_players: Players from the reference database.
        event_players: Players from the event file.
        fuzzy_threshold: Threshold for fuzzy last name matching (0–1 scale).

    Returns:
        List of MatchResult for every event player.
    """
    name_index = _build_name_index(ref_players)
    swap_index = _build_swap_index(ref_players)

    lastname_threshold = fuzzy_threshold
    firstname_threshold = DEFAULT_FIRSTNAME_THRESHOLD

    results: list[MatchResult] = []

    for event in event_players:
        event_key = (_normalize_key(event.last_name), _normalize_key(event.first_name))

        # Stage 1: Exact match
        exact_candidates = name_index.get(event_key)
        if exact_candidates:
            result = _pick_best_candidate(event, exact_candidates, 'EXACT', 1.0, 1.0)
            results.append(result)
            continue

        # Stage 2: Name-swap match
        swap_candidates = swap_index.get(event_key)
        if swap_candidates:
            result = _pick_best_candidate(event, swap_candidates, 'NAME_SWAP', 1.0, 1.0)
            results.append(result)
            continue

        # Stage 3: Fuzzy match
        fuzzy_result = _try_fuzzy_match(
            event, ref_players, lastname_threshold, firstname_threshold,
        )
        if fuzzy_result:
            results.append(fuzzy_result)
            continue

        # Stage 4: No match
        results.append(MatchResult(
            event_player=event,
            ref_player=None,
            match_type='NONE',
            confidence=0.0,
            issues=['NO_MATCH'],
        ))

    log.info(
        "Matching abgeschlossen: %d Spieler verarbeitet",
        len(results),
    )
    return results
