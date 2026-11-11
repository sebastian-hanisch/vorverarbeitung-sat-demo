"""Vorverarbeitung einer CNF-Formel in einzeln aufrufbaren Schritten (nur Standardbibliothek).

Literale sind ganze Zahlen (+v = Variable v, -v = nicht v), eine Klausel ist ein Tupel nach Variablen sortierter Literale, eine Formel eine Liste von Klauseln.
Jeder Schritt ist eine eigene Funktion mit expliziten Ein- und Ausgaben (DEMO-PLAYBOOK §1b):

  `einheiten`        Einheitspropagation bis zum Fixpunkt (liefert Belegung und Rest)
  `subsumiere`       Klauseln streichen, die eine kürzere Klausel enthalten (liefert die Paare „A subsumiert B“)
  `verstaerke`       Selbst-Subsumption: subsumiert die Resolvente zweier Klauseln eine Elternklausel, verliert diese das Literal
  `waehle_variable`  Variable mit dem kleinsten Produkt der Vorkommen (Gleichstand: kleinere Nummer), eingefrorene ausgenommen
  `eliminiere`       Variable durch Resolventen ersetzen, wenn es nicht mehr Resolventen als entfernte Klauseln sind und keine länger als `max_resolvente` ist
  `vorverarbeite`    Runden aus den vier Schritten mit Ereignisprotokoll und Kostenzählern
  `modell_rekonstruieren`  Modell der vereinfachten Formel zu einem Modell der Ausgangsformel (Eliminationsstapel rückwärts)
  `vivifiziere`      nur für den Erklär-Reiter: Literale einer Klausel nacheinander falsch setzen, bei Widerspruch die Klausel kürzen

Die Schritte erhalten die **Erfüllbarkeit**, nicht die Menge der Modelle (die Elimination verliert Variablen). Kostenzähler: `resolventen` (berechnete
Paar-Resolventen, auch verworfene und tautologische) und `vergleiche` (Teilmengen-Prüfungen zwischen zwei Klauseln in Subsumption und Verstärkung).
Einfache Fassung: kein Entfernen blockierter Klauseln, keine Äquivalenzerkennung, kein Probing.

Herkunft: eigene Fassung auf der Grundlage von `vvs_vorverarbeitung.py` (Kopie des Kern-Moduls, dort sind die Schritte privat, es gibt weder
Einfrieren noch Protokoll noch Kostenzähler). Mit `eingefroren=()` und gleicher Rundenzahl gilt dieselbe Eliminationsregel wie im Kern.
"""

import heapq
from collections import deque
from dataclasses import dataclass, field

MAX_RESOLVENTE = 20
RUNDEN = 5
SCHRITTE = ("einheit", "subsumption", "verstaerkung", "elimination")   # die vier Schritte
RUNDE = ("subsumption", "verstaerkung", "einheit", "elimination")      # Reihenfolge innerhalb einer Runde (vor der ersten Runde: Einheiten)
SNAPSHOT_MAX = 60   # bis zu dieser Klauselzahl speichert das Protokoll die Formel nach jedem Schritt


def sortiere(klausel) -> tuple:
    """Klausel als Tupel, nach Variablen sortiert, ohne doppelte Literale."""
    return tuple(sorted(set(klausel), key=lambda l: (abs(l), l)))


def ist_tautologie(klausel) -> bool:
    s = set(klausel)
    return any(-l in s for l in s)


def normalisiere(klauseln) -> list:
    """Sortiert jede Klausel, streicht doppelte Literale, Tautologien und doppelte Klauseln (Reihenfolge des ersten Auftretens)."""
    gesehen, aus = set(), []
    for c in klauseln:
        if ist_tautologie(c):
            continue
        c = sortiere(c)
        if c not in gesehen:
            gesehen.add(c)
            aus.append(c)
    return aus


def variablen_von(klauseln) -> set:
    return {abs(l) for c in klauseln for l in c}


# ----------------------------------------------------------------------------------------------------------------------
# Klauselbestand mit Vorkommenslisten (intern)
# ----------------------------------------------------------------------------------------------------------------------

