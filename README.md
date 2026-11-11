# Vorverarbeitung – kleiner heißt nicht weniger Konflikte – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-vorverarbeitung-sat-demo.streamlit.app/)**

Siebtes Stück der Linie **SAT und Constraint Programming** in der „Konzepte“-Reihe für die Website „Sebastian Hanisch – Operations Research und Machine Learning“. Die Kante vom ersten Stück (Konfliktklauseln) ist ein **bewusster Kontrast**: Der CDCL-Löser lernt **während** der Suche und lässt die Formel, wie sie ist; die Vorverarbeitung verkleinert die Formel **vor** der Suche. Die Demo zeigt die vier Schritte einzeln (Einheiten, Subsumption, Verstärkung, begrenzte Variablenelimination), die Rückrechnung eliminierter Variablen in ein Modell der Originalformel und eine vorgerechnete Messreihe vorher/nachher; Inprocessing (Vereinfachen während der Suche) ist ein Erklär-Reiter ohne Messung.

## Warum dieses Problem

Eine kleinere Formel liegt nahe als schnellere Formel. Die Demo prüft das an Zählgrößen des eigenen Python-Lösers, nie an Sekunden (in der Messreihe wird die Formel kleiner und die Propagationen sinken, bei den Konflikten ist kein Unterschied erkennbar): Variablen, Klauseln, Konflikte, Propagationen und die **Kosten der Vorverarbeitung selbst** (berechnete Resolventen). Kernfrage: Senkt eine kleinere Formel die Arbeit der Suche, und woran sieht man es?

## Modell

Formeln in konjunktiver Normalform, Literale als ganze Zahlen (+v wahr, −v falsch). Die Aufgaben: Handbeispiele (von Hand nachrechenbar), der **Sinz-Zähler** „höchstens k von n“ (plus „mindestens eines“), **Vertex Cover** eines Zufallsgraphen (Kantenklauseln, Auswahlgrenze k = 0,4·n als Sinz-Zähler oder Totalizer), **3-Färbung** eines Zufallsgraphen, **Zufalls-3-SAT** (m/n = 4,26) und ein **lateinisches Quadrat mit Lücken** (Ordnung 12, 60 % der Zellen ohne Vorgabe). Alle Zufallsinstanzen laufen über den ganzzahligen SplitMix64 (`vvs_rng.py`), nie über Python-`random`.

Verfahren (Mathematik im 📐-Expander der App):

- **Einheitspropagation:** Einheitsklauseln in der Reihenfolge ihres Auftretens; erfüllte Klauseln fallen, das falsche Literal fällt aus den übrigen.
- **Subsumption:** Klausel B entfällt, wenn eine Klausel A nur Literale von B enthält.
- **Verstärkung (Selbst-Subsumption):** Subsumiert die Resolvente von A und B das B, verliert B das Literal, auf dem resolviert wurde.
- **Begrenzte Elimination:** gewählt wird die Variable mit dem kleinsten Produkt der Vorkommen (Gleichstand: kleinere Nummer, eingefrorene nie); eliminiert wird sie, wenn die Zahl der nicht tautologischen Resolventen die der entfernten Klauseln nicht übersteigt und keine Resolvente länger als 20 Literale ist. Jede Variable wird je Durchlauf höchstens einmal versucht.
- **Runden:** Einheiten; dann bis zu 5 Runden aus Subsumption, Verstärkung, Einheiten, Elimination. Eine Runde, die nichts ändert, beendet das Verfahren.
- **Rekonstruktion:** eliminierte Variablen rückwärts in der Reihenfolge der Elimination belegen, zunächst falsch, wahr, wenn eine gespeicherte Klausel, in der sie positiv vorkam, sonst unerfüllt bliebe. Jedes rekonstruierte Modell wird gegen die **Originalklauseln** geprüft.
- **Eingänge einfrieren:** Variablen, die nie eliminiert werden (bei Zählern und Vertex Cover die Variablen der Aufgabe). Die Messreihe zeigt je Zählerfamilie zwei Zeilen, damit „Hilfsvariablen verschwinden“ von „alles darf fallen“ trennbar ist.
- **Vivification** (nur Erklär-Reiter): Literale einer Klausel nacheinander falsch setzen, auf den übrigen Klauseln propagieren, bei Widerspruch kürzen.

