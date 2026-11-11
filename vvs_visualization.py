"""Plotly-Abbildungen. Alle Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht am Diagramm hängen bleiben."""

import plotly.graph_objects as go

import vvs_constants as C

SCHRITT_NAMEN = {"start": "Start", "einheit": "Einheiten", "subsumption": "Subsumption", "verstaerkung": "Verstärkung", "elimination": "Elimination"}


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height=360):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.25), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def prozent_von_vorher(vor, nach):
    """Nachher in Prozent von vorher; None, wenn vorher 0 ist (dann gibt es nichts zu vergleichen)."""
    return None if vor == 0 else 100.0 * nach / vor


def build_prozent(werte, key_hinweis=""):
    """Balken „nachher in % von vorher“ für eine Liste (Beschriftung, vorher, nachher); 100 % ist der Wert vorher. Zeilen mit vorher = 0 entfallen."""
    zeilen = [(name, vor, nach, prozent_von_vorher(vor, nach)) for name, vor, nach in werte]
    zeilen = [z for z in zeilen if z[3] is not None]
    fig = go.Figure(go.Bar(
        x=[z[0] for z in zeilen], y=[z[3] for z in zeilen], marker_color=[C.COLOR_NACH if z[3] <= 100 else "#b5483a" for z in zeilen],
        text=[f"{z[3]:.0f} %" for z in zeilen], textposition="outside", customdata=[[z[1], z[2]] for z in zeilen],
        hovertemplate="%{x}: vorher %{customdata[0]:,.0f}, nachher %{customdata[1]:,.0f} (%{y:.1f} % von vorher)<extra></extra>", showlegend=False))
    fig.add_hline(y=100, line=dict(color=C.COLOR_VOR, dash="dash"), annotation_text="vorher = 100 %", annotation_position="top left")
    fig.update_yaxes(title_text="nachher in % von vorher", range=[0, max([110] + [z[3] * 1.15 for z in zeilen])])
    return _base(fig, 330)


def build_verlauf(phasen):
    """Klauseln und Variablen nach jedem Schritt der Vorverarbeitung."""
    namen = [f"{SCHRITT_NAMEN[p['schritt']]}" + (f" (R{p['runde']})" if p["runde"] else "") for p in phasen]
    # eindeutige Beschriftungen als Text (nicht als Zahlen), damit Plotly eine Kategorienachse anlegt
    namen = [f"{i}. {n}" for i, n in enumerate(namen)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=namen, y=[p["klauseln_nach"] for p in phasen], mode="lines+markers", name="Klauseln", line=dict(color=C.COLOR_LINE, width=3),
                             hovertemplate="%{x}: %{y} Klauseln<extra></extra>"))
    fig.add_trace(go.Scatter(x=namen, y=[p["variablen_nach"] for p in phasen], mode="lines+markers", name="Variablen", line=dict(color=C.COLOR_NACH, width=3),
                             hovertemplate="%{x}: %{y} Variablen<extra></extra>"))
    fig.update_yaxes(title_text="nach dem Schritt", rangemode="tozero")
    fig.update_xaxes(tickangle=-40)
    return _base(fig, 380)


def build_messreihe(kennzahlen):
    """Änderung gegenüber vorher in Prozent je Zeile der Messreihe: Variablen, Klauseln, Propagationen, Konflikte (Median)."""
    namen = [z["kurz"] for z in kennzahlen]
    fig = go.Figure()
    for label, key, farbe in (("Variablen", "variablen_prozent", "#4c78a8"), ("Klauseln", "klauseln_prozent", "#72b7b2"),
                              ("Propagationen", "propagationen_prozent", "#f58518"), ("Konflikte", "konflikte_prozent", "#b5483a")):
        fig.add_trace(go.Bar(x=namen, y=[z[key] for z in kennzahlen], name=label, marker_color=farbe,
                             hovertemplate="%{x}: %{y:.1f} % (Median bzw. Summe vorher = 0 %)<extra>" + label + "</extra>"))
    fig.add_hline(y=0, line=dict(color=C.COLOR_VOR))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text="Änderung gegenüber vorher (%)", range=[-100, 40])
    return _base(fig, 400)


def build_streuung(formeln):
    """Konflikte je Formel (Median über die Löser-Seeds) vorher gegen nachher; auf der Diagonalen ändert sich nichts."""
    from statistics import median
    xs = [median(f["konflikte_vor"]) for f in formeln]
    ys = [median(f["konflikte_nach"]) for f in formeln]
    gipfel = max(xs + ys + [1]) * 1.1
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, gipfel], y=[0, gipfel], mode="lines", line=dict(color=C.COLOR_VOR, dash="dash"), name="gleich viele Konflikte", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", marker=dict(size=10, color=C.COLOR_NACH), name="Formel", text=[f"Seed {f['seed']}" for f in formeln],
                             hovertemplate="%{text}: vorher %{x:,.0f}, nachher %{y:,.0f}<extra></extra>"))
    fig.update_xaxes(title_text="Konflikte vorher", range=[0, gipfel])
    fig.update_yaxes(title_text="Konflikte nachher", range=[0, gipfel])
    return _base(fig, 360)
