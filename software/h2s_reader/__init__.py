"""Read the H2S sensor board (4-H2S-1000 cell, LMP91002, ADS1115) over I2C on a Raspberry Pi."""

from .calibration import Calibration, CalibrationError
from .h2s_sensor import H2SSensor, Reading, compensated_ppm, current_to_ppm

__version__ = "0.2.0"
__all__ = ["Calibration", "CalibrationError", "H2SSensor", "Reading",
           "compensated_ppm", "current_to_ppm", "__version__"]
