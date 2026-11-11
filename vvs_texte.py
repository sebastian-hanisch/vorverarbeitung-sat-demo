"""Texte der Schritt-für-Schritt-Ansicht: ein Satz je Ereignis des Protokolls (reine Funktionen, getestet an den Handbeispielen)."""

import vvs_algorithm as A
from vvs_scenario import klausel_text as K
from vvs_scenario import lit_text

SCHRITT_TITEL = {
    "start": "Start: die Ausgangsformel",
    "einheit": "Einheitspropagation",
    "subsumption": "Subsumption",
    "verstaerkung": "Verstärkung (Selbst-Subsumption)",
    "elimination": "Begrenzte Variablenelimination",
}


def _liste(klauseln) -> str:
    return ", ".join(K(c) for c in klauseln) if klauseln else "keine"


def ereignis_text(e: dict, max_resolvente: int = A.MAX_RESOLVENTE) -> str:
    art = e["art"]
    if art == "einheit":
        lit = e["literal"]
        wert = "wahr" if lit > 0 else "falsch"
        teile = [f"**{lit_text(lit)}** ist eine Einheit: x{abs(lit)} wird {wert} gesetzt. Erfüllt und gestrichen: {_liste(e['erfuellt'])}."]
        if e["gekuerzt"]:
            teile.append(f"Das falsche Literal {lit_text(-lit)} fällt aus: " + ", ".join(f"{K(a)} → {K(n)}" for a, n in e["gekuerzt"]) + ".")
        return " ".join(teile)
    if art == "subsumption":
        return f"{K(e['subsumierend'])} subsumiert {K(e['subsumiert'])}: jede Belegung, die die kürzere Klausel erfüllt, erfüllt auch die längere; die längere fällt weg."
    if art == "verstaerkung":
        return (f"Die Resolvente von {K(e['klausel'])} und {K(e['opfer'])} auf x{abs(e['literal'])} ist {K(e['neu'])}; sie subsumiert {K(e['opfer'])}, "
                f"das deshalb das Literal {lit_text(e['literal'])} verliert und zu {K(e['neu'])} wird.")
    if art == "elimination":
        v = e["variable"]
        alt = len(e["positiv"]) + len(e["negativ"])
        kopf = f"x{v}: positiv in {len(e['positiv'])} Klauseln, negativ in {len(e['negativ'])}"
        if e["erlaubt"]:
            return (f"**x{v} wird eliminiert.** {kopf}; {len(e['resolventen'])} Resolventen gegen {alt} entfernte Klauseln, also erlaubt: "
                    f"{_liste(e['resolventen'])}.")
        if e["grund"] == "anzahl":
            return f"x{v} bleibt: {kopf}; es entstünden mehr Resolventen als die {alt} Klauseln, die wegfallen."
        return f"x{v} bleibt: {kopf}; eine Resolvente hätte mehr als {max_resolvente} Literale."
    raise ValueError(art)
