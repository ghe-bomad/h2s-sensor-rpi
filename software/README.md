# h2s-reader

Python package and command-line tool for the H2S sensor board (4-H2S-1000 cell, LMP91002, ADS1115). It configures the analog front end over I2C, converts the cell current to ppm with a per-cell calibration, and corrects it for the cell temperature.

Needs Python 3.11 or newer (Raspberry Pi OS Bookworm or Trixie) and `smbus2`.

## Install

On the Raspberry Pi, with I2C enabled (`sudo raspi-config nonint do_i2c 0`):

```bash
python3 -m venv ~/h2s
~/h2s/bin/pip install "git+https://github.com/ghe-bomad/h2s-sensor-rpi#subdirectory=software"
```

Your user needs to be in the `i2c` group (the default user on Raspberry Pi OS is).

## Command line

```bash
h2s-reader --selftest                     # do both chips answer? (exit code 1 if not)
h2s-reader                                # one reading
h2s-reader --stream --interval 2          # a reading every 2 s until Ctrl-C
h2s-reader --calibration my-cell.toml --stream --average 4 --csv log.csv
```

| Option | Meaning |
|---|---|
| `--calibration FILE` | calibration file (TOML, see below). Without it the datasheet nominal values are used and a note is printed |
| `--stream` | keep reading until Ctrl-C |
| `--interval S` | seconds between readings (default 2) |
| `--average N` | average N ADC conversions per reading (default 1, about 20 ms each) |
| `--csv FILE` | also append each reading to a CSV file (the header is written once) |
| `--bus N` | I2C bus (default 1) |
| `--selftest` | only check that 0x48 and 0x49 answer |

Output, one line per reading:

```
H2S=  12.41 ppm  I_we=  1.117 uA  Vout=0.5078 V  T= 23.85 C
```

`SATURATED` at the end of a line means the amplifier output hit a limit, so the true concentration is out of range. `T=  --- C` means the NTC reading is invalid; the reading then has no temperature compensation.

CSV columns: `time_utc, ppm, i_we_ua, vout_v, temp_c, r_ntc_ohm, saturated`.

Exit codes: 0 fine, 1 self-test failed, 2 wrong usage or bad calibration file.

## Calibration file

Every cell has its own zero and sensitivity, so copy [calibration.example.toml](calibration.example.toml) and fill in your values. The procedure is in [docs/calibration.md](../docs/calibration.md). Keys you leave out keep their default.

| Key | Default | Meaning |
|---|---|---|
| `i0_ua` | 0.0 | zero current (µA) in clean air, at `cal_temp_c` |
| `sensitivity_ua_per_ppm` | 0.09 | sensitivity (µA/ppm) at `cal_temp_c` |
| `cal_temp_c` | 20.0 | cell temperature during the calibration |
| `polarity` | 1 | -1 if the output falls with H2S |
| `int_z` | 0.20 | internal zero of the LMP91002: 0.20, or 0.67 together with `polarity = -1` |
| `temp_compensation` | true | correct for the cell temperature |
| `temp_sensitivity_pct` | datasheet curve | `[[T, % of the 20 °C signal], ...]` |
| `temp_baseline_ppm` | datasheet curve | `[[T, ppm equivalent, 0 at 20 °C], ...]` |
| `ntc_vsupply_v` | 3.3 | the board's measured 3.3 V rail, for a more exact temperature |

Unknown keys and invalid values are rejected with a clear message.

## Python API

```python
from smbus2 import SMBus
from h2s_reader import Calibration, H2SSensor

cal = Calibration.from_toml("my-cell.toml")      # or Calibration() for nominal values
sensor = H2SSensor(SMBus(1), cal)
sensor.configure()                               # once after power-up
r = sensor.read(average=4)
print(r.ppm, r.i_we_uA, r.vout_v, r.temp_c, r.r_ntc_ohm, r.saturated)
```

The maths is also available on its own, for example to recalculate logged currents with a newer calibration:

- `compensated_ppm(i_uA, temp_c, i0, sensitivity, cal_temp_c, sensitivity_pct, baseline_ppm)`;
- `current_to_ppm`, `vout_to_current_uA`, `vnode_to_rntc` and `rntc_to_celsius` in `h2s_reader.h2s_sensor`.

## Modules

| Module | Content |
|---|---|
| `config.py` | board constants: I2C addresses, register values, reference voltage, gain, NTC, datasheet defaults |
| `calibration.py` | `Calibration` (per-cell values, validation, TOML loading) |
| `lmp91002.py` | LMP91002 driver: wait for ready, write TIACN/REFCN/MODECN |
| `ads1115.py` | ADS1115 single-shot reads |
| `h2s_sensor.py` | conversion maths and `H2SSensor` |
| `__main__.py` | the `h2s-reader` command |

## Development

```bash
cd software
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
```

The tests use an in-memory I2C bus (`tests/fakes.py`), so they run on any computer. GitHub Actions runs them on Python 3.11, 3.12 and 3.13.
