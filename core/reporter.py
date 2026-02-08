"""Report generation for match results (CSV, HTML, summary)."""

import csv
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from core import MatchResult

log = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / 'templates'

CSV_COLUMNS = [
    'Event_ExternID',
    'Event_LastName',
    'Event_FirstName',
    'Event_Sex',
    'Event_Association',
    'Event_DoB',
    'Event_MoB',
    'Event_YoB',
    'Ref_ExternID',
    'Ref_LastName',
    'Ref_FirstName',
    'Ref_Sex',
    'Ref_Association',
    'Ref_DoB',
    'Ref_MoB',
    'Ref_YoB',
    'Match_Type',
    'Confidence',
    'Issues',
]


def _result_to_row(result: MatchResult) -> dict:
    """Convert a MatchResult to a flat dict for CSV/HTML output."""
    ep = result.event_player
    ref = result.ref_player
    return {
        'Event_ExternID': ep.extern_id,
        'Event_LastName': ep.last_name,
        'Event_FirstName': ep.first_name,
        'Event_Sex': ep.sex,
        'Event_Association': ep.association,
        'Event_DoB': str(ep.dob),
        'Event_MoB': str(ep.mob),
        'Event_YoB': str(ep.yob),
        'Ref_ExternID': ref.extern_id if ref else '',
        'Ref_LastName': ref.last_name if ref else '',
        'Ref_FirstName': ref.first_name if ref else '',
        'Ref_Sex': ref.sex if ref else '',
        'Ref_Association': ref.association if ref else '',
        'Ref_DoB': str(ref.dob) if ref else '',
        'Ref_MoB': str(ref.mob) if ref else '',
        'Ref_YoB': str(ref.yob) if ref else '',
        'Match_Type': result.match_type,
        'Confidence': f'{result.confidence:.4f}',
        'Issues': ', '.join(result.issues),
        # Set of issue codes for targeted cell highlighting in HTML
        '_issues': set(result.issues),
    }


def write_csv_report(results: list[MatchResult], output_path: Path) -> None:
    """Write match results as a CSV report.

    Uses UTF-8 with BOM (utf-8-sig) and semicolon delimiter for
    compatibility with German Excel.

    Args:
        results: List of match results.
        output_path: Path for the output CSV file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(
            f, fieldnames=CSV_COLUMNS, delimiter=';', extrasaction='ignore',
        )
        writer.writeheader()
        for result in results:
            writer.writerow(_result_to_row(result))

    log.info("CSV-Report geschrieben: %s (%d Zeilen)", output_path, len(results))


def write_html_report(
    results: list[MatchResult],
    output_path: Path,
    event_name: str = '',
) -> None:
    """Write match results as an HTML report using Jinja2.

    Args:
        results: List of match results.
        output_path: Path for the output HTML file.
        event_name: Name of the event file (for the report title).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )
    template = env.get_template('report.html')

    rows = [_result_to_row(r) for r in results]
    stats = _compute_stats(results)

    html = template.render(
        event_name=event_name,
        rows=rows,
        stats=stats,
        columns=CSV_COLUMNS,
    )

    output_path.write_text(html, encoding='utf-8')
    log.info("HTML-Report geschrieben: %s", output_path)


def _compute_stats(results: list[MatchResult]) -> dict:
    """Compute summary statistics from match results."""
    total = len(results)
    exact = sum(1 for r in results if r.match_type == 'EXACT')
    name_swap = sum(1 for r in results if r.match_type == 'NAME_SWAP')
    fuzzy = sum(1 for r in results if r.match_type == 'FUZZY')
    none = sum(1 for r in results if r.match_type == 'NONE')

    all_issues = []
    for r in results:
        all_issues.extend(r.issues)

    return {
        'total': total,
        'exact': exact,
        'name_swap': name_swap,
        'fuzzy': fuzzy,
        'none': none,
        'dob_mob_swapped': all_issues.count('DOB_MOB_SWAPPED'),
        'dob_mismatch': all_issues.count('DOB_MISMATCH'),
        'mob_mismatch': all_issues.count('MOB_MISMATCH'),
        'yob_mismatch': all_issues.count('YOB_MISMATCH'),
        'sex_mismatch': all_issues.count('SEX_MISMATCH'),
        'assoc_mismatch': all_issues.count('ASSOC_MISMATCH'),
        'issues_total': sum(
            1 for r in results if r.issues and r.issues != ['NO_MATCH']
        ),
    }


def print_summary(results: list[MatchResult], event_name: str = '') -> None:
    """Print a summary of match results to stdout.

    Args:
        results: List of match results.
        event_name: Name of the event file.
    """
    stats = _compute_stats(results)

    print(f"\n=== Match-Report: {event_name} ===")
    print(f"Gesamt Event-Eintraege:    {stats['total']:>5}")
    print(f"Exakte Matches:            {stats['exact']:>5}")
    print(f"Name-Swaps erkannt:        {stats['name_swap']:>5}")
    print(f"Fuzzy Matches:             {stats['fuzzy']:>5}")
    print(f"DoB/MoB vertauscht:        {stats['dob_mob_swapped']:>5}")
    print(f"Kein Match gefunden:       {stats['none']:>5}")
    print("---")
    print(f"Fehler gesamt:             {stats['issues_total']:>5}")
    print(f"  - Geburtstag falsch:     {stats['dob_mismatch']:>5}")
    print(f"  - Monat falsch:          {stats['mob_mismatch']:>5}")
    print(f"  - Jahr falsch:           {stats['yob_mismatch']:>5}")
    print(f"  - Nationalitaet falsch:  {stats['assoc_mismatch']:>5}")
    print(f"  - Geschlecht falsch:     {stats['sex_mismatch']:>5}")
    print()
