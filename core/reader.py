"""CSV reader with automatic encoding detection and field normalization."""

import csv
import io
import logging
import re
from pathlib import Path

from core import Player

log = logging.getLogger(__name__)

# Matches any sequence of whitespace (including Unicode whitespace like U+2006)
_WHITESPACE_RE = re.compile(r'\s+')


def detect_encoding(path: Path) -> str:
    """Detect file encoding by checking for BOM bytes.

    Args:
        path: Path to the CSV file.

    Returns:
        Encoding string suitable for open().
    """
    with open(path, 'rb') as f:
        bom = f.read(2)
    if bom == b'\xff\xfe':
        return 'utf-16-le'
    return 'utf-8-sig'


def normalize_whitespace(value: str) -> str:
    """Normalize whitespace in a string value.

    Collapses any sequence of whitespace (including Unicode whitespace)
    into a single space and strips leading/trailing whitespace.

    Args:
        value: Raw string value from CSV.

    Returns:
        Normalized string.
    """
    return _WHITESPACE_RE.sub(' ', value).strip()


def read_players(path: str | Path) -> list[Player]:
    """Read player records from a CSV file.

    Handles UTF-16LE (with BOM) and UTF-8 encoded files automatically.
    Fields are trimmed and whitespace-normalized.

    Args:
        path: Path to the CSV file.

    Returns:
        List of Player objects.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If required columns are missing.
    """
    path = Path(path)
    encoding = detect_encoding(path)

    with open(path, 'r', encoding=encoding) as f:
        content = f.read()

    # Strip BOM if present
    content = content.lstrip('\ufeff')

    reader = csv.DictReader(io.StringIO(content), delimiter='\t')

    required_cols = {'Extern ID', 'Last Name', 'First Name', 'Sex',
                     'Association', 'DoB', 'MoB', 'YoB'}
    if reader.fieldnames is None:
        raise ValueError(f"Datei {path} ist leer oder hat keine Header-Zeile.")
    actual_cols = {normalize_whitespace(c) for c in reader.fieldnames}
    missing = required_cols - actual_cols
    if missing:
        raise ValueError(
            f"Fehlende Spalten in {path}: {', '.join(sorted(missing))}"
        )

    players: list[Player] = []
    for row_num, row in enumerate(reader, start=2):
        # Normalize keys and values
        cleaned = {normalize_whitespace(k): normalize_whitespace(v)
                    for k, v in row.items() if k is not None}
        try:
            player = Player(
                extern_id=cleaned.get('Extern ID', ''),
                last_name=cleaned.get('Last Name', ''),
                first_name=cleaned.get('First Name', ''),
                sex=cleaned.get('Sex', ''),
                association=cleaned.get('Association', ''),
                dob=int(cleaned['DoB']) if cleaned.get('DoB') else 0,
                mob=int(cleaned['MoB']) if cleaned.get('MoB') else 0,
                yob=int(cleaned['YoB']) if cleaned.get('YoB') else 0,
            )
            players.append(player)
        except (ValueError, KeyError) as exc:
            log.warning("Zeile %d in %s uebersprungen: %s", row_num, path, exc)

    log.info("%d Spieler gelesen aus %s", len(players), path)
    return players
