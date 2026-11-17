"""Per-cell calibration: values, validation and the TOML calibration file."""

from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

from . import config

# REFCN register value for each supported internal zero (external 2.5 V reference, zero bias).
REFCN_BY_INT_Z = {0.20: 0x80, 0.67: 0xC0}

Table = tuple[tuple[float, float], ...]


class CalibrationError(ValueError):
    """The calibration file or values are not usable."""


@dataclass(frozen=True)
class Calibration:
    """Everything that differs from cell to cell, or between installations.

    The defaults are the datasheet's nominal values: readings with them can be
    off by up to +/-44 %. Measure your own values (docs/calibration.md).
    """

    i0_ua: float = config.I0_UA                       # zero current at cal_temp_c
    sensitivity_ua_per_ppm: float = config.SENSITIVITY_UA_PER_PPM   # at cal_temp_c
    cal_temp_c: float = config.CAL_TEMP_C             # cell temperature during calibration
    polarity: int = config.POLARITY                   # -1 if Vout falls with H2S
    int_z: float = config.INT_Z                       # 0.20, or 0.67 with polarity -1
    temp_compensation: bool = config.TEMP_COMPENSATION
    temp_sensitivity_pct: Table = config.TEMP_SENSITIVITY_PCT
    temp_baseline_ppm: Table = config.TEMP_BASELINE_PPM
    ntc_vsupply_v: float = config.NTC_VSUPPLY         # measured 3.3 V rail, if known

    def __post_init__(self):
        problems = []
        if not _finite(self.i0_ua):
            problems.append("i0_ua must be a number")
        if not _finite(self.sensitivity_ua_per_ppm) or self.sensitivity_ua_per_ppm <= 0:
            problems.append("sensitivity_ua_per_ppm must be a positive number")
        if not _finite(self.cal_temp_c):
            problems.append("cal_temp_c must be a number")
        if self.polarity not in (1, -1):
            problems.append("polarity must be 1 or -1")
        if not any(math.isclose(self.int_z, z) for z in REFCN_BY_INT_Z):
            problems.append("int_z must be 0.20 or 0.67")
        if not isinstance(self.temp_compensation, bool):
            problems.append("temp_compensation must be true or false")
        problems += _table_problems("temp_sensitivity_pct", self.temp_sensitivity_pct, True)
        problems += _table_problems("temp_baseline_ppm", self.temp_baseline_ppm, False)
        if not _finite(self.ntc_vsupply_v) or self.ntc_vsupply_v <= 0:
            problems.append("ntc_vsupply_v must be a positive number")
        if problems:
            raise CalibrationError("; ".join(problems))

    @property
    def refcn(self) -> int:
        """LMP91002 REFCN register value for this internal zero."""
        for z, value in REFCN_BY_INT_Z.items():
            if math.isclose(self.int_z, z):
                return value
        raise CalibrationError("int_z must be 0.20 or 0.67")

    @property
    def v_zero(self) -> float:
        """Amplifier output voltage at zero current."""
        return self.int_z * config.VREF

    @classmethod
    def from_toml(cls, path: str | Path) -> "Calibration":
        """Read a calibration file. Missing keys keep their default."""
        path = Path(path)
        try:
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            raise CalibrationError(f"cannot read {path}: {exc}") from exc
        except tomllib.TOMLDecodeError as exc:
            raise CalibrationError(f"{path} is not valid TOML: {exc}") from exc
        known = {f.name for f in fields(cls)}
        unknown = sorted(set(raw) - known)
        if unknown:
            raise CalibrationError(f"{path}: unknown key(s) {', '.join(unknown)}")
        values = dict(raw)
        for key in ("temp_sensitivity_pct", "temp_baseline_ppm"):
            if key in values:
                values[key] = _to_table(key, values[key])
        for key in ("i0_ua", "sensitivity_ua_per_ppm", "cal_temp_c", "int_z", "ntc_vsupply_v"):
            if key in values and _is_number(values[key]):
                values[key] = float(values[key])
        try:
            return cls(**values)
        except CalibrationError as exc:
            raise CalibrationError(f"{path}: {exc}") from None


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _finite(v) -> bool:
    return _is_number(v) and math.isfinite(v)


def _to_table(key: str, value) -> Table:
    try:
        return tuple((float(t), float(v)) for t, v in value)
    except (TypeError, ValueError):
        raise CalibrationError(f"{key} must be a list of [temperature, value] pairs") from None


def _table_problems(key: str, table, positive: bool) -> list[str]:
    try:
        pairs = [(float(t), float(v)) for t, v in table]
    except (TypeError, ValueError):
        return [f"{key} must be a list of [temperature, value] pairs"]
    if len(pairs) < 2:
        return [f"{key} needs at least two points"]
    temps = [t for t, _ in pairs]
    if any(b <= a for a, b in zip(temps, temps[1:])):
        return [f"{key}: temperatures must increase"]
    if positive and any(v <= 0 for _, v in pairs):
        return [f"{key}: values must be positive"]
    return []
