"""Die kopierten Kern-Module sind unverändert gegenüber der Kern-Version, die im Modulkopf steht (Hash der Datei ohne Kopfzeilen und mit rückübersetzten Importen).

`vvs_rng`, `vvs_instanzen`, `vvs_kodierung`, `vvs_cdcl` und `vvs_vorverarbeitung` sind Kopien von `rng.py`, `instanzen.py`, `kodierung.py`, `cdcl.py` und `vorverarbeitung.py` aus
sat-cp-planung/kern, nur die Importe der Geschwistermodule sind auf `vvs_` umgestellt (keine weitere Abweichung)."""

import hashlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODULE = ["rng", "instanzen", "kodierung", "cdcl", "vorverarbeitung"]


def _kern_text(modul: str) -> tuple[str, str]:
    """(Kern-Version aus dem Kopf, Text im Zustand des Kerns)."""
    text = (ROOT / f"vvs_{modul}.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    version = re.match(r"# Herkunft: Kopie von sat-cp-planung/kern/\w+\.py \(Kern-Version ([0-9a-f]{16})", text).group(1)
    zeilen = text.split("\n")
    i = 0
    while zeilen[i].startswith("#"):
        i += 1
    return version, "\n".join(zeilen[i:]).replace("from vvs_rng import", "from rng import")


@pytest.mark.parametrize("modul", MODULE)
def test_kopie_gleicht_der_kern_version(modul):
    version, text = _kern_text(modul)
    assert hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] == version


def test_kopien_importieren_nichts_aus_dem_kern_oder_anderen_demos():
    erlaubt = {"heapq", "itertools", "dataclasses", "typing", "math", "vvs_rng"}
    for modul in MODULE:
        for zeile in (ROOT / f"vvs_{modul}.py").read_text(encoding="utf-8").splitlines():
            if zeile.startswith(("import ", "from ")):
                assert zeile.split()[1] in erlaubt, (modul, zeile)


def test_kein_python_random_und_kein_hash():
    """Zufall nur über SplitMix64: in keinem eigenen Modul der Demo steht `import random` oder ein Aufruf von `hash(`."""
    for pfad in [p for p in ROOT.glob("vvs_*.py") if p.stem[4:] not in MODULE] + [ROOT / "app.py"]:     # die Kopien sind oben gegen den Kern-Hash geprüft
        quelle = pfad.read_text(encoding="utf-8")
        assert "import random" not in quelle and "from random" not in quelle, pfad.name
        assert not re.search(r"(?<![\w.])hash\(", quelle), pfad.name
