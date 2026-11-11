"""Messung vorher/nachher, Kennzahlen der Messreihe und die Verdikte der App (reine Funktionen: `verdict_*` liefern (Art, Text), jede Zahl im Text stammt aus den Eingaben)."""

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import median

import vvs_algorithm as A
import vvs_constants as C
import vvs_scenario as S
from vvs_cdcl import solve
from vvs_instanzen import pruefe_modell

MESSREIHEN_DATEI = Path(__file__).with_name("vvs_messreihen.json")


# --- Zahlen deutsch --------------------------------------------------------------------------------------------------------------------------

def de(x, stellen: int = 0) -> str:
    """Deutsche Schreibweise: Punkt als Tausendertrenner, Komma als Dezimalzeichen, Minus als echtes Minuszeichen."""
    text = f"{abs(x):,.{stellen}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    null = float(f"{abs(x):.{stellen}f}") == 0          # −0,0 gibt es nicht
    return ("−" + text) if x < 0 and not null else text


def prozent_aenderung(vor, nach):
    """Änderung in Prozent des Wertes vorher (negativ: sinkt); None, wenn vorher 0 ist."""
    return None if vor == 0 else 100.0 * (nach - vor) / vor


def de_prozent(p, stellen: int = 0) -> str:
    return "–" if p is None else (("+" if p > 0 else "") + de(p, stellen) + " %")


def antwort_text(antwort) -> str:
    return {True: "erfüllbar", False: "unerfüllbar", None: "Budget erreicht"}[antwort]


# --- Messung einer Formel --------------------------------------------------------------------------------------------------------------------

def loese(n: int, klauseln, *, loeser_seed, budget: int) -> dict:
    """Ein Lauf des CDCL-Lösers (`loeser_seed` None: Standard ohne Zufall in der Anfangsaktivität, sonst zufällige Anfangsaktivität aus SplitMix64)."""
    if loeser_seed is None:
        r = solve(n, list(klauseln), conflict_budget=budget)
    else:
        r = solve(n, list(klauseln), conflict_budget=budget, seed=loeser_seed, noise=True)
    return {"antwort": r.antwort, "konflikte": r.stat["konflikte"], "propagationen": r.stat["propagationen"], "modell": r.modell}


def loese_vereinfacht(v: A.Vorverarbeitet, *, loeser_seed, budget: int) -> dict:
    """Löser auf der vereinfachten Formel; unerfüllbar nach der Vorverarbeitung und leere Formel brauchen keinen Lauf."""
    if v.unerfuellbar:
        return {"antwort": False, "konflikte": 0, "propagationen": 0, "modell": None}
    if v.n_dicht == 0:
        return {"antwort": True, "konflikte": 0, "propagationen": 0, "modell": {}}
    return loese(v.n_dicht, v.klauseln_dicht, loeser_seed=loeser_seed, budget=budget)


def messe_formel(a: S.Aufgabe, *, eingefroren: bool, loeser_seeds=(None,), budget: int = C.BUDGET, runden: int = A.RUNDEN) -> dict:
    """Vorher/nachher für eine Formel: Größen, Kosten der Vorverarbeitung, je Löser-Seed Antwort, Konflikte, Propagationen; geprüft wird jedes rekonstruierte Modell
    gegen die ORIGINALKLAUSELN und die Gleichheit der Antworten."""
    v = A.vorverarbeite(a.n, a.klauseln, eingefroren=a.eingaenge if eingefroren else (), runden=runden, protokoll=False)
    m = {"seed": a.meta.get("seed"), "variablen": [v.variablen_alt, v.variablen_neu], "klauseln": [len(v.klauseln_alt), len(v.klauseln)],
         "resolventen": v.zaehler["resolventen"], "vergleiche": v.zaehler["vergleiche"], "runden": v.zaehler["runden"],
         "eliminiert": v.zaehler["eliminiert"], "abgelehnt": v.zaehler["abgelehnt"], "einheiten": v.zaehler["einheiten"],
         "subsumiert": v.zaehler["subsumiert"], "verstaerkt": v.zaehler["verstaerkt"],
         "antwort_vor": [], "antwort_nach": [], "konflikte_vor": [], "konflikte_nach": [], "propagationen_vor": [], "propagationen_nach": [],
         "antwortfehler": 0, "modellfehler": 0}
    for s in loeser_seeds:
        vor = loese(a.n, a.klauseln, loeser_seed=s, budget=budget)
        nach = loese_vereinfacht(v, loeser_seed=s, budget=budget)
        m["antwort_vor"].append(vor["antwort"])
        m["antwort_nach"].append(nach["antwort"])
        m["konflikte_vor"].append(vor["konflikte"])
        m["konflikte_nach"].append(nach["konflikte"])
        m["propagationen_vor"].append(vor["propagationen"])
        m["propagationen_nach"].append(nach["propagationen"])
        if vor["antwort"] is not None and nach["antwort"] is not None and vor["antwort"] != nach["antwort"]:
            m["antwortfehler"] += 1
        if nach["antwort"] is True:
            modell = A.modell_rekonstruieren(v, v.modell_dicht_zu_alt(nach["modell"] or {}))
            if not pruefe_modell(a.klauseln, modell):
                m["modellfehler"] += 1
    return m


