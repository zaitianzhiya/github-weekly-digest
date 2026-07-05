"""Citation collectors — scrape Tier 2 curated platforms for repo mentions."""

import os, re, requests
from datetime import datetime

from .base import BaseCollector, RepoRecord


class CitationCollector(BaseCollector):
    """Collect repos recommended by curated platforms (OpenGithubs, HelloGitHub, etc.)."""

    def __init__(self, config: dict, source_key: str):
        super().__init__(config)
        self.source_key = source_key
        self.sc = config["sources"].get(source_key, {})
        self.repo = self.sc.get("repo", "")
        self.token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")

    def _auth_headers(self):
        h = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def collect(self):
        if not self.repo:
            print(f"[{self.source_key}] No repo configured.")
            return []
        content = self._fetch_content()
        if not content:
            return []
        repos = self._extract_repos(content)
        citation = self.create_citation(self.source_key)
        records = []
        for repo in repos:
            record = RepoRecord(
                repo_id=repo["full_name"], full_name=repo["full_name"],
                html_url=f"https://github.com/{repo['full_name']}",
                description=repo.get("description",""), language=repo.get("language",""),
                stars=repo.get("stars",0), weekly_growth=repo.get("weekly_growth",0),
                daily_growth=0, forks=0, open_issues=0,
                created_at="", pushed_at="", license="", readme_text="",
                topics=[], categories=repo.get("categories",[]),
                confidence_score=15.0, confidence_grade="D",
                citation_count=1, citations=[citation],
                sources=[citation.source_name],
                first_seen=datetime.utcnow().isoformat(),
                last_updated=datetime.utcnow().isoformat(), raw_data=repo,
            )
            records.append(record)
        return records

    def _fetch_content(self):
        if self.source_key == "opengithubs":
            return self._http_get(f"https://raw.githubusercontent.com/{self.repo}/main/README.md")
        if self.source_key == "ruanyf_weekly":
            return self._fetch_ruanyf_latest()
        if self.source_key == "githubdaily":
            return self._http_get(f"https://raw.githubusercontent.com/{self.repo}/master/README.md")
        if self.source_key == "hellogithub":
            return self._fetch_hellogithub_latest()
        return None

    def _fetch_ruanyf_latest(self):
        try:
            resp = requests.get(f"https://api.github.com/repos/{self.repo}/contents/docs", headers=self._auth_headers(), timeout=15)
            if resp.status_code != 200:
                return None
            files = [f["name"] for f in resp.json() if f["name"].startswith("issue-")]
            if not files:
                return None
            num_files = sorted(files, key=lambda x: int(re.findall(r'\d+',x)[0]) if re.findall(r'\d+',x) else 0)
            latest = num_files[-1]
            return self._http_get(f"https://raw.githubusercontent.com/{self.repo}/master/docs/{latest}")
        except requests.RequestException as e:
            print(f"[{self.source_key}] Failed: {e}")
            return None

    def _fetch_hellogithub_latest(self):
        try:
            resp = requests.get(f"https://api.github.com/repos/{self.repo}/contents/content", headers=self._auth_headers(), timeout=15)
            if resp.status_code != 200:
                return None
            dirs = [d["name"] for d in resp.json() if d["type"] == "dir"]
            if not dirs:
                return None
            latest = sorted(dirs)[-1]
            return self._http_get(f"https://raw.githubusercontent.com/{self.repo}/master/content/{latest}/README.md")
        except requests.RequestException as e:
            print(f"[{self.source_key}] Failed: {e}")
            return None

    def _http_get(self, url):
        try:
            resp = requests.get(url, timeout=15)
            return resp.text if resp.status_code == 200 else None
        except requests.RequestException as e:
            print(f"[{self.source_key}] GET {url[:60]}: {e}")
            return None

    def _extract_repos(self, content):
        repos = []
        seen = set()
        patterns = [
            r'\[([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)\]\(https?://github\.com/[^)]+\)',
            r'https?://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)',
            r'`([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)`',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                owner, repo_name = match.groups()
                if repo_name in ("trending","explore","topics","marketplace","sponsors"):
                    continue
                fn = f"{owner}/{repo_name}"
                if fn not in seen:
                    seen.add(fn)
                    repos.append({"full_name": fn, "description": "extracted from citation source"})
        return repos
