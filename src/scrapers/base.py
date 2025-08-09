from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from src.utils.events import Event


class Scraper(ABC):
    @abstractmethod
    def can_handle(self, url: str) -> bool:  # pragma: no cover
        raise NotImplementedError

    @abstractmethod
    def scrape(self, url: str, timezone: str) -> List[Event]:  # pragma: no cover
        raise NotImplementedError