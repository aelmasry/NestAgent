"""GitHub search — check open source before creating new tools."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class GitHubHit:
    full_name: str
    html_url: str
    description: str | None
    stars: int


class GitHubDiscovery:
    def __init__(self, limit: int = 5) -> None:
        self._limit = limit

    def search_repositories(self, query: str) -> list[GitHubHit]:
        q = urllib.parse.quote(f"{query} language:python")
        url = (
            "https://api.github.com/search/repositories?"
            f"q={q}&sort=stars&order=desc&per_page={self._limit}"
        )
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "NestAgent/0.1",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError:
            return []
        hits: list[GitHubHit] = []
        for item in data.get("items", []):
            hits.append(
                GitHubHit(
                    full_name=item.get("full_name", ""),
                    html_url=item.get("html_url", ""),
                    description=item.get("description"),
                    stars=int(item.get("stargazers_count", 0)),
                )
            )
        return hits

    def to_context(self, hits: list[GitHubHit]) -> list[dict[str, Any]]:
        return [
            {
                "repo": h.full_name,
                "url": h.html_url,
                "description": h.description,
                "stars": h.stars,
            }
            for h in hits
        ]
