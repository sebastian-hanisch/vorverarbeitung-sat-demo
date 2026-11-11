"""Orakel-Tests der Vorverarbeitung gegen einen anderen Rechenweg (DEMO-PLAYBOOK §12, ORACLE-PLAYBOOK §5).

Orakel ist die **Aufzählung aller Belegungen** (n ≤ 10, eigene Auswertung der Klauseln im Test, kein Code der Demo) und OR-Tools CP-SAT (`importorskip`).
Geprüft werden: (1) Äquierfüllbarkeit und Modell-Rekonstruktion (jedes Modell der vereinfachten Formel lässt sich zu einem Modell der Ausgangsformel ergänzen,
und die Modelle der vereinfachten Formel sind genau die Projektionen der Modelle der Ausgangsformel), (2) Subsumption und Verstärkung ändern die Modellmenge nicht,
die verstärkte Klausel folgt aus der Formel, (3) die Klauselzahl des Sinz-Zählers 2nk + n − 3k − 1 und seine Hilfsvariablen (n − 1)k an den erzeugten Mengen,
(4) die Antwort des Lösers vorher und nachher, (5) Vivification ändert die Modellmenge nicht. Im Scratch-Lauf (Aufzählung, ≥ 200 Formeln) fand sich kein Unterschied;
im Repo steht die kleine Fassung."""

import itertools

import pytest

import vvs_algorithm as A
import vvs_constants as C
import vvs_kodierung as K
import vvs_scenario as S
from vvs_cdcl import solve
from vvs_rng import SplitMix64


# --- Orakel: Aufzählung ---------------------------------------------------------------------------------------------------------------------

def erfuellt(klauseln, belegung) -> bool:
    return all(any((belegung[abs(l)] if l > 0 else not belegung[abs(l)]) for l in c) for c in klauseln)


def alle_modelle(klauseln, variablen) -> list:
    """Alle Belegungen der `variablen`, die die Klauseln erfüllen (die Klauseln dürfen nur diese Variablen enthalten)."""
    variablen = sorted(variablen)
    return [dict(zip(variablen, bits)) for bits in itertools.product([False, True], repeat=len(variablen)) if erfuellt(klauseln, dict(zip(variablen, bits)))]


def zufallsformel(seed: int, n: int, m: int, laenge=(1, 4)):
    """Zufällige Klauseln (Länge 1 bis 4, Wiederholungen und Tautologien erlaubt: der Normalisierer muss sie fangen); nur SplitMix64."""
    rng = SplitMix64(seed)
    kl = []
    for _ in range(m):
        k = laenge[0] + rng.below(laenge[1] - laenge[0] + 1)
        kl.append(tuple((1 + rng.below(n)) * (1 if rng.coin() else -1) for _ in range(k)))
    return kl


def projektion(modelle, variablen):
    return {tuple(sorted((v, m[v]) for v in variablen)) for m in modelle}


FORMELN = [(seed, 4 + seed % 6, 3 + (seed * 7) % 22) for seed in range(60)]     # n = 4..9, m = 3..24


