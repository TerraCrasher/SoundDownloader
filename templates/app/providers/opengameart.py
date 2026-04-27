# -*- coding: utf-8 -*-
"""
OpenGameArt.org provider — 음원(Music + Sound Effect) 검색 / 다운로드.

OGA 는 공식 API 가 없어 HTML 파싱으로 동작한다.
- 검색 URL: /art-search-advanced?keys=<query>&field_art_type_tid[]=<TID>&sort_by=<...>
- 카테고리 TID:  Music = 12, Sound Effect = 13
- 결과 항목: <div class="views-row">  안에 art-preview-title 링크
- 페이지당 24개, 페이저는 &page=N (0부터)
- 다운로드 직링크: <a href="https://opengameart.org/sites/default/files/...">

한 게시물에 여러 파일이 있을 수 있어 SoundItem.extra["all_files"] 에 모든 파일 URL,
SoundItem.download_url 은 첫 번째 파일을 보관한다.
"""
import os
import re
import time
import html as _html
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from core.downloader_base import DownloaderBase, SoundItem, SortOption


BASE = "https://opengameart.org"
SEARCH_PATH = "/art-search-advanced"

# 음원 카테고리 ID (정탐 v7 에서 확정)
CAT_MUSIC = 12
CAT_SFX = 13

CATEGORY_LABELS = {
    "music": ("음악 (Music)", CAT_MUSIC),
    "sfx":   ("효과음 (Sound Effect)", CAT_SFX),
    "both":  ("음악 + 효과음", None),  # 둘 다
}

# 다운로드로 받을 파일 확장자(오디오 + 패키지)
AUDIO_EXTS = (
    ".ogg", ".mp3", ".wav", ".flac", ".opus", ".m4a", ".aac",
    ".xm", ".it", ".s3m", ".mod", ".sfxr",
    ".zip", ".7z", ".rar", ".tar", ".gz",
)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36 "
      "SoundDownloader/1.0")


# ---------------------------------------------------------------------------
# 정렬 옵션 매핑 (DownloaderBase 의 SortOption  →  OGA 의 sort_by 값)
# ---------------------------------------------------------------------------
SORT_MAP = {
    SortOption.DOWNLOADS: "count",     # OGA 는 favorites 카운트 = 인기도
    SortOption.NEWEST:    "created",
    SortOption.RELEVANCE: "score",
}


def _sanitize_filename(name, max_len=80):
    """윈도우 금지문자 제거."""
    safe = re.sub(r'[\\/*?:"<>|\r\n\t]', "_", name).strip()
    safe = re.sub(r"\s+", " ", safe)
    return safe[:max_len].strip().rstrip(".")  # 끝 '.' 도 제거


def _decode(s):
    return _html.unescape(s).strip()


