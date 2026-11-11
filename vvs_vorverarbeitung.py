# Herkunft: Kopie von sat-cp-planung/kern/vorverarbeitung.py (Kern-Version 5b97cdced685984e, Datei HASHES.txt vom 2026-11-10), nur Importe auf vvs_ umgestellt.
# Nicht von Hand ändern: tests/test_copies.py vergleicht diese Datei mit dem Kern-Hash.
"""Vorverarbeitung des Kern-Pakets: Einheitspropagation, Subsumption, Verstärkung, begrenzte Variablenelimination.

Alle Schritte erhalten die Erfüllbarkeit (nicht die Menge der Lösungen). Eliminierte Variablen werden über einen Stapel
rekonstruiert (`modell_rekonstruieren`), sodass ein Modell der vereinfachten Formel zu einem Modell der Ausgangsformel wird.
Begrenzte Variablenelimination: eine Variable fällt weg, wenn ihre Resolventen nicht zahlreicher sind als die Klauseln, die sie ersetzen,
und keine Resolvente länger als `max_resolvente` ist. Einfache Fassung: keine Blocked-Clause-Elimination, keine Äquivalenzerkennung.
Herkunft: überarbeitet aus `vormessung/sc_v9_v15.py` (V15, Antwort- und Modellfehler 0).
"""
from dataclasses import dataclass, field


@dataclass
class Vereinfacht:
    unerfuellbar: bool
    n_alt: int
    n_neu: int                       # Variablen der vereinfachten Formel (dicht nummeriert)
    klauseln: list                   # Klauseln in der neuen Nummerierung
    abbildung: dict                  # alte Variable -> neue Variable (nur die, die noch vorkommen)
    stapel: list = field(default_factory=list)       # [(eliminierte Variable, Klauseln mit ihr positiv)]
    einheiten: dict = field(default_factory=dict)    # alte Variable -> Wert (durch Propagation festgelegt)
    n_klauseln_alt: int = 0
    n_klauseln_neu: int = 0


def _einheiten_propagieren(klauseln: dict, einheiten: dict) -> bool:
    """Wendet alle Einheitsklauseln an. Gibt False zurück bei Widerspruch (leere Klausel)."""
    veraendert = True
    while veraendert:
        veraendert = False
        for c in list(klauseln):
            if c not in klauseln:
                continue
            if len(c) == 0:
                return False
            if len(c) == 1:
                l = c[0]
                if abs(l) in einheiten and einheiten[abs(l)] != (l > 0):
                    return False
                einheiten[abs(l)] = l > 0
                del klauseln[c]
                for d in list(klauseln):
                    if l in d:
                        del klauseln[d]
                    elif -l in d:
                        del klauseln[d]
                        klauseln[tuple(x for x in d if x != -l)] = True
                veraendert = True
                break
    return True


def _subsumption(klauseln: dict):
    """Entfernt von anderen Klauseln enthaltene Klauseln und streicht Literale per Selbst-Subsumption (Verstärkung)."""
    vorkommen = {}
    for c in klauseln:
        for l in c:
            vorkommen.setdefault(l, []).append(c)
    for c in sorted(list(klauseln), key=len):
        if c not in klauseln:
            continue
        wenigste = min(c, key=lambda l: len(vorkommen.get(l, [])))
        for d in list(vorkommen.get(wenigste, [])):
            if d is not c and d in klauseln and len(d) >= len(c) and set(c) <= set(d):
                del klauseln[d]
        for l in c:
            rest = set(c) - {l}
            for d in list(vorkommen.get(-l, [])):
                if d in klauseln and rest <= set(d):
                    del klauseln[d]
                    klauseln[tuple(x for x in d if x != -l)] = True


def _eliminiere(klauseln: dict, einheiten: dict, stapel: list, max_resolvente: int) -> bool:
    vorkommen = {}
    for c in klauseln:
        for l in c:
            vorkommen.setdefault(l, []).append(c)
    variablen = sorted({abs(l) for c in klauseln for l in c},
                       key=lambda v: len(vorkommen.get(v, [])) * len(vorkommen.get(-v, [])))
    for v in variablen:
        pos = [c for c in klauseln if v in c]
        neg = [c for c in klauseln if -v in c]
        if not pos and not neg:
            continue
        resolventen, ok = [], True
        for p in pos:
            for q in neg:
                r = (set(p) | set(q)) - {v, -v}
                if any(-l in r for l in r):
                    continue
                if len(r) > max_resolvente:
                    ok = False
                    break
                resolventen.append(tuple(sorted(r)))
            if not ok:
                break
        if not ok or len(resolventen) > len(pos) + len(neg):
            continue
        stapel.append((v, [list(c) for c in pos]))
        for c in pos + neg:
            del klauseln[c]
        for r in resolventen:
            klauseln[r] = True
        if not _einheiten_propagieren(klauseln, einheiten):
            return False
    return True


def vorverarbeite(n: int, klauseln, max_resolvente: int = 20, runden: int = 5) -> Vereinfacht:
    kl = {}
    for c in klauseln:
        c = tuple(sorted(set(c)))
        if any(-l in c for l in c):
            continue
        kl[c] = True
    n_alt_klauseln = len(kl)
    stapel, einheiten = [], {}
    if _einheiten_propagieren(kl, einheiten):
        for _ in range(runden):
            vorher = len(kl)
            _subsumption(kl)
            if not _einheiten_propagieren(kl, einheiten) or not _eliminiere(kl, einheiten, stapel, max_resolvente):
                kl = None
                break
            if len(kl) == vorher:
                break
    else:
        kl = None
    if kl is None:
        return Vereinfacht(True, n, 0, [], {}, stapel, einheiten, n_alt_klauseln, 0)
    vs = sorted({abs(l) for c in kl for l in c})
    abbildung = {v: i + 1 for i, v in enumerate(vs)}
    neu = [tuple(abbildung[abs(l)] if l > 0 else -abbildung[abs(l)] for l in c) for c in kl]
    return Vereinfacht(False, n, len(vs), neu, abbildung, stapel, einheiten, n_alt_klauseln, len(neu))


def modell_rekonstruieren(v: Vereinfacht, modell_neu: dict) -> dict:
    """Modell der vereinfachten Formel (neue Nummern) -> Modell der Ausgangsformel (alte Nummern)."""
    wert = {x: False for x in range(1, v.n_alt + 1)}
    for x, w in v.einheiten.items():
        wert[x] = w
    for alt, neu in v.abbildung.items():
        wert[alt] = bool(modell_neu.get(neu, False))
    for x, pos in reversed(v.stapel):
        wert[x] = False
        for c in pos:
            if not any((wert[abs(l)] if l > 0 else not wert[abs(l)]) for l in c if abs(l) != x):
                wert[x] = True
                break
    return wert
