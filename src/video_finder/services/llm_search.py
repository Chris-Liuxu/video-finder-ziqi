from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx


class GlmSearchPlanner:
    def __init__(self, api_key: str, model: str = "glm-4.7-flash") -> None:
        self.api_key = api_key
        self.model = model

    def build_request(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You create one concise Google Custom Search query to find the original "
                        "YouTube video for a tampered clip. Prefer distinctive titles, subtitles, "
                        "names, channels, logos, languages, and scene context. Return JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False),
                },
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

    def plan_query(
        self,
        context: dict[str, Any],
        request_path: Path,
        response_path: Path,
        attempts_path: Path,
        max_attempts: int = 5,
    ) -> str | None:
        request_payload = self.build_request(context)
        request_path.write_text(
            json.dumps(request_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        attempts: list[dict[str, Any]] = []
        for attempt in range(1, max_attempts + 1):
            try:
                response = httpx.post(
                    "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=request_payload,
                    timeout=60,
                )
                response.raise_for_status()
                payload = response.json()
                response_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                content = payload["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                query = str(parsed.get("query") or "").strip()
                attempts.append({"attempt": attempt, "status": "success", "query": query})
                attempts_path.write_text(
                    json.dumps(attempts, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                return query or None
            except Exception as exc:
                attempts.append({"attempt": attempt, "status": "failed", "error": str(exc)})
                attempts_path.write_text(
                    json.dumps(attempts, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                if attempt < max_attempts:
                    time.sleep(min(2**attempt, 10))
        return None
