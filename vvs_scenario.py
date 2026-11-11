"""Aufgaben der Demo: Handbeispiele, Sinz-Zähler, Vertex Cover mit Zähler, Färbung, Zufalls-3-SAT, lateinisches Quadrat mit Lücken.

Alle Zufallsinstanzen laufen über den ganzzahligen SplitMix64 (`vvs_rng.py`), nie über Python-`random`. Eine Aufgabe ist `Aufgabe`:
Formel (Variablenzahl, Klauseln), die **Eingänge** (Variablen der eigentlichen Aufgabe; bei Zählern die, die beim Einfrieren stehen bleiben) und eine Beschriftung.
"""

import itertools
from dataclasses import dataclass, field

import vvs_constants as C
import vvs_instanzen as I
import vvs_kodierung as K
from vvs_rng import SplitMix64

HAND_TEIL1 = [(1,), (1, 3), (-1, 2, 4), (2, 3, 4), (-2, 4)]
HAND_TEIL3 = [(1, 2, 3), (1, 2, 4), (1, 2, -4)]


@dataclass(frozen=True)
class Aufgabe:
    familie: str
    n: int                                   # Variablen der Formel (einschließlich Hilfsvariablen)
    klauseln: tuple
    eingaenge: tuple = ()                    # Variablen der Aufgabe (bei Zählern die Zählereingänge)
    name: str = ""
    meta: dict = field(default_factory=dict, hash=False, compare=False)


def lit_text(lit: int) -> str:
    return f"x{lit}" if lit > 0 else f"¬x{-lit}"


def klausel_text(klausel) -> str:
    return "(" + " ∨ ".join(lit_text(l) for l in klausel) + ")" if klausel else "(leere Klausel)"


def formel_text(klauseln) -> str:
    return " ∧ ".join(klausel_text(c) for c in klauseln) if klauseln else "(leere Formel: erfüllt)"


def sinz_zaehler(n: int, k: int) -> Aufgabe:
    """Sinz-Zähler „höchstens k von x1 bis xn“ plus die Klausel „mindestens eines“ (x1 ∨ … ∨ xn); Hilfsvariablen ab n + 1. Für k = 1 und n = 3 das Handbeispiel."""
    pool = K.Hilfsvariablen(n)
    zaehler = K.hoechstens_sinz(list(range(1, n + 1)), k, pool)
    return Aufgabe("sinz", pool.n, tuple(zaehler) + (tuple(range(1, n + 1)),), tuple(range(1, n + 1)),
                   f"Sinz-Zähler, höchstens {k} von {n} (und mindestens eines)", {"n_eingaenge": n, "k": k, "zaehlerklauseln": len(zaehler)})


def vertex_cover(n: int, grad: float, k: int, verfahren: str, seed: int) -> Aufgabe:
    """Knotenüberdeckung eines Zufallsgraphen (n Knoten, mittlerer Grad `grad`): jede Kante hat einen Endpunkt in der Auswahl, höchstens k Knoten
    (Zähler „sinz“ oder „totalizer“). Variable i + 1 = Knoten i gewählt; Hilfsvariablen des Zählers ab n + 1."""
    kanten = I.zufallskanten(n, int(round(n * grad / 2)), seed)
    pool = K.Hilfsvariablen(n)
    kl = [(a + 1, b + 1) for a, b in kanten]
    kl += K.hoechstens(list(range(1, n + 1)), k, pool, verfahren)
    name = {"sinz": "Sinz-Zähler", "totalizer": "Totalizer"}[verfahren]
    return Aufgabe("vc_" + verfahren, pool.n, tuple(kl), tuple(range(1, n + 1)), f"Vertex Cover n = {n}, k = {k}, {name}",
                   {"kanten": len(kanten), "k": k, "verfahren": verfahren, "seed": seed})


def faerbung(n: int, grad: float, seed: int) -> Aufgabe:
    inst = I.flat_graph(n, grad, seed, 3)
    return Aufgabe("faerbung", inst.n, tuple(inst.klauseln), (), f"3-Färbung n = {n}, Grad {grad:g}".replace(".", ","), {"seed": seed, "kanten": len(inst.meta["kanten"])})


