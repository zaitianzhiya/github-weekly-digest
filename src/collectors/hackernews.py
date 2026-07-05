"""Hacker News collector via Algolia API."""
import requests, re
from datetime import datetime
from .base import BaseCollector, RepoRecord

class HackerNewsCollector(BaseCollector):
    API_URL = "https://hn.algolia.com/api/v1"
    def __init__(self, config):
        super().__init__(config)
        sc = config["sources"]["hackernews"]
        self.min_points = sc.get("min_points", 10)
        self.max_items = sc.get("max_items", 20)
    def collect(self):
        return []
