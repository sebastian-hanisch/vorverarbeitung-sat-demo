"""Vorverarbeitung – kleiner heißt nicht weniger Konflikte - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Siebtes Stück der Linie „SAT und Constraint Programming“: die Formel vor der Suche verkleinern (Einheiten, Subsumption, Verstärkung, Variablenelimination) und nachsehen, was das der Suche bringt.
Aufbau und Regeln stehen im DEMO-PLAYBOOK.md (§2).

Lauffähig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

import vvs_algorithm as A
import vvs_constants as C
import vvs_evaluation as ev
import vvs_fortschritt as F
import vvs_scenario as S
import vvs_texte as T
from vvs_layout import dunkles_design, kopf_css
from vvs_presets import (
    bounds,
    init_n,
    init_session_state_defaults,
    load_permalink_settings,
    n_key,
    randomize_seed,
    sidebar_presets,
    sync_query_params,
)
from vvs_visualization import build_messreihe, build_prozent, build_streuung, build_verlauf

st.set_page_config(page_title="Vorverarbeitung SAT – Sebastian Hanisch", layout="wide")

MAX_EREIGNISSE = 25      # Ereignisse je Schritt, die die Ansicht ausschreibt; der Rest wird gezählt


@st.cache_data(show_spinner=False, max_entries=6)
def _vorverarbeitet(familie, n, seed, eingefroren, runden):
    a = ev.aufgabe_von(ev.Settings(familie, n, seed, eingefroren, runden))
    return a, ev.vorverarbeite_aufgabe(a, eingefroren=eingefroren, runden=runden, protokoll=True)


@st.cache_data(show_spinner=False, max_entries=6)
def _analyse(familie, n, seed, eingefroren, runden):
    a, v = _vorverarbeitet(familie, n, seed, eingefroren, runden)
    return ev.analysiere(a, v)


@st.cache_data(show_spinner=False)
def _reihe():
    daten = ev.lade_messreihen()
    return daten, [ev.kennzahlen(z) for z in daten["zeilen"]]


@st.cache_data(show_spinner=False, max_entries=8)
def _sinz(n, k, eingefroren):
    return ev.sinz_experiment(n, k, eingefroren)


def _d(x):
    """Änderung mit ASCII-Vorzeichen (Streamlit erkennt die Richtung der Metrik-Änderung am führenden „-“ bzw. „+“)."""
    return ("+" if x > 0 else "") + ev.de(x).replace("−", "-")


def _bool_text(b):
    return "ja" if b else "nein"


def _formel_zeilen(klauseln):
    return "  \n".join(f"{i + 1}. {S.klausel_text(c)}" for i, c in enumerate(klauseln)) if klauseln else "_leer: erfüllt_"


# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in vvs_layout.py).
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("🧹 Vorverarbeitung – kleiner heißt nicht weniger Konflikte")
st.markdown(
    """
Ein CDCL-Löser (Stück 1 der Linie) **lernt während der Suche** und lässt die Formel, wie sie ist. Die **Vorverarbeitung** macht es umgekehrt: Sie verkleinert die Formel **vor** der Suche.
Vier Schritte stehen zur Wahl: **Einheiten** setzen, von kürzeren Klauseln **subsumierte** Klauseln streichen, Klauseln **verstärken**, Variablen **eliminieren**, solange dadurch nicht mehr Klauseln entstehen als wegfallen.
Eliminierte Variablen werden nie gelöst, sondern aus dem Modell der kleineren Formel **zurückgerechnet** und gegen die Originalklauseln geprüft. Die Demo zählt Variablen, Klauseln, Konflikte, Propagationen
und die Kosten der Vorverarbeitung (berechnete Resolventen), keine Sekunden als Messgröße: **In der Messreihe wird die Formel kleiner und die Propagationen sinken im Median (nach der Spannenregel erkennbar in fünf von sieben Zeilen); ein Unterschied in den Konflikten ist nicht erkennbar.**

Weiter unten: vier Reiter (**Schritt für Schritt**, **Elimination und Rekonstruktion**, **Vorher und nachher**, **Inprocessing**), die **Erklärtabelle**, der Abschnitt **🚧 Wo die Annahmen enden** und der Expander **📐 Mathematische Formulierung**.
"""
)

with st.expander("So funktioniert die Vorverarbeitung", expanded=True):
    st.markdown(
        """
