from __future__ import annotations

import os
from typing import Iterable

import requests

from backend.models import LearningResource


CURATED_RESOURCES = {
    "Kubernetes": [
        ("Kubernetes Full Course - freeCodeCamp", "https://www.youtube.com/watch?v=X48VuDVv0do", "freeCodeCamp.org"),
        ("Kubernetes Tutorial for Beginners", "https://www.youtube.com/watch?v=s_o8dwzRlu4", "TechWorld with Nana"),
    ],
    "Docker": [
        ("Docker in 100 Seconds", "https://www.youtube.com/watch?v=Gjnup-PuquQ", "Fireship"),
        ("Docker Crash Course", "https://www.youtube.com/watch?v=pg19Z8LL06w", "Traversy Media"),
    ],
    "Vector Databases": [
        ("Vector Databases Explained", "https://www.youtube.com/watch?v=dN0lsF2cvm4", "AssemblyAI"),
        ("RAG + Vector Databases", "https://www.youtube.com/watch?v=KlVs2RjVvTQ", "Weights & Biases"),
    ],
}


class YouTubeRecommender:
    def __init__(self, resources_per_skill: int = 2) -> None:
        self.resources_per_skill = resources_per_skill
        self.api_key = os.getenv("YOUTUBE_API_KEY", "").strip()

    def recommend(self, skills: Iterable[str]) -> list[LearningResource]:
        recommendations: list[LearningResource] = []
        for skill in skills:
            entries = self._search_youtube(skill)
            for idx, (title, url, channel) in enumerate(entries[: self.resources_per_skill], start=1):
                recommendations.append(
                    LearningResource(skill=skill, title=title, url=url, channel=channel, rank=idx)
                )
        return recommendations

    def _search_youtube(self, skill: str) -> list[tuple[str, str, str]]:
        if self.api_key:
            try:
                return self._youtube_api_search(skill)
            except Exception:
                pass

        curated = CURATED_RESOURCES.get(skill.title()) or CURATED_RESOURCES.get(skill)
        if curated:
            return curated
        return [
            (
                f"{skill} Tutorial for Beginners",
                f"https://www.youtube.com/results?search_query={skill.replace(' ', '+')}+tutorial",
                "YouTube Search",
            ),
            (
                f"Advanced {skill} Projects",
                f"https://www.youtube.com/results?search_query=advanced+{skill.replace(' ', '+')}",
                "YouTube Search",
            ),
        ]

    def _youtube_api_search(self, skill: str) -> list[tuple[str, str, str]]:
        endpoint = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "maxResults": self.resources_per_skill,
            "q": f"{skill} tutorial",
            "type": "video",
            "key": self.api_key,
            "order": "relevance",
        }
        response = requests.get(endpoint, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()

        output: list[tuple[str, str, str]] = []
        for item in payload.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            snippet = item.get("snippet", {})
            if not video_id:
                continue
            title = snippet.get("title", "Untitled")
            channel = snippet.get("channelTitle", "Unknown")
            url = f"https://www.youtube.com/watch?v={video_id}"
            output.append((title, url, channel))

        return output
