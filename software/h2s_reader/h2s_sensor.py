"""Calibration maths and the H2SSensor class that combines the two chip drivers."""

import math
from dataclasses import dataclass

from . import config
from .calibration import Calibration
from .ads1115 import ADS1115
from .lmp91002 import LMP91002


def vout_to_current_uA(vout, v_zero=config.V_ZERO, r_tia=config.R_TIA,
                       polarity=config.POLARITY):
    """LMP91002 TIA output voltage -> working-electrode current in microamps."""
    return polarity * (vout - v_zero) / r_tia * 1e6


def current_to_ppm(i_uA, i0=config.I0_UA, sensitivity=config.SENSITIVITY_UA_PER_PPM):
    """Electrode current (uA) -> H2S concentration (ppm) via two-point calibration."""
    return (i_uA - i0) / sensitivity


def interpolate(table, x):
    """Linear interpolation in a ((x, y), ...) table sorted by x, clamped at both ends."""
    if x <= table[0][0]:
        return float(table[0][1])
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return float(table[-1][1])


def compensated_ppm(i_uA, temp_c, i0=config.I0_UA, sensitivity=config.SENSITIVITY_UA_PER_PPM,
                    cal_temp_c=config.CAL_TEMP_C,
                    sensitivity_pct=config.TEMP_SENSITIVITY_PCT,
                    baseline_ppm=config.TEMP_BASELINE_PPM):
    """Electrode current (uA) -> ppm, corrected for the cell temperature.

    `i0` and `sensitivity` were measured at `cal_temp_c`. The baseline moves by
    the table's ppm equivalent between `cal_temp_c` and `temp_c`, and the
    sensitivity scales with the table's percentage. Without a valid temperature
    the result equals current_to_ppm().
    """
    if temp_c is None or not math.isfinite(temp_c):
        return current_to_ppm(i_uA, i0, sensitivity)
    s20 = sensitivity / (interpolate(sensitivity_pct, cal_temp_c) / 100.0)
    baseline_shift = s20 * (interpolate(baseline_ppm, temp_c)
                            - interpolate(baseline_ppm, cal_temp_c))
    s_now = s20 * interpolate(sensitivity_pct, temp_c) / 100.0
    return (i_uA - i0 - baseline_shift) / s_now


def vnode_to_rntc(v_node, r_fixed=config.NTC_R_FIXED, vsupply=config.NTC_VSUPPLY):
    """Divider node voltage -> NTC resistance. VSUPPLY--R_FIXED--node--NTC--GND.

    Returns NaN for an open (node at rail) or shorted (node at gnd) thermistor.
    """
    if v_node <= 0 or v_node >= vsupply:
        return math.nan
    return r_fixed * v_node / (vsupply - v_node)


def rntc_to_celsius(r_ntc, r0=config.NTC_R0, beta=config.NTC_BETA, t0_k=config.NTC_T0_K):
    """NTC resistance -> temperature (deg C) via the Beta equation."""
    if not math.isfinite(r_ntc) or r_ntc <= 0:
        return math.nan
    inv_t = 1.0 / t0_k + math.log(r_ntc / r0) / beta
    return 1.0 / inv_t - 273.15


@dataclass
class Reading:
    ppm: float           # H2S concentration (temperature compensated if enabled)
    i_we_uA: float       # working-electrode current
    vout_v: float        # amplifier output on AIN0
    temp_c: float        # cell temperature from the NTC, NaN if the NTC is open or shorted
    r_ntc_ohm: float
    saturated: bool = False   # Vout at a limit: the true concentration is out of range


class H2SSensor:
    """Combines the LMP91002 amplifier and the ADS1115 ADC into calibrated readings.

    `bus` is an smbus2.SMBus (or anything with the same methods).
    """

    def __init__(self, bus, calibration: Calibration | None = None):
        self.calibration = calibration or Calibration()
        self._lmp = LMP91002(bus)
        self._ads = ADS1115(bus)

    @classmethod
    def open(cls, bus_num=config.I2C_BUS, calibration: Calibration | None = None):
        from smbus2 import SMBus  # lazy: only needed on real hardware
        return cls(SMBus(bus_num), calibration)

    def configure(self):
        """Wait for the LMP91002 and write its registers. Call once after power-up."""
        self._lmp.wait_ready()
        self._lmp.configure(refcn=self.calibration.refcn)

    def read(self, average: int = 1) -> Reading:
        """One reading; with average > 1 the mean of that many ADC conversions."""
        if average < 1:
            raise ValueError("average must be at least 1")
        cal = self.calibration
        vouts, nodes = [], []
        for _ in range(average):
            vouts.append(self._ads.read_channel_volts(config.ADS_CONF_AIN0))
            nodes.append(self._ads.read_channel_volts(config.ADS_CONF_AIN2))
        vout = sum(vouts) / average
        v_node = sum(nodes) / average
        i_uA = vout_to_current_uA(vout, v_zero=cal.v_zero, polarity=cal.polarity)
        r_ntc = vnode_to_rntc(v_node, vsupply=cal.ntc_vsupply_v)
        temp_c = rntc_to_celsius(r_ntc)
        if cal.temp_compensation:
            ppm = compensated_ppm(i_uA, temp_c, i0=cal.i0_ua,
                                  sensitivity=cal.sensitivity_ua_per_ppm,
                                  cal_temp_c=cal.cal_temp_c,
                                  sensitivity_pct=cal.temp_sensitivity_pct,
                                  baseline_ppm=cal.temp_baseline_ppm)
        else:
            ppm = current_to_ppm(i_uA, i0=cal.i0_ua, sensitivity=cal.sensitivity_ua_per_ppm)
        saturated = any(v <= config.VOUT_MIN_V or v >= config.VOUT_MAX_V for v in vouts)
        return Reading(ppm=ppm, i_we_uA=i_uA, vout_v=vout, temp_c=temp_c,
                       r_ntc_ohm=r_ntc, saturated=saturated)