## Methodik

- **Messgerät:** der CDCL-Löser des Kern-Pakets der Linie (`vvs_cdcl.py`: 1-UIP, VSIDS in der MiniSat-Variante, Luby-Neustarts mit Einheit 32, Phasenspeicher, ohne Löschen gelernter Klauseln und ohne Minimierung), gezählt in Konflikten und Propagationen. Konfliktbudget der Messreihe 200.000, das in keinem Lauf erreicht wurde (`abgebrochen` 0 in allen sieben Zeilen).
- **Messreihe** (`vvs_messreihen.json`, erzeugt mit `tools/messreihe.py`, **vorgerechnet, nicht live**): je Zeile zehn feste Formeln (Zufalls-Seeds 1700 bis 1709), je Formel vorher und nachher fünf Läufe mit fünf Löser-Seeds (zufällige Anfangsaktivität aus SplitMix64), das sind 100 Läufe je Zeile. Wert je Formel: Median über die Löser-Seeds; Wert der Zeile: Median über die Formeln; Variablen und Klauseln: Mittel über die Formeln.
- **Verdikt der Konflikte (Spannenregel):** Für jeden Löser-Seed wird der Median über die Formeln gebildet; die Spanne ist Minimum bis Maximum dieser fünf Mediane, vorher und nachher. Eine Änderung der Konflikte gilt nur dann als erkennbar, wenn sich die beiden Spannen nicht überlappen. Die Spanne erfasst die Streuung der Suche bei **denselben** zehn Formeln, nicht die zwischen verschiedenen Formeln.
- **Kosten:** `resolventen` zählt untersuchte Resolventen-Paare (auch tautologische und verworfene; die Zählung bricht bei einer verworfenen Elimination ab), `vergleiche` die Teilmengen-Prüfungen in Subsumption und Verstärkung. Beide sind Zähler, keine Zeit, und nicht in Propagationen umrechenbar.
- **Verkleinerte Messreihe live** (Reiter „Vorher und nachher“): vier Formeln (Zufalls-Seeds 1700 bis 1703) mit der Größe der Seitenleiste, ein Löser-Seed, Budget 20.000; ohne Spanne, daher nur eine Zählung.
- **Kern-Kopien:** `vvs_rng.py`, `vvs_instanzen.py`, `vvs_kodierung.py`, `vvs_cdcl.py`, `vvs_vorverarbeitung.py` sind unveränderte Kopien aus `sat-cp-planung/kern` (Kern-Versionen im Kopf jeder Datei; `tests/test_copies.py` vergleicht die Hashes). Die App benutzt statt der Kern-Fassung `vvs_vorverarbeitung.py` die eigene Fassung `vvs_algorithm.py` (öffentliche Einzelschritte, Ereignisprotokoll, Kostenzähler, Einfrieren, Vivification); die Kern-Fassung bleibt als Vergleich in den Tests.

## Befunde (gemessen, keine Behauptungen)

Messreihe, zehn feste Formeln und fünf Löser-Seeds je Zeile (`vvs_messreihen.json`; `tests/test_claims.py` rechnet die Zahlen aus der Datei nach und die Vorverarbeitungsgrößen zusätzlich aus den Instanzen):