class _Bestand:
    """Klauseln mit Nummer, Vorkommenslisten je Literal und Duplikaterkennung; ersetzte Klauseln behalten ihre Nummer (und damit ihre Stelle)."""

    def __init__(self, klauseln):
        self.kl = []
        self.occ = {}
        self.index = {}
        self.mengen = {}
        self.geaendert = set()
        self.einheitsschlange = deque()      # Nummern neu entstandener Einheitsklauseln, in der Reihenfolge ihres Entstehens
        self.widerspruch = False
        for c in klauseln:
            self.fuege(c)

    def fuege(self, c):
        if c in self.index:
            return None
        if not c:
            self.widerspruch = True
        i = len(self.kl)
        self.kl.append(c)
        self.index[c] = i
        if len(c) == 1:
            self.einheitsschlange.append(i)
        for l in c:
            self.occ.setdefault(l, set()).add(i)
            self.geaendert.add(abs(l))
        return i

    def entferne(self, i):
        c = self.kl[i]
        self.kl[i] = None
        del self.index[c]
        self.mengen.pop(i, None)
        for l in c:
            self.occ[l].discard(i)
            self.geaendert.add(abs(l))

    def ersetze(self, i, neu):
        """Ersetzt Klausel i durch eine Teilmenge ihrer selbst; gibt es `neu` schon, fällt Klausel i weg (Rückgabe None)."""
        alt = self.kl[i]
        if neu in self.index:
            self.entferne(i)
            return None
        del self.index[alt]
        self.mengen.pop(i, None)
        for l in alt:
            if l not in neu:
                self.occ[l].discard(i)
            self.geaendert.add(abs(l))
        self.kl[i] = neu
        self.index[neu] = i
        if len(neu) == 1:
            self.einheitsschlange.append(i)
        if not neu:
            self.widerspruch = True
        return i

    def menge(self, i):
        m = self.mengen.get(i)
        if m is None:
            m = self.mengen[i] = frozenset(self.kl[i])
        return m

    def liste(self):
        return [c for c in self.kl if c is not None]

    def vorkommen(self, lit):
        return len(self.occ.get(lit, ()))

    def variablen(self):
        return {abs(l) for l, s in self.occ.items() if s}

    def produkt(self, v):
        return self.vorkommen(v) * self.vorkommen(-v)


def _neue_zaehler() -> dict:
    return {"einheiten": 0, "subsumiert": 0, "verstaerkt": 0, "eliminiert": 0, "abgelehnt": 0, "resolventen": 0, "vergleiche": 0}


# ----------------------------------------------------------------------------------------------------------------------
# Einzelschritte (intern auf dem Bestand, öffentlich auf Listen)
# ----------------------------------------------------------------------------------------------------------------------

def _einheiten(b: _Bestand, belegung: dict, ereignisse, z: dict):
    """Einheitspropagation: Einheitsklauseln in Reihenfolge ihres Auftretens; erfüllte Klauseln fallen, das falsche Literal fällt aus den übrigen."""
    schlange = b.einheitsschlange
    while schlange and not b.widerspruch:
        i = schlange.popleft()
        c = b.kl[i]
        if c is None or len(c) != 1:
            continue
        lit = c[0]
        v = abs(lit)
        if v in belegung:                     # nur nach einem Widerspruchsfall erreichbar; defensiv
            if belegung[v] != (lit > 0):
                b.widerspruch = True
                break
            b.entferne(i)
            continue
        belegung[v] = lit > 0
        z["einheiten"] += 1
        erfuellt = sorted(b.occ.get(lit, ()))
        gekuerzt = sorted(b.occ.get(-lit, ()))
        e_erfuellt = [b.kl[j] for j in erfuellt]
        for j in erfuellt:
            b.entferne(j)
        e_gekuerzt = []
        for j in gekuerzt:
            alt = b.kl[j]
            neu = tuple(x for x in alt if x != -lit)
            e_gekuerzt.append((alt, neu))
            b.ersetze(j, neu)
        if ereignisse is not None:
            ereignisse.append({"art": "einheit", "literal": lit, "erfuellt": e_erfuellt, "gekuerzt": e_gekuerzt})


def _subsumiere(b: _Bestand, ereignisse, z: dict):
    ids = sorted((i for i, c in enumerate(b.kl) if c), key=lambda i: (len(b.kl[i]), i))
    for i in ids:
        a = b.kl[i]
        if a is None:
            continue
        seltenste = min(a, key=lambda l: (b.vorkommen(l), abs(l)))
        sa = b.menge(i)
        for j in sorted(b.occ.get(seltenste, ())):
            d = b.kl[j]
            if j == i or d is None or len(d) < len(a):
                continue
            z["vergleiche"] += 1
            if sa <= b.menge(j):
                z["subsumiert"] += 1
                if ereignisse is not None:
                    ereignisse.append({"art": "subsumption", "subsumierend": a, "subsumiert": d})
                b.entferne(j)


