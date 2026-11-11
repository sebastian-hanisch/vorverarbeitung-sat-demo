"""Presets: Vollständigkeit, gültige Werte, Standard-Preset = Standardeinstellungen, Seed-Kette über SplitMix64, Permalink-Caster."""

import pytest

import vvs_constants as C
import vvs_evaluation as ev
import vvs_presets as P


def test_every_preset_has_help_and_only_known_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    for name, preset in C.PRESETS.items():
        assert set(preset) <= set(P.PRESET_KEYS) | {"n"}, name
        assert preset["familie"] in C.FAMILIEN and C.PRESET_HELP[name]


def test_preset_values_are_inside_the_bounds():
    for name, preset in C.PRESETS.items():
        lo, hi, _ = C.N_GRENZEN.get(preset["familie"], (0, 0, 0))
        assert preset.get("n", lo) >= lo and preset.get("n", lo) <= max(hi, lo), name
        assert 0 <= preset["seed"] <= C.SEED_MAX and C.RUNDEN_MIN <= preset["runden"] <= C.RUNDEN_MAX
        assert ("n" in preset) == (preset["familie"] in C.N_GRENZEN), name


def test_default_preset_equals_the_default_settings():
    assert ev.Settings(**{k: v for k, v in next(iter(C.PRESETS.values())).items()}) == ev.Settings()


def test_setting_specs_cover_every_preset_key_and_every_family_size():
    assert set(P.PRESET_KEYS.values()) <= set(P.SETTING_SPECS)
    for fam, (lo, hi, std) in C.N_GRENZEN.items():
        spec = P.SETTING_SPECS[P.n_key(fam)]
        assert (spec.lo, spec.hi, spec.default) == (lo, hi, std) and lo <= std <= hi


def test_preset_werte_legt_die_groesse_unter_dem_schluessel_der_familie_ab():
    w = P.preset_werte("Vertex Cover mit Zähler")
    assert w == {"familie_select": C.FAM_VC_SINZ, "n_vc_sinz": 40, "seed_input": C.DEFAULT_SEED, "eingefroren_toggle": False, "runden_slider": C.DEFAULT_RUNDEN}
    assert "n_hand1" not in P.preset_werte("Handbeispiel Teil 1") and not any(k.startswith("n_") for k in P.preset_werte("Handbeispiel Teil 1"))


def test_seed_kette_ist_deterministisch_und_begrenzt():
    s = C.DEFAULT_SEED
    kette = []
    for _ in range(20):
        s = P.neuer_seed(s)
        kette.append(s)
        assert 0 <= s <= C.SEED_MAX
    assert len(set(kette)) == 20
    assert P.neuer_seed(5) == P.neuer_seed(5) and P.neuer_seed(5) != P.neuer_seed(6)


def test_caster_fuer_den_permalink():
    assert P._bool("True") is True and P._bool("false") is False and P._bool("1") is True
    assert P._familie("latin") == "latin"
    with pytest.raises(ValueError):
        P._familie("unbekannt")
