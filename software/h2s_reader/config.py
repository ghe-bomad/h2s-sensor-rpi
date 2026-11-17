"""Hardware constants of the H2S sensor board and default calibration values.

The register values and analog constants describe the board and should only
change with the hardware. Per-cell calibration belongs in a calibration file
(see calibration.py and docs/calibration.md), not here; the defaults below are
the datasheet's nominal values.
"""

# --- I2C ---
I2C_BUS = 1
LMP91002_ADDR = 0x48   # fixed
ADS1115_ADDR = 0x49    # ADDR tied to +3V3

# --- LMP91002 register addresses ---
REG_STATUS = 0x00
REG_LOCK = 0x01
REG_TIACN = 0x10
REG_REFCN = 0x11
REG_MODECN = 0x12

# --- LMP91002 configuration values ---
TIACN_VALUE = 0x0C     # TIA gain 7k (011), Rload 10 ohm (00)
REFCN_VALUE = 0x80     # REF_SOURCE=1 (external 2.5V), INT_Z=20% (00), zero bias
MODECN_VALUE = 0x03    # 3-lead amperometric
LOCK_UNLOCK = 0x00
LOCK_LOCK = 0x01

# --- Reference / AFE derived ---
VREF = 2.5             # ADR3425 external reference (V)
INT_Z = 0.20           # internal zero fraction (matches REFCN 20%)
R_TIA = 7000.0         # TIA feedback (ohm), matches TIACN 7k
POLARITY = 1           # -1 if VOUT falls with H2S (docs/bring-up.md)
V_ZERO = INT_Z * VREF  # 0.50 V

# --- H2S calibration defaults (datasheet nominal, NOT a calibration) ---
# Cell: Euro-Gas 4-H2S-1000 (Honeywell CLE-0113-400), 0-1000 ppm.
# Datasheet: sensitivity 0.09 +/- 0.04 uA/ppm, baseline < +/- 0.4 uA at 20 C,
# so every cell needs its own zero and span calibration (docs/calibration.md).
I0_UA = 0.0                      # zero-gas baseline current (uA) at CAL_TEMP_C
SENSITIVITY_UA_PER_PPM = 0.09    # uA per ppm at CAL_TEMP_C
CAL_TEMP_C = 20.0                # sensor temperature during that calibration
TEMP_COMPENSATION = True         # correct with the temperature tables below

# Temperature dependence, average curves read from the 4-H2S-1000 datasheet
# (Euro-Gas, 01/16, page 2). Replace with your own lab results when you have them.
# (temperature C, output in % of the signal at 20 C)
TEMP_SENSITIVITY_PCT = ((-20, 88.0), (-10, 91.0), (0, 94.0), (10, 97.0), (20, 100.0),
                        (30, 101.0), (40, 102.0), (50, 103.0))
# (temperature C, baseline in ppm equivalent, nulled at 20 C)
TEMP_BASELINE_PPM = ((-20, 0.0), (30, 0.0), (35, 0.6), (40, 1.5), (45, 3.0), (50, 5.5))

# --- Signal limits (amplifier output on AIN0) ---
# The LMP91002 output cannot swing to the 3.3 V rail, and 0 V means the
# current is more negative than the 20 % zero allows.
VOUT_MIN_V = 0.02
VOUT_MAX_V = 3.20

# --- NTC thermistor (TH1) + divider: VSUPPLY -- R_FIXED -- node -- NTC -- GND ---
NTC_R0 = 10000.0       # nominal resistance @ T0 (ohm)
NTC_BETA = 3950.0      # B25/85 (K)
NTC_T0_K = 298.15      # 25 C in kelvin
NTC_R_FIXED = 10000.0  # R3, top of divider (ohm)
NTC_VSUPPLY = 3.3      # divider supply rail (V)

# --- ADS1115 ---
ADS_FSR = 4.096        # full-scale range (V), PGA = 001
ADS_REG_CONVERSION = 0x00
ADS_REG_CONFIG = 0x01
# single-shot, +-4.096V, 128 SPS, comparator off:
ADS_CONF_AIN0 = 0xC383  # MUX=100 (AIN0 vs GND) -> H2S VOUT
ADS_CONF_AIN2 = 0xE383  # MUX=110 (AIN2 vs GND) -> thermistor node