1. **Einheitspropagation:** Eine Klausel mit einem einzigen Literal erzwingt es. Erfüllte Klauseln fallen weg, das falsche Literal fällt aus den übrigen. Das wiederholt sich bis zum Fixpunkt.
2. **Subsumption:** Enthält eine Klausel A nur Literale einer Klausel B, ist B überflüssig: jede Belegung, die A erfüllt, erfüllt auch B.
3. **Verstärkung:** Subsumiert die Resolvente zweier Klauseln eine ihrer Eltern, verliert diese das Literal, auf dem resolviert wurde.
4. **Begrenzte Elimination:** Von der Variable mit dem kleinsten Produkt aus positiven und negativen Vorkommen werden alle Resolventen gebildet. Sind es **nicht mehr** als Klauseln mit dieser Variable und
   **keine länger als 20 Literale**, ersetzen sie diese Klauseln.
5. **Rekonstruktion:** Ein Modell der kleineren Formel wird zu einem der ursprünglichen: Die eliminierten Variablen werden **rückwärts** in der Reihenfolge der Elimination belegt, zunächst falsch, und wahr,
   wenn eine gespeicherte Klausel, in der sie positiv vorkam, sonst unerfüllt bliebe.
        """
    )

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Preset ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Aufgabe (Ergebnis und Reiter „Schritt für Schritt“)**")
    familie = st.selectbox("Aufgabe", C.FAMILIEN, format_func=C.FAMILIEN_NAMEN.get, key="familie_select",
                           help="Welche Formel die Abschnitte „Ergebnis“ und „Schritt für Schritt“ untersuchen. Der Reiter „Vorher und nachher“ zeigt eine vorgerechnete Messreihe über mehrere Familien.")
    if familie in C.N_GRENZEN:
        init_n(familie)
        n = st.slider(C.N_NAMEN[familie], *bounds(n_key(familie)), key=n_key(familie),
                      help="Größe der Aufgabe: Knoten, Variablen, Ordnung des Quadrats oder Zählereingänge. Der Regler gilt nur für die gewählte Aufgabe.")
    else:
        n = 0
    hat_zufall = familie not in (C.FAM_HAND, C.FAM_SINZ)
    seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1, disabled=not hat_zufall,
                           help="Wählt Graph, Formel bzw. Quadrat. Handbeispiel und Sinz-Zähler sind fest und kennen keinen Zufall.")
    st.button("🎲 Neue Formel generieren", width="stretch", on_click=randomize_seed, disabled=not hat_zufall)
    st.markdown("**Vorverarbeitung**")
    hat_eingaenge = familie in C.HAT_EINGAENGE
    eingefroren = st.toggle("Eingänge einfrieren", key="eingefroren_toggle", disabled=not hat_eingaenge,
                            help="Nur bei Zählern und Vertex Cover: Die Variablen der Aufgabe (Zählereingänge, Knoten) werden nie eliminiert, nur die Hilfsvariablen des Zählers. Sonst gesperrt.")
    runden = st.slider("Runden (höchstens)", *bounds("runden_slider"), key="runden_slider",
                       help="Eine Runde besteht aus Subsumption, Verstärkung, Einheiten und einem Eliminationsdurchlauf. Das Verfahren endet früher, wenn eine Runde nichts mehr ändert.")

sync_query_params({"familie_select": familie, "seed_input": int(seed), "eingefroren_toggle": bool(eingefroren), "runden_slider": int(runden),
                   **({n_key(familie): int(n)} if familie in C.N_GRENZEN else {})})

eingefroren = bool(eingefroren) and hat_eingaenge
a, v = _vorverarbeitet(familie, int(n), int(seed), eingefroren, int(runden))
with st.spinner("Rechne den Löser auf der Formel vorher und nachher …"):
    analyse = _analyse(familie, int(n), int(seed), eingefroren, int(runden))
vor, nach = analyse["vor"], analyse["nach"]

# --- Ergebnis ------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Ergebnis")
st.caption(f"Aufgabe: {a.name}" + (f", Zufalls-Seed {int(seed)}" if hat_zufall else "") + f". Eingänge eingefroren: {_bool_text(eingefroren)}. Konfliktbudget des Lösers: {ev.de(C.LIVE_BUDGET)}.")
m1, m2, m3, m4 = st.columns(4)
# Delta immer als „mein Wert minus Referenz“; die Farbe regelt delta_color="inverse" (Vorzeichen-Falle, DEMO-PLAYBOOK §2).
m1.metric("Variablen nachher", ev.de(v.variablen_neu), delta=f"{_d(v.variablen_neu - v.variablen_alt)} gegen vorher ({ev.de(v.variablen_alt)})", delta_color="inverse")
m2.metric("Klauseln nachher", ev.de(len(v.klauseln)), delta=f"{_d(len(v.klauseln) - len(v.klauseln_alt))} gegen vorher ({ev.de(len(v.klauseln_alt))})", delta_color="inverse")
m3.metric("Antwort vorher / nachher", f"{ev.antwort_text(vor['antwort'])} / {ev.antwort_text(nach['antwort'])}", delta="gleich" if analyse["antworten_gleich"] else "abweichend", delta_color="off")
m4.metric("Modellprüfung", "nicht nötig" if analyse["modell_ok"] is None else ("bestanden" if analyse["modell_ok"] else "FEHLER"),
          delta="rekonstruiertes Modell gegen die Originalklauseln" if analyse["modell_ok"] is not None else "unerfüllbar oder Budget erreicht", delta_color="off")
st.plotly_chart(build_prozent([("Variablen", v.variablen_alt, v.variablen_neu), ("Klauseln", len(v.klauseln_alt), len(v.klauseln)),
                               ("Konflikte (ein Lauf)", vor["konflikte"], nach["konflikte"]), ("Propagationen (ein Lauf)", vor["propagationen"], nach["propagationen"])]),
                width="stretch", key="main_chart")
st.caption(f"Kosten der Vorverarbeitung: {ev.de(v.zaehler['resolventen'])} Resolventen berechnet (auch verworfene und tautologische), {ev.de(v.zaehler['vergleiche'])} Klausel-Vergleiche, "
           f"Runden: {v.zaehler['runden']}; {v.zaehler['einheiten']} Einheiten, {v.zaehler['subsumiert']} subsumierte, {v.zaehler['verstaerkt']} verstärkte Klauseln, "
           f"{v.zaehler['eliminiert']} eliminierte Variablen ({v.zaehler['abgelehnt']} Versuche abgelehnt).")
kind, text = ev.verdict_formel(vor, nach, v, analyse["modell_ok"], analyse["antworten_gleich"])
getattr(st, kind)(text)

# --- Kernfrage ------------------------------------------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage: Wird die Suche durch die kleinere Formel schneller?")
daten, kennz = _reihe()
kind, text = ev.verdict_reihe(kennz)
getattr(st, kind)(text)
st.caption("Grundlage: die vorgerechnete Messreihe im Reiter „Vorher und nachher“ (zehn feste Formeln je Zeile, fünf Löser-Seeds, Zähler statt Sekunden).")

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["🔬 Schritt für Schritt", "🔬 Elimination und Rekonstruktion", "🔬 Vorher und nachher", "🔬 Inprocessing"])

# --- Reiter 1: Schritt für Schritt ---------------------------------------------------------------------------------------------------------

with tab1:
    st.caption("Die Formel der Seitenleiste, Schritt für Schritt: je Schritt die Zähler, die Begründung jeder Regel und (bei höchstens "
               f"{A.SNAPSHOT_MAX} Klauseln) die Formel. Voreinstellung ist das Handbeispiel Teil 1.")
    phasen = v.phasen
    st.session_state["schritt_slider"] = min(int(st.session_state.get("schritt_slider", 1)), len(phasen) - 1)
    schritt = st.slider("Schritt", 0, len(phasen) - 1, key="schritt_slider", help="0 ist die Ausgangsformel; danach folgen die Einheiten und je Runde Subsumption, Verstärkung, Einheiten, Elimination.")
    p = phasen[schritt]
    titel = T.SCHRITT_TITEL[p["schritt"]] + (f" (Runde {p['runde']})" if p["runde"] else "")
    st.markdown(f"**Schritt {schritt}: {titel}**")
    c1, c2 = st.columns(2)
    c1.metric("Klauseln", ev.de(p["klauseln_nach"]), delta=f"{_d(p['klauseln_nach'] - p['klauseln_vor'])} in diesem Schritt", delta_color="inverse")
    c2.metric("Variablen", ev.de(p["variablen_nach"]), delta=f"{_d(p['variablen_nach'] - p['variablen_vor'])} in diesem Schritt", delta_color="inverse")
    if p["schritt"] == "start":
        st.markdown("Ausgangsformel (doppelte Literale, Tautologien und doppelte Klauseln sind schon gestrichen).")
    elif not p["ereignisse"]:
        st.info("In diesem Schritt gibt es nichts zu tun.")
    else:
        for e in p["ereignisse"][:MAX_EREIGNISSE]:
            st.markdown("- " + T.ereignis_text(e))
        if len(p["ereignisse"]) > MAX_EREIGNISSE:
            st.caption(f"… und {len(p['ereignisse']) - MAX_EREIGNISSE} weitere Ereignisse in diesem Schritt.")
    if p["formel"] is not None:
        vorher = phasen[schritt - 1]["formel"] if schritt > 0 else None
        f1, f2 = st.columns(2)
        with f1:
            st.markdown("**Formel vorher**")
            st.markdown(_formel_zeilen(vorher) if schritt > 0 and vorher is not None else "_(Ausgangsformel)_")
        with f2:
            st.markdown("**Formel nachher**")
            st.markdown(_formel_zeilen(p["formel"]))
    else:
        st.caption(f"Die Formel hat mehr als {A.SNAPSHOT_MAX} Klauseln und wird nicht ausgeschrieben.")
    st.plotly_chart(build_verlauf(phasen), width="stretch", key="verlauf_chart")
    tabelle = [{"Nr": i, "Schritt": T.SCHRITT_TITEL[q["schritt"]], "Runde": q["runde"], "Klauseln vorher": q["klauseln_vor"], "Klauseln nachher": q["klauseln_nach"],
                "Variablen vorher": q["variablen_vor"], "Variablen nachher": q["variablen_nach"], "Ereignisse": len(q["ereignisse"])} for i, q in enumerate(phasen)]
    st.dataframe(pd.DataFrame(tabelle), hide_index=True, width="stretch")
    if v.einheiten:
        gesetzt = ", ".join(f"x{x} = {'wahr' if w else 'falsch'}" for x, w in sorted(v.einheiten.items())[:20])
        st.markdown(f"Durch Einheiten festgelegt: {gesetzt}" + (f" … ({len(v.einheiten)} Variablen)" if len(v.einheiten) > 20 else "") + ".")
    if v.stapel:
        st.markdown("Eliminationsstapel (Reihenfolge der Elimination): " + ", ".join(f"x{x}" for x, _ in v.stapel[:30]) + (" …" if len(v.stapel) > 30 else "") + ".")
    if familie == C.FAM_HAND and not v.klauseln:
        st.success("Die Formel ist leer, also erfüllt. Festgelegt sind x1 und x4 (wahr); x2 und x3 sind frei. Aufzählung aller 16 Belegungen: 4 Modelle, alle mit x1 = x4 = wahr.")

# --- Reiter 2: Elimination und Rekonstruktion -----------------------------------------------------------------------------------------------

with tab2:
    st.caption("Der Sinz-Zähler „höchstens k von n“ (plus die Klausel „mindestens eines“) mit seinen Hilfsvariablen, vorverarbeitet. Dieser Reiter hat eigene Regler und folgt nicht der Seitenleiste.")
    s1, s2, s3 = st.columns(3)
    sn = s1.slider("Eingänge n", C.SINZ_N_MIN, C.SINZ_N_MAX, 3, key="sinz_n", help="n = 3 und k = 1 ist das Handbeispiel Teil 2.")
    st.session_state["sinz_k"] = max(1, min(int(st.session_state.get("sinz_k", 1)), int(sn) - 1, C.SINZ_K_MAX))     # k bleibt innerhalb der Grenzen, wenn n sinkt
    sk = s2.slider("Höchstens k wahr", 1, min(C.SINZ_K_MAX, int(sn) - 1), key="sinz_k", help="k ist höchstens 3 und kleiner als n.")
    sf = s3.toggle("Eingänge einfrieren", True, key="sinz_fest", help="Aus: auch die Eingänge x1 bis xn dürfen eliminiert werden; dann verschwindet die Zählerstruktur.")
    x = _sinz(int(sn), int(sk), bool(sf))
    xv = x["v"]
    st.markdown("**Zählerformel vorher** (Hilfsvariablen ab x" + str(int(sn) + 1) + "): " + S.formel_text(xv.klauseln_alt))
    for e in [e for ph in xv.phasen for e in ph["ereignisse"] if e["art"] == "elimination"]:
        st.markdown("- " + T.ereignis_text(e))
    st.markdown("**Formel nachher:** " + S.formel_text(xv.klauseln))
    kind, text = ev.verdict_sinz(x)
    getattr(st, kind)(text)
    st.markdown("**Rückrechnung:** jedes Modell der vereinfachten Formel wird zu einem Modell der Originalformel ergänzt (eliminierte Variablen rückwärts, zunächst falsch, wahr wenn eine gespeicherte positive Klausel sonst unerfüllt bliebe).")
    zeilen = []
    for m in x["modelle"]:
        zeilen.append({"Modell der vereinfachten Formel": ", ".join(f"x{i} = {int(w)}" for i, w in sorted(m["reduziert"].items())) or "(keine Variable übrig)",
                       "Rückgerechnet (alle Variablen)": ", ".join(f"x{i} = {int(w)}" for i, w in sorted(m["voll"].items())),
                       "erfüllt die Originalklauseln": "ja" if m["ok"] else "NEIN"})
    st.dataframe(pd.DataFrame(zeilen), hide_index=True, width="stretch")
    st.caption("Die Rückrechnung ist nicht eindeutig umkehrbar: Aus einem Modell der vereinfachten Formel entsteht **ein** Modell der Originalformel, nicht jedes. Die Elimination erhält die Erfüllbarkeit, nicht die Zahl der Modelle.")
    if "sinz" in daten:
        st.markdown("**Gemessen für n = 3 bis 8 und k = 1 bis 3** (Eingänge eingefroren, `vvs_messreihen.json`):")
        sz = [{"n": r["n"], "k": r["k"], "Variablen vorher → nachher": f"{r['variablen'][0]} → {r['variablen'][1]}", "Klauseln vorher → nachher": f"{r['klauseln'][0]} → {r['klauseln'][1]}",
               "binomiale Kodierung (Klauseln)": r["binomial_klauseln"], "Ergebnis = binomial": _bool_text(r["gleich_binomial"]), "Resolventen berechnet": r["resolventen"]} for r in daten["sinz"]]
        st.dataframe(pd.DataFrame(sz), hide_index=True, width="stretch")

# --- Reiter 3: Vorher und nachher ----------------------------------------------------------------------------------------------------------

with tab3:
    st.caption(f"**Vorgerechnete Messreihe** (`vvs_messreihen.json`, Skript `tools/messreihe.py`; nicht live): je Zeile {len(C.MESS_SEEDS)} feste Formeln (Zufalls-Seeds {C.MESS_SEEDS[0]} bis {C.MESS_SEEDS[-1]}), "
               f"{len(C.LOESER_SEEDS)} Löser-Seeds (zufällige Anfangsaktivität), Konfliktbudget {ev.de(daten['budget'])}. Wert je Formel: Median über die Löser-Seeds; Wert der Zeile: Median über die Formeln.")
    zeilen = []
    for z in kennz:
        zeilen.append({
            "Zeile": z["name"], "Formeln (erfüllbar / unerfüllbar)": f"{z['formeln']} ({z['erfuellbar']} / {z['unerfuellbar']})",
            "Variablen (Mittel)": f"{ev.de(z['variablen'][0])} → {ev.de(z['variablen'][1])}", "Klauseln (Mittel)": f"{ev.de(z['klauseln'][0])} → {ev.de(z['klauseln'][1])}",
            "Konflikte (Median)": f"{ev.de(z['konflikte'][0], 1 if z['konflikte'][0] % 1 else 0)} → {ev.de(z['konflikte'][1], 1 if z['konflikte'][1] % 1 else 0)}",
            "Spanne Löser-Seeds vorher": f"{ev.de(z['konflikte_spanne']['vor'][0])} bis {ev.de(z['konflikte_spanne']['vor'][1])}",
            "Spanne Löser-Seeds nachher": f"{ev.de(z['konflikte_spanne']['nach'][0])} bis {ev.de(z['konflikte_spanne']['nach'][1])}",
            "Propagationen (Median)": f"{ev.de(z['propagationen'][0])} → {ev.de(z['propagationen'][1])}",
            "Resolventen berechnet (Median)": ev.de(z["resolventen"]), "Fehler (Antwort / Modell)": f"{z['antwortfehler']} / {z['modellfehler']}"})
    st.dataframe(pd.DataFrame(zeilen), hide_index=True, width="stretch")
    st.plotly_chart(build_messreihe(kennz), width="stretch", key="reihe_chart")
    st.caption("Balken: Änderung des Wertes nachher gegenüber vorher in Prozent (Variablen, Klauseln: Summe über die Formeln; Propagationen, Konflikte: Median). Fehlt ein Balken, war der Wert vorher 0.")
    kind, text = ev.verdict_reihe(kennz)
    getattr(st, kind)(text)
    zeile = st.selectbox("Eine Zeile genauer ansehen", [z["id"] for z in kennz], format_func=lambda i: next(z["name"] for z in kennz if z["id"] == i), key="zeilen_wahl")
    zk = next(z for z in kennz if z["id"] == zeile)
    for kind, text in (ev.verdict_zeile(zk), ev.verdict_konflikte(zk)):
        getattr(st, kind)(text)
    st.caption(f"Konflikte je Formel in dieser Zeile: weniger in {zk['konflikte_weniger_mehr_gleich'][0]}, mehr in {zk['konflikte_weniger_mehr_gleich'][1]}, gleich in {zk['konflikte_weniger_mehr_gleich'][2]} "
               f"von {zk['formeln']} Formeln (Median über die Löser-Seeds). Abgebrochene Läufe (Budget erreicht): {zk['abgebrochen']}.")
    st.plotly_chart(build_streuung(next(r for r in daten["zeilen"] if r["id"] == zeile)["formeln"]), width="stretch", key="streuung_chart")

    st.markdown("---")
    st.markdown("**Verkleinerte Messreihe live** für die Aufgabe der Seitenleiste")
    st.caption(f"{len(C.LIVE_SEEDS)} feste Formeln (Zufalls-Seeds {C.LIVE_SEEDS[0]} bis {C.LIVE_SEEDS[-1]}) mit der Größe aus der Seitenleiste, ein Löser-Seed, Konfliktbudget {ev.de(C.LIVE_BUDGET)}. "
               "Ohne Streubreite: nur eine Zählung, kein Verdikt über einen Unterschied.")
    live_moeglich = familie not in (C.FAM_HAND, C.FAM_SINZ)
    if st.button("▶️ Verkleinerte Messreihe rechnen", key="live_knopf", disabled=not live_moeglich):
        with F.fortschrittsbalken("Rechne vier Formeln vorher und nachher, fertige Formeln") as melde:
            formeln_live, sek_live = F.reihe(familie, int(n), eingefroren, int(runden), melde)
        st.session_state["live"] = ((familie, int(n), eingefroren, int(runden)), formeln_live, sek_live)
    gespeichert = st.session_state.get("live")
    if not live_moeglich:
        st.info("Handbeispiel und Sinz-Zähler sind feste Formeln: die verkleinerte Messreihe braucht eine Zufallsfamilie.")
    elif gespeichert and gespeichert[0] == (familie, int(n), eingefroren, int(runden)):
        formeln = gespeichert[1]
        st.dataframe(pd.DataFrame([{"Zufalls-Seed": f["seed"], "Variablen": f"{f['variablen'][0]} → {f['variablen'][1]}", "Klauseln": f"{f['klauseln'][0]} → {f['klauseln'][1]}",
                                    "Antwort": ev.antwort_text(f["antwort_vor"][0]) + " / " + ev.antwort_text(f["antwort_nach"][0]),
                                    "Konflikte": f"{ev.de(f['konflikte_vor'][0])} → {ev.de(f['konflikte_nach'][0])}", "Propagationen": f"{ev.de(f['propagationen_vor'][0])} → {ev.de(f['propagationen_nach'][0])}",
                                    "Resolventen berechnet": ev.de(f["resolventen"])} for f in formeln]), hide_index=True, width="stretch")
        kind, text = ev.verdict_live(formeln)
        getattr(st, kind)(text)
        st.caption(f"Rechenzeit dieses Laufs: {gespeichert[2]:.0f} s (nur zur Orientierung, kein Messwert der Demo; bei schon zwischengespeicherten Formeln die Zeit ihrer ersten Rechnung).")
    else:
        st.info("Noch nicht gerechnet: „Verkleinerte Messreihe rechnen“ startet die Reihe für die Aufgabe der Seitenleiste.")

# --- Reiter 4: Inprocessing ----------------------------------------------------------------------------------------------------------------

with tab4:
    st.markdown(
        """
