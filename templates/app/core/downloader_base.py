# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SoundItem:
    id: str
    name: str
    url: str
    download_url: str
    duration: float = 0.0
    filesize: int = 0
    downloads: int = 0
    rating: float = 0.0
    username: str = ""
    license: str = ""
    tags: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)


class SortOption:
    DOWNLOADS = "downloads"
    RATING = "rating"
    DURATION_SHORT = "duration_short"
    DURATION_LONG = "duration_long"
    NEWEST = "newest"
    RELEVANCE = "relevance"


class DownloaderBase(ABC):
    NAME = "Unknown"
    REQUIRES_AUTH = False
    SUPPORTED_SORTS = [SortOption.RELEVANCE]

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def search(self, query, max_results=50, sort=SortOption.RELEVANCE,
               duration_max=None, duration_min=None):
        """
        duration_min, duration_max: 초 단위 (None이면 제한 없음)
        """
        pass

    @abstractmethod
    def download(self, item, save_dir, progress_cb=None):
        pass
