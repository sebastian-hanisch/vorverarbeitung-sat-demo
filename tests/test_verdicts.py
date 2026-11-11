"""Verdikte (reine Funktionen in vvs_evaluation): Schwellen und jede Zahl im Text an handgesetzten Zeilen, dazu die Kennzahlen aus Rohwerten."""

import vvs_algorithm as A
import vvs_evaluation as ev


def formel(variablen, klauseln, kv, kn, pv=None, pn=None, res=100, seed=1, antwort=True):
    """Eine Formel der Messreihe mit Konflikten je Löser-Seed (Listen kv, kn)."""
    pv = pv or [10 * x for x in kv]
    pn = pn or [10 * x for x in kn]
    return {"seed": seed, "variablen": variablen, "klauseln": klauseln, "resolventen": res, "vergleiche": 5, "runden": 1, "eliminiert": 1, "einheiten": 0, "subsumiert": 0, "verstaerkt": 0,
            "abgelehnt": 0, "antwort_vor": [antwort] * len(kv), "antwort_nach": [antwort] * len(kv), "konflikte_vor": kv, "konflikte_nach": kn,
            "propagationen_vor": pv, "propagationen_nach": pn, "antwortfehler": 0, "modellfehler": 0}


def zeile(formeln, zid="x", name="Zeile X"):
    return {"id": zid, "kurz": zid, "beschriftung": name, "formeln": formeln}


# Drei Formeln, drei Löser-Seeds. Mediane von Hand: Konflikte vorher je Formel 105, 200, 155 (Median 155); je Löser-Seed 150, 160, 155 (Spanne 150 bis 160).
STEIGT = zeile([formel([100, 40], [300, 200], [100, 110, 105], [300, 310, 320], res=50), formel([100, 50], [300, 220], [200, 210, 190], [400, 420, 410], res=70, seed=2),
                formel([100, 60], [300, 240], [150, 160, 155], [350, 360, 340], res=90, seed=3)], "sinz", "Sinz")


def test_kennzahlen_von_hand():
    k = ev.kennzahlen(STEIGT)
    assert k["variablen"] == [100, 50] and k["klauseln"] == [300, 220] and k["variablen_prozent"] == -50.0 and round(k["klauseln_prozent"], 6) == round(100 * (660 - 900) / 900, 6)
    assert k["konflikte"] == [155, 350] and k["konflikte_spanne"] == {"vor": [150, 160], "nach": [340, 360]}
    assert k["propagationen"] == [1550, 3500] and k["resolventen"] == 70 and k["formeln"] == 3 and k["loeser_seeds"] == 3
    assert k["konflikte_weniger_mehr_gleich"] == [0, 3, 0] and k["erfuellbar"] == 3 and k["unerfuellbar"] == 0


def test_verdict_konflikte_steigen_bei_einer_sinz_zeile():
    art, text = ev.verdict_konflikte(ev.kennzahlen(STEIGT))
    assert art == "warning"
    assert "155 → 350" in text and "+126 %" in text and "150 bis 160" in text and "340 bis 360" in text and "3 Löser-Seeds" in text and "mehr Konflikte nach der Vorverarbeitung" in text


def test_verdict_konflikte_kein_unterschied_bei_ueberlappenden_spannen():
    z = zeile([formel([10, 9], [20, 18], [100, 140, 120], [110, 150, 100]), formel([10, 9], [20, 18], [200, 260, 230], [190, 280, 210]), formel([10, 9], [20, 18], [150, 170, 160], [140, 190, 150])])
    k = ev.kennzahlen(z)
    assert k["konflikte_spanne"]["vor"] == [150, 170] and k["konflikte_spanne"]["nach"] == [140, 190]       # je Löser-Seed Median über die Formeln
    art, text = ev.verdict_konflikte(k)
    assert art == "info" and "kein Unterschied in den Konflikten erkennbar" in text and "150 bis 170" in text and "140 bis 190" in text


def test_verdict_konflikte_weniger_bei_getrennten_spannen():
    z = zeile([formel([10, 5], [20, 12], [1000, 1010, 990], [600, 620, 610]), formel([10, 5], [20, 12], [2000, 2020, 1980], [1200, 1230, 1190]), formel([10, 5], [20, 12], [1500, 1510, 1490], [900, 910, 890])])
    art, text = ev.verdict_konflikte(ev.kennzahlen(z))
    assert art == "success" and "1.500 → 900" in text and "−40 %" in text and "weniger Konflikte" in text