class OpenGameArtDownloader(DownloaderBase):
    NAME = "OpenGameArt"
    REQUIRES_AUTH = False
    SUPPORTED_SORTS = [
        SortOption.DOWNLOADS,    # 인기(favorites)
        SortOption.NEWEST,       # 최신
        SortOption.RELEVANCE,    # 관련도
    ]

    PER_PAGE = 24            # OGA 검색 결과는 페이지당 24개 고정
    DETAIL_WORKERS = 4       # 상세 페이지 동시 접근 제한
    PAGE_SLEEP = 0.4         # 검색 페이지 사이 sleep (서버 예의)

    def __init__(self, config):
        super().__init__(config)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": UA,
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
        })
        # 사용자가 카테고리를 지정할 때 search() 호출 전에 세팅
        self.category_key = "both"   # "music" / "sfx" / "both"

    # =====================================================================
    # 외부 API: search / download (DownloaderBase 인터페이스 구현)
    # =====================================================================
    def search(self, query, max_results=50, sort=SortOption.DOWNLOADS,
               duration_max=None, duration_min=None):
        """
        OGA 음원 검색.
        category_key 는 인스턴스 속성으로 전달 ("music"/"sfx"/"both").
        duration_min/max 는 OGA 가 제공하지 않으므로 무시.
        """
        sort_value = SORT_MAP.get(sort, "count")

        # 카테고리 → TID 리스트
        tids = []
        if self.category_key == "music":
            tids = [CAT_MUSIC]
        elif self.category_key == "sfx":
            tids = [CAT_SFX]
        else:  # both
            tids = [CAT_MUSIC, CAT_SFX]

        # 1) 검색 결과 페이지 N개 모아서 (slug, title) 리스트 만들기
        slug_title = []
        page = 0
        seen = set()
        while len(slug_title) < max_results:
            html = self._fetch_search(query, tids, sort_value, page)
            items = self._parse_search_items(html)
            if not items:
                break
            for slug, title in items:
                if slug in seen:
                    continue
                seen.add(slug)
                slug_title.append((slug, title))
                if len(slug_title) >= max_results:
                    break
            page += 1
            # 안전장치: 너무 많은 페이지 방지
            if page > 50:
                break
            time.sleep(self.PAGE_SLEEP)

        # 2) 각 항목의 상세 페이지를 병렬로 가져와 다운로드 링크/메타 보강
        results = [None] * len(slug_title)
        with ThreadPoolExecutor(max_workers=self.DETAIL_WORKERS) as ex:
            fut_to_idx = {
                ex.submit(self._build_item, slug, title): i
                for i, (slug, title) in enumerate(slug_title)
            }
            for fut in as_completed(fut_to_idx):
                idx = fut_to_idx[fut]
                try:
                    results[idx] = fut.result()
                except Exception:
                    results[idx] = None  # 실패한 항목은 스킵

        return [r for r in results if r is not None]

    def download(self, item, save_dir, progress_cb=None):
        """
        한 게시물 = 한 폴더 정책.
        - downloads/opengameart/<게시물제목>/<파일1>, <파일2>, ...
        - 같은 폴더에 README.txt (출처/라이선스/작성자/태그) 자동 생성
        """
        os.makedirs(save_dir, exist_ok=True)

        folder_name = _sanitize_filename(item.name) or f"oga_{item.id}"
        target_dir = os.path.join(save_dir, folder_name)
        os.makedirs(target_dir, exist_ok=True)

        all_files = item.extra.get("all_files") or []
        if not all_files and item.download_url:
            all_files = [item.download_url]

        if not all_files:
            raise RuntimeError("다운로드 가능한 파일이 없습니다 (외부 호스팅이거나 게시물에 첨부 없음)")

        # README 먼저 작성 (다운로드 실패해도 출처는 남도록)
        self._write_readme(target_dir, item)

        saved_paths = []
        for url in all_files:
            try:
                p = self._download_file(url, target_dir, progress_cb)
                saved_paths.append(p)
            except Exception as e:
                # 한 파일 실패해도 다른 파일은 계속 받기 — 마지막에 라벨로 알림
                err_log = os.path.join(target_dir, "_download_errors.txt")
                with open(err_log, "a", encoding="utf-8") as f:
                    f.write(f"{url}\t{e}\n")

        return target_dir

    # =====================================================================
    # 내부 헬퍼
    # =====================================================================
    def _fetch_search(self, query, tids, sort_value, page):
        params = [("keys", query or "")]
        for tid in tids:
            params.append(("field_art_type_tid[]", str(tid)))
        params.extend([
            ("sort_by", sort_value),
            ("sort_order", "DESC"),
        ])
        if page > 0:
            params.append(("page", str(page)))
        url = BASE + SEARCH_PATH + "?" + urllib.parse.urlencode(params)
        r = self.session.get(url, timeout=20)
        r.raise_for_status()
        return r.text

    def _parse_search_items(self, html):
        """검색 결과 HTML 에서 (slug, title) 추출."""
        # art-preview-title"><a href="/content/<slug>">제목</a>
        items = re.findall(
            r'art-preview-title"><a href="(/content/[^"]+)">([^<]+)</a>',
            html,
        )
        out = []
        for slug, title in items:
            out.append((slug, _decode(title)))
        return out

    def _build_item(self, slug, title):
        """상세 페이지를 받아 SoundItem 으로 변환."""
        url = BASE + slug
        r = self.session.get(url, timeout=20)
        r.raise_for_status()
        dh = r.text

        # /sites/default/files/ 직링크 중 오디오/패키지 확장자만
        all_files = re.findall(
            r'href="(https?://opengameart\.org/sites/default/files/[^"]+)"',
            dh,
        )
        # 중복 제거 + 확장자 필터
        seen = set()
        audio_files = []
        for f in all_files:
            base = f.split("?")[0].lower()
            # URL-인코딩된 확장자도 매칭 (e.g. .zip 가 안전)
            if base.endswith(AUDIO_EXTS) and f not in seen:
                seen.add(f)
                audio_files.append(f)

        # 메타: submitter
        m = re.search(r'class="username"[^>]*>([^<]+)</a>', dh)
        submitter = _decode(m.group(1)) if m else ""

        # tags
        tags = []
        m = re.search(
            r'class="[^"]*field-name-field-art-tags[^"]*"[^>]*>(.+?)</div>\s*</div>',
            dh, re.S,
        )
        if m:
            tags = [_decode(t) for t in re.findall(r'>([^<]+)</a>', m.group(1))]

        # 라이선스(베스트 에포트, 다양한 형태 시도)
        license_str = ""
        m = re.search(
            r'class="[^"]*field-name-field-art-licenses[^"]*"[^>]*>(.+?)</div>\s*</div>',
            dh, re.S,
        )
        if m:
            licenses = re.findall(r'>([^<]+)</a>', m.group(1))
            license_str = ", ".join(_decode(l) for l in licenses if l.strip())
        if not license_str:
            # alt 텍스트에 라이선스 아이콘이 있는 경우
            licenses = re.findall(
                r'alt="(CC[\s\-][A-Za-z0-9 \.]+|GPL[^\"]*|OGA[^\"]*|LGPL[^\"]*|Public[^\"]*)"',
                dh,
            )
            license_str = ", ".join(dict.fromkeys(licenses))

        # 노드 ID
        m = re.search(r'node-(\d+)', dh)
        node_id = m.group(1) if m else slug.rsplit("/", 1)[-1]

        # favorites (있으면 downloads 자리에 매핑)
        m = re.search(r'(\d+)\s*(?:user[s]?\s+)?favorit', dh, re.I)
        favs = int(m.group(1)) if m else 0

        if not audio_files:
            return None  # 다운로드 불가능한 항목은 스킵

        return SoundItem(
            id=node_id,
            name=title,
            url=url,
            download_url=audio_files[0],
            duration=0.0,            # OGA 는 길이를 노출하지 않음
            filesize=0,
            downloads=favs,
            rating=0.0,
            username=submitter,
            license=license_str,
            tags=tags,
            extra={
                "all_files": audio_files,
                "file_count": len(audio_files),
                "category": self.category_key,
            },
        )

    def _download_file(self, url, target_dir, progress_cb):
        """단일 파일 다운로드. 이미 있으면 스킵."""
        # URL 끝의 파일명 사용 (URL-decode + 위험문자 정리)
        raw_name = urllib.parse.unquote(url.rsplit("/", 1)[-1].split("?")[0])
        filename = _sanitize_filename(raw_name) or "file.bin"
        save_path = os.path.join(target_dir, filename)
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            return save_path

        with self.session.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            written = 0
            with open(save_path, "wb") as f:
                for chunk in r.iter_content(64 * 1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    written += len(chunk)
                    if progress_cb:
                        progress_cb(written, total)
        return save_path

    def _write_readme(self, target_dir, item):
        """게시물 폴더에 출처/라이선스/메타 README.txt 생성."""
        path = os.path.join(target_dir, "README.txt")
        lines = [
            f"제목     : {item.name}",
            f"출처 URL : {item.url}",
            f"작성자   : {item.username or '(미상)'}",
            f"라이선스 : {item.license or '(상세 페이지에서 확인 필요)'}",
            f"즐겨찾기 : {item.downloads}",
            f"태그     : {', '.join(item.tags) if item.tags else '-'}",
            f"파일 수  : {item.extra.get('file_count', 0)}",
            "",
            "※ OpenGameArt 의 라이선스는 게시물마다 다릅니다 (CC0/CC-BY/GPL/OGA-BY 등).",
            "  상업 이용 / 재배포 시 위 출처 URL 의 라이선스 안내를 반드시 확인하세요.",
        ]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
