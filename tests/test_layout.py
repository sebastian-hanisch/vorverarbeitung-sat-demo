"""Layout (DEMO-PLAYBOOK §2): fester Kopf, Schnellstart oben in der Seitenleiste, aktives Preset hervorgehoben.

Die Hervorhebung ist zustandslos (`aktives_preset` vergleicht jeden Regler aus SETTING_SPECS mit dem Preset). Die Größe n hat je Familie einen eigenen Schlüssel `n_<Familie>`,
gezeichnet wird nur der Regler der gewählten Familie; der Test unten stellt sicher, dass jeder gezeichnete Regler in SETTING_SPECS steht und seine Änderung die Markierung aufhebt."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import vvs_constants as C
import vvs_presets as P

APP = str(Path(__file__).resolve().parent.parent / "app.py")
REGLER_ARTEN = ("slider", "number_input", "select_slider", "selectbox", "radio", "toggle", "checkbox", "text_input")


def _app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _typen(at) -> dict:
    return {b.label: b.proto.type for b in at.sidebar.button if b.label in C.PRESETS}


def _regler(at, key):
    for art in REGLER_ARTEN:
        try:
            return getattr(at.sidebar, art)(key=key)
        except KeyError:
            continue
    raise AssertionError(f"Regler {key} steht nicht in der Seitenleiste")


def test_presets_stehen_in_der_seitenleiste_und_nicht_im_hauptbereich():
    at = _app()
    assert [b.label for b in at.sidebar.button][: len(C.PRESETS)] == list(C.PRESETS)
    assert not [b for b in at.main.button if b.label in C.PRESETS]


def test_titel_steht_im_festen_kopf():
    at = _app()
    assert "st-key-kopf" in " ".join(h.proto.body for h in at.get("html"))
    assert at.title[0].value


def test_beim_start_ist_genau_das_standard_preset_hervorgehoben():
    assert [name for name, typ in _typen(_app()).items() if typ == "primary"] == [next(iter(C.PRESETS))]


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_angeklicktes_preset_ist_hervorgehoben_und_bleibt_es_im_naechsten_lauf(name):
    at = _app()
    at.sidebar.button(key=f"preset_{name}").click().run()
    assert not at.exception, [str(e) for e in at.exception]
    assert [n for n, typ in _typen(at).items() if typ == "primary"] == [name]
    at.run()
    assert [n for n, typ in _typen(at).items() if typ == "primary"] == [name]


def test_jeder_gezeichnete_regler_der_seitenleiste_steht_in_setting_specs():
    for name in C.PRESETS:
        at = _app()
        at.sidebar.button(key=f"preset_{name}").click().run()
        schluessel = {w.key for art in REGLER_ARTEN for w in getattr(at.sidebar, art) if w.key}
        fehlt = schluessel - set(P.SETTING_SPECS)
        assert not fehlt, f"Regler {sorted(fehlt)} fehlen in SETTING_SPECS: ihre Änderung hebt das aktive Preset nicht auf"


def _aendere(at, state_key):
    spec = P.SETTING_SPECS[state_key]
    regler = _regler(at, state_key)
    if state_key == "familie_select":
        regler.select(C.FAM_LATIN)
    elif isinstance(spec.default, bool):
        regler.set_value(not regler.value)
    else:
        regler.set_value(spec.hi if regler.value != spec.hi else spec.lo)
    at.run()


def test_gesperrte_regler_gibt_es_nur_wo_sie_wirkungslos_waeren():
    """Zufalls-Seed beim Handbeispiel und beim Sinz-Zähler, „Eingänge einfrieren“ bei Familien ohne Eingänge: gesperrt (nicht ausgeblendet, damit ihr Zustand erhalten bleibt)."""
    at = _app()
    assert _regler(at, "seed_input").proto.disabled and _regler(at, "eingefroren_toggle").proto.disabled
    for familie in C.FAMILIEN:
        _regler(at, "familie_select").select(familie).run()
        assert _regler(at, "seed_input").proto.disabled == (familie in (C.FAM_HAND, C.FAM_SINZ)), familie
        assert _regler(at, "eingefroren_toggle").proto.disabled == (familie not in C.HAT_EINGAENGE), familie


@pytest.mark.parametrize("name,state_key", [
    ("Handbeispiel Teil 1", "familie_select"), ("Färbung", "seed_input"), ("Handbeispiel Teil 1", "runden_slider"), ("Vertex Cover mit Zähler", "eingefroren_toggle"),
    ("Vertex Cover mit Zähler", "n_vc_sinz"), ("Färbung", "n_faerbung"), ("Sinz-Zähler k = 1", "n_sinz"), ("Sinz-Zähler k = 1", "eingefroren_toggle"),
])
def test_jede_aenderung_eines_reglers_hebt_die_hervorhebung_auf(name, state_key):
    at = _app()
    at.sidebar.button(key=f"preset_{name}").click().run()
    assert _typen(at)[name] == "primary"
    _aendere(at, state_key)
    assert not at.exception, [str(e) for e in at.exception]
    assert "primary" not in _typen(at).values(), (name, state_key)
    at.sidebar.button(key=f"preset_{name}").click().run()          # erneutes Anklicken markiert wieder
    assert _typen(at)[name] == "primary"


@pytest.mark.parametrize("familie", [f for f in C.FAMILIEN if f in C.N_GRENZEN])
def test_jede_familie_zeichnet_genau_ihren_groessenregler_ohne_fehler(familie):
    at = _app()
    _regler(at, "familie_select").select(familie).run()
    assert not at.exception, [str(e) for e in at.exception]
    keys = {s.key for s in at.sidebar.slider}
    assert P.n_key(familie) in keys and not ({P.n_key(f) for f in C.N_GRENZEN} - {P.n_key(familie)}) & keys
