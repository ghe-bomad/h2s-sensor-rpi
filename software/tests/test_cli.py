import csv
import math
from datetime import datetime, timezone

import pytest

from h2s_reader import config
from h2s_reader.__main__ import format_reading, main
from h2s_reader.h2s_sensor import Reading
from fakes import FakeBus

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)


def reading(**kw):
    base = dict(ppm=50.0, i_we_uA=5.02, vout_v=0.5351, temp_c=25.0, r_ntc_ohm=10000.0)
    return Reading(**{**base, **kw})


def make_bus():
    bus = FakeBus()
    bus.byte_regs[(config.LMP91002_ADDR, config.REG_STATUS)] = 0x01
    bus.conversion_by_config[config.ADS_CONF_AIN0] = [0x10, 0xB9]
    bus.conversion_by_config[config.ADS_CONF_AIN2] = [0x33, 0x90]
    return bus


def run(argv, bus=None, sleep=lambda s: None):
    bus = bus or make_bus()
    return main(argv, bus_factory=lambda n: bus, sleep=sleep, clock=lambda: NOW)


def test_format_reading_contains_ppm_and_temp():
    line = format_reading(reading())
    assert "50.00 ppm" in line and "25.00 C" in line and "uA" in line
    assert "SATURATED" not in line


def test_format_reading_flags_saturation_and_missing_temperature():
    line = format_reading(reading(saturated=True, temp_c=math.nan))
    assert "SATURATED" in line and "--- C" in line


def test_single_reading_without_calibration_warns(capsys):
    assert run([]) == 0
    out, err = capsys.readouterr()
    assert out.count("ppm") == 1 and "nominal" in err


def test_calibration_file_is_used(tmp_path, capsys):
    cal = tmp_path / "cal.toml"
    cal.write_text("i0_ua = 0.063\nsensitivity_ua_per_ppm = 0.099\ntemp_compensation = false\n")
    assert run(["--calibration", str(cal)]) == 0
    out, err = capsys.readouterr()
    assert "50.05 ppm" in out and err == ""


def test_bad_calibration_file_exits_2(tmp_path, capsys):
    cal = tmp_path / "cal.toml"
    cal.write_text("polarity = 3\n")
    assert run(["--calibration", str(cal)]) == 2
    assert "polarity" in capsys.readouterr().err


def test_stream_until_ctrl_c_and_csv(tmp_path, capsys):
    out_csv = tmp_path / "log.csv"
    calls = []

    def sleep(s):
        calls.append(s)
        if len(calls) == 2:
            raise KeyboardInterrupt
    assert run(["--stream", "--interval", "5", "--csv", str(out_csv)], sleep=sleep) == 0
    assert calls == [5.0, 5.0]
    assert run(["--csv", str(out_csv)]) == 0          # appends, no second header
    rows = list(csv.reader(out_csv.open()))
    assert rows[0] == ["time_utc", "ppm", "i_we_ua", "vout_v", "temp_c", "r_ntc_ohm", "saturated"]
    assert len(rows) == 1 + 3 and rows[1][0] == "2026-11-17T12:00:00Z" and rows[1][6] == "0"


def test_selftest(capsys):
    bus = FakeBus()
    bus.present = {config.LMP91002_ADDR}
    assert run(["--selftest"], bus=bus) == 1
    out = capsys.readouterr().out
    assert "OK   LMP91002" in out and "FAIL ADS1115" in out


@pytest.mark.parametrize("argv", [["--average", "0"]])
def test_bad_arguments(argv):
    assert run(argv) == 2