# --- Eine Formel in der App (Seitenleiste) ---------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    familie: str = C.FAM_HAND
    n: int = 0
    seed: int = C.DEFAULT_SEED
    eingefroren: bool = False
    runden: int = C.DEFAULT_RUNDEN


def aufgabe_von(s: Settings) -> S.Aufgabe:
    if s.familie == C.FAM_HAND:
        return S.Aufgabe(C.FAM_HAND, 4, tuple(S.HAND_TEIL1), (), "Handbeispiel Teil 1", {})
    return S.aufgabe(s.familie, s.n, s.seed)


def vorverarbeite_aufgabe(a: S.Aufgabe, *, eingefroren: bool, runden: int, protokoll: bool = True) -> A.Vorverarbeitet:
    return A.vorverarbeite(a.n, a.klauseln, eingefroren=a.eingaenge if eingefroren else (), runden=runden, protokoll=protokoll)


def analysiere(a: S.Aufgabe, v: A.Vorverarbeitet, *, budget: int = C.LIVE_BUDGET) -> dict:
    """Antwort vorher und nachher mit dem CDCL-Löser, Modellprüfung gegen die Originalklauseln."""
    vor = loese(a.n, a.klauseln, loeser_seed=None, budget=budget)
    nach = loese_vereinfacht(v, loeser_seed=None, budget=budget)
    modell_ok = None
    if nach["antwort"] is True:
        modell = A.modell_rekonstruieren(v, v.modell_dicht_zu_alt(nach["modell"] or {}))
        modell_ok = pruefe_modell(a.klauseln, modell)
    return {"vor": {k: x for k, x in vor.items() if k != "modell"}, "nach": {k: x for k, x in nach.items() if k != "modell"},
            "modell_ok": modell_ok, "antworten_gleich": vor["antwort"] is None or nach["antwort"] is None or vor["antwort"] == nach["antwort"]}


# --- Kennzahlen einer Zeile der Messreihe ----------------------------------------------------------------------------------------------------

def kennzahlen(zeile: dict) -> dict:
    """Aus den Rohwerten einer Zeile (Formeln × Löser-Seeds): Summen der Größen, Mediane und die Spanne der Löser-Seeds.

    Wert je Formel = Median über die Löser-Seeds; Wert der Zeile = Median über die Formeln. Die Spanne eines Löser-Seeds s ist der Median über die Formeln von s;
    die Spannen sind Minimum und Maximum dieser Mediane über die Löser-Seeds (sie erfasst die Streuung der Suche bei denselben Formeln, nicht die zwischen Formeln)."""
    f = zeile["formeln"]
    n_seeds = len(f[0]["konflikte_vor"])
    v0, v1 = sum(x["variablen"][0] for x in f), sum(x["variablen"][1] for x in f)
    c0, c1 = sum(x["klauseln"][0] for x in f), sum(x["klauseln"][1] for x in f)
    k = {"name": zeile.get("beschriftung", ""), "kurz": zeile.get("kurz", zeile.get("id", "")), "id": zeile.get("id", ""), "formeln": len(f), "loeser_seeds": n_seeds, "variablen": [v0 / len(f), v1 / len(f)], "klauseln": [c0 / len(f), c1 / len(f)],
         "variablen_prozent": prozent_aenderung(v0, v1), "klauseln_prozent": prozent_aenderung(c0, c1),
         "resolventen": median(x["resolventen"] for x in f), "vergleiche": median(x["vergleiche"] for x in f),
         "antwortfehler": sum(x["antwortfehler"] for x in f), "modellfehler": sum(x["modellfehler"] for x in f)}
    for name in ("konflikte", "propagationen"):
        je_formel = {w: [median(x[f"{name}_{w}"]) for x in f] for w in ("vor", "nach")}
        je_seed = {w: [median(x[f"{name}_{w}"][s] for x in f) for s in range(n_seeds)] for w in ("vor", "nach")}
        k[name] = [median(je_formel["vor"]), median(je_formel["nach"])]
        k[name + "_spanne"] = {w: [min(je_seed[w]), max(je_seed[w])] for w in ("vor", "nach")}
        k[name + "_prozent"] = prozent_aenderung(k[name][0], k[name][1])
        k[name + "_weniger_mehr_gleich"] = [sum(1 for a, b in zip(je_formel["vor"], je_formel["nach"]) if b < a),
                                            sum(1 for a, b in zip(je_formel["vor"], je_formel["nach"]) if b > a),
                                            sum(1 for a, b in zip(je_formel["vor"], je_formel["nach"]) if b == a)]
    k["erfuellbar"] = sum(1 for x in f if all(a is True for a in x["antwort_vor"]))
    k["unerfuellbar"] = sum(1 for x in f if all(a is False for a in x["antwort_vor"]))
    k["abgebrochen"] = sum(1 for x in f for a in x["antwort_vor"] + x["antwort_nach"] if a is None)
    return k