def _verstaerke(b: _Bestand, ereignisse, z: dict):
    schlange = deque(i for i, c in enumerate(b.kl) if c is not None)
    while schlange and not b.widerspruch:
        i = schlange.popleft()
        c = b.kl[i]
        if c is None:
            continue
        sc = b.menge(i)
        for lit in c:
            rest = sc - {lit}
            for j in sorted(b.occ.get(-lit, ())):
                d = b.kl[j]
                if j == i or d is None or len(d) < len(c):
                    continue
                z["vergleiche"] += 1
                if rest <= b.menge(j) - {-lit}:
                    neu = tuple(x for x in d if x != -lit)
                    z["verstaerkt"] += 1
                    if ereignisse is not None:
                        ereignisse.append({"art": "verstaerkung", "klausel": c, "opfer": d, "literal": -lit, "neu": neu})
                    r = b.ersetze(j, neu)
                    if r is not None:
                        schlange.append(j)


def _resolventen(b: _Bestand, v: int, max_resolvente: int, z: dict) -> dict:
    """Resolventen auf v; bricht ab, sobald die Regel verletzt ist (zu viele oder zu lange). `berechnet` zählt die untersuchten Paare."""
    pos = sorted(b.occ.get(v, ()))
    neg = sorted(b.occ.get(-v, ()))
    erlaubt_zahl = len(pos) + len(neg)
    res, grund = [], None
    for p in pos:
        for q in neg:
            z["resolventen"] += 1
            r = (set(b.kl[p]) | set(b.kl[q])) - {v, -v}
            if any(-l in r for l in r):
                continue
            if len(r) > max_resolvente:
                grund = "laenge"
                break
            res.append(sortiere(r))
            if len(res) > erlaubt_zahl:
                grund = "anzahl"
                break
        if grund:
            break
    return {"pos": pos, "neg": neg, "resolventen": res, "grund": grund}


def _eliminiere(b: _Bestand, v: int, max_resolvente: int, stapel: list, z: dict) -> dict:
    """Versucht die Elimination von v; bei Erfolg ersetzt sie die Klauseln mit v durch die Resolventen und legt den Stapeleintrag an."""
    erg = _resolventen(b, v, max_resolvente, z)
    pos_klauseln = [b.kl[i] for i in erg["pos"]]
    neg_klauseln = [b.kl[i] for i in erg["neg"]]
    ereignis = {"art": "elimination", "variable": v, "positiv": pos_klauseln, "negativ": neg_klauseln,
                "resolventen": list(erg["resolventen"]), "erlaubt": erg["grund"] is None, "grund": erg["grund"]}
    if erg["grund"] is not None:
        z["abgelehnt"] += 1
        return ereignis
    for i in erg["pos"] + erg["neg"]:
        b.entferne(i)
    for r in erg["resolventen"]:
        b.fuege(r)
    stapel.append((v, [tuple(c) for c in pos_klauseln]))
    z["eliminiert"] += 1
    return ereignis


def _wahl(b: _Bestand, ausgeschlossen) -> int | None:
    kandidaten = [(b.produkt(v), v) for v in b.variablen() if v not in ausgeschlossen]
    return min(kandidaten)[1] if kandidaten else None


def _eliminationsdurchlauf(b: _Bestand, belegung: dict, stapel: list, eingefroren, max_resolvente: int, ereignisse, z: dict):
    """Jede nicht eingefrorene Variable wird höchstens einmal versucht; Auswahl immer die mit dem kleinsten Produkt der Vorkommen (Heap mit Nachführung)."""
    versucht = set(eingefroren)
    heap = [(b.produkt(v), v) for v in b.variablen() if v not in versucht]
    heapq.heapify(heap)
    while heap and not b.widerspruch:
        p, v = heapq.heappop(heap)
        if v in versucht or v not in b.variablen():
            continue
        aktuell = b.produkt(v)
        if aktuell != p:
            heapq.heappush(heap, (aktuell, v))
            continue
        versucht.add(v)
        b.geaendert.clear()
        e = _eliminiere(b, v, max_resolvente, stapel, z)
        if ereignisse is not None:
            ereignisse.append(e)
        if e["erlaubt"]:
            _einheiten(b, belegung, ereignisse, z)
            for w in b.geaendert:
                if w not in versucht and (b.vorkommen(w) or b.vorkommen(-w)):
                    heapq.heappush(heap, (b.produkt(w), w))


