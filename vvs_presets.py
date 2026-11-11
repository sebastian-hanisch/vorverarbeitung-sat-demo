"""Permalink (Begrenzen), Presets und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio).

Besonderheit: Die Größe n hat je Familie eigene Grenzen und eine eigene Schlüsselzeile `n_<Familie>`; gezeichnet wird immer nur der Regler der gewählten Familie.
Deshalb legen Voreinstellungen, Permalink und Preset den Wert nur für die Familie ab, die sie selbst festlegen (kein Schreiben in einen Regler, der in diesem Lauf nicht gezeichnet wird,
DEMO-PLAYBOOK §3, „Ausblendbare Regler“)."""

from dataclasses import dataclass

import streamlit as st

import vvs_constants as C
from vvs_rng import SplitMix64


def _bool(text) -> bool:
    return str(text).strip().lower() in ("1", "true", "ja", "wahr")


def _familie(text) -> str:
    if text not in C.FAMILIEN:
        raise ValueError(text)
    return text


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: object
    default: object
    lo: float | None = None
    hi: float | None = None


def n_key(familie: str) -> str:
    return f"n_{familie}"


SETTING_SPECS = {
    "familie_select": SettingSpec("fam", _familie, C.FAM_HAND),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, 0, C.SEED_MAX),
    "eingefroren_toggle": SettingSpec("fest", _bool, False),
    "runden_slider": SettingSpec("runden", int, C.DEFAULT_RUNDEN, C.RUNDEN_MIN, C.RUNDEN_MAX),
}
for _fam, (_lo, _hi, _std) in C.N_GRENZEN.items():
    SETTING_SPECS[n_key(_fam)] = SettingSpec(f"n_{_fam}", int, _std, _lo, _hi)
PRESET_KEYS = {"familie": "familie_select", "seed": "seed_input", "eingefroren": "eingefroren_toggle", "runden": "runden_slider"}   # „n“ siehe preset_werte


def preset_werte(name: str) -> dict:
    """Session-State-Werte, die ein Preset festlegt (die Größe unter dem Schlüssel seiner Familie)."""
    preset = C.PRESETS[name]
    werte = {PRESET_KEYS[k]: v for k, v in preset.items() if k in PRESET_KEYS}
    if "n" in preset:
        werte[n_key(preset["familie"])] = preset["n"]
    return werte


def init_session_state_defaults():
    """Voreinstellungen der Regler, die in jedem Lauf gezeichnet werden; die Größe der gewählten Familie nur über `init_n`."""
    for state_key in ("familie_select", "seed_input", "eingefroren_toggle", "runden_slider"):
        if state_key not in st.session_state:
            st.session_state[state_key] = SETTING_SPECS[state_key].default


def init_n(familie: str):
    """Voreinstellung der Größe der gewählten Familie, unmittelbar vor ihrem Regler (nur dessen Schlüssel)."""
    key = n_key(familie)
    if key not in st.session_state:
        st.session_state[key] = SETTING_SPECS[key].default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def load_permalink_settings():
    """Einmal je Sitzung: Werte aus der Adresszeile übernehmen, auf die Reglergrenzen begrenzt; die Größe nur für die Familie der Adresszeile."""
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    familie = None
    if "fam" in qp:
        try:
            familie = _familie(qp["fam"])
        except ValueError:
            familie = None
    for state_key, spec in SETTING_SPECS.items():
        if state_key.startswith("n_") and (familie is None or state_key != n_key(familie)):
            continue
        if state_key == "familie_select" and familie is None:
            continue
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
            except (ValueError, TypeError):
                continue
            if spec.lo is not None:
                value = max(spec.lo, value)
            if spec.hi is not None:
                value = min(spec.hi, value)
            st.session_state[state_key] = value
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}; die Adresszeile spiegelt die Konfiguration (nur Regler, die gezeichnet werden)."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    for state_key, value in preset_werte(name).items():
        st.session_state[state_key] = value


def aktives_preset():
    """Name des Presets, dessen Werte GENAU den aktuellen Einstellungen entsprechen, sonst None.

    Zustandslos: verglichen wird jeder Regler aus SETTING_SPECS (ein Preset ohne Eintrag für einen Regler meint dessen Standardwert) mit dem Session State.
    Die Größen anderer Familien stehen nicht im Session State (ihr Regler wird nicht gezeichnet) und gelten als Standardwert."""
    for name in C.PRESETS:
        werte = preset_werte(name)
        if all(st.session_state.get(state_key, spec.default) == werte.get(state_key, spec.default) for state_key, spec in SETTING_SPECS.items()):
            return name
    return None


def sidebar_presets():
    """Schnellstart oben in der Seitenleiste; das aktive Preset ist hervorgehoben (`type="primary"`)."""
    if not C.PRESETS:
        return
    st.header("🎯 Schnellstart")
    st.caption("Ein Beispielszenario laden:")
    aktiv = aktives_preset()
    for name in C.PRESETS:
        st.button(
            name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}",
            type="primary" if aktiv == name else "secondary",
        )


def neuer_seed(seed: int) -> int:
    """Der nächste Zufalls-Seed der Kette: aus dem aktuellen über SplitMix64 (kein Python-`random`), in 0 bis SEED_MAX."""
    return SplitMix64(seed + 7919).below(C.SEED_MAX + 1)


def randomize_seed():
    st.session_state["seed_input"] = neuer_seed(int(st.session_state.get("seed_input", C.DEFAULT_SEED)))