def test_verdict_konflikte_ohne_konflikte_vorher_und_nachher():
    art, text = ev.verdict_konflikte(ev.kennzahlen(zeile([formel([10, 5], [20, 12], [0, 0], [0, 0]), formel([10, 5], [20, 12], [0, 0], [0, 0])], "latin", "Latin")))
    assert art == "info" and "keinen Konflikt" in text


def test_verdict_zeile_nennt_alle_zahlen():
    k = ev.kennzahlen(STEIGT)
    art, text = ev.verdict_zeile(k)
    assert art == "info" and "entfernt 50,0 % der Variablen und 26,7 % der Klauseln" in text and "Propagationen im Median um" not in text and "steigen im Median um 125,8 %" in text and "70 Resolventen" in text
    weniger = ev.kennzahlen(zeile([formel([100, 50], [300, 150], [100, 100], [100, 100], pv=[1000, 1000], pn=[400, 400])]))
    assert "senkt die Propagationen im Median um 60,0 %" in ev.verdict_zeile(weniger)[1]


def test_verdict_reihe_zaehlt_zeilen():
    weniger = ev.kennzahlen(zeile([formel([10, 5], [20, 12], [1000, 1010, 990], [600, 620, 610])], "t", "Totalizer"))
    gleich = ev.kennzahlen(zeile([formel([10, 5], [20, 12], [100, 140, 120], [110, 150, 100])], "z", "Zufall"))
    trivial = ev.kennzahlen(zeile([formel([10, 5], [20, 12], [0, 0, 0], [0, 0, 0])], "l", "Latin"))
    mehr = ev.kennzahlen(STEIGT)
    art, text = ev.verdict_reihe([weniger, gleich, trivial, mehr])
    assert art == "info"
    assert "In 2 von 4 Zeilen sinken die Propagationen im Median" in text       # Totalizer- und Zufallszeile; Latin bleibt bei 0, die Sinz-Zeile steigt
    assert "in 1 von 3 Zeilen weniger, in 1 mehr und in 1 keinen erkennbaren Unterschied" in text and "weniger: Totalizer" in text and "mehr: Sinz" in text
    art_alle, _ = ev.verdict_reihe([weniger])
    assert art_alle == "success"


def test_verdict_formel_gleiche_antwort_und_fehler(teil1):
    v = A.vorverarbeite(4, teil1)
    vor = {"antwort": True, "konflikte": 3, "propagationen": 20}
    nach = {"antwort": True, "konflikte": 0, "propagationen": 0}
    art, text = ev.verdict_formel(vor, nach, v, True, True)
    assert art == "success" and "erfüllbar" in text and "Variablen 4 → 0, Klauseln 5 → 0" in text and "Konflikte in einem Lauf 3 → 0" in text and "alle Originalklauseln" in text
    assert ev.verdict_formel(vor, {**nach, "antwort": False}, v, None, False)[0] == "error"
    assert ev.verdict_formel(vor, nach, v, False, True)[0] == "error"
    assert ev.verdict_formel({**vor, "antwort": None}, nach, v, None, True)[0] == "warning"


def test_verdict_live_zaehlung():
    f = [formel([10, 5], [20, 12], [100], [80], seed=1), formel([10, 5], [20, 12], [100], [120], seed=2), formel([10, 5], [20, 12], [50], [50], seed=3), formel([10, 5], [20, 12], [70], [60], seed=4)]
    art, text = ev.verdict_live(f)
    assert art == "info" and "In 2 von 4 Formeln sinken die Konflikte, in 1 steigen sie, in 1 bleiben sie gleich" in text and "Modellfehler: 0." in text
    f[0]["modellfehler"] = 1
    assert ev.verdict_live(f)[0] == "error"


def test_verdict_sinz_texte():
    x = ev.sinz_experiment(3, 1, True)
    art, text = ev.verdict_sinz(x)
    assert art == "success" and "5 Variablen und 6 Klauseln" in text and "3 Variablen und 4 Klauseln" in text and "binomiale Kodierung" in text and "Alle 3 Modelle" in text
    art, text = ev.verdict_sinz(ev.sinz_experiment(3, 1, False))
    assert art == "warning" and "Nichts war eingefroren" in text
    art, text = ev.verdict_sinz(ev.sinz_experiment(8, 1, True))
    assert art == "info" and "nicht** die binomiale Kodierung (29 Klauseln)" in text and "Hilfsvariablen bleiben" in text
