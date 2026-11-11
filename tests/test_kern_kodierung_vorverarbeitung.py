"""Regressionstests der kopierten Kern-Module `vvs_kodierung` und `vvs_vorverarbeitung` (aus sat-cp-planung/kern/tests/test_kodierung_vorverarbeitung_probsat.py,
Importe auf vvs_ umgestellt, sonst unverändert; der probSAT-Teil entfällt, weil das Modul nicht kopiert ist). `vvs_vorverarbeitung` ist die Kern-Fassung (nichts eingefroren,
Schritte privat); die App benutzt `vvs_algorithm`, die Kern-Fassung dient als Vergleich (tests/test_algorithm.py)."""
import itertools
from math import comb

import pytest

import vvs_instanzen as I
from vvs_cdcl import solve
from vvs_kodierung import (Hilfsvariablen, genau, hoechstens, hoechstens_eins, klauselzahl_binomial, klauselzahl_sinz,
                           mindestens)
from vvs_vorverarbeitung import modell_rekonstruieren, vorverarbeite


def zaehle_loesungen(n, klauseln, n_gesamt, belegung):
    einheiten = [((i + 1) if b else -(i + 1),) for i, b in enumerate(belegung)]
    return solve(n_gesamt, list(klauseln) + einheiten).antwort is True


@pytest.mark.parametrize("verfahren", ["binomial", "sinz", "totalizer"])
def test_hoechstens_exakt_gegen_aufzaehlung(verfahren):
    n = 6
    for k in range(0, n + 1):
        pool = Hilfsvariablen(n)
        kl = hoechstens(list(range(1, n + 1)), k, pool, verfahren)
        for bits in itertools.product([False, True], repeat=n):
            erwartet = sum(bits) <= k
            assert zaehle_loesungen(n, kl, pool.n, bits) == erwartet, (verfahren, k, bits)


@pytest.mark.parametrize("verfahren", ["binomial", "sinz", "totalizer"])
def test_mindestens_und_genau_gegen_aufzaehlung(verfahren):
    n = 5
    for k in range(0, n + 2):
        pool_m, pool_g = Hilfsvariablen(n), Hilfsvariablen(n)
        km = mindestens(list(range(1, n + 1)), k, pool_m, verfahren)
        kg = genau(list(range(1, n + 1)), k, pool_g, verfahren)
        for bits in itertools.product([False, True], repeat=n):
            assert zaehle_loesungen(n, km, pool_m.n, bits) == (sum(bits) >= k), (verfahren, k, bits)
            assert zaehle_loesungen(n, kg, pool_g.n, bits) == (sum(bits) == k), (verfahren, k, bits)


def test_klauselzahlen_formeln():
    for n, k in [(5, 1), (6, 2), (10, 4), (20, 7)]:
        pool = Hilfsvariablen(n)
        kl = hoechstens(list(range(1, n + 1)), k, pool, "sinz")
        assert len(kl) == klauselzahl_sinz(n, k) == 2 * n * k + n - 3 * k - 1      # Sinz 2005, nachgerechnet
        assert pool.n - n == (n - 1) * k
        pool_b = Hilfsvariablen(n)
        assert len(hoechstens(list(range(1, n + 1)), k, pool_b, "binomial")) == klauselzahl_binomial(n, k) == comb(n, k + 1)
    assert len(hoechstens_eins([1, 2, 3])) == 3


def test_randfaelle_kodierung():
    pool = Hilfsvariablen(3)
    assert hoechstens([1, 2, 3], 3, pool, "sinz") == [] and pool.n == 3
    assert mindestens([1, 2], 3, Hilfsvariablen(2)) == [()]
    assert mindestens([1, 2], 0, Hilfsvariablen(2)) == []


def test_kern_vorverarbeitung_handbeispiel():
    v = vorverarbeite(5, [(1,), (-1, 2), (2, 3), (-3, 4), (-4, -2, 5)])
    assert not v.unerfuellbar and v.einheiten == {1: True, 2: True}
    erg = solve(v.n_neu, v.klauseln) if v.n_neu else None
    modell = modell_rekonstruieren(v, erg.modell if erg else {})
    assert I.pruefe_modell([(1,), (-1, 2), (2, 3), (-3, 4), (-4, -2, 5)], modell)


def test_kern_vorverarbeitung_erkennt_unerfuellbar():
    assert vorverarbeite(2, [(1,), (-1, 2), (-2,)]).unerfuellbar
    assert vorverarbeite(2, [(1, 2), (-1, 2), (1, -2), (-1, -2)]).unerfuellbar


def test_kern_vorverarbeitung_erhaelt_antwort_und_modell():
    gesehen_sat = gesehen_unsat = 0
    for seed in range(40):
        inst = I.rand3(40, 150 + seed, seed)
        orig = solve(inst.n, inst.klauseln)
        v = vorverarbeite(inst.n, inst.klauseln)
        if v.unerfuellbar:
            assert orig.antwort is False
            gesehen_unsat += 1
            continue
        neu = solve(v.n_neu, v.klauseln) if v.n_neu else None
        antwort = True if neu is None else neu.antwort
        assert antwort == orig.antwort
        if antwort:
            gesehen_sat += 1
            assert I.pruefe_modell(inst.klauseln, modell_rekonstruieren(v, neu.modell if neu else {}))
    assert gesehen_sat > 5 and gesehen_unsat + gesehen_sat >= 20
