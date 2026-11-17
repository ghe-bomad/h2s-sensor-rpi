import math

import pytest

from h2s_reader import config
from h2s_reader.calibration import Calibration
from h2s_reader.h2s_sensor import H2SSensor, Reading
from fakes import FakeBus

# AIN0 0x10B9 = 4281 counts -> 0.535125 V -> 5.018 uA
# AIN2 0x3390 = 13200 counts -> 1.65 V -> 10 kOhm -> 25 C
VOUT_50PPM = [0x10, 0xB9]
NODE_25C = [0x33, 0x90]
CELL = Calibration(i0_ua=0.063, sensitivity_ua_per_ppm=0.099, temp_compensation=False)


def counts(n):
    return [(n >> 8) & 0xFF, n & 0xFF]


def _bus_with(vout_bytes, temp_bytes):
    bus = FakeBus()
    bus.byte_regs[(config.LMP91002_ADDR, config.REG_STATUS)] = 0x01
    bus.conversion_by_config[config.ADS_CONF_AIN0] = vout_bytes
    bus.conversion_by_config[config.ADS_CONF_AIN2] = temp_bytes
    return bus


def test_configure_runs_lmp_sequence():
    bus = _bus_with(VOUT_50PPM, NODE_25C)
    H2SSensor(bus).configure()
    # unlock, TIACN, REFCN, lock, MODECN
    assert len(bus.writes) == 5
    assert bus.writes[2] == (config.LMP91002_ADDR, config.REG_REFCN, 0x80)


def test_read_returns_ppm_and_temp():
    bus = _bus_with(VOUT_50PPM, NODE_25C)
    sensor = H2SSensor(bus, CELL)
    sensor.configure()
    r = sensor.read()
    assert isinstance(r, Reading)
    assert r.ppm == pytest.approx(50.05, abs=0.02)
    assert r.temp_c == pytest.approx(25.0, abs=0.1)
    assert r.vout_v == pytest.approx(0.535125, abs=1e-6)
    assert r.r_ntc_ohm == pytest.approx(10000.0, abs=1.0)
    assert not r.saturated


def test_temperature_compensation_applied_at_25c():
    # datasheet: 100.5 % sensitivity at 25 C, baseline 0
    from dataclasses import replace
    bus = _bus_with(VOUT_50PPM, NODE_25C)
    r = H2SSensor(bus, replace(CELL, temp_compensation=True)).read()
    assert r.ppm == pytest.approx(50.05 / 1.005, abs=0.02)


def test_high_zero_and_negative_polarity():
    bus = _bus_with(counts(12800), NODE_25C)          # Vout 1.600 V
    cal = Calibration(int_z=0.67, polarity=-1, i0_ua=0.0, sensitivity_ua_per_ppm=0.1,
                      temp_compensation=False)
    sensor = H2SSensor(bus, cal)
    sensor.configure()
    assert bus.writes[2] == (config.LMP91002_ADDR, config.REG_REFCN, 0xC0)
    r = sensor.read()
    assert r.i_we_uA == pytest.approx((1.675 - 1.6) / 7000 * 1e6, abs=1e-3)
    assert r.ppm == pytest.approx(107.1, abs=0.1)


@pytest.mark.parametrize("vout_counts", [26000, 0])   # 3.25 V and 0 V
def test_saturation_flagged(vout_counts):
    bus = _bus_with(counts(vout_counts), NODE_25C)
    assert H2SSensor(bus, CELL).read().saturated


def test_average_of_several_conversions():
    bus = _bus_with([counts(4200), counts(4300), counts(4400)], NODE_25C)
    r = H2SSensor(bus, CELL).read(average=3)
    assert r.vout_v == pytest.approx(4300 * 125e-6, abs=1e-9)


def test_average_must_be_positive():
    with pytest.raises(ValueError):
        H2SSensor(_bus_with(VOUT_50PPM, NODE_25C)).read(average=0)


def test_broken_ntc_gives_nan_temperature_and_plain_ppm():
    from dataclasses import replace
    bus = _bus_with(VOUT_50PPM, [0x00, 0x00])        # node at 0 V: shorted NTC
    r = H2SSensor(bus, replace(CELL, temp_compensation=True)).read()
    assert math.isnan(r.temp_c)
    assert r.ppm == pytest.approx(50.05, abs=0.02)
