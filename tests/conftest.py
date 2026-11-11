"""Gemeinsame Fixtures: die Handbeispiele, an denen jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def teil1():
    """Handbeispiel Teil 1: P = (x1), (x1 x3), (¬x1 x2 x4), (x2 x3 x4), (¬x2 x4)."""
    return [(1,), (1, 3), (-1, 2, 4), (2, 3, 4), (-2, 4)]


@pytest.fixture
def sinz3():
    """Handbeispiel Teil 2: Sinz-Zähler „höchstens 1 von x1 x2 x3“ (Hilfsvariablen x4, x5) plus (x1 x2 x3): 6 Klauseln, 5 Variablen."""
    return [(-1, 4), (-2, 5), (-4, 5), (-2, -4), (-3, -5), (1, 2, 3)]
