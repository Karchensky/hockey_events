from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Set
from loguru import logger


class StateStore:
    def __init__(self, path: Path = Path("data/state.json")) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Set[str]] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self._data = {k: set(v) for k, v in raw.items()}
            except Exception as exc:
                logger.warning(f"Failed to load state: {exc}")
                self._data = {}

    def save(self) -> None:
        serializable = {k: sorted(list(v)) for k, v in self._data.items()}
        self.path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")

    def has_seen(self, recipient_key: str, event_id: str) -> bool:
        return event_id in self._data.get(recipient_key, set())

    def mark_seen(self, recipient_key: str, event_id: str) -> None:
        if recipient_key not in self._data:
            self._data[recipient_key] = set()
        self._data[recipient_key].add(event_id)