| Zeile | Formeln (erfüllbar / unerfüllbar) | Variablen (Mittel) | Klauseln (Mittel) | Propagationen (Median) | Konflikte (Median) | Spanne der Löser-Seeds vorher | Spanne nachher | Resolventen berechnet (Median) |
|---|---|---|---|---|---|---|---|---|
| Vertex Cover n = 60, k = 24, Totalizer, nichts eingefroren | 10 (0 / 10) | 371 → 252,1 | 1.932 → 1.341,9 | 94.784 → 70.772,5 (−25,3 %) | 1.213,5 → 1.314,5 (+8,3 %) | 1.180 bis 1.346 | 1.191 bis 1.454 | 18.894,5 |
| Vertex Cover n = 60, k = 24, Totalizer, Eingänge eingefroren | 10 (0 / 10) | 371 → 284 | 1.932 → 1.500 | 94.784 → 81.460 (−14,1 %) | 1.213,5 → 1.378 (+13,6 %) | 1.180 bis 1.346 | 1.186 bis 1.572,5 | 7.332 |
| Vertex Cover n = 60, k = 24, Sinz-Zähler, nichts eingefroren | 10 (0 / 10) | 1.476 → 425,2 | 2.957 → 1.634,4 | 307.619 → 133.645 (−56,6 %) | 1.578 → 1.811 (+14,8 %) | 1.526 bis 1.786,5 | 1.762 bis 2.026 | 25.649 |
| Vertex Cover n = 60, k = 24, Sinz-Zähler, Eingänge eingefroren | 10 (0 / 10) | 1.476 → 470 | 2.957 → 1.784 | 307.619 → 135.400,5 (−56,0 %) | 1.578 → 1.708,5 (+8,3 %) | 1.526 bis 1.786,5 | 1.585,5 bis 1.948 | 9.018 |
| 3-Färbung n = 120, Grad 4,5 | 10 (5 / 5) | 360 → 174,8 | 930 → 718,2 | 7.305,5 → 2.932 (−59,9 %) | 83 → 59 (−28,9 %) | 54,5 bis 92,5 | 56 bis 70,5 | 12.184,5 |
| Zufalls-3-SAT n = 150, m = 639 | 10 (1 / 9) | 150 → 147,2 | 639 → 634,6 | 88.935 → 83.863 (−5,7 %) | 2.890 → 2.756 (−4,6 %) | 2.696 bis 3.071 | 2.558,5 bis 2.897 | 4.205,5 |
| Latin 12, Lücken 0,6 | 10 (10 / 0) | 1.728 → 405,3 | 29.002 → 2.819,8 | 2.014,5 → 798 (−60,4 %) | 3,5 → 4 (+14,3 %) | 2,5 bis 5 | 1 bis 5 | 10.107 |