# ----------------------------------------------------------------------------------------------------------------------
# Öffentliche Einzelschritte
# ----------------------------------------------------------------------------------------------------------------------

@dataclass
class EinheitenErgebnis:
    belegung: dict           # Variable -> bool, durch Einheitspropagation festgelegt
    klauseln: list           # Rest (Reihenfolge der übrigen Klauseln bleibt, gekürzte Klauseln behalten ihre Stelle)
    widerspruch: bool        # leere Klausel entstanden: unerfüllbar
    ereignisse: list = field(default_factory=list)


def einheiten(klauseln) -> EinheitenErgebnis:
    """Einheitspropagation bis zum Fixpunkt."""
    b = _Bestand(normalisiere(klauseln))
    belegung, ereignisse, z = {}, [], _neue_zaehler()
    _einheiten(b, belegung, ereignisse, z)
    return EinheitenErgebnis(belegung, b.liste(), b.widerspruch, ereignisse)


def subsumiere(klauseln) -> tuple:
    """(neue Formel, Paare (A, B) mit „A subsumiert B“): B wird gestrichen, A bleibt. Die Paare folgen der Reihenfolge der Suche (kurze Klauseln zuerst)."""
    b = _Bestand(normalisiere(klauseln))
    ereignisse = []
    _subsumiere(b, ereignisse, _neue_zaehler())
    return b.liste(), [(e["subsumierend"], e["subsumiert"]) for e in ereignisse]


def verstaerke(klauseln) -> tuple:
    """(neue Formel, Schritte): Schritt = {klausel, opfer, literal, neu}; die Resolvente von `klausel` und `opfer` ist `neu` und subsumiert `opfer`."""
    b = _Bestand(normalisiere(klauseln))
    ereignisse = []
    _verstaerke(b, ereignisse, _neue_zaehler())
    return b.liste(), ereignisse


def waehle_variable(klauseln, eingefroren=()) -> int | None:
    """Variable mit dem kleinsten Produkt (Vorkommen positiv) mal (Vorkommen negativ); Gleichstand: kleinere Nummer; eingefrorene nie; None, wenn keine bleibt."""
    return _wahl(_Bestand(normalisiere(klauseln)), set(eingefroren))


@dataclass
class Elimination:
    variable: int
    positiv: list
    negativ: list
    resolventen: list        # nicht tautologische Resolventen in der Reihenfolge der Paare (bei Abbruch: die bis dahin gefundenen)
    erlaubt: bool
    grund: str | None        # None | "anzahl" (mehr Resolventen als entfernte Klauseln) | "laenge" (Resolvente länger als max_resolvente)
    stapel: tuple | None     # (Variable, positive Klauseln) für die Rekonstruktion; None, wenn abgelehnt
    klauseln: list           # Formel danach (unverändert, wenn abgelehnt)
    berechnet: int           # untersuchte Paare (Kostenzähler)


def eliminiere(klauseln, var: int, max_resolvente: int = MAX_RESOLVENTE) -> Elimination:
    """Elimination einer Variablen (Davis-Putnam-Schritt, begrenzt): erlaubt, wenn nicht mehr Resolventen als entfernte Klauseln und jede höchstens `max_resolvente` Literale hat."""
    b = _Bestand(normalisiere(klauseln))
    z, stapel = _neue_zaehler(), []
    e = _eliminiere(b, var, max_resolvente, stapel, z)
    return Elimination(var, e["positiv"], e["negativ"], e["resolventen"], e["erlaubt"], e["grund"], stapel[0] if stapel else None, b.liste(), z["resolventen"])


# ----------------------------------------------------------------------------------------------------------------------
# Das ganze Verfahren
# ----------------------------------------------------------------------------------------------------------------------