def spannen_ueberlappen(sp_vor, sp_nach) -> bool:
    return not (sp_nach[1] < sp_vor[0] or sp_vor[1] < sp_nach[0])


def lade_messreihen() -> dict:
    return json.loads(MESSREIHEN_DATEI.read_text(encoding="utf-8"))


# --- Verdikte --------------------------------------------------------------------------------------------------------------------------------

def verdict_konflikte(k: dict) -> tuple[str, str]:
    """Konflikte einer Zeile: ‚erkennbar‘ nur, wenn sich die Spannen der Löser-Seeds vorher und nachher nicht überlappen (Entscheidung Z4)."""
    vor, nach = k["konflikte"]
    sv, sn = k["konflikte_spanne"]["vor"], k["konflikte_spanne"]["nach"]
    if vor == 0 and nach == 0 and sv[1] == 0 and sn[1] == 0:
        return "info", "Die Aufgabe braucht vorher und nachher keinen Konflikt: Einheitspropagation allein löst sie (eine Suche findet nichts mehr zu lernen)."
    beschr = (f"Konflikte im Median {de(vor, 1 if vor % 1 else 0)} → {de(nach, 1 if nach % 1 else 0)} ({de_prozent(k['konflikte_prozent'])}); "
              f"Spanne der {k['loeser_seeds']} Löser-Seeds vorher {de(sv[0])} bis {de(sv[1])}, nachher {de(sn[0])} bis {de(sn[1])}.")
    if spannen_ueberlappen(sv, sn):
        return "info", beschr + " Die Spannen überlappen: **kein Unterschied in den Konflikten erkennbar.**"
    if nach < vor:
        return "success", beschr + " Die Spannen überlappen nicht: **weniger Konflikte** (für diese Formeln und diese Löser-Seeds)."
    return "warning", beschr + " Die Spannen überlappen nicht: **mehr Konflikte nach der Vorverarbeitung** (für diese Formeln und diese Löser-Seeds)."


def verdict_zeile(k: dict) -> tuple[str, str]:
    """Der Satz der Zeile: Variablen, Klauseln, Propagationen, Kosten."""
    p = k["propagationen_prozent"]
    entfernt = lambda x: "–" if x is None else de(-x, 1)  # noqa: E731
    sp = k.get("propagationen_spanne")
    ueberlappt = p is not None and p < 0 and sp is not None and spannen_ueberlappen(sp["vor"], sp["nach"])
    return "info", (f"Die Vorverarbeitung entfernt {entfernt(k['variablen_prozent'])} % der Variablen und {entfernt(k['klauseln_prozent'])} % der Klauseln"
                    + ("" if p is None else (f" und senkt die Propagationen im Median um {de(-p, 1)} %" if p < 0 else f"; die Propagationen steigen im Median um {de(p, 1)} %"))
                    + (" (die Spannen der Löser-Seeds überlappen: nach der Spannenregel kein erkennbarer Rückgang)" if ueberlappt else "")
                    + f"; sie berechnet dafür im Median {de(k['resolventen'])} Resolventen (Paare untersucht).")