| Frage | Befund |
|---|---|
| Wird die Formel kleiner? | **Ja, in allen sieben Zeilen**: Variablen −1,9 % (Zufalls-3-SAT) bis −76,5 % (Latin 12), Klauseln −0,7 % bis −90,3 % (Mittel über zehn Formeln). Beim Sinz-Zähler (n = 60, k = 24) sinkt die Variablenzahl von 1.476 auf 425,2 (nichts eingefroren) bzw. 470 (Eingänge eingefroren; die Variablen der Aufgabe werden dann nie eliminiert, können aber durch Einheiten festgelegt werden und verschwinden damit ebenfalls). |
| Sinken die Propagationen? | **Im Median in allen sieben Zeilen**: von −5,7 % (Zufalls-3-SAT) bis −60,4 % (Latin 12); bei Vertex Cover mit Totalizer −25,3 % (nichts eingefroren) bzw. −14,1 % (Eingänge eingefroren), mit Sinz-Zähler −56,6 % bzw. −56,0 %. Nach derselben Spannenregel wie bei den Konflikten ist der Rückgang in fünf Zeilen erkennbar; bei Zufalls-3-SAT (Spannen 82.407 bis 92.440,5 gegen 79.701,5 bis 89.076; nur 6 von 10 Formeln mit weniger Propagationen) und bei Vertex Cover mit Totalizer, Eingänge eingefroren (91.655 bis 104.980 gegen 72.618 bis 93.578,5) überlappen die Spannen. |
| Sinken die Konflikte? | **Nicht erkennbar.** In keiner der sieben Zeilen liegt die Spanne der fünf Löser-Seeds nachher getrennt von der vorher; die Mediane ändern sich von −28,9 % (Färbung) bis +14,8 % (Vertex Cover mit Sinz-Zähler). Die Vorzeichen sind gemischt: In fünf der sieben Zeilen steigt der Median der Konflikte, in zwei (Färbung, Zufalls-3-SAT) sinkt er. |
| Was kostet die Vorverarbeitung? | Im Median berechnet sie 4.205,5 (Zufalls-3-SAT) bis 25.649 (Vertex Cover mit Sinz-Zähler, nichts eingefroren) Resolventen-Paare je Formel; mit eingefrorenen Eingängen 7.332 (Totalizer) bzw. 9.018 (Sinz-Zähler). Die Kosten sind eine Zählung und mit den Propagationen nicht verrechenbar; Sekunden wurden nicht gemessen. |
| Stimmen Antworten und Modelle? | **Ja**: 0 Antwortfehler und 0 Modellfehler in 350 Vergleichen vorher/nachher (700 Läufe); 80 rekonstruierte Modelle (Färbung 25, Zufall 5, Latin 50) wurden gegen die Originalklauseln geprüft. In den Vertex-Cover-Zeilen ist jede der 10 Formeln unerfüllbar (k = 24), dort wird kein Modell rekonstruiert. |
| Was greift wann? | Mit eingefrorenen Eingängen greifen Subsumption und Verstärkung in **keiner** der 20 Formeln der beiden Vertex-Cover-Zeilen (0 subsumierte, 0 verstärkte Klauseln); dort wirken nur Einheiten (30 bzw. 230 in zehn Formeln) und Elimination. Ohne Einfrieren greifen beide (Totalizer 64 subsumierte, 804 verstärkte; Sinz 49 und 262 in zehn Formeln). In der Latin-Zeile wirken allein die Einheiten (13.227 in zehn Formeln): danach ist keine Runde mehr nötig. |
| Wird der Sinz-Zähler zur paarweisen Kodierung? | **Nur für kleine n.** Eingänge eingefroren, k = 1: n = 3 und n = 4 ergeben genau die binomiale Kodierung (Handbeispiel Teil 2: 5 → 3 Variablen, 6 → 4 Klauseln), ab n = 5 bleiben Hilfsvariablen (n = 8: 15 → 10 Variablen, 21 → 19 Klauseln, binomial wären 29). Für k = 2 stimmt es bei n = 3 und 4, für k = 3 bei n = 4 und 5 (Tabelle in der App, `vvs_messreihen.json`, Schlüssel `sinz`). |

Von Hand und per Aufzählung geprüfte Handbeispiele stehen in `tests/test_algorithm.py` (Quelle: `sat-cp-planung/handbeispiele/hb_07.py`): Teil 1 (Einheit x1, Subsumption (x2 ∨ x4) ⊂ (x2 ∨ x3 ∨ x4), Verstärkung (¬x2 ∨ x4) → (x4), Einheit x4: leere Formel, 4 Modelle alle mit x1 = x4 = wahr), Teil 2 (x4: 2 Resolventen gegen 3 alte, x5: 2 gegen 3; Rückrechnung der drei Modelle; ohne Einfrieren Stapel x1, x3, x2, x4 und leere Formel) und Teil 3 (Vivification (x1 ∨ x2 ∨ x3) → (x1 ∨ x2), 12 gleich 12 Modelle).

## Ehrliche Grenzen

