"""Dedup module: in-memory + JSON file persistence."""

import os
import re
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
        week_override = os.environ.get("REPORT_WEEK", "")
        if week_override and re.fullmatch(r"\d{4}-W\d{2}", week_override):
            self.state_file = self.data_dir / f"dedup_state_{week_override}.json"

        self.state = self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                if isinstance(data, dict) and isinstance(data.get("repos"), dict):
                    return data
                raise ValueError("unexpected schema")
            except (json.JSONDecodeError, IOError, ValueError):
                backup = self.state_file.with_name(
                    f"{self.state_file.name}.corrupt-{int(datetime.now().timestamp())}"
                )
                try:
                    self.state_file.replace(backup)
                    print(f"[Dedup] Corrupt state file backed up to {backup.name}")
                except OSError:
                    pass
        return {"repos": {}}

    def save(self):
        """Persist state atomically (tmp file + os.replace)."""
        tmp = self.state_file.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, self.state_file)

    def deduplicate(self, records):
        now = datetime.utcnow()
        current_week = now.strftime("%G-W%V")
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

        return new_records, already_seen

    def get_stats(self):
        now = datetime.utcnow()
        current_week = now.strftime("%G-W%V")
        total = len(self.state["repos"])
        new_this_week = sum(
            1
            for r in self.state["repos"].values()
            if r.get("first_seen_week") == current_week
        )
        return {"total_seen": total, "new_this_week": new_this_week}
