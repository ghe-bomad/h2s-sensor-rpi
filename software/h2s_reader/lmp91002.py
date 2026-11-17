"""LMP91002 potentiostat AFE register driver. The I2C bus is injected.

MENB is tied to GND on this board, so the device is always enabled; no GPIO
handling is required here.
"""

import time

from . import config


class LMP91002:
    def __init__(self, bus, addr=config.LMP91002_ADDR):
        self._bus = bus
        self._addr = addr

    def _read(self, reg):
        return self._bus.read_byte_data(self._addr, reg)

    def _write(self, reg, value):
        self._bus.write_byte_data(self._addr, reg, value)

    def wait_ready(self, timeout_s=1.0, poll_s=0.005):
        """Poll STATUS until bit0 (ready) is set; raise TimeoutError otherwise."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self._read(config.REG_STATUS) & 0x01:
                return True
            time.sleep(poll_s)
        raise TimeoutError("LMP91002 STATUS never signalled ready")

    def configure(self, refcn=config.REFCN_VALUE):
        """Unlock, write TIACN (7 kOhm, 10 Ohm load) and REFCN, lock, then set 3-lead mode.

        refcn: 0x80 = external reference, 20 % zero (default); 0xC0 = 67 % zero.
        """
        self._write(config.REG_LOCK, config.LOCK_UNLOCK)
        self._write(config.REG_TIACN, config.TIACN_VALUE)
        self._write(config.REG_REFCN, refcn)
        self._write(config.REG_LOCK, config.LOCK_LOCK)
        self._write(config.REG_MODECN, config.MODECN_VALUE)