- **Einfache Fassung:** Einheiten, Subsumption, Verstärkung, begrenzte Elimination (Resolventen höchstens so viele wie entfernte Klauseln, Länge höchstens 20, höchstens 5 Runden). Entfernen blockierter Klauseln, Äquivalenzerkennung, Probing und Variablenaddition fehlen; **kein Urteil über moderne Vorverarbeiter.**
- **Zählgrößen, keine Zeit:** Die Zeit der Vorverarbeitung und der Gesamtlauf in Sekunden sind nicht gemessen; „kleiner heißt nicht weniger Konflikte“ meint hier: Konflikte und Propagationen des eigenen Python-Lösers, an den gezeigten Familien und Größen.
- **Ein Löser, zehn Formeln:** Die Spannen erfassen die Streuung der Suche bei denselben Formeln. Ob sich die Konflikte bei anderen Formeln oder mit mehr als zehn Formeln je Zeile erkennbar ändern, sagen die Zahlen nicht; „kein Unterschied erkennbar“ heißt hier nur: die Spannen überlappen.
- **Alle Vertex-Cover-Formeln der Messreihe sind unerfüllbar** (k = 24 bei n = 60): Die Aussagen über Vertex Cover betreffen unerfüllbare Formeln.
- **Nichts eingefroren eliminiert auch die Variablen der Aufgabe.** Bei Zählern verschwindet dann die Zählerstruktur (Handbeispiel Teil 2 ohne Einfrieren: leere Formel); erfüllbar bleibt die Formel trotzdem.
- **Elimination erhält die Erfüllbarkeit, nicht die Modellmenge:** Die Modelle der vereinfachten Formel sind die Projektionen der Modelle der Ausgangsformel auf die verbliebenen Variablen (`tests/test_oracle_vorverarbeitung_sat.py`); die Rückrechnung liefert **ein** Modell der Ausgangsformel, nicht jedes.
- **Latin 12:** Die Zeile zeigt, wie viel die Einheiten allein leisten; die Konflikte sind vorher und nachher klein (Median 3,5 und 4, Spannen der Löser-Seeds 2,5 bis 5 und 1 bis 5).
- **Totalizer** nach der Sekundärbeschreibung von Bailleux/Boufkhad 2003 (Original nicht gelesen); der Sinz-Zähler nach Sinz 2005 (2nk + n − 3k − 1 Klauseln, (n − 1)k Hilfsvariablen, nachgerechnet).
- **Inprocessing** (Reiter): nur das, was die Beschreibung von CaDiCaL/Kissat zur SAT Competition 2025 (Biere u. a.) nennt: Vivification, Variablenaddition, Äquivalenz-Sweeping; keine Messung, keine Wirkungsaussage. Subsumption und Variablenelimination als Technik sind aus dem Gedächtnis beschrieben (Originalarbeiten nicht gelesen).

## Befunde und Korrekturen gegenüber dem Plan

Der Plan stützte sich auf die Vormessung V15 (Rohausgabe `sat-cp-planung/vormessung/out_v15.txt`, nicht Teil dieses Repos und hier nicht nachgerechnet; Python-`random`-Instanzen, vier bis acht Formeln je Zeile, ein Löser-Seed). Die Neumessung mit SplitMix64-Instanzen, zehn Formeln und fünf Löser-Seeds ändert folgende Aussagen:

