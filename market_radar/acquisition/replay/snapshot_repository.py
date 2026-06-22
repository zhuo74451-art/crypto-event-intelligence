from __future__ import annotations
import json
import os
from datetime import datetime
from ..contracts.replay import ReplayMode, ReplayQuery, ReplayResult
from ..contracts.timestamps import utc_now


class SnapshotRepository:
    """Persist and load point-in-time snapshots."""

    def save_snapshot(self, as_of_time: datetime, observations: list, base_path: str = ".") -> str:
        timestamp = as_of_time.strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp}.json"
        path = os.path.join(base_path, filename)
        data = {
            "snapshot_version": "1.0.0",
            "as_of_time": as_of_time.isoformat(),
            "generated_at": utc_now().isoformat(),
            "observations": [o.to_dict() if hasattr(o, "to_dict") else o for o in observations],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return path

    def load_snapshot(self, path: str) -> ReplayResult:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        as_of = datetime.fromisoformat(data["as_of_time"])
        query = ReplayQuery(as_of_time=as_of)
        return ReplayResult(
            query=query,
            observations=tuple(data.get("observations", [])),
            observation_count=len(data.get("observations", [])),
            generated_at=data.get("generated_at", ""),
        )

    @staticmethod
    def list_snapshots(base_path: str = ".") -> list[dict]:
        snapshots = []
        for fname in sorted(os.listdir(base_path)):
            if fname.startswith("snapshot_") and fname.endswith(".json"):
                path = os.path.join(base_path, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    snapshots.append({
                        "filename": fname,
                        "as_of_time": data.get("as_of_time", ""),
                        "observation_count": len(data.get("observations", [])),
                    })
                except (json.JSONDecodeError, OSError):
                    snapshots.append({"filename": fname, "error": "corrupt"})
        return snapshots
