"""Jede Zahl der README (Abschnitte „Befunde“ und „Befunde und Korrekturen gegenüber dem Plan“) wird hier nachgerechnet.

Quelle der Messreihe ist `vvs_messreihen.json` (Skript `tools/messreihe.py`, Zufalls-Seeds 1700 bis 1709, fünf Löser-Seeds). Dieser Test rechnet (1) alle Zahlen der README aus der Datei nach
und (2) Ausschnitte der Messreihe neu (Vorverarbeitung aller sieben Zeilen für zwei Formeln, Löserläufe für eine Formel je Zeile und die ganze Sinz-Tabelle) und vergleicht sie mit der Datei.
Zahlen aus der Vormessung V15 (Plan) sind in der README als solche gekennzeichnet; sie stehen in `sat-cp-planung/vormessung/out_v15.txt`, nicht in diesem Repo, und werden hier nicht geprüft.
Zeiten kommen nirgends vor."""

from pathlib import Path

import pytest

import vvs_algorithm as A
import vvs_constants as C
import vvs_evaluation as ev
import vvs_kodierung as K
import vvs_scenario as S

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def reihe():
    daten = ev.lade_messreihen()
    return daten, {z["id"]: ev.kennzahlen(z) for z in daten["zeilen"]}, {z["id"]: z for z in daten["zeilen"]}


def m(x):
    return ev.de(x, 1 if x % 1 else 0)


def test_aufbau_der_messreihe(reihe):
    daten, k, roh = reihe
    assert list(k) == ["vc_totalizer_frei", "vc_totalizer_eingefroren", "vc_sinz_frei", "vc_sinz_eingefroren", "faerbung", "zufall", "latin"]
    assert daten["budget"] == C.BUDGET == 200000 and daten["mess_seeds"] == list(C.MESS_SEEDS) and daten["loeser_seeds"] == list(C.LOESER_SEEDS)
    assert all(len(z["formeln"]) == 10 and all(len(f["konflikte_vor"]) == 5 for f in z["formeln"]) for z in daten["zeilen"])
    assert [f["seed"] for f in roh["faerbung"]["formeln"]] == list(range(1700, 1710))
    assert all(x["abgebrochen"] == 0 for x in k.values())                               # das Budget wurde in keinem Lauf erreicht


def test_readme_tabelle_gleicht_den_kennzahlen(reihe):
    _, k, _ = reihe
    for z in k.values():
        sv, sn = z["konflikte_spanne"]["vor"], z["konflikte_spanne"]["nach"]
        zeile = (f"| {z['name']} | {z['formeln']} ({z['erfuellbar']} / {z['unerfuellbar']}) | {m(z['variablen'][0])} → {m(z['variablen'][1])} | {m(z['klauseln'][0])} → {m(z['klauseln'][1])} | "
                 f"{m(z['propagationen'][0])} → {m(z['propagationen'][1])} ({ev.de_prozent(z['propagationen_prozent'], 1)}) | {m(z['konflikte'][0])} → {m(z['konflikte'][1])} "
                 f"({ev.de_prozent(z['konflikte_prozent'], 1)}) | {m(sv[0])} bis {m(sv[1])} | {m(sn[0])} bis {m(sn[1])} | {m(z['resolventen'])} |")
        assert zeile in README, z["name"]


def test_formel_wird_kleiner_in_allen_zeilen(reihe):
    _, k, _ = reihe
    assert all(z["variablen"][1] < z["variablen"][0] and z["klauseln"][1] < z["klauseln"][0] for z in k.values())
    v = [z["variablen_prozent"] for z in k.values()]
    c = [z["klauseln_prozent"] for z in k.values()]
    assert (round(max(v), 1), round(min(v), 1)) == (-1.9, -76.5) and (round(max(c), 1), round(min(c), 1)) == (-0.7, -90.3)
    assert k["zufall"]["variablen_prozent"] == max(v) and k["latin"]["variablen_prozent"] == min(v) and k["zufall"]["klauseln_prozent"] == max(c) and k["latin"]["klauseln_prozent"] == min(c)
    for text in ("−1,9 %", "−76,5 %", "−0,7 %", "−90,3 %"):
        assert text in README


