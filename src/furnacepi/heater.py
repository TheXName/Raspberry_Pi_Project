from __future__ import annotations

import time

from .config import HeaterConfig


class TimeProportioningSSR:
    def __init__(self, cfg: HeaterConfig) -> None:
        self.cfg = cfg
        self.duty = 0.0
        self._cycle_anchor = time.monotonic()
        self._out = None
        self._mock_on = False

    def open(self) -> None:
        if self.cfg.mock:
            self.force_off()
            return
        from gpiozero import OutputDevice

        self._out = OutputDevice(
            pin=self.cfg.gpio_pin,
            active_high=self.cfg.active_high,
            initial_value=False,
        )
        self.force_off()

    @property
    def is_on(self) -> bool:
        return self._mock_on if self.cfg.mock else bool(self._out and self._out.value)

    def set_duty(self, duty: float) -> None:
        self.duty = max(0.0, min(1.0, duty))

    def force_off(self) -> None:
        self.duty = 0.0
        self._set_output(False)

    def update(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        elapsed = now - self._cycle_anchor
        if elapsed >= self.cfg.cycle_s:
            self._cycle_anchor = now
            elapsed = 0.0
        on_time = self.cfg.cycle_s * self.duty
        heater_on = elapsed < on_time and self.duty > 0.0
        self._set_output(heater_on)
        return heater_on

    def close(self) -> None:
        self.force_off()
        if self._out is not None:
            self._out.close()
            self._out = None

    def _set_output(self, state: bool) -> None:
        if self.cfg.mock:
            self._mock_on = state
            return
        if self._out is None:
            return
        if state:
            self._out.on()
        else:
            self._out.off()
