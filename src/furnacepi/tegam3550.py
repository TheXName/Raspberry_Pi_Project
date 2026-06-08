from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import random
import re

from .config import TegamConfig

_NUM_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?")


@dataclass(frozen=True)
class TegamReading:
    raw: str
    values: list[float]
    primary: float | None
    secondary: float | None


class Tegam3550:
    def __init__(self, cfg: TegamConfig) -> None:
        self.cfg = cfg
        self._serial = None

    def open(self) -> None:
        if self.cfg.mock or not self.cfg.enabled:
            return
        import serial

        self._serial = serial.Serial(
            port=self.cfg.port,
            baudrate=self.cfg.baudrate,
            bytesize=self.cfg.bytesize,
            parity=self.cfg.parity,
            stopbits=self.cfg.stopbits,
            timeout=self.cfg.timeout_s,
            write_timeout=self.cfg.write_timeout_s,
        )
        for command in self.cfg.startup_commands:
            self.send_cmd(command)

    def send_cmd(self, command: str) -> None:
        if self.cfg.mock or not self.cfg.enabled:
            return
        if self._serial is None:
            raise RuntimeError("TEGAM serial port is not open")
        payload = (command + self.cfg.terminator).encode("ascii")
        self._serial.write(payload)

    def read_line(self) -> str:
        if self.cfg.mock or not self.cfg.enabled:
            c_value = 1.2e-9 + random.uniform(-2e-12, 2e-12)
            d_value = random.uniform(-5e-4, 5e-4)
            return f"{c_value:.6E},{d_value:.6E}"
        if self._serial is None:
            raise RuntimeError("TEGAM serial port is not open")
        line = self._serial.readline()
        if not line:
            raise TimeoutError("TEGAM read timeout")
        return line.decode("ascii", errors="replace").strip()

    def measure_once(self) -> TegamReading:
        if self.cfg.measurement_command:
            self.send_cmd(self.cfg.measurement_command)
        return parse_tegam_response(self.read_line())

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None


def parse_tegam_response(line: str) -> TegamReading:
    raw = line.strip()
    values = [float(x) for x in _NUM_RE.findall(raw)]
    return TegamReading(
        raw=raw,
        values=values,
        primary=values[0] if len(values) >= 1 else None,
        secondary=values[1] if len(values) >= 2 else None,
    )


def reading_as_dict(reading: TegamReading) -> dict[str, Any]:
    return {
        "raw": reading.raw,
        "values": reading.values,
        "primary": reading.primary,
        "secondary": reading.secondary,
    }
