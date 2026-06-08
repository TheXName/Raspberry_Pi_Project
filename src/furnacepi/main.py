from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
from enum import Enum
import signal
import sys
import time

from .agilent34972 import Agilent34972A
from .config import AppConfig, load_config
from .heater import TimeProportioningSSR
from .interlocks import InterlockError, SafetyInterlocks
from .logger_dt import DtLogger, DtRow
from .profile import ProportionalHeater, TemperatureProgram
from .tegam3550 import Tegam3550


class State(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FAULT = "FAULT"
    SAFE_OFF = "SAFE_OFF"


_STOP_REQUESTED = False


def _stop_handler(signum: int, frame: object) -> None:
    global _STOP_REQUESTED
    _STOP_REQUESTED = True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the FurnacePi experiment controller")
    parser.add_argument("--config", default="config.real.toml", help="Path to config TOML")
    parser.add_argument("--dry-run-seconds", type=float, default=None, help="Stop automatically after N seconds")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    return run(cfg, dry_run_seconds=args.dry_run_seconds)


def run(cfg: AppConfig, *, dry_run_seconds: float | None = None) -> int:
    signal.signal(signal.SIGINT, _stop_handler)
    signal.signal(signal.SIGTERM, _stop_handler)

    agilent = Agilent34972A(cfg.agilent)
    tegam = Tegam3550(cfg.tegam)
    heater = TimeProportioningSSR(cfg.heater)
    safety = SafetyInterlocks(cfg.safety)
    profile = TemperatureProgram.from_config(cfg.profile)
    controller = ProportionalHeater(cfg.control.proportional_band_c)
    logger: DtLogger | None = None
    state = State.IDLE

    try:
        heater.open()
        heater.force_off()
        agilent.open()
        tegam.open()
        logger = DtLogger(
            cfg.logging.results_dir,
            flush_every_lines=cfg.logging.flush_every_lines,
            strict_dt=cfg.logging.strict_dt,
            metadata={"config": asdict(cfg), "started_at": datetime.now().astimezone().isoformat()},
        )
        state = State.RUNNING
        t0 = time.monotonic()
        last_loop = t0

        while not _STOP_REQUESTED:
            loop_start = time.monotonic()
            safety.validate_loop_delay(loop_start - last_loop)
            last_loop = loop_start
            elapsed_s = loop_start - t0
            if dry_run_seconds is not None and elapsed_s >= dry_run_seconds:
                break

            ag = agilent.read_once()
            safety.validate_temperature(ag.temperature_c, loop_start)
            safety.check(loop_start)
            tg = tegam.measure_once()

            setpoint_c = profile.setpoint_at(elapsed_s)
            duty = controller.compute_duty(setpoint_c, ag.temperature_c)
            heater.set_duty(duty)
            heater_on = heater.update(loop_start)

            logger.write_row(
                DtRow(
                    iso_ts=datetime.now().astimezone().isoformat(timespec="microseconds"),
                    elapsed_s=elapsed_s,
                    setpoint_c=setpoint_c,
                    process_c=ag.temperature_c,
                    tegam_primary=tg.primary,
                    tegam_secondary=tg.secondary,
                    duty=duty,
                    heater_on=int(heater_on),
                    state=state.value,
                )
            )

            sleep_s = cfg.control.loop_period_s - (time.monotonic() - loop_start)
            if sleep_s > 0:
                time.sleep(sleep_s)

        state = State.SAFE_OFF
        return 0
    except (InterlockError, TimeoutError, OSError, RuntimeError, ValueError) as exc:
        state = State.FAULT
        print(f"FAULT: {exc}", file=sys.stderr)
        return 2
    finally:
        heater.force_off()
        if logger is not None:
            logger.write_row(
                DtRow(
                    iso_ts=datetime.now().astimezone().isoformat(timespec="microseconds"),
                    elapsed_s=0.0,
                    setpoint_c=0.0,
                    process_c=0.0,
                    tegam_primary=None,
                    tegam_secondary=None,
                    duty=0.0,
                    heater_on=0,
                    state=state.value,
                )
            )
            logger.close()
        tegam.close()
        agilent.close()
        heater.close()
