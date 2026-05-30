from __future__ import annotations

from dataclasses import dataclass

from .config import ProfileConfig, SegmentConfig


@dataclass(frozen=True)
class Segment:
    target_c: float
    ramp_c_per_min: float
    hold_s: float


class TemperatureProgram:
    def __init__(self, start_c: float, segments: list[Segment]) -> None:
        self.start_c = start_c
        self.segments = segments

    @classmethod
    def from_config(cls, cfg: ProfileConfig) -> "TemperatureProgram":
        return cls(
            start_c=cfg.start_c,
            segments=[_segment_from_config(item) for item in cfg.segments],
        )

    def setpoint_at(self, elapsed_s: float) -> float:
        temp = self.start_c
        cursor = 0.0
        for seg in self.segments:
            delta = seg.target_c - temp
            ramp_rate_c_s = max(seg.ramp_c_per_min, 1e-9) / 60.0
            ramp_s = abs(delta) / ramp_rate_c_s
            if elapsed_s <= cursor + ramp_s:
                direction = 1.0 if delta >= 0.0 else -1.0
                return temp + direction * ramp_rate_c_s * (elapsed_s - cursor)
            cursor += ramp_s
            temp = seg.target_c
            if elapsed_s <= cursor + seg.hold_s:
                return temp
            cursor += seg.hold_s
        return temp


class ProportionalHeater:
    def __init__(self, band_c: float) -> None:
        if band_c <= 0:
            raise ValueError("Proportional band must be positive")
        self.band_c = band_c

    def compute_duty(self, setpoint_c: float, measured_c: float) -> float:
        error = setpoint_c - measured_c
        if error <= 0:
            return 0.0
        if error >= self.band_c:
            return 1.0
        return error / self.band_c


def _segment_from_config(cfg: SegmentConfig) -> Segment:
    return Segment(
        target_c=cfg.target_c,
        ramp_c_per_min=cfg.ramp_c_per_min,
        hold_s=cfg.hold_s,
    )
