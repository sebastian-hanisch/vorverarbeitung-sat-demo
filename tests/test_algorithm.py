"""Einheiten der Vorverarbeitung an den Handbeispielen (sat-cp-planung/handbeispiele/hb_07.py, Sollwerte von Hand und per Aufzählung geprüft) und Vergleich mit der Kern-Fassung."""

import itertools

import vvs_algorithm as A
import vvs_constants as C
import vvs_scenario as S
import vvs_texte as T
import vvs_vorverarbeitung as KV


def modelle(klauseln, n):
    out = []
    for bits in itertools.product([False, True], repeat=n):
        m = {i + 1: b for i, b in enumerate(bits)}
        if all(any((m[abs(l)] if l > 0 else not m[abs(l)]) for l in c) for c in klauseln):
            out.append(m)
    return out


# --- Teil 1: Einheiten, Subsumption, Verstärkung ----------------------------------------------------------------------------------------------

def test_einheiten_handbeispiel_schritt1(teil1):
    r = A.einheiten(teil1)
    assert r.belegung == {1: True}
    assert r.klauseln == [(2, 4), (2, 3, 4), (-2, 4)]          # (x1), (x1 x3) fallen, ¬x1 fällt aus (¬x1 x2 x4)
    assert not r.widerspruch
    e = r.ereignisse[0]
    assert e["literal"] == 1 and e["erfuellt"] == [(1,), (1, 3)] and e["gekuerzt"] == [((-1, 2, 4), (2, 4))]


def test_subsumiere_handbeispiel_schritt2():
    neu, paare = A.subsumiere([(2, 4), (2, 3, 4), (-2, 4)])
    assert neu == [(2, 4), (-2, 4)] and paare == [((2, 4), (2, 3, 4))]


def test_verstaerke_handbeispiel_schritt3():
    neu, schritte = A.verstaerke([(2, 4), (-2, 4)])
    assert neu == [(2, 4), (4,)]
    assert len(schritte) == 1 and schritte[0]["klausel"] == (2, 4) and schritte[0]["opfer"] == (-2, 4) and schritte[0]["neu"] == (4,) and schritte[0]["literal"] == -2


def test_vorverarbeite_teil1_phase_fuer_phase(teil1):
    v = A.vorverarbeite(4, teil1)
    formeln = [(p["runde"], p["schritt"], p["formel"]) for p in v.phasen]
    assert formeln == [
        (0, "start", [(1,), (1, 3), (-1, 2, 4), (2, 3, 4), (-2, 4)]),
        (0, "einheit", [(2, 4), (2, 3, 4), (-2, 4)]),
        (1, "subsumption", [(2, 4), (-2, 4)]),
        (1, "verstaerkung", [(2, 4), (4,)]),
        (1, "einheit", []),
        (1, "elimination", []),
    ]
    assert v.einheiten == {1: True, 4: True} and v.klauseln == [] and not v.unerfuellbar and v.zaehler["runden"] == 1
    assert len(modelle(teil1, 4)) == 4 and all(m[1] and m[4] for m in modelle(teil1, 4))      # Aufzählung: 4 Modelle, alle mit x1 = x4 = wahr


# --- Teil 2: Elimination am Sinz-Zähler -----------------------------------------------------------------------------------------------------------

def test_sinz_handbeispiel_ist_der_erzeugte_zaehler(sinz3):
    a = S.sinz_zaehler(3, 1)
    assert list(a.klauseln) == sinz3 and a.n == 5 and a.meta["zaehlerklauseln"] == 5 == 2 * 3 * 1 + 3 - 3 * 1 - 1


def test_eliminiere_x4_und_x5(sinz3):
    e4 = A.eliminiere(sinz3, 4)
    assert e4.erlaubt and e4.positiv == [(-1, 4)] and e4.negativ == [(-4, 5), (-2, -4)]
    assert sorted(e4.resolventen) == [(-2, -1), (-1, 5)] or sorted(e4.resolventen) == sorted([(-1, 5), (-1, -2)])
    assert len(e4.resolventen) == 2 and len(e4.positiv) + len(e4.negativ) == 3          # 2 neue gegen 3 alte
    assert e4.stapel == (4, [(-1, 4)])
    e5 = A.eliminiere(e4.klauseln, 5)
    assert e5.erlaubt and len(e5.resolventen) == 2 and len(e5.positiv) + len(e5.negativ) == 3
    assert sorted(e5.positiv) == [(-2, 5), (-1, 5)] and e5.negativ == [(-3, -5)]
    assert sorted(e5.klauseln) == sorted([(-1, -2), (-1, -3), (-2, -3), (1, 2, 3)])


