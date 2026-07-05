"""GitHub Trending collector - scrapes trending page + API enrichment + README."""

import os, re, requests
from datetime import datetime, timedelta

from .base import BaseCollector, RepoRecord


class GitHubTrendingCollector(BaseCollector):
    TRENDING_URL = "https://github.com/trending"
    API_URL = "https://api.github.com"

    def __init__(self, config: dict):
        super().__init__(config)
        sc = config["sources"]["github_trending"]
        self.max_items = sc.get("max_items", 25)
        self.include_readme = sc.get("include_readme", True)
        self.readme_chars = sc.get("readme_chars", 6000)
        self.token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")

    def _auth_headers(self, extra=None):
        h = {"Accept": "application/vnd.github.v3+json"}
        if extra:
            h.update(extra)
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def collect(self):
        repos = self._fetch_trending()
        records = []
        for i, repo in enumerate(repos):
            if i >= self.max_items:
                break
            self._enrich_from_api(repo)
            readme_text = ""
            if self.include_readme:
                readme_text = self._fetch_readme(repo["full_name"])
            citation = self.create_citation("github_trending")
            record = RepoRecord(
                repo_id=repo["full_name"], full_name=repo["full_name"],
                html_url=repo["html_url"], description=repo.get("description",""),
                language=repo.get("language",""), stars=repo.get("stars",0),
                weekly_growth=repo.get("weekly_growth",0),
                daily_growth=repo.get("daily_growth",0),
                forks=repo.get("forks",0), open_issues=repo.get("open_issues",0),
                created_at=repo.get("created_at",""), pushed_at=repo.get("pushed_at",""),
                license=repo.get("license",""), readme_text=readme_text,
                topics=repo.get("topics",[]), categories=[],
                confidence_score=40.0, confidence_grade="C",
                citation_count=1, citations=[citation],
                sources=[citation.source_name],
                first_seen=datetime.utcnow().isoformat(),
                last_updated=datetime.utcnow().isoformat(), raw_data=repo,
            )
            records.append(record)
        return records

    def _fetch_trending(self):
        hdrs = {"User-Agent": "Mozilla/5.0 (compatible; github-digest/1.0)"}
        try:
            resp = requests.get(f"{self.TRENDING_URL}?since=weekly", headers=hdrs, timeout=15)
            resp.raise_for_status()
            repos = self._parse_trending_html(resp.text)
            if repos: return repos
        except requests.RequestException as e:
            print(f"[GH-Trending] Scrape failed: {e}")
        return self._fetch_trending_via_api_fallback()

    def _parse_trending_html(self, html):
        repos = []
        for section in re.split(r'<article\s+class="Box-row"', html)[1:]:
            m = re.search(r'href="/([^/"]+)/([^/"]+)"', section)
            if not m: continue
            owner, name = m.groups()
            if name in ("trending","explore","sponsors"): continue
            fn = f"{owner}/{name}"
            dm = re.search(r'<p\s+class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', section, re.DOTALL)
            desc = re.sub(r'<[^>]+>','', dm.group(1).strip()) if dm else ""
            lm = re.search(r'itemprop="programmingLanguage"[^>]*>([^<]+)<', section)
            lang = lm.group(1).strip() if lm else ""
            sm = re.search(r'(\d[\d,]*)\s*stars?\s*(this week|today)', section, re.IGNORECASE)
            wg = int(sm.group(1).replace(",","")) if sm else 0
            repos.append({"full_name":fn,"html_url":f"https://github.com/{fn}",
                "description":desc,"language":lang,"weekly_growth":wg,
                "daily_growth":max(1,wg//7),"stars":0,"forks":0,"open_issues":0,
                "created_at":"","pushed_at":"","license":"","topics":[]})
        return repos

    def _fetch_trending_via_api_fallback(self):
        print("[GH-Trending] Using API fallback...")
        since = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        params = {"q":f"created:>={since}","sort":"stars","order":"desc","per_page":min(self.max_items,100)}
        try:
            resp = requests.get(f"{self.API_URL}/search/repositories", headers=self._auth_headers(), params=params, timeout=15)
            resp.raise_for_status()
            items = resp.json().get("items",[])
        except requests.RequestException as e:
            print(f"[GH-Trending] API fallback failed: {e}"); return []
        repos = []
        for item in items:
            lic = item.get("license") or {}
            repos.append({"full_name":item["full_name"],"html_url":item["html_url"],
                "description":item.get("description",""),"language":item.get("language",""),
                "weekly_growth":item.get("stargazers_count",0),"daily_growth":0,
                "stars":item.get("stargazers_count",0),"forks":item.get("forks_count",0),
                "open_issues":item.get("open_issues_count",0),
                "created_at":item.get("created_at",""),"pushed_at":item.get("pushed_at",""),
                "license":lic.get("spdx_id",""),"topics":item.get("topics",[])})
        return repos

    def _enrich_from_api(self, repo):
        try:
            resp = requests.get(f"{self.API_URL}/repos/{repo['full_name']}", headers=self._auth_headers(), timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                repo["stars"] = d.get("stargazers_count",0)
                repo["forks"] = d.get("forks_count",0)
                repo["open_issues"] = d.get("open_issues_count",0)
                repo["created_at"] = d.get("created_at","")
                repo["pushed_at"] = d.get("pushed_at","")
                lic = d.get("license") or {}
                repo["license"] = lic.get("spdx_id","")
                repo["topics"] = d.get("topics",[])
        except requests.RequestException:
            pass

    def _fetch_readme(self, full_name):
        try:
            resp = requests.get(f"{self.API_URL}/repos/{full_name}/readme",
                headers=self._auth_headers({"Accept":"application/vnd.github.v3.raw"}), timeout=10)
            if resp.status_code == 200:
                return resp.text[:self.readme_chars]
        except requests.RequestException:
            pass
        return ""
