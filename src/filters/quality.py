"""Quality filter — basic health checks on repo records."""

from datetime import datetime

from src.collectors.base import RepoRecord


class QualityFilter:
    """Apply basic quality gates to collected records."""

    def __init__(self, config: dict):
        self.filters = config.get("filters", {})
        self.max_inactive = self.filters.get("max_inactive_days", 90)
        self.min_readme = self.filters.get("min_readme_length", 200)
        self.require_license = self.filters.get("require_license", True)
        self.exclude_fork = self.filters.get("exclude_fork", True)

    def filter(self, records):
        return [r for r in records if self._check_all(r)]

    def _check_all(self, record):
        # Fork check
        if self.exclude_fork and record.raw_data.get("fork", False):
            return False

        # Inactivity check (graceful: skip if no data)
        pushed = record.pushed_at or record.raw_data.get("pushed_at", "")
        if pushed:
            try:
                pd = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
                if (datetime.utcnow() - pd.replace(tzinfo=None)).days > self.max_inactive:
                    return False
            except (ValueError, TypeError):
                pass

        # README length (only check if we actually have README data)
        readme = record.readme_text or ""
        if readme and len(readme) < self.min_readme:
            return False

        # License (only fail if we have explicit negative signal)
        if self.require_license:
            lic = record.license or record.raw_data.get("license", "")
            if lic and lic in ("NOASSERTION", "Other"):
                return False
            # Empty license = unknown → let through

        return True
