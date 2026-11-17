import pytest

from h2s_reader import config
from h2s_reader.calibration import Calibration, CalibrationError


def write(tmp_path, text):
    p = tmp_path / "cal.toml"
    p.write_text(text)
    return p


def test_defaults_are_datasheet_nominal():
    c = Calibration()
    assert c.i0_ua == 0.0 and c.sensitivity_ua_per_ppm == 0.09
    assert c.refcn == 0x80 and c.v_zero == pytest.approx(0.50)
    assert c.temp_sensitivity_pct == config.TEMP_SENSITIVITY_PCT


def test_full_file(tmp_path):
    c = Calibration.from_toml(write(tmp_path, """
i0_ua = 0.063
sensitivity_ua_per_ppm = 0.099
cal_temp_c = 21
polarity = -1
int_z = 0.67
temp_compensation = false
temp_sensitivity_pct = [[0, 95], [20, 100], [40, 104]]
temp_baseline_ppm = [[20, 0], [40, -2]]
ntc_vsupply_v = 3.31
"""))
    assert c.sensitivity_ua_per_ppm == 0.099 and c.cal_temp_c == 21.0
    assert c.polarity == -1 and c.refcn == 0xC0 and c.v_zero == pytest.approx(1.675)
    assert c.temp_compensation is False
    assert c.temp_sensitivity_pct == ((0.0, 95.0), (20.0, 100.0), (40.0, 104.0))
    assert c.temp_baseline_ppm == ((20.0, 0.0), (40.0, -2.0))


def test_missing_keys_keep_defaults(tmp_path):
    c = Calibration.from_toml(write(tmp_path, "sensitivity_ua_per_ppm = 0.07\n"))
    assert c.sensitivity_ua_per_ppm == 0.07 and c.i0_ua == 0.0 and c.temp_compensation


def test_example_file_loads():
    from pathlib import Path
    example = Path(__file__).resolve().parents[1] / "calibration.example.toml"
    if not example.exists():          # vendored copies of the package ship without it
        pytest.skip("calibration.example.toml not next to the tests")
    assert Calibration.from_toml(example).sensitivity_ua_per_ppm == 0.099


@pytest.mark.parametrize("text, needle", [
    ("sensitivity = 0.1\n", "unknown key"),
    ("sensitivity_ua_per_ppm = 0\n", "positive"),
    ("sensitivity_ua_per_ppm = 'high'\n", "positive"),
    ("polarity = 2\n", "polarity"),
    ("int_z = 0.5\n", "int_z"),
    ("temp_compensation = 1\n", "true or false"),
    ("temp_sensitivity_pct = [[20, 100]]\n", "at least two"),
    ("temp_sensitivity_pct = [[20, 100], [10, 90]]\n", "increase"),
    ("temp_sensitivity_pct = [[0, 0], [20, 100]]\n", "positive"),
    ("temp_baseline_ppm = 'flat'\n", "pairs"),
    ("i0_ua = \n", "not valid TOML"),
])
def test_invalid_files(tmp_path, text, needle):
    with pytest.raises(CalibrationError) as e:
        Calibration.from_toml(write(tmp_path, text))
    assert needle in str(e.value)


def test_missing_file(tmp_path):
    with pytest.raises(CalibrationError, match="cannot read"):
        Calibration.from_toml(tmp_path / "nope.toml")
