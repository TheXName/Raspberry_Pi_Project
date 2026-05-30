from __future__ import annotations

from dataclasses import dataclass
import time

from .config import SafetyConfig


class InterlockError(RuntimeError):
    pass


@dataclass
class SensorWatchdog:
    timeout_s: float
    last_ok_monotonic: float = 0.0

    def mark_ok(self, now: float | None = None) -> None:
        self.last_ok_monotonic = time.monotonic() if now is None else now

    def check(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        if self.last_ok_monotonic <= 0:
            raise InterlockError("No valid sensor reading yet")
        if now - self.last_ok_monotonic > self.timeout_s:
            raise InterlockError("Sensor timeout")


class SafetyInterlocks:
    def __init__(self, cfg: SafetyConfig) -> None:
        self.cfg = cfg
        self.sensor = SensorWatchdog(timeout_s=cfg.sensor_timeout_s)

    def validate_temperature(self, process_c: float, now: float | None = None) -> None:
        if process_c > self.cfg.max_temp_c:
            raise InterlockError(f"Overtemperature: {process_c:.2f} C")
        self.sensor.mark_ok(now)

    def validate_loop_delay(self, delay_s: float) -> None:
        if delay_s > self.cfg.max_loop_delay_s:
            raise InterlockError(f"Control loop delay too large: {delay_s:.3f} s")

    def check(self, now: float | None = None) -> None:
        self.sensor.check(now)
