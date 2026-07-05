"""Dedup module: in-memory + JSON file persistence."""

import json
from datetime import datetime
from pathlib import Path

from src.collectors.base import RepoRecord


class Deduplicator:
    """Deduplicator backed by a JSON state file."""

    def __init__(self, db_path=None):
        if db_path:
            self.data_dir = Path(db_path).parent
        else:
            self.data_dir = Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / "dedup_state.json"
        self.state = self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass
        return {"repos": {}}

    def _save_state(self):
        self.state_file.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def deduplicate(self, records):
        now = datetime.utcnow()
        current_week = now.strftime("%Y-W%V")
        new_records = []
        already_seen = 0

        for record in records:
            repo_id = record.repo_id
            existing = self.state["repos"].get(repo_id)
            if existing:
                existing["last_seen_at"] = now.isoformat()
                existing["seen_count"] = existing.get("seen_count", 1) + 1
                already_seen += 1
                if existing.get("first_seen_week") == current_week:
                    new_records.append(record)
            else:
                self.state["repos"][repo_id] = {
                    "first_seen_week": current_week,
                    "first_seen_at": now.isoformat(),
                    "last_seen_at": now.isoformat(),
                    "seen_count": 1,
                }
                new_records.append(record)

        self._save_state()
        return new_records, already_seen

    def get_stats(self):
        now = datetime.utcnow()
        current_week = now.strftime("%Y-W%V")
        total = len(self.state["repos"])
        new_this_week = sum(
            1
            for r in self.state["repos"].values()
            if r.get("first_seen_week") == current_week
        )
        return {"total_seen": total, "new_this_week": new_this_week}