def test_propagationen_sinken_in_allen_zeilen(reihe):
    _, k, _ = reihe
    assert all(z["propagationen"][1] < z["propagationen"][0] for z in k.values())
    p = {i: round(z["propagationen_prozent"], 1) for i, z in k.items()}
    assert p == {"vc_totalizer_frei": -25.3, "vc_totalizer_eingefroren": -14.1, "vc_sinz_frei": -56.6, "vc_sinz_eingefroren": -56.0, "faerbung": -59.9, "zufall": -5.7, "latin": -60.4}
    for text in ("−5,7 %", "−60,4 %", "−25,3 %", "−14,1 %", "−56,6 %", "−56,0 %"):
        assert text in README


def test_propagationen_nach_der_spannenregel_in_fuenf_von_sieben_zeilen_erkennbar(reihe):
    """Dieselbe Spannenregel wie bei den Konflikten: nicht erkennbar nur bei Zufalls-3-SAT und Vertex Cover mit Totalizer, Eingänge eingefroren."""
    _, k, _ = reihe
    ueberlappen = {i for i, z in k.items() if ev.spannen_ueberlappen(z["propagationen_spanne"]["vor"], z["propagationen_spanne"]["nach"])}
    assert ueberlappen == {"zufall", "vc_totalizer_eingefroren"}
    assert k["zufall"]["propagationen_spanne"] == {"vor": [82407, 92440.5], "nach": [79701.5, 89076]}
    assert k["vc_totalizer_eingefroren"]["propagationen_spanne"] == {"vor": [91655, 104980], "nach": [72618, 93578.5]}
    assert k["vc_totalizer_frei"]["propagationen_spanne"]["nach"] == [63976.5, 77818]
    assert k["zufall"]["propagationen_weniger_mehr_gleich"][0] == 6                         # nur 6 von 10 Formeln mit weniger Propagationen
    text = ev.verdict_reihe(list(k.values()))[1]
    assert "(nach der Spannenregel erkennbar in 5 von 7)" in text


def test_konflikte_kein_erkennbarer_unterschied_in_keiner_zeile(reihe):
    _, k, _ = reihe
    assert all(ev.spannen_ueberlappen(z["konflikte_spanne"]["vor"], z["konflikte_spanne"]["nach"]) for z in k.values())     # Spannenregel: in 0 von 7 Zeilen getrennt
    assert all(ev.verdict_konflikte(z)[0] == "info" for z in k.values())
    prozent = {i: round(z["konflikte_prozent"], 1) for i, z in k.items()}
    assert min(prozent.values()) == -28.9 and prozent["faerbung"] == -28.9 and max(prozent.values()) == 14.8 and prozent["vc_sinz_frei"] == 14.8
    assert sum(1 for z in k.values() if z["konflikte"][1] > z["konflikte"][0]) == 5 and sum(1 for z in k.values() if z["konflikte"][1] < z["konflikte"][0]) == 2
    assert {i for i, z in k.items() if z["konflikte"][1] < z["konflikte"][0]} == {"faerbung", "zufall"}
    assert k["faerbung"]["konflikte_spanne"] == {"vor": [54.5, 92.5], "nach": [56, 70.5]} and k["vc_sinz_frei"]["konflikte_spanne"] == {"vor": [1526, 1786.5], "nach": [1762, 2026]}
    assert k["latin"]["konflikte"] == [3.5, 4] and k["latin"]["konflikte_spanne"] == {"vor": [2.5, 5], "nach": [1, 5]}


def test_kosten_der_vorverarbeitung(reihe):
    _, k, _ = reihe
    assert min(z["resolventen"] for z in k.values()) == k["zufall"]["resolventen"] == 4205.5 and max(z["resolventen"] for z in k.values()) == k["vc_sinz_frei"]["resolventen"] == 25649
    assert (k["vc_totalizer_eingefroren"]["resolventen"], k["vc_sinz_eingefroren"]["resolventen"], k["vc_totalizer_frei"]["resolventen"]) == (7332, 9018, 18894.5)
    assert k["vc_totalizer_eingefroren"]["resolventen"] < k["vc_totalizer_frei"]["resolventen"]