def test_waehle_variable(sinz3):
    assert A.waehle_variable(sinz3, {1, 2, 3}) == 4          # x4: 1 × 2 = 2, x5: 2 × 1 = 2, Gleichstand nach Nummer
    assert A.waehle_variable(sinz3) == 1                      # x1: 1 × 1 = 1 (und x3 ebenfalls 1), kleinere Nummer
    assert A.waehle_variable(sinz3, {1, 2, 3, 4, 5}) is None
    assert A.waehle_variable([(1, 2), (1, -2)], ()) == 1      # x1 kommt nur positiv vor: Produkt 0


def test_vorverarbeite_teil2_eingefroren_und_nicht(sinz3):
    v = A.vorverarbeite(5, sinz3, eingefroren={1, 2, 3})
    assert sorted(v.klauseln) == sorted([(-1, -2), (-1, -3), (-2, -3), (1, 2, 3)])
    assert [x for x, _ in v.stapel] == [4, 5] and v.variablen_alt == 5 and v.variablen_neu == 3 and len(v.klauseln_alt) == 6
    # ohne Einfrieren: alle fünf Variablen fallen, Stapel für x1, x3, x2, x4 (Probelauf des Plans mit dem Kern), leere Formel
    frei = A.vorverarbeite(5, sinz3)
    assert frei.klauseln == [] and frei.variablen_neu == 0 and [x for x, _ in frei.stapel] == [1, 3, 2, 4]


def test_rekonstruktion_teil2_drei_modelle(sinz3):
    v = A.vorverarbeite(5, sinz3, eingefroren={1, 2, 3})
    erwartet = {(0, 0, 1): (0, 0), (0, 1, 0): (1, 0), (1, 0, 0): (1, 1)}      # (x1, x2, x3) -> (x5, x4) von Hand
    for (x1, x2, x3), (x5, x4) in erwartet.items():
        voll = A.modell_rekonstruieren(v, {1: bool(x1), 2: bool(x2), 3: bool(x3)})
        assert (int(voll[5]), int(voll[4])) == (x5, x4)
    assert len(modelle(sinz3, 5)) == 3                        # die Originalformel hat genau 3 Modelle
    assert len(modelle(v.klauseln, 3)) == 3


# --- Teil 3: Vivification --------------------------------------------------------------------------------------------------------------------------

def test_vivification_teil3():
    c, d, e = S.HAND_TEIL3
    r = A.vivifiziere(S.HAND_TEIL3, c)
    assert r.neue_klausel == (1, 2) and r.art == "konflikt"
    assert r.schritte[1]["geschlossen"] == [(4, d)] and r.schritte[1]["konflikt"] == e     # D erzwingt x4, E ist verletzt
    ersetzt = [(1, 2), d, e]
    assert len(modelle(S.HAND_TEIL3, 4)) == len(modelle(ersetzt, 4)) == 12 and modelle(ersetzt, 4) == modelle(S.HAND_TEIL3, 4)
    # D = (x1 x2 x4): ¬x1, ¬x2 lassen E = (x1 x2 ¬x4) ¬x4 erzwingen, also entfällt x4 aus D (ein Literal folgt als falsch)
    r_d = A.vivifiziere(S.HAND_TEIL3, d)
    assert r_d.neue_klausel == (1, 2) and r_d.art == "gekuerzt" and r_d.schritte[2]["ereignis"] == "folgt_falsch"
    assert A.vivifiziere([(1, 2), (2, 3)], (1, 2)).art == "unveraendert"


# --- Zähler, Protokoll, Kern-Fassung ----------------------------------------------------------------------------------------------------------------

