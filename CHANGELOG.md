# Changelog

## 0.2.0 (2026-11-17)

- **Repository restructured:** now `hardware/`, `software/` and `docs/`, licensed CERN-OHL-P-2.0 (hardware) and MIT (software, docs).
- **Board files:** the latest KiCad design with production files H2S-RPi-V1. The schematic is also exported as PDF, with board renders and a `check.sh` for ERC and DRC.
- **Datasheets:** the phosphine datasheet that was filed by mistake as the cell's datasheet is removed.
- **Software:**
  - the Python package is now `h2s-reader`, with a `h2s-reader` command, and needs Python 3.11 or newer;
  - per-cell calibration comes from a TOML file (`Calibration`); the built-in defaults are the datasheet's nominal values;
  - temperature compensation with the datasheet's curves, or your own;
  - new options `--calibration`, `--average`, `--csv`; readings flag a saturated output;
  - `int_z` and `polarity` can be set in the calibration file, and REFCN follows `int_z`;
  - tests for calibration, the command line, averaging and saturation, plus a GitHub Actions workflow.
- **Documentation:** bring-up, calibration and how-it-works.

## 0.1.0 (2026-07-14)

- First version of the board and the reader.