**Inprocessing** heißt: Vereinfachen **während** der Suche statt nur davor. Die Beschreibung von CaDiCaL und Kissat zur SAT Competition 2025 (Biere, Faller, Fleury, Froleyks, Pollitt) nennt unter den
Techniken unter anderem **Vivification**, **Variablenaddition** (bounded variable addition) und **Äquivalenz-Sweeping** (clausal equivalence sweeping). Mehr belegt die Demo nicht: Dieser Reiter enthält
**keine Messung und keine Wirkungsaussage**; wie stark welche Technik wirkt, wurde hier nicht untersucht. Auch zu Probing, zum Wechsel zwischen stabilem und fokussiertem Modus, zu Rephasing und zur Rolle der begrenzten Variablenelimination
in modernen Lösern macht die Demo keine Aussage (nicht aus einer gelesenen Quelle).

**Vivification an einer Klausel** (kleine Rechnung): Die Literale einer Klausel werden nacheinander falsch gesetzt, nach jedem Schritt folgt die Einheitspropagation auf den **übrigen** Klauseln.
Gibt es einen Widerspruch, folgt aus den übrigen Klauseln schon die Klausel aus den bisher gesetzten Literalen; sie ersetzt die ursprüngliche. Wird ein späteres Literal durch die Propagation wahr, genügt die Klausel bis dorthin;
wird es falsch, entfällt es. Die Modelle der Formel ändern sich dabei nicht.
        """
    )
    formel = S.HAND_TEIL3
    st.markdown("Formel des Handbeispiels Teil 3: " + S.formel_text(formel))
    wahl = st.selectbox("Klausel, die vivifiziert wird", range(len(formel)), format_func=lambda i: S.klausel_text(formel[i]), key="viv_klausel")
    r = A.vivifiziere(formel, formel[int(wahl)])
    for s in r.schritte:
        if s["ereignis"] == "gesetzt":
            zeile = f"{S.lit_text(-s['literal'])} wird gesetzt (das Literal {S.lit_text(s['literal'])} der Klausel wird falsch)."
            if s["geschlossen"]:
                zeile += " Es folgt: " + ", ".join(f"{S.lit_text(l)} (aus {S.klausel_text(c)})" for l, c in s["geschlossen"]) + "."
            if s["konflikt"] is not None:
                zeile += f" **Widerspruch:** {S.klausel_text(s['konflikt'])} ist verletzt."
        elif s["ereignis"] == "folgt_wahr":
            zeile = f"{S.lit_text(s['literal'])} folgt schon als wahr: die Klausel genügt bis hierher."
        else:
            zeile = f"{S.lit_text(s['literal'])} folgt als falsch: das Literal entfällt."
        st.markdown("- " + zeile)
    if r.neue_klausel != r.klausel:
        st.success(f"{S.klausel_text(r.klausel)} wird zu **{S.klausel_text(r.neue_klausel)}**. Die Modelle der Formel bleiben unverändert (Aufzählung aller 16 Belegungen im Test: 12 gleich 12).")
    else:
        st.info(f"{S.klausel_text(r.klausel)} bleibt unverändert: ihre Literale lassen sich hier nicht kürzen.")

# --- Erklärtabelle -------------------------------------------------------------------------------------------------------------------------

st.markdown("---")
st.subheader("📖 Erklärtabelle")
st.markdown(
    """
