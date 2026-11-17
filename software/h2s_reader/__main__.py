"""Command line: h2s-reader [--selftest] [--stream] [--calibration FILE] [--csv FILE] ..."""

from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, config
from .calibration import Calibration, CalibrationError
from .h2s_sensor import H2SSensor, Reading

CSV_COLUMNS = ["time_utc", "ppm", "i_we_ua", "vout_v", "temp_c", "r_ntc_ohm", "saturated"]


def format_reading(r: Reading) -> str:
    temp = "  --- C" if math.isnan(r.temp_c) else f"{r.temp_c:6.2f} C"
    line = (f"H2S={r.ppm:7.2f} ppm  I_we={r.i_we_uA:7.3f} uA  "
            f"Vout={r.vout_v:6.4f} V  T={temp}")
    return line + "  SATURATED" if r.saturated else line


def csv_row(r: Reading, now: datetime) -> list:
    return [now.isoformat(timespec="seconds").replace("+00:00", "Z"),
            f"{r.ppm:.3f}", f"{r.i_we_uA:.4f}", f"{r.vout_v:.5f}",
            "" if math.isnan(r.temp_c) else f"{r.temp_c:.2f}",
            "" if math.isnan(r.r_ntc_ohm) else f"{r.r_ntc_ohm:.0f}",
            int(r.saturated)]


def selftest(bus) -> int:
    ok = True
    for name, addr in (("LMP91002", config.LMP91002_ADDR),
                       ("ADS1115", config.ADS1115_ADDR)):
        try:
            bus.read_byte(addr)
            print(f"OK   {name} @ 0x{addr:02X}")
        except OSError:
            print(f"FAIL {name} @ 0x{addr:02X} not responding")
            ok = False
    return 0 if ok else 1


def _open_bus(num: int):
    from smbus2 import SMBus  # lazy: only needed on real hardware
    return SMBus(num)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="h2s-reader",
        description="Read the H2S sensor board over I2C and print H2S (ppm) and temperature.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--bus", type=int, default=config.I2C_BUS, help="I2C bus number (default 1)")
    p.add_argument("--selftest", action="store_true",
                   help="check that both chips answer on I2C, then exit")
    p.add_argument("--calibration", type=Path, metavar="FILE",
                   help="calibration file (TOML); without it the datasheet nominal values are used")
    p.add_argument("--stream", action="store_true", help="keep reading until Ctrl-C")
    p.add_argument("--interval", type=float, default=2.0, help="seconds between readings (default 2)")
    p.add_argument("--average", type=int, default=1, metavar="N",
                   help="average N conversions per reading (default 1)")
    p.add_argument("--csv", type=Path, metavar="FILE",
                   help="also append every reading to this CSV file")
    return p


def main(argv=None, bus_factory=_open_bus, sleep=time.sleep, clock=None) -> int:
    args = build_parser().parse_args(argv)
    if args.average < 1:
        print("--average must be at least 1", file=sys.stderr)
        return 2
    try:
        cal = Calibration.from_toml(args.calibration) if args.calibration else Calibration()
    except CalibrationError as exc:
        print(f"Calibration error: {exc}", file=sys.stderr)
        return 2
    if not args.calibration and not args.selftest:
        print("Note: no --calibration file, using datasheet nominal values (up to +/-44 % off).",
              file=sys.stderr)

    bus = bus_factory(args.bus)
    if args.selftest:
        return selftest(bus)

    sensor = H2SSensor(bus, cal)
    sensor.configure()
    clock = clock or (lambda: datetime.now(timezone.utc))
    csv_file = None
    try:
        if args.csv:
            new = not args.csv.exists() or args.csv.stat().st_size == 0
            csv_file = args.csv.open("a", newline="", encoding="utf-8")
            writer = csv.writer(csv_file)
            if new:
                writer.writerow(CSV_COLUMNS)
        while True:
            reading = sensor.read(average=args.average)
            print(format_reading(reading), flush=True)
            if csv_file:
                writer.writerow(csv_row(reading, clock()))
                csv_file.flush()
            if not args.stream:
                break
            sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        if csv_file:
            csv_file.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
