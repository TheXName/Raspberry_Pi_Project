from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class AgilentConfig:
    enabled: bool = True
    mock: bool = False
    # Sem zadaj VISA adres Agilent 34972A, najcastejsie TCPIP0::<IP>::inst0::INSTR.
    resource: str = "TCPIP0::192.168.1.50::inst0::INSTR"
    # Sem zadaj kanaly, na ktorych su pripojene teplotne senzory pece.
    temp_channels: list[int] = field(default_factory=lambda: [101])
    tc_type: str = "K"
    timeout_ms: int = 3000


@dataclass(frozen=True)
class TegamConfig:
    enabled: bool = True
    mock: bool = False
    # Sem zadaj stabilny Linux port USB-RS232 adaptera, napr. /dev/tegam3550.
    port: str = "/dev/tegam3550"
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = "N"
    stopbits: int = 1
    timeout_s: float = 1.0
    write_timeout_s: float = 1.0
    terminator: str = "\r"
    # Pravdepodobne uvodne prikazy pre TEGAM 3550 RS-232; over ich so starym MATLAB kodom.
    startup_commands: list[str] = field(default_factory=lambda: ["E3", "REN", "O1"])
    # Pravdepodobny prikaz merania pri rezime E3 je T0; over ho so starym MATLAB kodom.
    measurement_command: str = "T0"


@dataclass(frozen=True)
class HeaterConfig:
    mock: bool = True
    # Sem zadaj BCM cislo GPIO pinu, ktory ovlada SSR/rele driver.
    gpio_pin: int = 17
    active_high: bool = True
    cycle_s: float = 5.0


@dataclass(frozen=True)
class SafetyConfig:
    # Sem zadaj maximalnu dovolenu teplotu pece v stupnoch C.
    max_temp_c: float = 900.0
    sensor_timeout_s: float = 3.0
    require_time_sync: bool = False
    max_loop_delay_s: float = 5.0


@dataclass(frozen=True)
class LoggingConfig:
    results_dir: str = "Results"
    flush_every_lines: int = 1
    strict_dt: bool = False


@dataclass(frozen=True)
class SegmentConfig:
    target_c: float
    ramp_c_per_min: float
    hold_s: float


@dataclass(frozen=True)
class ProfileConfig:
    # Sem zadaj startovaciu teplotu programu v stupnoch C.
    start_c: float = 25.0
    segments: list[SegmentConfig] = field(default_factory=list)


@dataclass(frozen=True)
class ControlConfig:
    loop_period_s: float = 1.0
    proportional_band_c: float = 20.0


@dataclass(frozen=True)
class AppConfig:
    agilent: AgilentConfig
    tegam: TegamConfig
    heater: HeaterConfig
    safety: SafetyConfig
    logging: LoggingConfig
    profile: ProfileConfig
    control: ControlConfig


def _section(data: dict, name: str) -> dict:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"Config section [{name}] must be a table")
    return value


def load_config(path: str | Path) -> AppConfig:
    raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    profile_raw = _section(raw, "profile")
    segments = [
        SegmentConfig(
            target_c=float(item["target_c"]),
            ramp_c_per_min=float(item["ramp_c_per_min"]),
            hold_s=float(item.get("hold_s", 0.0)),
        )
        for item in profile_raw.get("segments", [])
    ]
    return AppConfig(
        agilent=AgilentConfig(**_section(raw, "agilent")),
        tegam=TegamConfig(**_section(raw, "tegam")),
        heater=HeaterConfig(**_section(raw, "heater")),
        safety=SafetyConfig(**_section(raw, "safety")),
        logging=LoggingConfig(**_section(raw, "logging")),
        profile=ProfileConfig(start_c=float(profile_raw.get("start_c", 25.0)), segments=segments),
        control=ControlConfig(**_section(raw, "control")),
    )
