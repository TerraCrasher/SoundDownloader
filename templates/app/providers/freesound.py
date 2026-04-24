# -*- coding: utf-8 -*-
import os
import re
import requests
from core.downloader_base import DownloaderBase, SoundItem, SortOption


class FreesoundDownloader(DownloaderBase):
    NAME = "Freesound"
    BASE_URL = "https://freesound.org/apiv2"

    SUPPORTED_SORTS = [
        SortOption.DOWNLOADS, SortOption.RATING,
        SortOption.DURATION_SHORT, SortOption.DURATION_LONG,
        SortOption.NEWEST, SortOption.RELEVANCE,
    ]

    SORT_MAP = {
        SortOption.DOWNLOADS: "downloads_desc",
        SortOption.RATING: "rating_desc",
        SortOption.DURATION_SHORT: "duration_asc",
        SortOption.DURATION_LONG: "duration_desc",
        SortOption.NEWEST: "created_desc",
        SortOption.RELEVANCE: "score",
    }

    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.get("freesound_api_key", "")
        self.oauth_token = config.get("freesound_oauth_token", "")
        self.use_oauth = bool(self.oauth_token)

    def search(self, query, max_results=50, sort=SortOption.DOWNLOADS,
               duration_max=None, duration_min=None):
        if not self.api_key:
            raise RuntimeError("Freesound API Key가 설정되지 않았습니다. 메뉴 '2. 설정'에서 입력하세요.")

        sort_value = self.SORT_MAP.get(sort, "score")
        items = []
        page = 1
        page_size = min(150, max_results)

        while len(items) < max_results:
            params = {
                "query": query,
                "sort": sort_value,
                "page": page,
                "page_size": page_size,
                "fields": ("id,name,url,previews,download,duration,filesize,"
                           "num_downloads,avg_rating,username,license,tags"),
                "token": self.api_key,
            }

            # 길이 필터 (Freesound filter 문법: duration:[min TO max])
            if duration_min is not None or duration_max is not None:
                lo = str(duration_min) if duration_min is not None else "*"
                hi = str(duration_max) if duration_max is not None else "*"
                params["filter"] = f"duration:[{lo} TO {hi}]"
            r = requests.get(f"{self.BASE_URL}/search/text/", params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])
            if not results:
                break

            for s in results:
                if self.use_oauth and s.get("download"):
                    dl_url = s["download"]
                else:
                    dl_url = s.get("previews", {}).get("preview-hq-mp3", "")
                if not dl_url:
                    continue
                items.append(SoundItem(
                    id=str(s["id"]),
                    name=s["name"],
                    url=s.get("url", ""),
                    download_url=dl_url,
                    duration=s.get("duration", 0.0),
                    filesize=s.get("filesize", 0),
                    downloads=s.get("num_downloads", 0),
                    rating=s.get("avg_rating", 0.0),
                    username=s.get("username", ""),
                    license=s.get("license", ""),
                    tags=s.get("tags", []),
                ))
                if len(items) >= max_results:
                    break

            if not data.get("next"):
                break
            page += 1

        return items

    def download(self, item, save_dir, progress_cb=None):
        os.makedirs(save_dir, exist_ok=True)

        headers = {}
        if self.use_oauth and "/download/" in item.download_url:
            headers["Authorization"] = f"Bearer {self.oauth_token}"

        safe = re.sub(r'[\\/*?:"<>|]', "_", item.name)[:80]
        ext = ".mp3" if "preview" in item.download_url else ".wav"
        if not safe.lower().endswith(ext):
            safe = f"{safe}{ext}"
        save_path = os.path.join(save_dir, f"{item.id}_{safe}")

        if os.path.exists(save_path):
            return save_path

        with requests.get(item.download_url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            written = 0
            with open(save_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    if not chunk:
                        continue
                    f.write(chunk)
                    written += len(chunk)
                    if progress_cb:
                        progress_cb(written, total)

        return save_path
