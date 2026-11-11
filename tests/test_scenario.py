"""Aufgaben der Demo: Erzeuger gegen Zählformeln, Erfüllbarkeit des Quadrats mit Lücken und Determinismus (SplitMix64)."""

import vvs_algorithm as A
import vvs_constants as C
import vvs_scenario as S
from vvs_cdcl import solve


def test_vertex_cover_groessen():
    a = S.vertex_cover(60, 3.0, 24, "sinz", 1700)
    assert a.meta["kanten"] == 90 and a.n == 60 + 59 * 24 == 1476                     # n + (n − 1)k Variablen (Sinz 2005)
    assert len(a.klauseln) == 90 + 2 * 60 * 24 + 60 - 3 * 24 - 1 == 2957             # Kanten + Zählerklauseln
    t = S.vertex_cover(60, 3.0, 24, "totalizer", 1700)
    assert t.n == 371 and len(t.klauseln) == 1932                                      # gleiche Größe wie in der Vormessung V15 (Totalizer)
    assert a.eingaenge == tuple(range(1, 61)) and S.vc_k(60) == 24 and S.vc_k(40) == 16


def test_faerbung_zufall_latin_groessen():
    f = S.faerbung(120, 4.5, 1700)
    assert f.n == 360 and f.meta["kanten"] == 270 and len(f.klauseln) == 120 + 270 * 3 == 930
    z = S.aufgabe(C.FAM_ZUFALL, 150, 1700)
    assert z.n == 150 and len(z.klauseln) == 639
    la = S.latin_luecken(12, 0.6, 1700)
    assert la.n == 1728 and la.meta["vorgegeben"] == 58 and len(la.klauseln) == 144 * 67 + 2 * 12 * 12 * 67 + 58 == 29002


def test_zufallsquadrat_ist_lateinisch_und_deterministisch():
    for seed in (1, 2, 3):
        assert S.ist_lateinisch(S.zufallsquadrat(7, seed))
    assert S.zufallsquadrat(7, 1) == S.zufallsquadrat(7, 1) and S.zufallsquadrat(7, 1) != S.zufallsquadrat(7, 2)


def test_latin_ist_erfuellbar_und_die_vorgaben_stimmen_mit_dem_quadrat():
    for ordnung, seed in ((5, 1), (6, 2), (8, 3)):
        a = S.latin_luecken(ordnung, 0.6, seed)
        assert solve(a.n, list(a.klauseln)).antwort is True
        q = S.zufallsquadrat(ordnung, seed)
        for lit in [c[0] for c in a.klauseln if len(c) == 1]:     # Variable (r, c, s) = (r·ordnung + c)·ordnung + s + 1
            r, rest = divmod(lit - 1, ordnung * ordnung)
            c, s = divmod(rest, ordnung)
            assert q[r][c] == s


def test_aufgaben_sind_deterministisch_und_seed_abhaengig():
    for fam, n in ((C.FAM_VC_SINZ, 20), (C.FAM_FAERBUNG, 30), (C.FAM_ZUFALL, 40), (C.FAM_LATIN, 6)):
        assert S.aufgabe(fam, n, 5).klauseln == S.aufgabe(fam, n, 5).klauseln
        assert S.aufgabe(fam, n, 5).klauseln != S.aufgabe(fam, n, 6).klauseln


def test_texte_der_literale():
    assert S.lit_text(3) == "x3" and S.lit_text(-3) == "¬x3"
    assert S.klausel_text((1, -2)) == "(x1 ∨ ¬x2)" and S.klausel_text(()) == "(leere Klausel)" and S.formel_text([]) == "(leere Formel: erfüllt)"


def test_vorverarbeitung_erhaelt_die_antwort_auf_allen_familien():
    for fam, n in ((C.FAM_VC_SINZ, 20), (C.FAM_VC_TOTALIZER, 20), (C.FAM_FAERBUNG, 30), (C.FAM_ZUFALL, 40), (C.FAM_LATIN, 6)):
        a = S.aufgabe(fam, n, 3)
        v = A.vorverarbeite(a.n, a.klauseln)
        vor = solve(a.n, list(a.klauseln)).antwort
        nach = False if v.unerfuellbar else (True if v.n_dicht == 0 else solve(v.n_dicht, v.klauseln_dicht).antwort)
        assert vor == nach, fam