@dataclass
class Vorverarbeitet:
    unerfuellbar: bool
    n_alt: int
    klauseln_alt: list                     # normalisierte Ausgangsformel
    klauseln: list                         # vereinfachte Formel in den alten Variablennummern
    einheiten: dict                        # Variable -> bool (durch Einheitspropagation festgelegt)
    stapel: list                           # [(eliminierte Variable, Klauseln, in denen sie positiv vorkam)]
    eingefroren: frozenset
    phasen: list                           # je Schritt: runde, schritt, ereignisse, Zähler vor/nach, formel (bei kleinen Formeln)
    zaehler: dict                          # einheiten, subsumiert, verstaerkt, eliminiert, abgelehnt, resolventen, vergleiche, runden
    protokoll: bool = True

    @property
    def variablen_alt(self) -> int:
        return len(variablen_von(self.klauseln_alt))

    @property
    def variablen_neu(self) -> int:
        return len(variablen_von(self.klauseln))

    @property
    def abbildung(self) -> dict:
        """Alte Nummer -> dichte neue Nummer 1..m für die noch vorkommenden Variablen."""
        return {v: i + 1 for i, v in enumerate(sorted(variablen_von(self.klauseln)))}

    @property
    def n_dicht(self) -> int:
        return self.variablen_neu

    @property
    def klauseln_dicht(self) -> list:
        """Vereinfachte Formel mit dicht nummerierten Variablen (für den Löser)."""
        ab = self.abbildung
        return [tuple((ab[abs(l)] if l > 0 else -ab[abs(l)]) for l in c) for c in self.klauseln]

    def modell_dicht_zu_alt(self, modell_dicht: dict) -> dict:
        return {alt: bool(modell_dicht.get(neu, False)) for alt, neu in self.abbildung.items()}


def _phase(runde, schritt, ereignisse, b, vorher):
    nach = (len(b.index), len(b.variablen()))
    p = {"runde": runde, "schritt": schritt, "ereignisse": ereignisse if ereignisse is not None else [],
         "klauseln_vor": vorher[0], "variablen_vor": vorher[1], "klauseln_nach": nach[0], "variablen_nach": nach[1]}
    p["formel"] = b.liste() if nach[0] <= SNAPSHOT_MAX else None
    return p


def vorverarbeite(n: int, klauseln, *, runden: int = RUNDEN, max_resolvente: int = MAX_RESOLVENTE, eingefroren=(), protokoll: bool = True) -> Vorverarbeitet:
    """Einheiten; dann bis zu `runden` Runden aus Subsumption, Verstärkung, Einheiten, begrenzter Elimination; eine Runde ohne Änderung beendet das Verfahren
    (sie zählt nicht als Runde und steht nicht im Protokoll).

    `eingefroren`: Variablen, die nie eliminiert werden (bei Zählern die Eingänge). `protokoll=False` lässt die Ereignislisten weg, die Zähler bleiben.
    """
    alt = normalisiere(klauseln)
    b = _Bestand(alt)
    eingefroren = frozenset(eingefroren)
    belegung, stapel, z, phasen = {}, [], _neue_zaehler(), []

    def messe():
        return (len(b.index), len(b.variablen()))

    phasen.append(_phase(0, "start", [], b, messe()))
    e = [] if protokoll else None
    vorher = messe()
    _einheiten(b, belegung, e, z)
    phasen.append(_phase(0, "einheit", e, b, vorher))
    runde = 0
    while runde < runden and not b.widerspruch:
        runde += 1
        stand = (frozenset(b.index), len(belegung))
        n_phasen = len(phasen)
        for schritt in RUNDE:
            e = [] if protokoll else None
            vorher = messe()
            if schritt == "subsumption":
                _subsumiere(b, e, z)
            elif schritt == "verstaerkung":
                _verstaerke(b, e, z)
            elif schritt == "einheit":
                _einheiten(b, belegung, e, z)
            else:
                _eliminationsdurchlauf(b, belegung, stapel, eingefroren, max_resolvente, e, z)
            phasen.append(_phase(runde, schritt, e, b, vorher))
            if b.widerspruch:
                break
        if (frozenset(b.index), len(belegung)) == stand:     # die Runde hat nichts geändert: sie wird nicht mitgezählt und nicht angezeigt
            del phasen[n_phasen:]
            runde -= 1
            break
    z["runden"] = runde
    rest = [()] if b.widerspruch else b.liste()
    return Vorverarbeitet(b.widerspruch, n, alt, rest, belegung, stapel, eingefroren, phasen, z, protokoll)