def zufall3(n: int, m: int, seed: int) -> Aufgabe:
    inst = I.rand3(n, m, seed)
    return Aufgabe("zufall", inst.n, tuple(inst.klauseln), (), f"Zufalls-3-SAT n = {n}, m = {m}", {"seed": seed, "m": m})


def zufallsquadrat(ordnung: int, seed: int) -> list:
    """Lateinisches Quadrat durch viele Zyklentausche (cycle switching) aus dem zyklischen Quadrat; 30·ordnung² Tausche, damit es nicht isotop zur Gruppe bleibt."""
    rng = SplitMix64(seed)
    L = [[(r + c) % ordnung for c in range(ordnung)] for r in range(ordnung)]
    for _ in range(30 * ordnung * ordnung):
        r1 = rng.below(ordnung)
        r2 = (r1 + 1 + rng.below(ordnung - 1)) % ordnung
        pos = {L[r1][c]: c for c in range(ordnung)}
        c0 = rng.below(ordnung)
        zyklus, c = [], c0
        while True:
            zyklus.append(c)
            c = pos[L[r2][c]]
            if c == c0:
                break
        for c in zyklus:
            L[r1][c], L[r2][c] = L[r2][c], L[r1][c]
    return L


def latin_luecken(ordnung: int, luecken: float, seed: int) -> Aufgabe:
    """Lateinisches Quadrat mit Lücken (Anteil `luecken` der Zellen ohne Vorgabe), erfüllbar nach Konstruktion. Variable (Zeile r, Spalte c, Symbol s) = (r·ordnung + c)·ordnung + s + 1."""
    quadrat = zufallsquadrat(ordnung, seed)
    rng = SplitMix64(seed * 7919 + 13)

    def v(r, c, s):
        return (r * ordnung + c) * ordnung + s + 1

    R = range(ordnung)
    kl = []
    for r in R:
        for c in R:
            kl.append(tuple(v(r, c, s) for s in R))
            kl += [(-v(r, c, s), -v(r, c, t)) for s, t in itertools.combinations(R, 2)]
    for s in R:
        for r in R:
            kl.append(tuple(v(r, c, s) for c in R))
            kl += [(-v(r, c, s), -v(r, d, s)) for c, d in itertools.combinations(R, 2)]
        for c in R:
            kl.append(tuple(v(r, c, s) for r in R))
            kl += [(-v(r, c, s), -v(q, c, s)) for r, q in itertools.combinations(R, 2)]
    zellen = [(r, c) for r in R for c in R]
    rng.shuffle(zellen)
    vorgegeben = zellen[: int(round(len(zellen) * (1 - luecken)))]
    kl += [(v(r, c, quadrat[r][c]),) for r, c in vorgegeben]
    return Aufgabe("latin", ordnung ** 3, tuple(kl), (), f"Latin {ordnung}, Lücken {luecken:g}".replace(".", ","),
                   {"seed": seed, "vorgegeben": len(vorgegeben), "ordnung": ordnung})


def ist_lateinisch(quadrat) -> bool:
    n = len(quadrat)
    return all(sorted(z) == list(range(n)) for z in quadrat) and all(sorted(quadrat[r][c] for r in range(n)) == list(range(n)) for c in range(n))


def aufgabe(familie: str, n: int, seed: int) -> Aufgabe:
    """Die Aufgabe einer Familie mit den Voreinstellungen der Messreihe (Seitenleiste: Familie, Größe n, Zufalls-Seed)."""
    if familie == C.FAM_VC_TOTALIZER:
        return vertex_cover(n, C.VC_GRAD, vc_k(n), "totalizer", seed)
    if familie == C.FAM_VC_SINZ:
        return vertex_cover(n, C.VC_GRAD, vc_k(n), "sinz", seed)
    if familie == C.FAM_FAERBUNG:
        return faerbung(n, C.FAERBUNG_GRAD, seed)
    if familie == C.FAM_ZUFALL:
        return zufall3(n, int(round(n * C.ZUFALL_DICHTE)), seed)
    if familie == C.FAM_LATIN:
        return latin_luecken(n, C.LATIN_LUECKEN, seed)
    if familie == C.FAM_SINZ:
        return sinz_zaehler(n, C.SINZ_K)
    raise ValueError(familie)


def vc_k(n: int) -> int:
    """Höchstzahl gewählter Knoten: 0,4·n (60 Knoten: 24)."""
    return int(round(C.VC_ANTEIL * n))
