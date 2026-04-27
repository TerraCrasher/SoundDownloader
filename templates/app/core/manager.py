# -*- coding: utf-8 -*-
from core.downloader_base import DownloaderBase
from providers.freesound import FreesoundDownloader
from providers.youtube import YouTubeDownloader
from providers.opengameart import OpenGameArtDownloader


class DownloaderManager:
    def __init__(self, config):
        self.config = config
        self._providers = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(FreesoundDownloader(self.config))
        self.register(YouTubeDownloader(self.config))
        self.register(OpenGameArtDownloader(self.config))

    def register(self, provider):
        self._providers[provider.NAME] = provider

    def get(self, name):
        return self._providers[name]

    def list_providers(self):
        return list(self._providers.keys())
