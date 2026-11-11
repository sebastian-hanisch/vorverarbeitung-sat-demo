"""Randfälle der Vorverarbeitung (DEMO-PLAYBOOK §12): leere Formel, einzelne Einheit, doppelte Literale, Tautologie, reine Variable, null Resolventen, Grenzen."""

import pytest

import vvs_algorithm as A
import vvs_evaluation as ev


def test_leere_formel_und_einzelne_einheit():
    leer = A.vorverarbeite(3, [])
    assert not leer.unerfuellbar and leer.klauseln == [] and leer.zaehler["runden"] == 0 and leer.variablen_alt == 0
    eins = A.vorverarbeite(1, [(1,)])
    assert eins.einheiten == {1: True} and eins.klauseln == [] and A.modell_rekonstruieren(eins, {}) == {1: True}


def test_doppeltes_literal_tautologie_und_doppelte_klausel():
    assert A.normalisiere([(2, 2, 1), (1, -1, 3), (1, 2), (2, 1)]) == [(1, 2)]
    v = A.vorverarbeite(3, [(1, 1), (2, -2)])
    assert v.einheiten == {1: True} and v.klauseln == []          # (x1 ∨ x1) ist die Einheit x1, die Tautologie fällt weg


def test_reine_variable_hat_null_resolventen():
    e = A.eliminiere([(1, 2), (1, 3), (-2, 3)], 1)            # x1 nur positiv: keine negative Klausel, keine Resolvente
    assert e.erlaubt and e.resolventen == [] and e.berechnet == 0 and e.klauseln == [(-2, 3)] and e.stapel == (1, [(1, 2), (1, 3)])
    v = A.vorverarbeite(3, [(1, 2), (1, 3), (-2, 3)])
    voll = A.modell_rekonstruieren(v, {x: False for x in A.variablen_von(v.klauseln)})
    assert voll[1] is True                                    # x1 muss wahr werden, damit (x1 ∨ x2) erfüllt ist


def test_eliminieren_einer_variablen_die_nicht_vorkommt():
    e = A.eliminiere([(1, 2)], 5)
    assert e.erlaubt and e.klauseln == [(1, 2)] and e.stapel == (5, [])


def test_widerspruch_ueber_einheiten_und_elimination():
    assert A.einheiten([(1,), (-1, 2), (-2,)]).widerspruch
    assert A.vorverarbeite(2, [(1, 2), (-1, 2), (1, -2), (-1, -2)]).unerfuellbar       # die Elimination liefert (x2) und (¬x2)
    with pytest.raises(ValueError):
        A.modell_rekonstruieren(A.vorverarbeite(1, [(1,), (-1,)]), {})


def test_alles_eingefroren_eliminiert_nichts():
    kl = [(1, 2), (-1, 3), (-2, -3)]
    v = A.vorverarbeite(3, kl, eingefroren={1, 2, 3})
    assert v.stapel == [] and v.zaehler["eliminiert"] == 0 and sorted(v.klauseln) == sorted(kl)


def test_runden_grenzen():
    kl = [(1, 2), (-1, 3), (-2, -3), (2, 3)]
    assert A.vorverarbeite(3, kl, runden=0).zaehler["runden"] == 0
    assert A.vorverarbeite(3, kl, runden=1).zaehler["runden"] <= 1


def test_zahlen_deutsch_und_prozent():
    assert ev.de(1476) == "1.476" and ev.de(1562.5, 1) == "1.562,5" and ev.de(-24.0) == "−24" and ev.de(-0.04, 1) == "0,0"
    assert ev.prozent_aenderung(0, 5) is None and ev.prozent_aenderung(200, 150) == -25.0
    assert ev.de_prozent(None) == "–" and ev.de_prozent(11.0) == "+11 %" and ev.de_prozent(-24.4, 1) == "−24,4 %"
