"""File-based evidence storage with atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from pathlib import Path


class LocalEvidenceStore:
    """Persist raw payloads and observations on the local filesystem.

    All writes are atomic: content is written to a temporary file first,
    then atomically moved to the final destination via *os.replace*.
    """

    def __init__(self, base_path: str) -> None:
        self.base_path = Path(base_path).resolve()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def store_raw(
        self,
        source_id: str,
        raw_document_id: str,
        payload_bytes: bytes,
        meta: dict | None = None,
    ) -> str:
        """Save *payload_bytes* to ``base_path/{source_id}/raw/{raw_document_id}.bin``.

        If *meta* is supplied, a sidecar ``.meta.json`` file is written
        alongside the raw file.

        Returns the absolute path of the saved binary file.
        """
        raw_dir = self.base_path / source_id / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        dest = raw_dir / f"{raw_document_id}.bin"

        # Atomic write: .tmp → final
        tmp = tempfile.NamedTemporaryFile(
            dir=str(raw_dir),
            prefix=f".{raw_document_id}.",
            suffix=".tmp",
            delete=False,
        )
        try:
            tmp.write(payload_bytes)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, str(dest))
        except BaseException:
            # Best-effort cleanup of the temp file
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
            raise

        # Optional sidecar metadata
        if meta is not None:
            meta_path = raw_dir / f"{raw_document_id}.bin.meta.json"
            tmp2 = tempfile.NamedTemporaryFile(
                dir=str(raw_dir),
                prefix=f".{raw_document_id}.meta.",
                suffix=".tmp",
                delete=False,
            )
            try:
                with open(tmp2.name, "w", encoding="utf-8") as fh:
                    json.dump(meta, fh, ensure_ascii=False)
                os.replace(tmp2.name, str(meta_path))
            except BaseException:
                try:
                    os.unlink(tmp2.name)
                except Exception:
                    pass
                raise

        return str(dest)

    def store_observation(self, observation: object) -> str:
        """Save ``observation.to_dict()`` as JSON.

        The file is placed at ``base_path/{source_id}/obs/{observation_id}.json``.

        Returns the absolute path of the saved JSON file.
        """
        data = observation.to_dict()
        source_id = data.get("source_id", "unknown")
        obs_id = data.get("observation_id", uuid.uuid4().hex)

        obs_dir = self.base_path / source_id / "obs"
        obs_dir.mkdir(parents=True, exist_ok=True)

        dest = obs_dir / f"{obs_id}.json"

        tmp = tempfile.NamedTemporaryFile(
            dir=str(obs_dir),
            prefix=f".{obs_id}.",
            suffix=".tmp",
            delete=False,
            mode="w",
            encoding="utf-8",
        )
        try:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, str(dest))
        except BaseException:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
            raise

        return str(dest)

    def get_raw(self, raw_document_id: str) -> bytes | None:
        """Read and return the content of a raw document by its ID.

        Scans all ``raw/`` directories under every source_id.
        Returns *None* if the document cannot be found.
        """
        for raw_dir in self.base_path.rglob("raw/"):
            if not raw_dir.is_dir():
                continue
            target = raw_dir / f"{raw_document_id}.bin"
            if target.is_file():
                return target.read_bytes()
        return None

    def get_observation(self, observation_id: str) -> dict | None:
        """Read and parse a JSON observation by its ID.

        Scans all ``obs/`` directories under every source_id.
        Returns *None* if the document cannot be found.
        """
        for obs_dir in self.base_path.rglob("obs/"):
            if not obs_dir.is_dir():
                continue
            target = obs_dir / f"{observation_id}.json"
            if target.is_file():
                with open(target, "r", encoding="utf-8") as fh:
                    return json.load(fh)
        return None

    def get_manifest(self) -> dict:
        """Build a manifest dictionary describing all stored evidence.

        The returned dict has the form::

            {
                "generated_at": "<ISO-8601 UTC>",
                "sources": {
                    "<source_id>": {
                        "raw_count": N,
                        "raw_ids": [...],
                        "observation_count": M,
                        "observation_ids": [...],
                    }
                }
            }
        """
        manifest: dict = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sources": {},
        }

        if not self.base_path.is_dir():
            return manifest

        for source_dir in sorted(self.base_path.iterdir()):
            if not source_dir.is_dir():
                continue
            source_id = source_dir.name

            raw_ids: list[str] = []
            raw_dir = source_dir / "raw"
            if raw_dir.is_dir():
                for f in sorted(raw_dir.iterdir()):
                    if f.suffix == ".bin" and not f.name.startswith("."):
                        raw_ids.append(f.stem)

            obs_ids: list[str] = []
            obs_dir = source_dir / "obs"
            if obs_dir.is_dir():
                for f in sorted(obs_dir.iterdir()):
                    if f.suffix == ".json" and not f.name.startswith("."):
                        obs_ids.append(f.stem)

            manifest["sources"][source_id] = {
                "raw_count": len(raw_ids),
                "raw_ids": raw_ids,
                "observation_count": len(obs_ids),
                "observation_ids": obs_ids,
            }

        return manifest