def test_antworten_und_modelle(reihe):
    _, k, roh = reihe
    assert all(z["antwortfehler"] == 0 and z["modellfehler"] == 0 for z in k.values())
    assert sum(z["formeln"] * z["loeser_seeds"] for z in k.values()) == 350                      # 350 Vergleiche vorher/nachher = 700 Läufe
    geprueft = {i: sum(1 for f in z["formeln"] for a in f["antwort_nach"] if a is True) for i, z in roh.items()}
    assert sum(geprueft.values()) == 80 and (geprueft["faerbung"], geprueft["zufall"], geprueft["latin"]) == (25, 5, 50)
    assert all(geprueft[i] == 0 for i in ("vc_totalizer_frei", "vc_totalizer_eingefroren", "vc_sinz_frei", "vc_sinz_eingefroren"))
    assert all(k[i]["unerfuellbar"] == 10 for i in ("vc_totalizer_frei", "vc_totalizer_eingefroren", "vc_sinz_frei", "vc_sinz_eingefroren"))
    assert (k["faerbung"]["erfuellbar"], k["zufall"]["erfuellbar"], k["latin"]["erfuellbar"]) == (5, 1, 10)


def test_was_greift_wann(reihe):
    _, _, roh = reihe

    def summe(zid, feld):
        return sum(f[feld] for f in roh[zid]["formeln"])
    for zid in ("vc_totalizer_eingefroren", "vc_sinz_eingefroren"):
        assert summe(zid, "subsumiert") == 0 and summe(zid, "verstaerkt") == 0 and summe(zid, "eliminiert") > 0
    assert (summe("vc_totalizer_eingefroren", "einheiten"), summe("vc_sinz_eingefroren", "einheiten")) == (30, 230)
    assert (summe("vc_totalizer_frei", "subsumiert"), summe("vc_totalizer_frei", "verstaerkt")) == (64, 804)
    assert (summe("vc_sinz_frei", "subsumiert"), summe("vc_sinz_frei", "verstaerkt")) == (49, 262)
    assert summe("latin", "einheiten") == 13227 and summe("latin", "eliminiert") == 0 and summe("latin", "subsumiert") == 0 and summe("latin", "verstaerkt") == 0
    assert all(f["runden"] == 0 for f in roh["latin"]["formeln"])


def test_einfrieren_gegen_nichts_eingefroren(reihe):
    _, k, _ = reihe
    t, tf, s, sf = k["vc_totalizer_frei"], k["vc_totalizer_eingefroren"], k["vc_sinz_frei"], k["vc_sinz_eingefroren"]
    assert (round(t["variablen_prozent"], 1), round(tf["variablen_prozent"], 1)) == (-32.0, -23.5)
    assert tf["variablen"][1] == 284 and sf["variablen"][1] == 470 and s["variablen"][1] == 425.2
    assert round(tf["klauseln_prozent"], 1) == -22.4 and round(t["klauseln_prozent"], 1) == -30.5 and round(sf["klauseln_prozent"], 1) == -39.7 and round(s["klauseln_prozent"], 1) == -44.7
    assert tf["propagationen_prozent"] > t["propagationen_prozent"] and sf["propagationen_prozent"] > s["propagationen_prozent"]
    assert sf["variablen"][0] == 1476 and 60 * 24 - 24 == 1416 and 1476 - 60 == 1416                       # Hilfsvariablen des Sinz-Zählers (n − 1)k = 59 · 24


