# tt-csv-matcher

CLI-Tool zum Abgleich von Tischtennis-Event-CSV-Dateien gegen eine Referenz-Datenbank. Erkennt Tippfehler, vertauschte Felder und inkonsistente Spielerdaten.

## Installation

```bash
pip install -r requirements.txt
```

Voraussetzung: Python 3.10+

## Daten vorbereiten

**Wichtig:** Die CSV-Dateien sind aus Datenschutzgruenden nicht im Repository enthalten. Vor der Nutzung muessen eigene Dateien im Verzeichnis `data/` abgelegt werden.

Benoetigte Dateien:

| Datei | Beschreibung |
|-------|-------------|
| `data/Reference.csv` | Referenz-Datenbank mit allen bekannten Spielern |
| `data/<event>.csv` | Event-Datei(en), die abgeglichen werden sollen |

### CSV-Format

Alle Dateien muessen folgendes Format haben:

- **Encoding:** UTF-16LE mit BOM
- **Trennzeichen:** Tab (`\t`)
- **Zeilenende:** CRLF
- **Pflichtfelder:** `Extern ID`, `Last Name`, `First Name`, `Sex`, `Association`, `DoB`, `MoB`, `YoB`

## Verwendung

### Einzelne Event-Datei pruefen

```bash
python matcher.py --ref data/Reference.csv --event data/evc2025.csv --output report.csv --summary
```

### Mit HTML-Report

```bash
python matcher.py --ref data/Reference.csv --event data/evc2025.csv --output report.csv --html --summary
```

### Batch-Modus (alle CSVs in einem Verzeichnis)

```bash
python matcher.py --ref data/Reference.csv --event-dir data/ --output-dir reports/
```

### Schwellenwert anpassen

```bash
python matcher.py --ref data/Reference.csv --event data/evc2025.csv --output report.csv --fuzzy-threshold 0.90
```

## Matching-Strategie

Das Tool verwendet ein mehrstufiges Matching:

1. **Exakter Match** — Nachname + Vorname identisch (case-insensitive)
2. **Name-Swap** — Erkennung vertauschter Vor-/Nachnamen
3. **Fuzzy Match** — Jaro-Winkler-Similarity fuer Tippfehler-Erkennung
4. **Kein Match** — Neue Spieler oder zu starke Abweichungen

Zusaetzlich werden erkannt:
- Vertauschter Geburtstag/Monat (DoB/MoB-Swap)
- Abweichende Nationalitaet, Geschlecht, Geburtsdaten

## Report-Ausgabe

### CSV-Report
- Encoding: UTF-8 mit BOM (kompatibel mit deutschem Excel)
- Trennzeichen: Semikolon

### HTML-Report
- Farbcodierte Tabelle (gruen=exakt, gelb=swap, orange=fuzzy, rot=kein Match)
- Zusammenfassung mit Statistiken

## Tests

```bash
python -m pytest tests/ -v
```

## Projektstruktur

```
tt-csv-matcher/
├── matcher.py             # CLI-Einstiegspunkt
├── core/
│   ├── __init__.py        # Player/MatchResult Dataclasses
│   ├── reader.py          # CSV-Einlesen & Normalisierung
│   ├── matching.py        # Mehrstufige Matching-Engine
│   ├── scoring.py         # Confidence-Score & Issue-Erkennung
│   └── reporter.py        # Report-Generierung (CSV/HTML/Summary)
├── templates/
│   └── report.html        # Jinja2-Template
├── tests/
│   ├── conftest.py        # Gemeinsame Test-Fixtures
│   ├── test_reader.py
│   ├── test_matching.py
│   └── test_scoring.py
├── data/                  # CSV-Dateien hier ablegen (nicht im Repo)
├── requirements.txt
└── README.md
```
