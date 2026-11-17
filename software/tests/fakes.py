"""In-memory smbus2-compatible double for tests (no hardware)."""


class FakeBus:
    def __init__(self):
        self.byte_regs = {}            # (addr, reg) -> value
        self.block_reads = {}          # (addr, reg) -> [bytes]
        self.conversion_by_config = {} # config_word -> [msb, lsb] or [[msb, lsb], ...]
        self.writes = []               # (addr, reg, value)
        self.block_writes = []         # (addr, reg, [bytes])
        self._last_config = None
        self.present = set()           # addrs that ACK on read_byte

    # --- 8-bit register access (LMP91002) ---
    def read_byte_data(self, addr, reg):
        return self.byte_regs.get((addr, reg), 0x00)

    def write_byte_data(self, addr, reg, value):
        self.byte_regs[(addr, reg)] = value
        self.writes.append((addr, reg, value))

    # --- 16-bit block access (ADS1115) ---
    def write_i2c_block_data(self, addr, reg, data):
        data = list(data)
        self.block_writes.append((addr, reg, data))
        if reg == 0x01:  # ADS config register: remember requested channel
            self._last_config = (data[0] << 8) | data[1]

    def read_i2c_block_data(self, addr, reg, length):
        if reg == 0x00 and self._last_config in self.conversion_by_config:
            value = self.conversion_by_config[self._last_config]
            if value and isinstance(value[0], (list, tuple)):   # a sequence of results
                value = value.pop(0) if len(value) > 1 else value[0]
            return list(value)[:length]
        return list(self.block_reads.get((addr, reg), [0, 0]))[:length]

    # --- presence probe (selftest) ---
    def read_byte(self, addr):
        if self.present and addr not in self.present:
            raise OSError("no ACK")
        return 0x00
