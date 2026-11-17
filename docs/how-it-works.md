# How it works

## Signal chain

```
4-H2S-1000 cell ── LMP91002 ── AIN0 ┐
  (WE, CE, RE)     7 kΩ TIA         ├── ADS1115 ── I2C ── Raspberry Pi
NTC under cell ── divider ── AIN2 ──┘     (0x49)          (h2s-reader)
                  ADR3425 2.5 V ── LMP91002 VREF
```

1. **The cell:** H2S diffuses into the cell and is oxidised at the working electrode (WE). This produces a current proportional to the concentration, about 0.09 µA per ppm. The cell needs no bias voltage (0 mV).
2. **The LMP91002:**
   - it keeps the reference electrode (RE) at the working electrode's potential by driving the counter electrode (CE);
   - its transimpedance amplifier turns the WE current into a voltage, with a 7 kΩ internal gain resistor and a 10 Ω load resistor;
   - the output sits at 20 % of the 2.5 V reference when no current flows, so currents of both signs can be measured.
3. **The ADS1115** measures that output on AIN0, and the NTC divider on AIN2, at ±4.096 V full scale.
4. **The software** turns the voltages into a current, a concentration and a temperature, and corrects the concentration for temperature.

## Equations

```
Vout = Vzero + polarity × I_we × 7 kΩ            Vzero = int_z × 2.5 V = 0.50 V
I_we = polarity × (Vout − Vzero) / 7 kΩ
ppm  = (I_we − i0) / S                            without temperature compensation
```

`i0` is the zero current of the cell in clean air and `S` its sensitivity. Both come from the calibration (docs/calibration.md).

## Range and resolution

| Quantity | Value |
|---|---|
| ADC step (±4.096 V, 16 bit) | 125 µV, which is 0.018 µA or 0.2 ppm at 0.09 µA/ppm |
| Upper limit of Vout | about 3.2 V (`VOUT_MAX_V`), which is 386 µA: 2970 ppm even for the most sensitive cell (0.13 µA/ppm) |
| Negative headroom | 0.50 V, which is −71 µA |
| Cell range | 0 to 1000 ppm, overload 2000 ppm |

The whole range of the cell, including overload, fits without clipping. A reading whose output reaches 0.02 V or 3.2 V is marked `saturated`.

If a cell turns out to give a falling output with H2S, use `int_z = 0.67` (zero at 1.675 V) with `polarity = -1`, so the signal has room to fall (docs/bring-up.md).

## Temperature

The divider is 3.3 V, R3 (10 kΩ), AIN2, NTC, GND:

```
R_ntc = 10 kΩ × V / (3.3 V − V)
T     = 1 / (1/298.15 K + ln(R_ntc / 10 kΩ) / 3950) − 273.15
```

With an open or shorted NTC the temperature is NaN, and the concentration is then calculated without compensation. The 3.3 V rail has about ±1 % tolerance, which shifts the temperature by a few tenths of a degree. Set `ntc_vsupply_v` to the measured rail voltage if that matters.

## Temperature compensation

According to its datasheet, the cell's output depends on temperature in two ways:

| Temperature | Sensitivity (% of 20 °C) | Baseline (ppm equivalent, 0 at 20 °C) |
|---|---|---|
| −20 °C | 88 | 0 |
| 0 °C | 94 | 0 |
| 20 °C | 100 | 0 |
| 30 °C | 101 | 0 |
| 40 °C | 102 | 1.5 |
| 50 °C | 103 | 5.5 |

These are the averages read from the datasheet's curves; the full tables are in `config.py`. Between 15 and 35 °C the effect is below 2 % and 1 ppm, which is small next to the ±44 % spread between cells. So the span calibration matters most.

With `S` and `i0` measured at `cal_temp_c`, `rel(T)` the sensitivity table divided by 100 and `b(T)` the baseline table:

```
S20 = S / rel(cal_temp_c)
ppm = (I_we − i0 − S20 × (b(T) − b(cal_temp_c))) / (S20 × rel(T))
```

Values between table points are interpolated linearly, and outside the table the end values are used. Your own curves (docs/calibration.md, step 5) can replace the datasheet ones in the calibration file.

## LMP91002 registers

| Register | Value | Meaning |
|---|---|---|
| LOCK (0x01) | 0x00, then 0x01 | unlock, write, lock again |
| TIACN (0x10) | 0x0C | TIA gain 7 kΩ, load 10 Ω |
| REFCN (0x11) | 0x80 (or 0xC0) | external reference, internal zero 20 % (or 67 %), bias 0 |
| MODECN (0x12) | 0x03 | 3-lead amperometric cell |

The ADS1115 runs in single-shot mode at 128 samples/s: config word 0xC383 for AIN0 and 0xE383 for AIN2.
