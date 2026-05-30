from __future__ import annotations

from dataclasses import dataclass
import math
import random
import time

from .config import AgilentConfig


@dataclass(frozen=True)
class AgilentReading:
    temperature_c: float
    raw: str


class Agilent34972A:
    def __init__(self, cfg: AgilentConfig) -> None:
        self.cfg = cfg
        self._resource = None

    def open(self) -> None:
        if self.cfg.mock or not self.cfg.enabled:
            return
        import pyvisa

        rm = pyvisa.ResourceManager("@py")
        inst = rm.open_resource(self.cfg.resource)
        inst.timeout = self.cfg.timeout_ms
        channel_list = ",".join(str(ch) for ch in self.cfg.temp_channels)
        inst.write(f"CONF:TEMP TC,{self.cfg.tc_type},(@{channel_list})")
        inst.write("FORM:READ:CHAN ON")
        inst.write("FORM:READ:TIME ON")
        self._resource = inst

    def read_once(self) -> AgilentReading:
        if self.cfg.mock or not self.cfg.enabled:
            t = time.monotonic()
            temp = 25.0 + 6.0 * math.sin(t / 60.0) + random.uniform(-0.1, 0.1)
            return AgilentReading(temperature_c=temp, raw=f"{temp:.6f}")
        if self._resource is None:
            raise RuntimeError("Agilent resource is not open")
        raw = str(self._resource.query("READ?")).strip()
        return AgilentReading(temperature_c=_first_float(raw), raw=raw)

    def close(self) -> None:
        if self._resource is not None:
            self._resource.close()
            self._resource = None


def _first_float(raw: str) -> float:
    first = raw.replace("\n", ",").split(",")[0].strip()
    return float(first)
