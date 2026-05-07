"""Findings file writer for validation result schemas.

Per-run-id findings file writer that emits a deterministic JSON envelope.

Construction resolves the output directory:
  1. ``output_dir`` argument if provided
  2. environment variable GX_VALIDATION_FINDINGS_DIR if set
  3. else _DEFAULT_DIR (gitignored in the gx repo)

The filename is ``f"{run_id}.json"``. Findings are accumulated in memory and
flushed on ``close()``; the file is written atomically (write to ``.tmp``,
then ``Path.replace``). Within a file, findings are sorted by
``(expectation_type, engine, result_format)`` for deterministic diffs across
runs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from typing_extensions import Self

    from great_expectations.core.validation_result_schemas.types import Finding

_DEFAULT_DIR: Path = Path("tests/_artifacts/validation_result_schemas/findings")
_ENV_VAR: str = "GX_VALIDATION_FINDINGS_DIR"
SCHEMA_VERSION: int = 1


def _get_gx_version() -> str:
    """Return the installed great_expectations version string."""
    try:
        import great_expectations

        return str(great_expectations.__version__)
    except (ImportError, AttributeError):
        return "unknown"


class FindingsWriter:
    """Per-run-id findings file writer.

    Construction resolves the output directory:
      1. environment variable GX_VALIDATION_FINDINGS_DIR if set
      2. else _DEFAULT_DIR (gitignored in the gx repo)

    The filename is f"{run_id}.json". Findings are appended in memory and
    flushed on close(); the file is written atomically (write to .tmp, rename).
    Within a file, findings are sorted by (expectation_type, engine,
    result_format) for deterministic diffs across runs.
    """

    def __init__(self, run_id: str, output_dir: Optional[Path] = None) -> None:
        self._run_id = run_id
        self._findings: List[Finding] = []
        self._started_at_utc: str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Directory resolution: arg → env var → _DEFAULT_DIR
        if output_dir is not None:
            self._output_dir = Path(output_dir)
        else:
            env_val = os.environ.get(_ENV_VAR)  # noqa: TID251 # os.environ allowed in config files
            if env_val is not None:
                self._output_dir = Path(env_val)
            else:
                self._output_dir = _DEFAULT_DIR

        self._output_dir.mkdir(parents=True, exist_ok=True)

    def write_finding(self, finding: Finding) -> None:
        """Append *finding* to the in-memory list."""
        self._findings.append(finding)

    def close(self) -> None:
        """Sort findings and write them atomically to the output file."""
        completed_at_utc: str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Sort deterministically by (expectation_type, engine, result_format)
        sorted_findings: List[Finding] = sorted(
            self._findings,
            key=lambda f: (
                f.get("expectation_type", ""),
                f.get("engine", ""),
                f.get("result_format", ""),
            ),
        )

        envelope = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self._run_id,
            "started_at_utc": self._started_at_utc,
            "completed_at_utc": completed_at_utc,
            "gx_version": _get_gx_version(),
            "findings": sorted_findings,
        }

        filepath = self._output_dir / f"{self._run_id}.json"
        tmp_path = Path(str(filepath) + ".tmp")

        tmp_path.write_text(json.dumps(envelope, indent=2))
        tmp_path.replace(filepath)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