1. **„Die Konflikte sinken nicht verlässlich“ wird genauer:** In keiner Zeile ist ein Unterschied erkennbar (Spannenregel). Die Änderung der Mediane liegt zwischen −28,9 % und +14,8 %; die V15-Zeile „Sinz-Zähler mehr Konflikte“ (1.562,5 → 1.730) bleibt im Vorzeichen (1.578 → 1.811), liegt aber innerhalb der Streuung der Löser-Seeds (Spannen 1.526 bis 1.786,5 und 1.762 bis 2.026 überlappen). Die Färbung, in V15 „107,5 → 107,5“, zeigt jetzt −28,9 % im Median bei überlappenden Spannen (54,5 bis 92,5 gegen 56 bis 70,5).
2. **Propagationen „um 20 bis 55 %“ gilt nicht für alle Zeilen:** gemessen −5,7 % (Zufalls-3-SAT) bis −60,4 % (Latin 12); Vertex Cover mit Totalizer −25,3 %, mit Sinz-Zähler −56,6 % (nichts eingefroren).
3. **Latin 12 hat nicht „0 Konflikte“:** Median 3,5 vorher, 4 nachher (V15: 0). Der Erzeuger (Zyklentausch aus dem zyklischen Quadrat mit SplitMix64) ist neu; die Aufgabe bleibt nach den Einheiten nahezu trivial. Variablen 1.728 → 405,3 (V15: 418), Klauseln 29.002 → 2.819,8 (V15: 3.030).
4. **Sinz-Zähler mit k = 1 wird nicht allgemein zur paarweisen Kodierung:** nur für n = 3 und 4 (der Plan stützte sich auf das Handbeispiel n = 3). Ab n = 5 bleiben Hilfsvariablen, weil ihre Elimination mehr Resolventen erzeugen würde, als Klauseln wegfallen. **k > 1 ist jetzt gemessen** (n = 3 bis 8, k = 1 bis 3, Tabelle in der App).
5. **Die Trennung nach Einfrieren zeigt:** Mit eingefrorenen Eingängen sinken Variablen, Klauseln und Propagationen weniger als ohne (Totalizer: −23,5 % statt −32,0 % der Variablen, Propagationen −14,1 % statt −25,3 %, wobei die Spannen der Löser-Seeds überlappen: eingefroren 72.618 bis 93.578,5, nichts eingefroren 63.976,5 bis 77.818, der Unterschied der Propagationen ist nicht abgesichert); beim Sinz-Zähler ist der Unterschied bei den Propagationen klein (−56,0 % gegen −56,6 %). Die Kosten (Resolventen) sinken mit Einfrieren deutlich (Totalizer 7.332 gegen 18.894,5).
6. **Alle zehn Vertex-Cover-Formeln sind unerfüllbar** (der Plan nannte das nicht); Modelle werden deshalb an Färbung, Zufalls-3-SAT und Latin rekonstruiert.
7. **Schnittstelle des Kerns:** Die Kern-Fassung `vorverarbeitung.py` hat keine öffentlichen Einzelschritte, kein Protokoll, keine Kostenzähler und kein Einfrieren (Schnittstellenwünsche 1 bis 4 und 6 des Plans). Die Kopie bleibt unverändert (Hash-Test); `vvs_algorithm.py` setzt die Wünsche um. Die Fassungen stimmen bei Totalizer, Zufalls-3-SAT und Latin in Variablen und Klauseln überein; beim Sinz-Zähler und bei der Färbung wählt die dynamische Variablenwahl (Heap, Nachführung nach jeder Elimination) anders als die einmalig sortierte Reihenfolge des Kerns (Abstand unter 5 %, `tests/test_algorithm.py`).
8. **Zweig-Test:** Jeder der vier Schritte greift auf mindestens einer Messreihen-Instanz, aber **nicht in jeder Zeile**: mit eingefrorenen Eingängen greifen Subsumption und Verstärkung nie, in der Latin-Zeile nur die Einheiten.

## Bewusst nicht umgesetzt

Blockierte Klauseln, Äquivalenzerkennung, Probing, Variablenaddition, Cube-and-Conquer, Inprocessing als gemessenes Verfahren (Vivification ist nur als Rechnung an einer Klausel dabei), Beweise über vorverarbeitete Formeln (bräuchten Eliminationsschritte im Beweisformat; Stück 6 der Linie), Zeitmessungen, Industrieformeln, PDF-Export.

## Verifikation

