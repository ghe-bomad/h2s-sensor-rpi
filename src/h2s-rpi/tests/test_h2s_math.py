import math

import pytest

from h2s_reader.h2s_sensor import (
    vout_to_current_uA,
    current_to_ppm,
    vnode_to_rntc,
    rntc_to_celsius,
)


def test_current_is_zero_at_internal_zero_voltage():
    assert vout_to_current_uA(0.50) == 0.0


def test_current_at_span_point():
    # 9.9 uA -> VOUT = 0.5 + 9.9e-6 * 7000 = 0.5693 V
    assert vout_to_current_uA(0.5693) == pytest.approx(9.9, abs=1e-3)


def test_ppm_baseline_and_span():
    assert current_to_ppm(0.063) == pytest.approx(0.0, abs=1e-9)   # baseline -> 0 ppm
    assert current_to_ppm(9.9) == pytest.approx(99.36, abs=0.01)   # span -> ~100 ppm


def test_thermistor_resistance_at_midpoint():
    assert vnode_to_rntc(1.65) == pytest.approx(10000.0, abs=1.0)


def test_thermistor_open_and_short_guarded():
    assert math.isnan(vnode_to_rntc(3.3))   # node at rail -> open NTC
    assert math.isnan(vnode_to_rntc(0.0))   # node at gnd  -> shorted


def test_celsius_at_nominal_resistance():
    assert rntc_to_celsius(10000.0) == pytest.approx(25.0, abs=0.05)


def test_celsius_nan_when_resistance_invalid():
    assert math.isnan(rntc_to_celsius(math.nan))


# --- temperature compensation (4-H2S-1000 datasheet curves) -------------------

from h2s_reader.h2s_sensor import compensated_ppm, interpolate  # noqa: E402

S, I0 = 0.099, 0.063


def test_interpolate_linear_and_clamped():
    table = ((0, 0.0), (10, 10.0), (20, 30.0))
    assert interpolate(table, 5) == pytest.approx(5.0)
    assert interpolate(table, 15) == pytest.approx(20.0)
    assert interpolate(table, -5) == 0.0
    assert interpolate(table, 99) == 30.0


def test_no_change_at_calibration_temperature():
    i = I0 + S * 250
    assert compensated_ppm(i, 20.0) == pytest.approx(current_to_ppm(i), abs=1e-9)


def test_cold_cell_reads_low_without_compensation():
    # datasheet: 94 % of the 20 C signal at 0 C, baseline unchanged
    i = I0 + S * 0.94 * 100
    assert current_to_ppm(i) == pytest.approx(94.0, abs=0.01)
    assert compensated_ppm(i, 0.0) == pytest.approx(100.0, abs=0.01)


def test_hot_cell_baseline_and_sensitivity():
    # datasheet at 50 C: baseline +5.5 ppm equivalent, 103 % sensitivity
    i = I0 + S * 5.5 + S * 1.03 * 100
    assert compensated_ppm(i, 50.0) == pytest.approx(100.0, abs=0.01)
    assert compensated_ppm(I0 + S * 5.5, 50.0) == pytest.approx(0.0, abs=1e-9)


def test_calibration_done_at_other_temperature():
    # span measured at 30 C: the same 30 C reading must give the gas value back
    s30 = 0.101
    i = I0 + s30 * 400
    assert compensated_ppm(i, 30.0, i0=I0, sensitivity=s30, cal_temp_c=30.0) \
        == pytest.approx(400.0, abs=0.01)


def test_missing_temperature_falls_back_to_uncompensated():
    i = I0 + S * 50
    assert compensated_ppm(i, math.nan) == pytest.approx(current_to_ppm(i))
    assert compensated_ppm(i, None) == pytest.approx(current_to_ppm(i))
