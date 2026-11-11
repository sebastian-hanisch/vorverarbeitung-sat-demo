"""Verkleinerte Messreihe live mit Fortschrittsanzeige und Zwischenspeicher (nur Bedienung, keine Rechnung).

Aufgabe ist hier eine Formel: `formel_messung` ruft `vvs_evaluation.messe_formel` mit denselben Angaben auf wie `vvs_evaluation.live_reihe` und wird je Formel
zwischengespeichert (`st.cache_data`, höchstens 16 Einträge: vier Einstellungen zu vier Formeln). Der Fortschrittsbalken zählt die fertigen Formeln; klickt
jemand mit derselben Einstellung erneut, kommen alle Formeln aus dem Zwischenspeicher. Das Ergebnis ist gleich dem von `live_reihe`
(`tests/test_fortschritt.py`); die Rechenzeit ist die Summe der Zeiten, in denen die Formeln tatsächlich gerechnet wurden (nur Anzeige)."""

import time
from contextlib import contextmanager

import streamlit as st

import vvs_constants as C
import vvs_evaluation as ev
import vvs_scenario as S

_ZAEHLER = {"gerechnet": 0}


def gerechnet() -> int:
    """Wie viele Formeln in diesem Prozess tatsächlich gerechnet (nicht aus dem Zwischenspeicher geholt) wurden; dient dem Test."""
    return _ZAEHLER["gerechnet"]


@st.cache_data(show_spinner=False, max_entries=16)
def formel_messung(familie: str, n: int, seed: int, eingefroren: bool, runden: int) -> tuple:
    """(Messung der Formel, Sekunden): die Messung ist ein Element von `ev.live_reihe(familie, n, eingefroren, runden)`."""
    _ZAEHLER["gerechnet"] += 1
    t0 = time.perf_counter()
    f = ev.messe_formel(S.aufgabe(familie, n, seed), eingefroren=eingefroren, loeser_seeds=(None,), budget=C.LIVE_BUDGET, runden=runden)
    return f, time.perf_counter() - t0


def reihe(familie: str, n: int, eingefroren: bool, runden: int, melde=None) -> tuple:
    """(Liste der Messungen wie `ev.live_reihe`, Rechenzeit der Formeln in Sekunden); `melde(fertig, gesamt)` wird nach jeder Formel aufgerufen."""
    formeln, sek = [], 0.0
    for i, seed in enumerate(C.LIVE_SEEDS, start=1):
        f, t = formel_messung(familie, n, seed, eingefroren, runden)
        formeln.append(f)
        sek += t
        if melde:
            melde(i, len(C.LIVE_SEEDS))
    return formeln, sek


@contextmanager
def fortschrittsbalken(text: str):
    """Fortschrittsbalken mit Beschriftung; liefert `melde(fertig, gesamt)` und räumt den Balken am Ende weg."""
    balken = st.progress(0.0, text=text)

    def melde(fertig: int, gesamt: int) -> None:
        balken.progress(fertig / gesamt, text=f"{text}: {fertig} von {gesamt}")

    try:
        yield melde
    finally:
        balken.empty()