- **Kern:** Einzelschritte an den Handbeispielen des Plans (Teil 1 bis 3, `tests/test_algorithm.py`), Randfälle (leere Formel, einzelne Einheit, doppeltes Literal, Tautologie, reine Variable, null Resolventen, alles eingefroren, Rundengrenzen; `tests/test_edge_cases.py`).
- **Orakel** (`tests/test_oracle_vorverarbeitung_sat.py`, Aufzählung aller Belegungen und OR-Tools CP-SAT als Gegenprobe): (1) Äquierfüllbarkeit, Rückrechnung **jedes** Modells der vereinfachten Formel zu einem Modell der Ausgangsformel und Gleichheit der Modelle der vereinfachten Formel mit den Projektionen der Ausgangsmodelle, mit und ohne Einfrieren; im Scratch-Lauf 1.200 Läufe über 600 Zufallsformeln (n 4 bis 10) ohne Unterschied, im Repo 60 Formeln je Variante; (2) Subsumption und Verstärkung ändern die Modellmenge nicht, die verstärkte Klausel folgt aus der Formel; (3) Elimination ist die Existenzquantifizierung (Projektion) und lässt die Klauselzahl nicht wachsen; (4) Klauselzahl 2nk + n − 3k − 1 und Hilfsvariablen (n − 1)k des Sinz-Zählers gegen die erzeugten Mengen, Zähler gegen Aufzählung der Eingänge; (5) Antwort vorher gegen nachher; (6) Vivification ändert die Modellmenge nicht. Eigenschaften: Permutationstest (Nummerierung und Klauselreihenfolge), Idempotenz nach dem Fixpunkt, Zweig-Test.
- **Kern-Kopien:** Hash-Test gegen die Kern-Version, Regressionstests aus dem Kern (SplitMix64, Instanzen, CDCL-Einheiten, Kodierungen, Kern-Vorverarbeitung).
- **Verdikte:** reine Funktionen in `vvs_evaluation.py`, an handgesetzten Zeilen geprüft (`tests/test_verdicts.py`, darunter „Konflikte steigen“ bei einer Sinz-Zeile und „kein Unterschied erkennbar“ bei überlappenden Spannen).
- **Claims:** `tests/test_claims.py` rechnet jede Zahl dieser README aus `vvs_messreihen.json` nach und prüft Ausschnitte der Messreihe (Vorverarbeitung aller Zeilen für drei Formeln, Löserläufe für je eine Formel) gegen eine Neumessung; Zeiten stehen nirgends.
- **Presets, Layout, Oberfläche:** Presets vollständig und innerhalb der Grenzen; Schnellstart in der Seitenleiste, fester Kopf, aktives Preset hervorgehoben, jede Änderung eines Reglers hebt die Markierung auf; AppTest-Rauchtest (jeder Knopf, jeder Regler am Minimum und Maximum), verkleinerte Messreihe, Schrittregler, Reiter „Elimination“, Footer.
- **Anzahl:** 153 Tests (`pytest --collect-only -q tests`).

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App: Ergebnis, Kernfrage, vier Reiter, Erklärtabelle, Annahmen, Mathematik |
| `requirements-dev.txt` | Laufzeit plus pytest und OR-Tools (nur Gegenprobe im Test) |
| `requirements.txt` | Laufzeit-Bibliotheken (ungepinnt) |
| `tools/messreihe.py` | rechnet die Messreihe und die Sinz-Tabelle und schreibt `vvs_messreihen.json` |
| `vvs_algorithm.py` | Kern: Einheiten, Subsumption, Verstärkung, Variablenwahl, Elimination, `vorverarbeite` mit Protokoll und Zählern, Rekonstruktion, Vivification |
| `vvs_cdcl.py`, `vvs_instanzen.py`, `vvs_kodierung.py`, `vvs_rng.py`, `vvs_vorverarbeitung.py` | unveränderte Kopien aus dem Kern-Paket der Linie (Kern-Version im Dateikopf) |
| `vvs_constants.py` | Familien, Regler-Grenzen, Messreihen-Festlegungen, Presets |
| `vvs_evaluation.py` | Messung vorher/nachher, Kennzahlen, Verdikte, Experiment „Sinz-Zähler“, verkleinerte Messreihe |
| `vvs_layout.py` | Fester Kopf (Stylesheet) |
| `vvs_messreihen.json` | vorgerechnete Messreihe (zehn Formeln je Zeile, fünf Löser-Seeds) und Sinz-Tabelle |
| `vvs_presets.py` | Permalink (Begrenzen), Presets (Schnellstart in der Seitenleiste, aktives Preset hervorgehoben), Seed-Kette über SplitMix64 |
| `vvs_scenario.py` | Aufgaben: Handbeispiele, Sinz-Zähler, Vertex Cover, Färbung, Zufalls-3-SAT, lateinisches Quadrat mit Lücken |
| `vvs_texte.py` | ein Satz je Ereignis des Protokolls |
| `vvs_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `tests/` | Handbeispiele, Randfälle, Orakel, Kern-Kopien, Verdikte, Claims, Presets, Layout, AppTest-Smoke-Test, Footer, Laufzeit-Importe |

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly und pandas; der CDCL-Löser und die Vorverarbeitung sind reines Python.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zur Reihe: [SAT und CP: Konfliktlernen bis Wahl](https://sebastianhanisch.net/konzepte-sat-constraint-programming.html).