def verdict_reihe(zeilen: list[dict]) -> tuple[str, str]:
    """Verdikt der ganzen Messreihe aus den Kennzahlen aller Zeilen (Liste von `kennzahlen`-Ergebnissen mit Schlüssel 'name')."""
    nicht_trivial = [z for z in zeilen if z["konflikte"][0] > 0 or z["konflikte"][1] > 0]
    weniger = [z["name"] for z in nicht_trivial if not spannen_ueberlappen(z["konflikte_spanne"]["vor"], z["konflikte_spanne"]["nach"]) and z["konflikte"][1] < z["konflikte"][0]]
    mehr = [z["name"] for z in nicht_trivial if not spannen_ueberlappen(z["konflikte_spanne"]["vor"], z["konflikte_spanne"]["nach"]) and z["konflikte"][1] > z["konflikte"][0]]
    gleich = len(nicht_trivial) - len(weniger) - len(mehr)
    prop_weniger = sum(1 for z in zeilen if z["propagationen"][1] < z["propagationen"][0])
    prop_erkennbar = sum(1 for z in zeilen if z["propagationen"][1] < z["propagationen"][0] and not spannen_ueberlappen(z["propagationen_spanne"]["vor"], z["propagationen_spanne"]["nach"]))
    text = (f"In {prop_weniger} von {len(zeilen)} Zeilen sinken die Propagationen im Median (nach der Spannenregel erkennbar in {prop_erkennbar} von {len(zeilen)}). Bei den Konflikten (ohne die Zeilen, die ohnehin keine brauchen) zeigt die Spannenregel "
            f"in {len(weniger)} von {len(nicht_trivial)} Zeilen weniger, in {len(mehr)} mehr und in {gleich} keinen erkennbaren Unterschied")
    text += (f"; weniger: {', '.join(weniger)}" if weniger else "") + (f"; mehr: {', '.join(mehr)}" if mehr else "") + "."
    if len(weniger) == len(nicht_trivial) and nicht_trivial:
        return "success", text
    return "info", text


def verdict_formel(vor: dict, nach: dict, v: A.Vorverarbeitet, modell_ok, gleich: bool) -> tuple[str, str]:
    """Verdikt der Formel der Seitenleiste: gleiche Antwort, Modell gegen die Originalklauseln, Größen und Konflikte eines Laufs."""
    if not gleich:
        return "error", f"Die Antworten weichen ab (vorher {antwort_text(vor['antwort'])}, nachher {antwort_text(nach['antwort'])}): das darf nicht vorkommen."
    if modell_ok is False:
        return "error", "Das rekonstruierte Modell erfüllt die Originalformel nicht: das darf nicht vorkommen."
    teil = (f"Antwort vorher und nachher: **{antwort_text(vor['antwort'])}**"
            + (", das rekonstruierte Modell erfüllt alle Originalklauseln" if modell_ok else "")
            + f". Variablen {de(v.variablen_alt)} → {de(v.variablen_neu)}, Klauseln {de(len(v.klauseln_alt))} → {de(len(v.klauseln))}; "
            f"Konflikte in einem Lauf {de(vor['konflikte'])} → {de(nach['konflikte'])}, Propagationen {de(vor['propagationen'])} → {de(nach['propagationen'])}.")
    if vor["antwort"] is None or nach["antwort"] is None:
        return "warning", teil + " Mindestens ein Lauf hat das Konfliktbudget erreicht."
    return "success", teil


# --- Experiment „Elimination und Rekonstruktion“ (Sinz-Zähler) ---------------------------------------------------------------------------------

def sinz_experiment(n: int, k: int, eingefroren: bool) -> dict:
    """Sinz-Zähler vorverarbeiten; alle Modelle der vereinfachten Formel (Aufzählung über die verbliebenen Variablen) werden zurückgerechnet und gegen die Originalklauseln geprüft."""
    import itertools

    from vvs_kodierung import hoechstens_binomial
    a = S.sinz_zaehler(n, k)
    v = A.vorverarbeite(a.n, a.klauseln, eingefroren=a.eingaenge if eingefroren else (), protokoll=True)
    rest = sorted(A.variablen_von(v.klauseln))
    modelle = []
    for bits in itertools.product([False, True], repeat=len(rest)):
        m = dict(zip(rest, bits))
        if all(any((m[abs(l)] if l > 0 else not m[abs(l)]) for l in c) for c in v.klauseln):
            voll = A.modell_rekonstruieren(v, m)
            modelle.append({"reduziert": m, "voll": voll, "ok": pruefe_modell(a.klauseln, voll)})
    binom = set(A.normalisiere(hoechstens_binomial(list(range(1, n + 1)), k) + [tuple(range(1, n + 1))]))
    return {"aufgabe": a, "v": v, "modelle": modelle, "binomial_klauseln": len(binom), "gleich_binomial": set(v.klauseln) == binom,
            "formel_klauseln": 2 * n * k + n - 3 * k - 1, "hilfsvariablen": (n - 1) * k}


