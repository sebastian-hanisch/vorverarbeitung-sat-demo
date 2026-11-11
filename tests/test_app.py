"""End-to-end Smoke-Test via Streamlits offiziellem AppTest-Framework: laedt app.py mit den
Standardeinstellungen, klickt jeden Preset-Button und faehrt jeden Slider an seine Grenzen und prueft, dass
kein Python-Fehler auftritt - insbesondere `streamlit.errors.StreamlitDuplicateElementId` (mehrere
st.plotly_chart-Aufrufe ohne eindeutiges key= koennen zufaellig identischen Inhalt rendern und kollidieren)
und `StreamlitAPIException` bei Slidern mit berechneten Grenzen (min == max)."""

import os

from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))  # unter Last (parallele Läufe) reichen 180 s nicht immer; Umgebungsvariable zum Anpassen
AUTOPLAY_MARKER = "\u25b6"  # Auto-Play-Buttons (Animation mit sleep) im Smoke-Test auslassen


def _fresh_app() -> AppTest:
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def test_app_loads_without_exception():
    _fresh_app()


def test_every_button_click_does_not_raise():
    ersteller = _fresh_app()
    labels = [b.label for b in ersteller.button]
    gesperrt = {i for i, b in enumerate(ersteller.button) if b.proto.disabled}      # beim Handbeispiel gesperrt: Zufalls-Knopf, verkleinerte Messreihe
    assert labels, "keine Buttons gefunden"
    for index, label in enumerate(labels):
        if AUTOPLAY_MARKER in label or index in gesperrt:
            continue
        at = _fresh_app()
        at.button[index].click().run(timeout=TIMEOUT)
        assert not at.exception, (label, [str(e) for e in at.exception])


def test_every_slider_at_its_min_and_max_does_not_raise():
    labels = [s.label for s in _fresh_app().slider]
    assert labels, "keine Slider gefunden"
    for index, label in enumerate(labels):
        for edge in ("min", "max"):
            at = _fresh_app()
            slider = at.slider[index]
            value = slider.min if edge == "min" else slider.max
            if isinstance(slider.value, int):
                value = int(value)
            slider.set_value(value).run(timeout=TIMEOUT)
            assert not at.exception, (label, edge, [str(e) for e in at.exception])


def test_verkleinerte_messreihe_live_rechnet_vier_formeln():
    """Zufalls-3-SAT n = 30: der Knopf rechnet vier Formeln vorher und nachher, die Tabelle und das Verdikt erscheinen, kein Fehler."""
    at = _fresh_app()
    at.sidebar.selectbox(key="familie_select").select("zufall").run(timeout=TIMEOUT)
    at.sidebar.slider(key="n_zufall").set_value(30).run(timeout=TIMEOUT)
    live = next(b for b in at.main.button if b.key == "live_knopf")
    assert not live.proto.disabled
    live.click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    texte = " ".join(x.value for x in at.info) + " ".join(x.value for x in at.success)
    assert "von 4 Formeln sinken die Konflikte" in texte
    assert not any("Noch nicht gerechnet" in x.value for x in at.info if "Verkleinerte" in x.value)


def test_schritt_regler_am_handbeispiel_zeigt_die_formeln():
    at = _fresh_app()
    at.slider(key="schritt_slider").set_value(2).run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    text = " ".join(m.value for m in at.markdown)
    assert "Schritt 2: Subsumption (Runde 1)" in text and "(x2 ∨ x4) subsumiert (x2 ∨ x3 ∨ x4)" in text and "(x2 ∨ x4)" in text


def test_reiter_elimination_zeigt_das_handbeispiel_teil_2():
    at = _fresh_app()
    nachher = next(m.value for m in at.markdown if m.value.startswith("**Formel nachher:**"))
    assert sorted(nachher.removeprefix("**Formel nachher:** ").split(" ∧ ")) == sorted(["(¬x1 ∨ ¬x2)", "(¬x1 ∨ ¬x3)", "(¬x2 ∨ ¬x3)", "(x1 ∨ x2 ∨ x3)"])
    assert any("binomiale Kodierung" in s.value for s in at.success)
    at.slider(key="sinz_n").set_value(8).run(timeout=TIMEOUT)
    assert not at.exception
    at.slider(key="sinz_n").set_value(3).run(timeout=TIMEOUT)      # k darf nicht über n − 1 stehen bleiben
    assert not at.exception, [str(e) for e in at.exception]
    at.toggle(key="sinz_fest").set_value(False).run(timeout=TIMEOUT)
    assert not at.exception and any("Nichts war eingefroren" in w.value for w in at.warning)
