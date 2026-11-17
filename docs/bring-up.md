# Bring-up

Checks for a new board, in order. You need a multimeter, a Raspberry Pi with I2C enabled and `h2s-reader` installed (software/README.md).

## Without the cell

1. **Visual check:** solder joints of U2 (WSON-14), U3 and U7, no bridges. CN1 is fitted, and the cell sockets sit straight.
2. **Supply:** connect 5 V and GND only. Measure:
   - 3.3 V on H5 pin 2, or on the 3.3V side of R1/R2;
   - 2.5 V on C6 (VREF).
3. **I2C:** connect SDA and SCL, then run `i2cdetect -y 1`. Expected: `48` and `49`. Then `h2s-reader --selftest`.
4. **Temperature:** `h2s-reader` should show the room temperature within about 1 °C. `---` means the NTC divider is open or shorted.

## With the cell

Plug the cell in with the power off. A new cell needs time to settle after power-up: wait at least 1 hour, and overnight the first time.

1. **Zero:** in clean air, `h2s-reader --stream` should show `Vout` near 0.50 V. The current should be within the datasheet baseline (±0.4 µA), so with nominal values the reading stays within about ±4 ppm.
2. **Direction:** expose the cell to a little H2S, for example from a certified test gas or bump-test cylinder. `Vout` should rise.
   - If it falls, set `polarity = -1` and `int_z = 0.67` in your calibration file. With a 20 % zero there is only 0.5 V of room downwards, so a falling signal would clip. After the change, `Vout` sits near 1.675 V in clean air.
3. **Calibrate:** follow docs/calibration.md.

## Use in biogas

- **Cross-sensitivity:** other gases can read as H2S. According to the datasheet, 35 ppm NO gives up to 3 ppm, while CO (300 ppm), H2 (1000 ppm), SO2 and NO2 give 0. Ammonia is not listed: test it if your gas contains a lot of it.
- **Oxygen:** electrochemical cells generally expect some oxygen at the counter electrode. In pure, oxygen-free biogas, check that the baseline stays stable over hours and flush the cell with air between measurements.
- **Range and lifetime:** the cell is rated for 0 to 1000 ppm, overload 2000 ppm, and about 2 years in air. Long exposure to high H2S shortens its life. Dilute the gas if you expect more than 1000 ppm.
- **Moisture:** keep the gas non-condensing (15 to 90 % RH). Condensation on the board or the cell gives wrong readings and corrosion. A hydrophobic filter in front of the cell and conformal coating on the board help.
- **Tubing:** use PTFE or FEP. H2S sticks to silicone and rubber, which makes the readings slow and too low.