@pytest.mark.parametrize("eingefroren_anteil", [0, 2])
def test_aequierfuellbar_und_modelle_stimmen_mit_der_aufzaehlung_ueberein(eingefroren_anteil):
    sat = unsat = eliminiert = 0
    for seed, n, m in FORMELN:
        kl = zufallsformel(seed, n, m)
        frei = set(range(1, n + 1))
        original = alle_modelle(kl, frei)
        einfrieren = set(range(1, 1 + n // 2)) if eingefroren_anteil else set()
        v = A.vorverarbeite(n, kl, eingefroren=einfrieren)
        if v.unerfuellbar:
            assert not original, (seed, "unerfüllbar gemeldet, Aufzählung findet Modelle")
            unsat += 1
            continue
        rest_vars = A.variablen_von(v.klauseln)
        reduziert = alle_modelle(v.klauseln, rest_vars)
        assert bool(reduziert) == bool(original), seed                         # Äquierfüllbarkeit
        if original:
            sat += 1
        else:
            unsat += 1
        eliminiert += len(v.stapel)
        # jedes Modell der vereinfachten Formel lässt sich zu einem Modell der Ausgangsformel ergänzen
        for mod in reduziert:
            voll = A.modell_rekonstruieren(v, mod)
            assert erfuellt(kl, voll), (seed, mod)
        # und die Modelle der vereinfachten Formel sind genau die Projektionen der Ausgangsmodelle auf die verbliebenen Variablen
        assert projektion(reduziert, rest_vars) == projektion(original, rest_vars), seed
        assert not (set(v.einheiten) & rest_vars)                               # festgelegte Variablen kommen nicht mehr vor
        assert all(w == original[0][x] for x, w in v.einheiten.items()) if original else True   # Einheiten gelten in jedem Modell
        assert not (einfrieren & {x for x, _ in v.stapel})                      # eingefrorene werden nie eliminiert
    assert sat >= 15 and unsat >= 10 and eliminiert > 20                       # beide Antworten und echte Eliminationen kamen vor


def test_antwort_gegen_cpsat():
    cp = pytest.importorskip("ortools.sat.python.cp_model")
    for seed, n, m in FORMELN[:25]:
        kl = zufallsformel(seed, n, m)
        modell = cp.CpModel()
        x = {i: modell.NewBoolVar(f"x{i}") for i in range(1, n + 1)}
        for c in kl:
            modell.AddBoolOr([x[abs(l)] if l > 0 else x[abs(l)].Not() for l in c])
        erwartet = cp.CpSolver().Solve(modell) in (cp.OPTIMAL, cp.FEASIBLE)
        v = A.vorverarbeite(n, kl)
        assert (not v.unerfuellbar and solve(max(v.n_dicht, 1), v.klauseln_dicht).antwort is True) == erwartet, seed


def test_modell_rekonstruktion_gegen_cpsat_an_strukturierten_aufgaben():
    cp = pytest.importorskip("ortools.sat.python.cp_model")
    for a in [S.faerbung(30, 4.5, 1), S.latin_luecken(6, 0.6, 3), S.sinz_zaehler(6, 2), S.zufall3(40, 150, 2)]:
        modell = cp.CpModel()
        x = {i: modell.NewBoolVar(f"x{i}") for i in range(1, a.n + 1)}
        for c in a.klauseln:
            modell.AddBoolOr([x[abs(l)] if l > 0 else x[abs(l)].Not() for l in c])
        erwartet = cp.CpSolver().Solve(modell) in (cp.OPTIMAL, cp.FEASIBLE)
        v = A.vorverarbeite(a.n, a.klauseln, eingefroren=a.eingaenge)
        if v.unerfuellbar:
            assert not erwartet, a.name
        if not v.unerfuellbar and v.n_dicht:
            r = solve(v.n_dicht, v.klauseln_dicht)
            assert (r.antwort is True) == erwartet, a.name
            if r.antwort:
                assert erfuellt(a.klauseln, A.modell_rekonstruieren(v, v.modell_dicht_zu_alt(r.modell))), a.name


# --- Subsumption und Verstärkung -------------------------------------------------------------------------------------------------------------

def test_subsumption_aendert_die_modellmenge_nicht():
    gesehen = 0
    for seed in range(60):
        n = 4 + seed % 5
        kl = A.normalisiere(zufallsformel(seed, n, 14, (1, 4)))
        neu, paare = A.subsumiere(kl)
        frei = set(range(1, n + 1))
        assert alle_modelle(kl, frei) == alle_modelle(neu, frei), seed
        for a, b in paare:
            assert set(a) < set(b) and b in kl and b not in neu and a in neu     # echte Teilmenge, B gestrichen, A bleibt
        gesehen += len(paare)
    assert gesehen > 20


def test_verstaerkung_klausel_folgt_aus_der_formel_und_modelle_bleiben():
    gesehen = 0
    for seed in range(80):
        n = 4 + seed % 4
        kl = A.normalisiere(zufallsformel(seed, n, 12, (2, 4)))
        neu, schritte = A.verstaerke(kl)
        frei = set(range(1, n + 1))
        original = alle_modelle(kl, frei)
        assert alle_modelle(neu, frei) == original, seed
        for s in schritte:
            assert all(erfuellt([s["neu"]], mod) for mod in original), (seed, s)  # die verstärkte Klausel folgt aus der Formel
            assert set(s["neu"]) < set(s["opfer"]) and len(s["opfer"]) - len(s["neu"]) == 1
        gesehen += len(schritte)
    assert gesehen > 10


# --- Elimination: Resolventen gegen die Definition (∃x.F) ------------------------------------------------------------------------------------

def test_elimination_ist_die_existenzquantifizierung():
    for seed in range(60):
        n = 4 + seed % 4
        kl = A.normalisiere(zufallsformel(seed, n, 10, (2, 3)))
        for var in range(1, n + 1):
            e = A.eliminiere(kl, var, max_resolvente=20)
            if not e.erlaubt:
                assert e.klauseln == kl
                continue
            rest = set(range(1, n + 1)) - {var}
            ursprung = projektion(alle_modelle(kl, range(1, n + 1)), rest)
            assert projektion(alle_modelle(e.klauseln, rest), rest) == ursprung, (seed, var)
            assert len(e.klauseln) <= len(kl)                                        # die Klauselzahl nimmt nicht zu


# --- Sinz-Zähler: Klauselzahl und Hilfsvariablen --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("n,k", [(3, 1), (4, 2), (6, 3), (8, 1), (10, 4)])
def test_sinz_klauselzahl_und_hilfsvariablen(n, k):
    pool = K.Hilfsvariablen(n)
    kl = K.hoechstens_sinz(list(range(1, n + 1)), k, pool)
    assert len(kl) == 2 * n * k + n - 3 * k - 1
    assert pool.n - n == (n - 1) * k
    a = S.sinz_zaehler(n, k)
    assert a.n == n + (n - 1) * k and len(a.klauseln) == 2 * n * k + n - 3 * k - 1 + 1       # plus die Klausel „mindestens eines“


def test_sinz_zaehler_erlaubt_genau_die_belegungen_mit_hoechstens_k_wahren():
    """Aufzählung der Eingänge: erfüllbar genau dann, wenn höchstens k wahr sind und mindestens eines."""
    n, k = 5, 2
    a = S.sinz_zaehler(n, k)
    for bits in itertools.product([False, True], repeat=n):
        einheit = [((i + 1) if b else -(i + 1),) for i, b in enumerate(bits)]
        assert (solve(a.n, list(a.klauseln) + einheit).antwort is True) == (1 <= sum(bits) <= k), bits


# --- Eigenschaften -----------------------------------------------------------------------------------------------------------------------------

def test_reihenfolge_der_klauseln_und_nummerierung_aendert_die_antwort_nicht():
    for seed, n, m in FORMELN[:30]:
        kl = zufallsformel(seed, n, m)
        sat = bool(alle_modelle(kl, range(1, n + 1)))
        rng = SplitMix64(seed + 99)
        perm = list(range(1, n + 1))
        rng.shuffle(perm)
        abb = {i + 1: perm[i] for i in range(n)}
        kl2 = [tuple((abb[abs(l)] if l > 0 else -abb[abs(l)]) for l in c) for c in kl]
        rng.shuffle(kl2)
        for formel in (kl, kl2):
            v = A.vorverarbeite(n, formel)
            antwort = (not v.unerfuellbar) and bool(alle_modelle(v.klauseln, A.variablen_von(v.klauseln)))
            assert antwort == sat, seed


def test_vorverarbeitung_ist_nach_dem_fixpunkt_idempotent():
    for seed, n, m in FORMELN[:30]:
        kl = zufallsformel(seed, n, m)
        v = A.vorverarbeite(n, kl, runden=12)
        if v.unerfuellbar:
            continue
        w = A.vorverarbeite(n, v.klauseln, runden=12)
        assert w.klauseln == v.klauseln and not w.einheiten and not w.stapel, seed


def test_leere_klausel_ist_unerfuellbar_und_leere_formel_erfuellbar():
    assert A.vorverarbeite(3, [(1, 2), ()]).unerfuellbar
    assert A.vorverarbeite(2, [(1,), (-1,)]).unerfuellbar
    assert A.einheiten([(1,), (-1,)]).widerspruch
    leer = A.vorverarbeite(3, [])
    assert not leer.unerfuellbar and leer.klauseln == [] and leer.einheiten == {}
    assert erfuellt([], A.modell_rekonstruieren(leer, {}))


def test_zweig_jeder_schritt_greift_auf_einer_instanz_der_messreihe():
    """Jede Variante des Verfahrens (Einheit, Subsumption, Verstärkung, Elimination) wird auf mindestens einer Instanz der Messreihen-Familien (Größen der Messreihe,
    nichts eingefroren) ausgeführt, sonst wäre sie eine tote Variante. Bei eingefrorenen Eingängen greifen Subsumption und Verstärkung dort nie (Messreihe, README)."""
    summe = {"einheiten": 0, "subsumiert": 0, "verstaerkt": 0, "eliminiert": 0}
    for seed in (1700, 1701):
        for fam in (C.FAM_VC_TOTALIZER, C.FAM_FAERBUNG):
            a = S.aufgabe(fam, C.MESS_GROESSEN[fam], seed)
            z = A.vorverarbeite(a.n, a.klauseln, protokoll=False).zaehler
            for k in summe:
                summe[k] += z[k]
    a = S.aufgabe(C.FAM_VC_SINZ, 60, 1700)
    summe["einheiten"] += A.vorverarbeite(a.n, a.klauseln, protokoll=False).zaehler["einheiten"]
    assert all(x > 0 for x in summe.values()), summe


# --- Vivification ------------------------------------------------------------------------------------------------------------------------------

def test_vivification_aendert_die_modellmenge_nicht_und_folgt_aus_der_formel():
    gesehen = 0
    for seed in range(80):
        n = 4 + seed % 3
        kl = A.normalisiere(zufallsformel(seed, n, 12, (2, 4)))
        for c in kl[:4]:
            viv = A.vivifiziere(kl, c)
            neu = [viv.neue_klausel if d == c else d for d in kl]
            assert set(viv.neue_klausel) <= set(c)
            frei = set(range(1, n + 1))
            if viv.neue_klausel:
                assert alle_modelle(neu, frei) == alle_modelle(kl, frei), (seed, c, viv)
            else:
                assert not alle_modelle(kl, frei)       # die leere Klausel folgt nur aus unerfüllbaren Formeln
            gesehen += viv.neue_klausel != c
    assert gesehen > 10
