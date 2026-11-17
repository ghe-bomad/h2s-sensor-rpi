# H2S sensor board for Raspberry Pi

A small I2C board that measures H2S from 0 to 1000 ppm with an electrochemical cell, plus the Python package that reads it on a Raspberry Pi. It is used in the Mzuzu biogas composition rig ([ghe-bomad/mzuzu-composition-measurements](https://github.com/ghe-bomad/mzuzu-composition-measurements)), which vendors `src/h2s-rpi/h2s_reader`.

| Part | Role |
|---|---|
| Euro-Gas 4-H2S-1000 cell (Honeywell CLE-0113-400) | 3-electrode H2S cell, 0.09 ± 0.04 µA/ppm, 0 to 1000 ppm |
| LMP91002 (I2C 0x48) | potentiostat and transimpedance amplifier, 7 kΩ gain, 20 % internal zero |
| ADR3425 | 2.5 V reference for the LMP91002, so the zero does not move with the 3.3 V rail |
| ADS1115 (I2C 0x49) | 16-bit ADC: AIN0 amplifier output, AIN2 NTC divider, AIN3 spare on header H5 |
| NTC 10 kΩ, B 3950 (TH1) | under the cell, used for temperature compensation |
| LP5907 | 3.3 V regulator from the 5 V input |

## Layout

- `hardware/h2s-pcb-rpi/pcb-design/`: KiCad project, footprints, `production/` files of version H2S-RPi-V1 (gerber zip, BOM, positions).
- `hardware/h2s-pcb-rpi/docs/`: datasheets. Note: `honeywell-CLE-0113-400.pdf` is in fact the datasheet of a phosphine (PH3) cell; the H2S cell's datasheet is `4_H2S_1000.pdf`.
- `src/h2s-rpi/`: the `h2s_reader` package and its tests (`pytest`), see its README.
- `docs/CALIBRATION.md`: zero, span and temperature calibration with certified test gas.

## Design notes

- The sensor pins match the datasheet's pinout: WE on its own, CE and RE on either side.
- The NTC sits at the low side of the divider: 3.3 V, R3 10 kΩ, AIN2, NTC, GND.
- The LMP91002 filter pins C1 and C2 are not connected. An optional capacitor there would add hardware low-pass filtering in a future revision. Software averaging is enough for now.
- The ESD diodes E1 to E3 are bidirectional, so their orientation does not matter.
