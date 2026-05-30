from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
import os
from typing import Any


@dataclass(frozen=True)
class DtRow:
    iso_ts: str
    elapsed_s: float
    setpoint_c: float
    process_c: float
    tegam_primary: float | None
    tegam_secondary: float | None
    duty: float
    heater_on: int
    state: str


class DtLogger:
    def __init__(
        self,
        results_dir: str | Path,
        *,
        flush_every_lines: int = 1,
        strict_dt: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H%M%S")
        self.path = self.results_dir / f"Data-{stamp}.dt"
        self.metadata_path = self.results_dir / f"Data-{stamp}.json"
        self.flush_every_lines = max(1, flush_every_lines)
        self.strict_dt = strict_dt
        self._line_count = 0
        self._fh = self.path.open("w", encoding="utf-8", newline="\n")
        if not strict_dt:
            self._fh.write(
                "# iso_ts\telapsed_s\tsetpoint_c\tprocess_c\ttegam_primary\t"
                "tegam_secondary\tduty\theater_on\tstate\n"
            )
        if metadata is not None:
            self.metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    def write_row(self, row: DtRow) -> None:
        self._fh.write(self._format_row(row) + "\n")
        self._line_count += 1
        if self._line_count % self.flush_every_lines == 0:
            self.flush()

    def flush(self) -> None:
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def close(self) -> None:
        if not self._fh.closed:
            self.flush()
            self._fh.close()

    def _format_row(self, row: DtRow) -> str:
        values = asdict(row)
        if self.strict_dt:
            values.pop("state", None)
        return "\t".join(_format_value(v) for v in values.values())


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6e}"
    return str(value)
