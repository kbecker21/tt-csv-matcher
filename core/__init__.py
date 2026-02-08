"""Core module for tt-csv-matcher."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Player:
    """Represents a player record from a CSV file."""

    extern_id: str
    last_name: str
    first_name: str
    sex: str
    association: str
    dob: int      # Day of birth
    mob: int      # Month of birth
    yob: int      # Year of birth


@dataclass
class MatchResult:
    """Result of matching an event player against the reference database."""

    event_player: Player
    ref_player: Optional[Player]
    match_type: str       # EXACT, NAME_SWAP, FUZZY, NONE
    confidence: float     # 0.0 – 1.0
    confidence_tolerant: float = 0.0  # 0.0 – 1.0 (tolerant name comparison)
    issues: list[str] = field(default_factory=list)
