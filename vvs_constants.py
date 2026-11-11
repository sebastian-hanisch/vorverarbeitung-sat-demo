"""Konstanten: Familien, Regler-Grenzen, feste Annahmen der Messreihe, Farben und Presets."""

# --- Familien ---------------------------------------------------------------------------------------------------------------------------------
FAM_HAND = "hand1"
FAM_SINZ = "sinz"
FAM_VC_TOTALIZER = "vc_totalizer"
FAM_VC_SINZ = "vc_sinz"
FAM_FAERBUNG = "faerbung"
FAM_ZUFALL = "zufall"
FAM_LATIN = "latin"
FAMILIEN = (FAM_HAND, FAM_SINZ, FAM_VC_SINZ, FAM_VC_TOTALIZER, FAM_FAERBUNG, FAM_ZUFALL, FAM_LATIN)
FAMILIEN_NAMEN = {
    FAM_HAND: "Handbeispiel Teil 1 (5 Klauseln)",
    FAM_SINZ: "Sinz-Zähler, höchstens 1 von n (Handbeispiel Teil 2 bei n = 3)",
    FAM_VC_SINZ: "Vertex Cover mit Sinz-Zähler",
    FAM_VC_TOTALIZER: "Vertex Cover mit Totalizer",
    FAM_FAERBUNG: "3-Färbung eines Zufallsgraphen",
    FAM_ZUFALL: "Zufalls-3-SAT (m/n = 4,26)",
    FAM_LATIN: "Lateinisches Quadrat mit Lücken",
}
MESS_FAMILIEN = (FAM_VC_TOTALIZER, FAM_VC_SINZ, FAM_FAERBUNG, FAM_ZUFALL, FAM_LATIN)   # Zeilen der Messreihe
HAT_EINGAENGE = (FAM_SINZ, FAM_VC_SINZ, FAM_VC_TOTALIZER)                               # nur dort wirkt „Eingänge einfrieren“

# Größe n je Familie (Knoten, Variablen, Ordnung, Zählereingänge): kleinster, größter, Voreinstellung
N_GRENZEN = {
    FAM_SINZ: (3, 8, 3),
    FAM_VC_SINZ: (20, 40, 40),
    FAM_VC_TOTALIZER: (20, 40, 40),
    FAM_FAERBUNG: (30, 90, 90),
    FAM_ZUFALL: (30, 150, 100),
    FAM_LATIN: (6, 12, 12),
}
N_NAMEN = {FAM_SINZ: "Zählereingänge n", FAM_VC_SINZ: "Knoten n", FAM_VC_TOTALIZER: "Knoten n", FAM_FAERBUNG: "Knoten n",
           FAM_ZUFALL: "Variablen n", FAM_LATIN: "Ordnung n"}

VC_GRAD = 3.0            # mittlerer Grad des Zufallsgraphen
VC_ANTEIL = 0.4          # Auswahl höchstens 0,4·n Knoten (n = 60: 24)
FAERBUNG_GRAD = 4.5
ZUFALL_DICHTE = 4.26     # Klauseln je Variable (n = 150: 639 Klauseln)
LATIN_LUECKEN = 0.6
SINZ_K = 1

RUNDEN_MIN, RUNDEN_MAX, DEFAULT_RUNDEN = 1, 5, 5
SEED_MAX, DEFAULT_SEED = 999999, 1700
SINZ_N_MIN, SINZ_N_MAX, SINZ_K_MAX = 3, 8, 3      # Experiment „Elimination und Rekonstruktion“ (Hauptbereich)

# --- Messreihe (Skript tools/messreihe.py, Ergebnis vvs_messreihen.json) ----------------------------------------------------------------------
MESS_GROESSEN = {FAM_VC_TOTALIZER: 60, FAM_VC_SINZ: 60, FAM_FAERBUNG: 120, FAM_ZUFALL: 150, FAM_LATIN: 12}
MESS_SEEDS = tuple(range(1700, 1710))      # zehn feste Instanzen je Zeile (nie ein einzelner Seed als Befund)
LOESER_SEEDS = (11, 12, 13, 14, 15)        # fünf Löser-Seeds (zufällige Anfangsaktivität) für die Streubreite
BUDGET = 200000                            # Konfliktbudget je Lauf
LIVE_BUDGET = 20000
LIVE_SEEDS = tuple(range(1700, 1704))      # Messreihe live (verkleinert): vier Formeln, ein Löser-Seed (kein Seed der Löser-Streubreite)

COLOR_VOR = "rgba(150,150,150,0.75)"
COLOR_NACH = "#2F6B65"
COLOR_LINE = "#4c78a8"

PRESETS = {
    "Handbeispiel Teil 1": {"familie": FAM_HAND, "seed": DEFAULT_SEED, "eingefroren": False, "runden": DEFAULT_RUNDEN},
    "Sinz-Zähler k = 1": {"familie": FAM_SINZ, "n": 3, "seed": DEFAULT_SEED, "eingefroren": True, "runden": DEFAULT_RUNDEN},
    "Vertex Cover mit Zähler": {"familie": FAM_VC_SINZ, "n": 40, "seed": DEFAULT_SEED, "eingefroren": False, "runden": DEFAULT_RUNDEN},
    "Färbung": {"familie": FAM_FAERBUNG, "n": 90, "seed": DEFAULT_SEED, "eingefroren": False, "runden": DEFAULT_RUNDEN},
}
PRESET_HELP = {
    "Handbeispiel Teil 1": "Fünf Klauseln: Einheit, Subsumption, Verstärkung, wieder eine Einheit; die Formel wird leer. Von Hand nachrechenbar.",
    "Sinz-Zähler k = 1": "„Höchstens 1 von 3“ als sequenzieller Zähler mit zwei Hilfsvariablen; die Eingänge bleiben stehen, die Hilfsvariablen werden eliminiert.",
    "Vertex Cover mit Zähler": "Knotenüberdeckung eines Zufallsgraphen mit 40 Knoten und höchstens 16 gewählten Knoten, Auswahlgrenze als Sinz-Zähler. Nichts eingefroren.",
    "Färbung": "3-Färbung eines Zufallsgraphen mit 90 Knoten und mittlerem Grad 4,5.",
}
