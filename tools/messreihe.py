"""Rechnet die Messreihe „Vorverarbeitung vorher/nachher“ und die Sinz-Tabelle und schreibt `vvs_messreihen.json`.

Aufruf aus dem Repo-Ordner (mit dem Laufzeit- oder Test-venv-Python):
  python tools/messreihe.py --zeilen vc_totalizer_frei vc_totalizer_eingefroren faerbung --teil teil1.json    (eine Gruppe von Zeilen, Teildatei)
  python tools/messreihe.py --zusammenfuegen teil1.json teil2.json                                              (schreibt vvs_messreihen.json samt Sinz-Tabelle)

Warum vorgerechnet: eine Zeile braucht zehn Formeln, je zwei Formeln (vorher/nachher) und fünf Löser-Seeds, also 100 Läufe des Python-CDCL (zusammen rund eine Viertelstunde bis
eine halbe Stunde); die App zeigt diese Datei ausdrücklich als „vorgerechnet, nicht live“. Die Rechnung ist deterministisch (SplitMix64, keine Zeitmessung);
`tests/test_claims.py` rechnet Zeilenausschnitte neu und vergleicht sie mit dieser Datei."""

import argparse
import itertools
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))

import vvs_algorithm as A  # noqa: E402
import vvs_constants as C  # noqa: E402
import vvs_evaluation as ev  # noqa: E402
import vvs_kodierung as K  # noqa: E402
import vvs_scenario as S  # noqa: E402

ZEILEN = {
    "vc_totalizer_frei": (C.FAM_VC_TOTALIZER, False),
    "vc_totalizer_eingefroren": (C.FAM_VC_TOTALIZER, True),
    "vc_sinz_frei": (C.FAM_VC_SINZ, False),
    "vc_sinz_eingefroren": (C.FAM_VC_SINZ, True),
    "faerbung": (C.FAM_FAERBUNG, False),
    "zufall": (C.FAM_ZUFALL, False),
    "latin": (C.FAM_LATIN, False),
}


KURZ = {"vc_totalizer_frei": "VC Totalizer", "vc_totalizer_eingefroren": "VC Totalizer (Eingänge fest)", "vc_sinz_frei": "VC Sinz",
        "vc_sinz_eingefroren": "VC Sinz (Eingänge fest)", "faerbung": "Färbung", "zufall": "Zufalls-3-SAT", "latin": "Latin 12"}


def beschriftung(familie: str, eingefroren: bool) -> str:
    n = C.MESS_GROESSEN[familie]
    basis = S.aufgabe(familie, n, C.MESS_SEEDS[0]).name
    if familie in C.HAT_EINGAENGE:
        return basis + (", Eingänge eingefroren" if eingefroren else ", nichts eingefroren")
    return basis


def messe_zeile(zid: str) -> dict:
    familie, eingefroren = ZEILEN[zid]
    n = C.MESS_GROESSEN[familie]
    formeln = []
    for seed in C.MESS_SEEDS:
        a = S.aufgabe(familie, n, seed)
        formeln.append(ev.messe_formel(a, eingefroren=eingefroren, loeser_seeds=C.LOESER_SEEDS, budget=C.BUDGET))
        print(zid, seed, formeln[-1]["konflikte_vor"], formeln[-1]["konflikte_nach"], flush=True)
    return {"id": zid, "familie": familie, "n": n, "eingefroren": eingefroren, "beschriftung": beschriftung(familie, eingefroren), "formeln": formeln}


def sinz_tabelle() -> list:
    """Sinz-Zähler „höchstens k von n“ plus (x1 ∨ … ∨ xn), Eingänge eingefroren: Größe vorher/nachher und Vergleich mit der binomialen Kodierung."""
    zeilen = []
    for k in range(1, C.SINZ_K_MAX + 1):
        for n in range(C.SINZ_N_MIN, C.SINZ_N_MAX + 1):
            if k >= n:
                continue
            a = S.sinz_zaehler(n, k)
            v = A.vorverarbeite(a.n, a.klauseln, eingefroren=a.eingaenge, protokoll=False)
            binom = set(A.normalisiere(K.hoechstens_binomial(list(range(1, n + 1)), k) + [tuple(range(1, n + 1))]))
            zeilen.append({"n": n, "k": k, "variablen": [v.variablen_alt, v.variablen_neu], "klauseln": [len(v.klauseln_alt), len(v.klauseln)],
                           "binomial_klauseln": len(binom), "gleich_binomial": set(v.klauseln) == binom, "eliminiert": v.zaehler["eliminiert"],
                           "resolventen": v.zaehler["resolventen"], "runden": v.zaehler["runden"]})
    return zeilen


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zeilen", nargs="+", choices=list(ZEILEN))
    ap.add_argument("--teil")
    ap.add_argument("--zusammenfuegen", nargs="+")
    args = ap.parse_args()
    if args.zeilen:
        daten = [messe_zeile(z) for z in args.zeilen]
        Path(args.teil).write_text(json.dumps(daten, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        return
    zeilen = list(itertools.chain.from_iterable(json.loads(Path(p).read_text(encoding="utf-8")) for p in args.zusammenfuegen))
    reihenfolge = {z: i for i, z in enumerate(ZEILEN)}
    zeilen.sort(key=lambda z: reihenfolge[z["id"]])
    for z in zeilen:
        z["kurz"] = KURZ[z["id"]]
    daten = {
        "hinweis": "vorgerechnet mit tools/messreihe.py, nicht live; zehn feste Formeln je Zeile (SplitMix64-Seeds), fünf Löser-Seeds, Budget siehe 'budget'",
        "budget": C.BUDGET, "mess_seeds": list(C.MESS_SEEDS), "loeser_seeds": list(C.LOESER_SEEDS),
        "kern_versionen": {"cdcl": "832b2c10dfdea62d", "instanzen": "6795de796b66fff8", "kodierung": "208571302afd04b4", "rng": "5d5d8f45d0e1eddf", "vorverarbeitung": "5b97cdced685984e"},
        "zeilen": zeilen, "sinz": sinz_tabelle(),
    }
    (HIER / ev.MESSREIHEN_DATEI.name).write_text(json.dumps(daten, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("geschrieben:", ev.MESSREIHEN_DATEI.name, len(zeilen), "Zeilen")


if __name__ == "__main__":
    main()