| Verfahren | Was es tut | Wirkung auf Erfüllbarkeit und Modelle |
|---|---|---|
| **Einheitspropagation** | Eine Klausel mit einem Literal erzwingt es; erfüllte Klauseln fallen, das falsche Literal fällt aus den übrigen. | Erhält die Modelle (die erzwungenen Variablen sind in jedem Modell festgelegt). |
| **Subsumption** | Klausel B entfällt, wenn eine Klausel A nur Literale von B enthält. | Erhält die Modellmenge. |
| **Verstärkung** | Subsumiert die Resolvente von A und B das B, verliert B das Literal, auf dem resolviert wurde. | Erhält die Modellmenge (die neue Klausel folgt aus der Formel). |
| **Variablenelimination** | Alle Klauseln mit x werden durch ihre Resolventen auf x ersetzt, wenn das nicht mehr Klauseln ergibt und keine Resolvente länger als 20 ist. | Erhält die Erfüllbarkeit, nicht die Modellmenge. |
| **Rekonstruktion** | Eliminierte Variablen rückwärts belegen: zunächst falsch, wahr, wenn eine gespeicherte positive Klausel sonst unerfüllt bliebe. | Macht aus einem Modell der kleinen Formel **ein** Modell der Originalformel. |
| **Vivification** (Inprocessing) | Literale einer Klausel falsch setzen, propagieren, bei Widerspruch kürzen. | Erhält die Modellmenge. |
"""
)

# --- Grenzen -------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist |
|---|---|
| **Einfache Fassung.** | Gebaut sind Einheiten, Subsumption, Verstärkung und die begrenzte Variablenelimination (Resolventen höchstens so viele wie entfernte Klauseln, Länge höchstens 20, höchstens 5 Runden). Entfernen blockierter Klauseln, Äquivalenzerkennung, Probing und Variablenaddition fehlen; die Demo urteilt nicht über moderne Vorverarbeiter. |
| **Zählgrößen statt Zeit.** | Konflikte, Propagationen und berechnete Resolventen sind Zähler. Wie lange die Vorverarbeitung selbst oder der ganze Lauf dauert, ist nicht gemessen; ein Konflikt kostet auf der kleineren Formel nicht dasselbe wie auf der größeren. |
| **Ein Löser, fünf Seeds.** | Die Konflikte stammen vom Python-CDCL dieser Demo (VSIDS, Luby-Neustarts, Phasenspeicher). Die Spannen der fünf Löser-Seeds erfassen die Streuung der Suche bei **denselben** Formeln, nicht die zwischen verschiedenen Formeln. |
| **Zehn Formeln je Zeile.** | Die Messreihe gilt für die gezeigten Familien und Größen; für andere Größen, Familien oder Industrieformeln sagen die Zahlen nichts. |
| **Nichts eingefroren heißt: alles darf fallen.** | Ohne Einfrieren eliminiert die Vorverarbeitung auch die Variablen der Aufgabe (Knoten, Zählereingänge); die beiden Zeilen je Zählerfamilie trennen das. |
| **Elimination erhält nur die Erfüllbarkeit.** | Nach der Vorverarbeitung sagt die Zahl der Modelle der kleinen Formel nichts über die der Originalformel. |
| **Inprocessing ist nur erklärt.** | Der Reiter enthält keine Messung. |
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Lesehilfe.** Gegeben ist eine Formel $F$ in konjunktiver Normalform (eine Menge von Klauseln $C$, jede eine Menge von Literalen). Gesucht ist eine kleinere Formel $F'$ und eine Vorschrift, die jedes Modell von $F'$
zu einem Modell von $F$ ergänzt. Die Vorverarbeitung erhält die **Erfüllbarkeit**.

| Symbol | Bedeutung |
|---|---|
| $F$, $F'$ | Formel vorher und nachher |
| $x$ | eine Variable; $x$ und $\bar x$ sind ihre Literale |
| $F_x$, $F_{\bar x}$ | Klauseln von $F$ mit dem Literal $x$ bzw. $\bar x$ |
| $A \otimes_x B$ | Resolvente zweier Klauseln auf $x$ |
| $R(x)$ | Menge der nicht tautologischen Resolventen auf $x$ |
| $m$ | größte erlaubte Länge einer Resolvente (hier 20) |

**Resolvente.** Für $A \in F_x$ und $B \in F_{\bar x}$:

$$A \otimes_x B = (A \setminus \{x\}) \cup (B \setminus \{\bar x\}).$$

**Eliminationsregel.** $x$ wird eliminiert, wenn

$$|R(x)| \le |F_x| + |F_{\bar x}| \quad \text{und} \quad |r| \le m \text{ für alle } r \in R(x);$$

dann ist $F' = (F \setminus (F_x \cup F_{\bar x})) \cup R(x)$. Gewählt wird die Variable mit dem kleinsten Produkt $|F_x| \cdot |F_{\bar x}|$ (Gleichstand: kleinere Nummer).

**Erhaltung.** $F'$ ist logisch äquivalent zu $\exists x\, F$; deshalb gilt: $F$ erfüllbar $\iff$ $F'$ erfüllbar, aber die Modellmenge von $F'$ ist die Projektion der Modelle von $F$, nicht diese selbst.

**Subsumption und Verstärkung.** $A$ subsumiert $B$, wenn $A \subset B$; dann entfällt $B$. Gilt $A = A' \cup \{\ell\}$ und $A' \subseteq B \setminus \{\bar\ell\}$ mit $\bar\ell \in B$, so ist die Resolvente $B \setminus \{\bar\ell\}$ aus der Formel
gefolgert und subsumiert $B$: $B$ wird durch $B \setminus \{\bar\ell\}$ ersetzt.

**Rekonstruktion.** Sind $x_1, \dots, x_s$ in dieser Reihenfolge eliminiert, mit gespeicherten Klauseln $S_i = F_{x_i}$ zum Zeitpunkt der Elimination, so wird für $i = s, \dots, 1$ gesetzt:

$$x_i = \begin{cases} \text{wahr} & \text{wenn eine Klausel in } S_i \text{ unter der bisherigen Belegung ohne } x_i \text{ unerfüllt ist,} \\ \text{falsch} & \text{sonst.} \end{cases}$$

Das Ergebnis erfüllt alle entfernten Klauseln, weil jede Resolvente erfüllt ist.

**Die Auswertung.** Variablen und Klauseln werden als Summen über die Formeln einer Zeile verglichen, Konflikte und Propagationen als Median über die Formeln (je Formel Median über die Löser-Seeds). Eine Änderung der Konflikte
(im Urteil der Messreihe auch der Propagationen: „erkennbar in … Zeilen“) gilt nur dann als erkennbar, wenn sich die Spannen (Minimum bis Maximum der Mediane je Löser-Seed) vorher und nachher nicht überlappen.

**Sinz-Zähler.** Der sequenzielle Zähler „höchstens $k$ von $n$“ hat für $1 \le k < n$ genau $2nk + n - 3k - 1$ Klauseln und $(n-1)k$ Hilfsvariablen (Sinz 2005). Der Totalizer ist nach der Beschreibung von Bailleux und Boufkhad (2003)
umgesetzt, die in der Demo nur über Sekundärquellen bekannt ist.

**Literatur.** Sinz: *Towards an Optimal CNF Encoding of Boolean Cardinality Constraints*, CP 2005. Biere, Faller, Fleury, Froleyks, Pollitt: *CaDiCaL, Gimsatul, IsaSAT and Kissat Entering the SAT Competition 2025*:
Vivification, Variablenaddition und Äquivalenz-Sweeping als Inprocessing-Techniken. Subsumption und Variablenelimination als Technik sind aus dem Gedächtnis beschrieben, die Originalarbeiten sind nicht gelesen. Alle Zahlen der Demo sind eigene Messungen.
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [SAT und CP: Konfliktlernen bis Wahl](https://sebastianhanisch.net/konzepte-sat-constraint-programming.html)."
)