def test_sinz_tabelle(reihe):
    daten, _, _ = reihe
    tab = {(r["n"], r["k"]): r for r in daten["sinz"]}
    assert len(tab) == 17
    gleich = sorted(key for key, r in tab.items() if r["gleich_binomial"])
    assert gleich == [(3, 1), (3, 2), (4, 1), (4, 2), (4, 3), (5, 3)]                                    # k = 1: n = 3, 4; k = 2: n = 3, 4; k = 3: n = 4, 5
    assert (tab[(3, 1)]["variablen"], tab[(3, 1)]["klauseln"]) == ([5, 3], [6, 4])
    assert (tab[(8, 1)]["variablen"], tab[(8, 1)]["klauseln"], tab[(8, 1)]["binomial_klauseln"]) == ([15, 10], [21, 19], 29)
    for (n, k), r in tab.items():
        assert r["variablen"][0] == n + (n - 1) * k and r["klauseln"][0] == 2 * n * k + n - 3 * k - 1 + 1
        assert r["binomial_klauseln"] == K.klauselzahl_binomial(n, k) + 1


# --- Neumessung von Ausschnitten --------------------------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def messreihe_modul():
    import importlib.util
    spec = importlib.util.spec_from_file_location("vvs_messreihe_tool", ROOT / "tools" / "messreihe.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def test_vorverarbeitung_aller_zeilen_stimmt_mit_der_datei_ueberein(reihe, messreihe_modul):
    _, _, roh = reihe
    for zid, (familie, eingefroren) in messreihe_modul.ZEILEN.items():
        for seed in (1700, 1701):
            a = S.aufgabe(familie, C.MESS_GROESSEN[familie], seed)
            v = A.vorverarbeite(a.n, a.klauseln, eingefroren=a.eingaenge if eingefroren else (), protokoll=False)
            f = next(x for x in roh[zid]["formeln"] if x["seed"] == seed)
            assert (f["variablen"], f["klauseln"], f["resolventen"], f["vergleiche"], f["runden"], f["eliminiert"], f["einheiten"], f["subsumiert"], f["verstaerkt"], f["abgelehnt"]) == (
                [v.variablen_alt, v.variablen_neu], [len(v.klauseln_alt), len(v.klauseln)], v.zaehler["resolventen"], v.zaehler["vergleiche"], v.zaehler["runden"],
                v.zaehler["eliminiert"], v.zaehler["einheiten"], v.zaehler["subsumiert"], v.zaehler["verstaerkt"], v.zaehler["abgelehnt"]), (zid, seed)


def test_loeserlaeufe_einer_formel_je_zeile_stimmen_mit_der_datei_ueberein(reihe):
    _, _, roh = reihe
    for zid, familie, eingefroren in (("vc_totalizer_frei", C.FAM_VC_TOTALIZER, False), ("vc_sinz_frei", C.FAM_VC_SINZ, False), ("faerbung", C.FAM_FAERBUNG, False),
                                      ("zufall", C.FAM_ZUFALL, False), ("latin", C.FAM_LATIN, False)):
        a = S.aufgabe(familie, C.MESS_GROESSEN[familie], 1700)
        neu = ev.messe_formel(a, eingefroren=eingefroren, loeser_seeds=(C.LOESER_SEEDS[0],), budget=C.BUDGET)
        alt = next(x for x in roh[zid]["formeln"] if x["seed"] == 1700)
        for feld in ("konflikte_vor", "konflikte_nach", "propagationen_vor", "propagationen_nach", "antwort_vor", "antwort_nach"):
            assert neu[feld] == alt[feld][:1], (zid, feld)
        assert neu["antwortfehler"] == 0 and neu["modellfehler"] == 0


def test_sinz_tabelle_stimmt_mit_neumessung_ueberein(reihe, messreihe_modul):
    daten, _, _ = reihe
    assert messreihe_modul.sinz_tabelle() == daten["sinz"]


def test_beschriftungen_der_zeilen(reihe):
    _, k, _ = reihe
    assert k["vc_totalizer_frei"]["name"] == "Vertex Cover n = 60, k = 24, Totalizer, nichts eingefroren"
    assert k["latin"]["name"] == "Latin 12, Lücken 0,6" and k["faerbung"]["name"] == "3-Färbung n = 120, Grad 4,5" and k["zufall"]["name"] == "Zufalls-3-SAT n = 150, m = 639"
