# Calibration of the 4-H2S-1000 cell

The datasheet sensitivity is 0.09 ± 0.04 µA/ppm, so an uncalibrated cell can read up to ±44 % off, and the zero current can be up to ±0.4 µA (±4 ppm). Every cell needs a zero and a span calibration with certified test gas.

Temperature matters much less. Between 15 and 35 °C the sensitivity changes by −2 % to +1.5 % and the baseline by less than 1 ppm. `h2s_reader` corrects for it with the datasheet's average curves (`TEMP_SENSITIVITY_PCT`, `TEMP_BASELINE_PPM` in `h2s_reader/config.py`), using the NTC under the cell.

## Why not rotten eggs

Rotten eggs or other home-made H2S give an unknown, changing concentration mixed with other sulphur compounds. Without a known concentration nothing can be calibrated; at most you can see that the cell responds, next to a reference meter.

## Equipment and safety

- **Test gas:** certified H2S in air or N2 (for example 50 ppm and about 500 ppm), with a 0.5 L/min fixed-flow regulator.
- **Zero air:** a synthetic air cylinder, or clean outdoor air.
- **Tubing:** PTFE or FEP only. H2S sticks to silicone and rubber.
- **Gas feed:** gas flows over the cell through an open T-piece, so nothing is pressurised.
- **Safety:** H2S is toxic (immediately dangerous at 100 ppm) and dulls the sense of smell. Work in a fume hood, vent outside, and wear a personal H2S monitor.

## Procedure

`python -m h2s_reader --stream --interval 2` prints `I_we` (cell current) and `T` (cell temperature) every 2 s.

1. **Warm-up:** power the board for at least 1 hour, overnight the first time.
2. **Zero:** zero air for 10 minutes. The average current of the last 2 minutes gives `I0_UA`; the average temperature gives `CAL_TEMP_C`.
3. **Span:** test gas at concentration C until flat (3 to 5 minutes). Then `SENSITIVITY_UA_PER_PPM = (I_gas − I0_UA) / C`. Two concentrations should give sensitivities within about 5 %.
4. **Enter the values:** put them into `h2s_reader/config.py`. In the Mzuzu rig, they go into `/etc/gasmon/config.yaml` instead (`h2s_pcb:` section, same names in lower case, see that repo's `docs/H2S-CALIBRATION.md`).
5. **Own temperature curves (optional):** repeat steps 2 and 3 at about 5, 20, 30 and 40 °C, at least 1 hour at each. Then, with the 20 °C run as reference:
   - `TEMP_SENSITIVITY_PCT = ((T, 100 × S(T) / S(20)), ...)`
   - `TEMP_BASELINE_PPM = ((T, (I0(T) − I0(20)) / S(20)), ...)`
6. **Repeat:** redo steps 2 and 3 every 6 months; the cell drifts by up to 2 % per month.

## Formula

```
S20 = S / rel(CAL_TEMP_C)
ppm = (I − I0 − S20 × (b(T) − b(CAL_TEMP_C))) / (S20 × rel(T))
```

`rel` is the sensitivity table divided by 100 and `b` is the baseline table. Values between table points are interpolated linearly; outside the table the end values are used. Without a valid NTC reading, the plain `(I − I0) / S` is used. This is `compensated_ppm()` in `h2s_reader/h2s_sensor.py`.
