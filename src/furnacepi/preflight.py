from __future__ import annotations

import argparse
import sys

from .config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check FurnacePi instrument connectivity")
    parser.add_argument("--config", default="config.example.toml", help="Path to config TOML")
    parser.add_argument("--skip-agilent-idn", action="store_true", help="Do not query Agilent *IDN?")
    parser.add_argument("--list-ports", action="store_true", help="List serial ports via pySerial")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    ok = True

    print("FurnacePi preflight")
    print(f"Agilent resource: {cfg.agilent.resource} mock={cfg.agilent.mock}")
    print(f"TEGAM port: {cfg.tegam.port} mock={cfg.tegam.mock}")
    print(f"Heater GPIO: {cfg.heater.gpio_pin} mock={cfg.heater.mock}")

    if args.list_ports:
        ok = _list_ports() and ok

    if not cfg.agilent.mock and cfg.agilent.enabled and not args.skip_agilent_idn:
        ok = _query_agilent_idn(cfg.agilent.resource, cfg.agilent.timeout_ms) and ok
    elif cfg.agilent.mock:
        print("Agilent *IDN? skipped because mock=true")

    if not cfg.tegam.mock and cfg.tegam.enabled:
        print("TEGAM command/response is not auto-tested here; use the exact command from MATLAB/manual.")
        print("Check port visibility with: python -m serial.tools.list_ports -v")
    elif cfg.tegam.mock:
        print("TEGAM serial check skipped because mock=true")

    return 0 if ok else 2


def _list_ports() -> bool:
    try:
        from serial.tools import list_ports
    except ImportError:
        print("pyserial is not installed", file=sys.stderr)
        return False

    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found")
        return False
    print("Serial ports:")
    for port in ports:
        print(f"  {port.device} - {port.description} [{port.hwid}]")
    return True


def _query_agilent_idn(resource: str, timeout_ms: int) -> bool:
    try:
        import pyvisa
    except ImportError:
        print("pyvisa/pyvisa-py is not installed", file=sys.stderr)
        return False

    try:
        rm = pyvisa.ResourceManager("@py")
        inst = rm.open_resource(resource)
        inst.timeout = timeout_ms
        try:
            print(f"Agilent *IDN?: {inst.query('*IDN?').strip()}")
        finally:
            inst.close()
        return True
    except Exception as exc:
        print(f"Agilent *IDN? failed: {exc}", file=sys.stderr)
        return False


if __name__ == "__main__":
    raise SystemExit(main())