def test_kostenzaehler_am_handbeispiel(sinz3):
    v = A.vorverarbeite(5, sinz3, eingefroren={1, 2, 3})
    assert v.zaehler["resolventen"] == 4 and v.zaehler["eliminiert"] == 2 and v.zaehler["abgelehnt"] == 0   # x4: 1 × 2 Paare, x5: 2 × 1 Paare
    ohne = A.vorverarbeite(5, sinz3, eingefroren={1, 2, 3}, protokoll=False)
    assert ohne.klauseln == v.klauseln and ohne.zaehler == v.zaehler and all(not p["ereignisse"] for p in ohne.phasen)


def test_elimination_abgelehnt_wegen_anzahl_und_laenge():
    kl = [(1, 2), (1, 3), (1, 4), (-1, 5), (-1, 6), (-1, 7)]      # x1 positiv in 3, negativ in 3 Klauseln: 9 Resolventen > 6 entfernte
    e = A.eliminiere(kl, 1)
    assert not e.erlaubt and e.grund == "anzahl" and e.klauseln == A.normalisiere(kl) and e.stapel is None
    lang = A.eliminiere([(1, 2, 3), (-1, 4, 5)], 1, max_resolvente=3)
    assert not lang.erlaubt and lang.grund == "laenge"
    assert A.eliminiere([(1, 2, 3), (-1, 4, 5)], 1, max_resolvente=4).erlaubt


def test_eigene_fassung_und_kern_fassung_stimmen_auf_mehreren_familien_ueberein():
    """Ohne Einfrieren, gleiche Regeln: gleiche Größen auf Totalizer, Zufalls-3-SAT und Latin; bei Sinz-Zähler und Färbung wählt die dynamische Variablenwahl anders (unter 5 % Abstand)."""
    for fam, n, exakt in ((C.FAM_VC_TOTALIZER, 40, True), (C.FAM_ZUFALL, 100, True), (C.FAM_LATIN, 10, True), (C.FAM_VC_SINZ, 30, False), (C.FAM_FAERBUNG, 60, False)):
        a = S.aufgabe(fam, n, 1700)
        k = KV.vorverarbeite(a.n, a.klauseln)
        v = A.vorverarbeite(a.n, a.klauseln, protokoll=False)
        if exakt:
            assert (v.variablen_neu, len(v.klauseln)) == (k.n_neu, k.n_klauseln_neu), fam
        else:
            assert abs(v.variablen_neu - k.n_neu) <= 0.05 * k.n_neu + 1 and abs(len(v.klauseln) - k.n_klauseln_neu) <= 0.05 * k.n_klauseln_neu + 1, fam


def test_ereignis_texte_handbeispiel(teil1):
    v = A.vorverarbeite(4, teil1)
    t = {p["schritt"] + str(p["runde"]): [T.ereignis_text(e) for e in p["ereignisse"]] for p in v.phasen}
    assert t["einheit0"][0].startswith("**x1** ist eine Einheit: x1 wird wahr gesetzt. Erfüllt und gestrichen: (x1), (x1 ∨ x3).")
    assert "(¬x1 ∨ x2 ∨ x4) → (x2 ∨ x4)" in t["einheit0"][0]
    assert t["subsumption1"] == ["(x2 ∨ x4) subsumiert (x2 ∨ x3 ∨ x4): jede Belegung, die die kürzere Klausel erfüllt, erfüllt auch die längere; die längere fällt weg."]
    assert t["verstaerkung1"][0].startswith("Die Resolvente von (x2 ∨ x4) und (¬x2 ∨ x4) auf x2 ist (x4); sie subsumiert (¬x2 ∨ x4)")
    sinz = A.vorverarbeite(5, S.sinz_zaehler(3, 1).klauseln, eingefroren={1, 2, 3})
    texte = [T.ereignis_text(e) for p in sinz.phasen for e in p["ereignisse"] if e["art"] == "elimination"]
    assert texte[0].startswith("**x4 wird eliminiert.** x4: positiv in 1 Klauseln, negativ in 2; 2 Resolventen gegen 3 entfernte Klauseln, also erlaubt")