def verdict_sinz(x: dict) -> tuple[str, str]:
    v, a = x["v"], x["aufgabe"]
    n, k = a.meta["n_eingaenge"], a.meta["k"]
    if v.unerfuellbar:
        return "error", "Die Vorverarbeitung meldet unerfüllbar: der Zähler mit „mindestens eines“ ist erfüllbar, das darf nicht vorkommen."
    if any(not m["ok"] for m in x["modelle"]):
        return "error", "Ein zurückgerechnetes Modell erfüllt die Originalformel nicht: das darf nicht vorkommen."
    kopf = (f"Vorher {v.variablen_alt} Variablen und {len(v.klauseln_alt)} Klauseln (Zähler: {a.meta['zaehlerklauseln']} Klauseln = 2nk + n − 3k − 1 = {x['formel_klauseln']}, "
            f"Hilfsvariablen (n − 1)k = {x['hilfsvariablen']}), nachher {v.variablen_neu} Variablen und {len(v.klauseln)} Klauseln. "
            f"Alle {len(x['modelle'])} Modelle der vereinfachten Formel erfüllen nach der Rückrechnung die Originalklauseln.")
    if v.variablen_neu == 0:
        return "warning", kopf + " Nichts war eingefroren: auch die Eingänge wurden eliminiert, von der Zählerstruktur bleibt nichts (die Formel ist erfüllbar, aber die Aufgabe „höchstens k“ ist weg)."
    if x["gleich_binomial"]:
        return "success", kopf + f" Die vereinfachte Formel ist genau die binomiale Kodierung (höchstens {k} von {n}, alle {k + 1}-Teilmengen verboten) plus „mindestens eines“."
    return "info", kopf + (f" Die vereinfachte Formel ist **nicht** die binomiale Kodierung ({x['binomial_klauseln']} Klauseln): {v.variablen_neu - n} Hilfsvariablen bleiben, "
                           "weil ihre Elimination mehr Resolventen erzeugen würde, als Klauseln wegfallen.")


# --- Messreihe live (verkleinert) ---------------------------------------------------------------------------------------------------------------

def live_reihe(familie: str, n: int, eingefroren: bool, runden: int) -> list:
    """Vier feste Formeln (`LIVE_SEEDS`) der Familie, ein Löser-Seed (Standard), Budget `LIVE_BUDGET`."""
    return [messe_formel(S.aufgabe(familie, n, seed), eingefroren=eingefroren, loeser_seeds=(None,), budget=C.LIVE_BUDGET, runden=runden) for seed in C.LIVE_SEEDS]


def verdict_live(formeln: list) -> tuple[str, str]:
    """Zählung statt Streubreite: es gibt nur einen Löser-Seed. Fehler (Antwort, Modell) und Budgetabbrüche werden mitgezählt."""
    weniger = sum(1 for f in formeln if f["konflikte_nach"][0] < f["konflikte_vor"][0])
    mehr = sum(1 for f in formeln if f["konflikte_nach"][0] > f["konflikte_vor"][0])
    gleich = len(formeln) - weniger - mehr
    fehler = sum(f["antwortfehler"] + f["modellfehler"] for f in formeln)
    abbruch = sum(1 for f in formeln if f["antwort_vor"][0] is None or f["antwort_nach"][0] is None)
    text = (f"In {weniger} von {len(formeln)} Formeln sinken die Konflikte, in {mehr} steigen sie, in {gleich} bleiben sie gleich (ein Löser-Seed: ohne Streubreite sagt das nichts über einen Unterschied der Verfahren). "
            f"Antwort- und Modellfehler: {fehler}" + (f"; Budget erreicht in {abbruch} Formeln." if abbruch else "."))
    return ("error", text) if fehler else ("info", text)
