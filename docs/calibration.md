# Calibration

Cells differ a lot. The 4-H2S-1000 datasheet gives a sensitivity of 0.09 ± 0.04 µA/ppm and a zero current of up to ±0.4 µA, so an uncalibrated cell can be up to ±44 % off and show a few ppm in clean air. Every cell therefore needs a zero and a span calibration with certified test gas. The result goes into a calibration file (software/README.md).

| Effect | Size (datasheet) | Handled by |
|---|---|---|
| Sensitivity of one cell | 0.09 ± 0.04 µA/ppm | span, step 3 |
| Zero current of one cell | < ±0.4 µA at 20 °C (about ±4 ppm) | zero, step 2 |
| Temperature 15 to 35 °C | sensitivity −2 % to +1.5 %, baseline < 1 ppm | temperature compensation (datasheet curves) |
| Temperature 0 or 50 °C | sensitivity −6 % / +3 %, baseline +5.5 ppm at 50 °C | same; own curves (step 5) are better |
| Ageing | < 2 % of the signal per month | repeat steps 2 and 3 every 6 months |

## Not with rotten eggs

Rotten eggs or other home-made H2S give an unknown concentration that changes by the minute, mixed with other sulphur compounds and moisture. That can show at most that the cell responds, and only next to a reference meter. A calibration needs a known concentration.

## Equipment

- **Test gas:** certified H2S in synthetic air or nitrogen, with a fixed-flow regulator (about 0.5 L/min). One concentration in the middle of your range is enough for a span; a second one, for example 50 and 500 ppm, also shows linearity.
- **Zero air:** synthetic air from a cylinder, or clean outdoor air.
- **Tubing:** PTFE or FEP only. H2S sticks to silicone and rubber, and even a short piece makes the reading creep up slowly.
- **Gas feed:** a cap or flow cell over the cell's face, fed through an open T-piece so the excess vents and nothing is pressurised.
- **For step 5:** a fridge, the lab, and an incubator or drying oven.
- **Safety:** H2S is toxic (immediately dangerous to life at 100 ppm) and dulls the sense of smell. Work in a fume hood, vent the exhaust outside, wear a personal H2S monitor, and follow your lab's rules for gas cylinders.

## Procedure

Log while you calibrate; the CSV has the current and the temperature you need:

```bash
h2s-reader --stream --interval 2 --average 4 --csv cal-run.csv
```

1. **Warm-up:** power the board for at least 1 hour before calibrating, and overnight the first time.
2. **Zero:** feed zero air for 10 minutes. Average `i_we_ua` over the last 2 minutes, which gives `i0_ua`. The average `temp_c` gives `cal_temp_c`.
3. **Span:** feed test gas at concentration C until the reading is flat (T90 < 45 s, so wait 3 to 5 minutes), then average the last minute as `I_gas`.

   ```
   sensitivity_ua_per_ppm = (I_gas − i0_ua) / C
   ```

   With two concentrations the two sensitivities should agree within about 5 %.
4. **Write the file and check:**
   - copy `software/calibration.example.toml`, enter `i0_ua`, `sensitivity_ua_per_ppm` and `cal_temp_c`;
   - run `h2s-reader --calibration my-cell.toml --stream` on the test gas; it should show C;
   - in zero air, the current should return to `i0_ua` within a few minutes.
5. **Own temperature curves (optional):** repeat steps 2 and 3 at several temperatures, for example 5, 20, 30 and 40 °C. Keep the board at each temperature for at least 1 hour, and let it warm up slowly after the fridge so no water condenses. With `i0(T)` and `S(T)` from each run and 20 °C as reference:

   ```toml
   temp_sensitivity_pct = [[5, 100 × S(5)/S(20)], [20, 100], [30, ...], [40, ...]]
   temp_baseline_ppm    = [[5, (i0(5) − i0(20)) / S(20)], [20, 0], [30, ...], [40, ...]]
   ```

   Use the 20 °C values for `i0_ua` and `sensitivity_ua_per_ppm` with `cal_temp_c = 20`.
6. **Repeat:** redo steps 2 and 3 every 6 months, or when readings disagree with a reference instrument.

## Calibrating at another temperature

Write down the cell temperature during the calibration as `cal_temp_c`. The software then converts the sensitivity to 20 °C using the temperature curve, so a calibration at 26 °C works as well as one at 20 °C.

## Recalculating old data

If you logged `i_we_ua` and `temp_c` (CSV), a later calibration can be applied to old data with `compensated_ppm()` from `h2s_reader.h2s_sensor` (docs/how-it-works.md).