def modell_rekonstruieren(v: Vorverarbeitet, modell: dict) -> dict:
    """Modell der vereinfachten Formel (alte Nummern der noch vorkommenden Variablen) -> Modell der Ausgangsformel für 1..n_alt.

    Reihenfolge: durch Einheiten festgelegte Variablen, dann die Eliminationen **rückwärts**: eine eliminierte Variable ist zunächst falsch und wird wahr,
    wenn eine der gespeicherten Klauseln, in denen sie positiv vorkam, sonst unerfüllt wäre. Variablen, die nirgends mehr vorkommen, sind frei (falsch)."""
    if v.unerfuellbar:
        raise ValueError("eine unerfüllbare Formel hat kein Modell")
    wert = {x: False for x in range(1, v.n_alt + 1)}
    for x in variablen_von(v.klauseln_alt):
        wert.setdefault(x, False)
    for x, w in v.einheiten.items():
        wert[x] = w
    for x in variablen_von(v.klauseln):
        wert[x] = bool(modell.get(x, False))
    for x, pos in reversed(v.stapel):
        wert[x] = False
        for c in pos:
            if not any((wert[abs(l)] if l > 0 else not wert[abs(l)]) for l in c if abs(l) != x):
                wert[x] = True
                break
    return wert


# ----------------------------------------------------------------------------------------------------------------------
# Vivification (nur Erklär-Reiter)
# ----------------------------------------------------------------------------------------------------------------------

@dataclass
class Vivifikation:
    klausel: tuple
    neue_klausel: tuple
    schritte: list            # je Literal: {literal, ereignis, geschlossen: [(Literal, Klausel)], konflikt: Klausel | None}
    art: str                  # "konflikt" (Widerspruch), "folgt" (ein Literal folgt wahr), "gekuerzt" (nur Literale entfallen), "unveraendert"


def _propagiere_klein(klauseln, belegung: dict):
    """Einheitspropagation auf einer kleinen Formel (Liste), ändert `belegung`; liefert (Schlüsse [(Literal, Klausel)], verletzte Klausel | None)."""
    schluesse = []
    veraendert = True
    while veraendert:
        veraendert = False
        for c in klauseln:
            if any(belegung.get(abs(l)) == (l > 0) for l in c):
                continue
            frei = [l for l in c if abs(l) not in belegung]
            if not frei:
                return schluesse, c
            if len(frei) == 1:
                belegung[abs(frei[0])] = frei[0] > 0
                schluesse.append((frei[0], c))
                veraendert = True
    return schluesse, None


def vivifiziere(klauseln, klausel) -> Vivifikation:
    """Vivification einer Klausel C: die übrigen Klauseln bleiben; die Literale von C werden nacheinander falsch gesetzt und propagiert.

    Konflikt nach den ersten i Literalen: C wird zu diesen i Literalen (sie folgen aus den übrigen Klauseln). Wird ein späteres Literal durch die Propagation wahr,
    genügt C bis zu ihm; wird es falsch, entfällt es. Das Ergebnis folgt aus der Formel und ist Teilmenge von C, die Modelle der Formel bleiben dieselben."""
    c = sortiere(klausel)
    rest = [d for d in normalisiere(klauseln) if d != c]
    belegung, behalten, schritte = {}, [], []
    art = "unveraendert"
    for lit in c:
        wert = belegung.get(abs(lit))
        if wert is not None and wert == (lit > 0):
            behalten.append(lit)
            schritte.append({"literal": lit, "ereignis": "folgt_wahr", "geschlossen": [], "konflikt": None})
            art = "folgt"
            break
        if wert is not None:
            schritte.append({"literal": lit, "ereignis": "folgt_falsch", "geschlossen": [], "konflikt": None})
            art = "gekuerzt"
            continue
        belegung[abs(lit)] = lit < 0
        behalten.append(lit)
        schluesse, konflikt = _propagiere_klein(rest, belegung)
        schritte.append({"literal": lit, "ereignis": "gesetzt", "geschlossen": schluesse, "konflikt": konflikt})
        if konflikt is not None:
            art = "konflikt"
            break
    neu = tuple(behalten)
    if art == "unveraendert" and neu != c:
        art = "gekuerzt"
    return Vivifikation(c, neu, schritte, art)
