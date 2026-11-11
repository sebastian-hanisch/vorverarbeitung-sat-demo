"""Verkleinerte Messreihe live mit Fortschrittsanzeige und Zwischenspeicher: das Ergebnis ist gleich dem ungepufferten, ein anderer Parameter kommt nicht aus dem Speicher."""

import os

from streamlit.testing.v1 import AppTest

import vvs_constants as C
import vvs_evaluation as ev
import vvs_fortschritt as F

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))


def test_zwischengespeicherte_reihe_ist_gleich_der_ungepufferten():
    for familie, n, eingefroren, runden in ((C.FAM_ZUFALL, 30, False, 5), (C.FAM_VC_SINZ, 20, True, 3), (C.FAM_LATIN, 6, False, 5)):
        F.formel_messung.clear()
        direkt = ev.live_reihe(familie, n, eingefroren, runden)
        for _ in range(2):                                                   # zweiter Aufruf aus dem Zwischenspeicher
            formeln, sek = F.reihe(familie, n, eingefroren, runden)
            assert formeln == direkt, (familie, n)
            assert sek >= 0


def test_zweiter_aufruf_rechnet_nichts_neu_ein_anderer_parameter_schon():
    F.formel_messung.clear()
    v0 = F.gerechnet()
    erste, _ = F.reihe(C.FAM_ZUFALL, 30, False, 5)
    assert F.gerechnet() - v0 == len(C.LIVE_SEEDS)
    v1 = F.gerechnet()
    assert F.reihe(C.FAM_ZUFALL, 30, False, 5)[0] == erste and F.gerechnet() == v1
    for args in ((C.FAM_ZUFALL, 40, False, 5), (C.FAM_ZUFALL, 30, False, 2), (C.FAM_FAERBUNG, 30, False, 5)):
        v = F.gerechnet()
        neu, _ = F.reihe(*args)
        assert F.gerechnet() - v == len(C.LIVE_SEEDS), args
        assert neu == ev.live_reihe(*args) and neu != erste, args
    v = F.gerechnet()
    F.reihe(C.FAM_VC_SINZ, 20, False, 5)
    F.reihe(C.FAM_VC_SINZ, 20, True, 5)
    assert F.gerechnet() - v == 2 * len(C.LIVE_SEEDS), "„Eingänge einfrieren“ gehört zum Schlüssel"


def test_fortschritt_meldet_jede_formel_in_ordnung():
    F.formel_messung.clear()
    meldungen = []
    F.reihe(C.FAM_LATIN, 6, False, 5, lambda fertig, gesamt: meldungen.append((fertig, gesamt)))
    assert meldungen == [(i, 4) for i in range(1, 5)]


def test_app_zweiter_klick_kommt_aus_dem_zwischenspeicher_und_zeigt_dasselbe():
    F.formel_messung.clear()
    v0 = F.gerechnet()
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=TIMEOUT)
    at.sidebar.selectbox(key="familie_select").select("zufall").run(timeout=TIMEOUT)
    at.sidebar.slider(key="n_zufall").set_value(30).run(timeout=TIMEOUT)
    next(b for b in at.main.button if b.key == "live_knopf").click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    erste = [d.value.to_dict("records") for d in at.dataframe]
    assert F.gerechnet() - v0 == 4
    v = F.gerechnet()
    next(b for b in at.main.button if b.key == "live_knopf").click().run(timeout=TIMEOUT)
    assert not at.exception and F.gerechnet() == v
    assert [d.value.to_dict("records") for d in at.dataframe] == erste
