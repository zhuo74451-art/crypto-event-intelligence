"""Atomic checkpoint/output transactions for data factory acquisition.

C03/C04: Durable checkpoint with atomic output-before-checkpoint commit.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional


class AtomicCheckpointWriter:
    """Write output and checkpoint atomically.

    On commit: output file is written to a temp location, then atomically
    renamed to the target path. The checkpoint is written and fsynced
    only after the output is committed.
    """

    def __init__(self, output_dir: str):
        self._output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _output_path(self, run_id: str) -> str:
        return os.path.join(self._output_dir, f"{run_id}.jsonl")

    def write_output(
        self, run_id: str, records: List[dict], append: bool = False
    ) -> str:
        """Write records atomically to output file. Returns output path."""
        output_path = os.path.join(self._output_dir, f"{run_id}.jsonl")
        tmp_fd, tmp_path = tempfile.mkstemp(
            suffix=".tmp", dir=self._output_dir
        )
        try:
            with os.fdopen(tmp_fd, "w") as f:
                for r in records:
                    f.write(json.dumps(r, sort_keys=True) + "\n")
                f.flush()
                os.fsync(f.fileno())
            if append and os.path.exists(output_path):
                # Append mode: copy existing content then rename
                combined = os.path.join(self._output_dir, f"{run_id}_combined.tmp")
                with open(output_path) as existing:
                    existing_content = existing.read()
                with open(tmp_path) as tmp_file:
                    tmp_content = tmp_file.read()
                with open(combined, "w") as cf:
                    cf.write(existing_content)
                    cf.write(tmp_content)
                    cf.flush()
                    os.fsync(cf.fileno())
                shutil.move(combined, output_path)
                os.unlink(tmp_path)
            else:
                shutil.move(tmp_path, output_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
        return output_path

    def write_checkpoint(self, checkpoint: dict, path: str) -> None:
        """Write checkpoint atomically after output is committed."""
        tmp_fd, tmp_path = tempfile.mkstemp(
            suffix=".cp.tmp", dir=self._output_dir
        )
        try:
            with os.fdopen(tmp_fd, "w") as f:
                json.dump(checkpoint, f, sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            shutil.move(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
