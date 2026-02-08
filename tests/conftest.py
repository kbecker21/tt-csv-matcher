"""Shared test fixtures."""

from pathlib import Path

import pytest

from core.reader import read_players


DATA_DIR = Path(__file__).resolve().parent.parent / 'data'


@pytest.fixture(scope='session')
def data_dir() -> Path:
    """Path to the data directory."""
    return DATA_DIR


@pytest.fixture(scope='session')
def ref_players():
    """All players from Reference.csv."""
    return read_players(DATA_DIR / 'Reference.csv')


@pytest.fixture(scope='session')
def evc2025_players():
    """All players from evc2025.csv."""
    return read_players(DATA_DIR / 'evc2025.csv')
