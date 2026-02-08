"""tt-csv-matcher – CLI-Tool zum Abgleich von Tischtennis-Event-CSVs."""

import argparse
import logging
import sys
from pathlib import Path

from core.reader import read_players
from core.matching import match_players
from core.reporter import write_csv_report, write_html_report, print_summary


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description='Abgleich von Tischtennis-Event-CSVs gegen eine Referenz-Datenbank.',
        prog='matcher.py',
    )
    parser.add_argument(
        '--ref', required=True, type=Path,
        help='Pfad zur Referenz-CSV-Datei',
    )
    parser.add_argument(
        '--event', type=Path,
        help='Pfad zur Event-CSV-Datei',
    )
    parser.add_argument(
        '--event-dir', type=Path,
        help='Verzeichnis mit Event-CSV-Dateien (Batch-Modus)',
    )
    parser.add_argument(
        '--output', type=Path,
        help='Pfad fuer die Report-Ausgabe (CSV)',
    )
    parser.add_argument(
        '--output-dir', type=Path,
        help='Verzeichnis fuer Report-Ausgaben (Batch-Modus)',
    )
    parser.add_argument(
        '--html', action='store_true',
        help='Zusaetzlich einen HTML-Report erzeugen',
    )
    parser.add_argument(
        '--summary', action='store_true',
        help='Zusammenfassung auf stdout ausgeben',
    )
    parser.add_argument(
        '--fuzzy-threshold', type=float, default=0.85,
        help='Schwellenwert fuer Fuzzy-Matching (Standard: 0.85)',
    )
    return parser


def process_single_event(
    ref_players: list,
    event_path: Path,
    output_path: Path,
    html: bool,
    summary: bool,
    fuzzy_threshold: float,
) -> None:
    """Process a single event file against the reference database."""
    event_players = read_players(event_path)
    results = match_players(ref_players, event_players, fuzzy_threshold)

    write_csv_report(results, output_path)
    logging.info("CSV-Report geschrieben: %s", output_path)

    if html:
        html_path = output_path.with_suffix('.html')
        write_html_report(results, html_path, event_path.stem)
        logging.info("HTML-Report geschrieben: %s", html_path)

    if summary:
        print_summary(results, event_path.name)


def main() -> None:
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s',
    )

    parser = build_parser()
    args = parser.parse_args()

    if not args.event and not args.event_dir:
        parser.error('Entweder --event oder --event-dir muss angegeben werden.')

    if args.event and not args.output:
        parser.error('--output ist erforderlich bei Verwendung von --event.')

    if args.event_dir and not args.output_dir:
        parser.error('--output-dir ist erforderlich bei Verwendung von --event-dir.')

    ref_players = read_players(args.ref)

    if args.event:
        process_single_event(
            ref_players, args.event, args.output,
            args.html, args.summary, args.fuzzy_threshold,
        )
    elif args.event_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        csv_files = sorted(args.event_dir.glob('*.csv'))
        # Exclude the reference file from batch processing
        ref_resolved = args.ref.resolve()
        csv_files = [f for f in csv_files if f.resolve() != ref_resolved]

        if not csv_files:
            logging.warning("Keine CSV-Dateien in %s gefunden.", args.event_dir)
            return

        for event_path in csv_files:
            output_path = args.output_dir / f"report_{event_path.stem}.csv"
            logging.info("Verarbeite %s ...", event_path.name)
            process_single_event(
                ref_players, event_path, output_path,
                args.html, args.summary, args.fuzzy_threshold,
            )


if __name__ == '__main__':
    main()
