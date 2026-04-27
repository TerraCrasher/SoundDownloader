# -*- coding: utf-8 -*-
"""
BBC Sound Effects (https://sound-effects.bbcrewind.co.uk/) provider — mp3 다운로드.

BBC 의 공개 SPA 백엔드 API 를 직접 호출한다. (정탐 결과 _scratch/bbc_probe* 참고)

- 검색 API:  POST https://sound-effects-api.bbcrewind.co.uk/api/sfx/search
            body: {"criteria": {"query": "<단어>", "size": 50, "from": 0,
                                 "categories": ["Nature"], "continents": ["Europe"]}}
            ※ GET ?q= 형태나 /cached/search 는 q 를 무시하고 인기 33066개를
              그대로 반환하므로 절대 사용 금지.
            ※ sort/duration 옵션은 API 가 무시 → 클라이언트 측에서 정렬·필터.
- 미디어:    https://sound-effects-media.bbcrewind.co.uk/mp3/<id>.mp3   (직접 GET, 인증 X)


응답 한 항목 (results[i]):
    { id, description, duration(ms 단위 float), recordedDate,
      categories[{className,p}], tags[],
      additionalMetadata{recordist, locationText, habitat, bandDescription, usage},
      technicalMetadata{file_name, sample_rate, bits_per_sample, channels, duration},
      fileSizes{mp3FileSize, wavFileSize} }

라이선스: BBC RemArc License — 개인/교육/연구용 무료 사용 허용, 비상업 한정.
         다운로드 폴더의 README.txt 에 자동 명시.

※ wav 원본은 AWS API Gateway WebSocket(batchDownload) 로만 받을 수 있어
   현재 범위 밖이다. 본 provider 는 mp3(보통 128kbps) 만 지원한다.
"""
import json
import os
import re
import time

import requests


from core.downloader_base import DownloaderBase, SoundItem, SortOption


API_BASE   = "https://sound-effects-api.bbcrewind.co.uk"
MEDIA_BASE = "https://sound-effects-media.bbcrewind.co.uk"
CLIENT_ORIGIN = "https://sound-effects.bbcrewind.co.uk"

# 정탐 결과: 진짜 검색은 POST /api/sfx/search + JSON body {"criteria": {...}}.
#   GET /api/sfx/cached/search?q= 는 q 를 무시하고 인기 33066 개를 반환하므로
#   결과가 항상 동일해 사실상 검색 기능이 없다. 절대 사용 금지.
SEARCH_PATH = "/api/sfx/search"


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36 "
      "SoundDownloader/1.0")


def _sanitize_filename(name, max_len=80):
    safe = re.sub(r'[\\/*?:"<>|\r\n\t]', "_", name).strip()
    safe = re.sub(r"\s+", " ", safe)
    safe = safe[:max_len].strip().rstrip(".")
    return safe or "track"


class BbcSoundEffectsDownloader(DownloaderBase):
    NAME = "BBC"
    REQUIRES_AUTH = False
    SUPPORTED_SORTS = [
        SortOption.RELEVANCE,        # API 기본 정렬 (= 검색 스코어)
        SortOption.DURATION_SHORT,   # 클라이언트 측 정렬 (받은 페이지 한정)
        SortOption.DURATION_LONG,
        SortOption.NEWEST,           # recordedDate 기준
    ]

    PER_PAGE = 50         # API 가 size 파라미터 받음. 50 이면 안전
    MAX_PAGES = 20        # 안전장치 (50 * 20 = 1000 결과 한도)
    PAGE_SLEEP = 0.15

    def __init__(self, config):
        super().__init__(config)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin":  CLIENT_ORIGIN,
            "Referer": CLIENT_ORIGIN + "/",
        })

    # =====================================================================
    # 외부 API
    # =====================================================================
    def search(self, query, max_results=50, sort=SortOption.RELEVANCE,
               duration_max=None, duration_min=None):
        """
        BBC 검색.
        - query 가 빈 문자열이면 전체 브라우징(API 가 인기/추천 결과 반환).
        - duration_min/max: 초 단위. API 자체 필터가 없어 클라이언트 측에서 거름.
        - sort: RELEVANCE 는 API 순서, NEWEST/DURATION_* 는 받은 결과를 재정렬.
        """
        # API 가 한 번에 size 100 정도까지 안정. 페이지네이션으로 모음.
        items_raw = []
        offset = 0
        page = 0
        # 필터링으로 결과가 줄 수 있으니 약간 여유롭게 받음
        target = max(max_results * 2, max_results + 30)
        while len(items_raw) < target and page < self.MAX_PAGES:
            page_size = min(self.PER_PAGE, max(target - len(items_raw), 10))
            data = self._fetch_search_page(query, offset, page_size)
            results = data.get("results") or []
            if not results:
                break
            items_raw.extend(results)
            offset += page_size
            page += 1
            # API 의 total 보다 모았으면 종료
            total = data.get("total")
            if isinstance(total, int) and offset >= total:
                break
            time.sleep(self.PAGE_SLEEP)

        # API → SoundItem 변환
        items = []
        for raw in items_raw:
            it = self._build_item(raw)
            if it is None:
                continue
            # 길이 필터 (초 단위)
            dur_s = it.duration
            if duration_min is not None and dur_s < duration_min:
                continue
            if duration_max is not None and dur_s > duration_max:
                continue
            items.append(it)

        # 클라이언트 측 정렬
        if sort == SortOption.DURATION_SHORT:
            items.sort(key=lambda x: x.duration)
        elif sort == SortOption.DURATION_LONG:
            items.sort(key=lambda x: x.duration, reverse=True)
        elif sort == SortOption.NEWEST:
            items.sort(key=lambda x: x.extra.get("recorded_date", ""), reverse=True)
        # RELEVANCE 는 API 순서 유지

        return items[:max_results]

    def download(self, item, save_dir, progress_cb=None):
        """
        한 트랙 = 한 mp3 파일 + (옵션) README.txt.
        OGA 와 달리 트랙 1개당 첨부 1개라 폴더 분리 없이 평탄하게 저장.
        파일명: <id>_<설명짧게>.mp3
        """
        os.makedirs(save_dir, exist_ok=True)

        if not item.download_url:
            raise RuntimeError("다운로드 URL 이 비어 있습니다")

        # 파일명: id + 설명을 짧게
        desc_short = _sanitize_filename(item.name, max_len=50)
        filename = f"{item.id}_{desc_short}.mp3"
        save_path = os.path.join(save_dir, filename)

        # 이미 있으면 스킵
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            return save_path

        with self.session.get(item.download_url, stream=True, timeout=60) as r:
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

        # 트랙별 메타 사이드카 파일 (.txt)
        self._write_sidecar(save_path, item)

        return save_path

    # =====================================================================
    # 내부 헬퍼
    # =====================================================================
    def _fetch_search_page(self, query, offset, size):
        """
        POST /api/sfx/search.

        body 형식:
            {"criteria": {"query": "<단어>", "size": <n>, "from": <offset>}}

        - query 가 빈 문자열이면 인기 33066 개 전체 풀에서 페이징 됨(브라우징).
        - 정렬·길이 필터 옵션은 서버가 무시하므로 호출 측에서 받지 않는다.
        """
        body = {
            "criteria": {
                "query": query or "",
                "size":  int(size),
                "from":  int(offset),
            }
        }
        url = API_BASE + SEARCH_PATH
        r = self.session.post(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        r.raise_for_status()
        return r.json()


    def _build_item(self, raw):
        """API 응답 한 항목 → SoundItem."""
        sid = raw.get("id")
        if not sid:
            return None

        desc = (raw.get("description") or "").strip() or sid

        # duration: ms 또는 s (정탐 결과 둘 다 등장하므로 보호적으로 처리)
        # technicalMetadata.duration 이 초 단위 문자열로 신뢰 가능
        dur_s = 0.0
        tm = raw.get("technicalMetadata") or {}
        try:
            dur_s = float(tm.get("duration") or 0.0)
        except (TypeError, ValueError):
            dur_s = 0.0
        if dur_s <= 0:
            # fallback: top-level duration 은 ms 일 가능성
            try:
                d = float(raw.get("duration") or 0.0)
                dur_s = d / 1000.0 if d > 1000 else d
            except (TypeError, ValueError):
                dur_s = 0.0

        # 카테고리(상위 1개만 표시)
        cats = raw.get("categories") or []
        category = cats[0].get("className") if cats and isinstance(cats[0], dict) else ""

        am = raw.get("additionalMetadata") or {}
        recordist = am.get("recordist") or ""
        location  = am.get("locationText") or ""
        habitat   = am.get("habitat") or ""
        band_desc = am.get("bandDescription") or ""
        usage     = am.get("usage") or ""

        recorded_date = raw.get("recordedDate") or ""

        # 파일 사이즈
        fs = raw.get("fileSizes") or {}
        try:
            mp3_size = int(fs.get("mp3FileSize") or 0)
        except (TypeError, ValueError):
            mp3_size = 0
        try:
            wav_size = int(fs.get("wavFileSize") or 0)
        except (TypeError, ValueError):
            wav_size = 0

        tags = raw.get("tags") or []

        # 미디어 URL 패턴: /mp3/<id>.mp3
        mp3_url = f"{MEDIA_BASE}/mp3/{sid}.mp3"
        page_url = f"{CLIENT_ORIGIN}/assets/{sid}"

        return SoundItem(
            id=sid,
            name=desc,
            url=page_url,
            download_url=mp3_url,
            duration=dur_s,
            filesize=mp3_size,
            downloads=0,            # BBC 는 다운로드 카운트 미공개
            rating=0.0,
            username=recordist,
            license="BBC RemArc License (개인/교육/연구용)",
            tags=tags,
            extra={
                "category": category,
                "location": location,
                "habitat": habitat,
                "band_description": band_desc,
                "usage": usage,
                "recorded_date": recorded_date,
                "wav_size": wav_size,
                "source": raw.get("source") or "",
            },
        )

    def _write_sidecar(self, mp3_path, item):
        """mp3 옆에 같은 이름의 .txt 메타 파일 생성."""
        sidecar = os.path.splitext(mp3_path)[0] + ".txt"
        ex = item.extra or {}
        # 길이 표시
        if item.duration:
            mins = int(item.duration // 60)
            secs = int(item.duration % 60)
            dur_str = f"{mins}:{secs:02d} ({item.duration:.1f}s)"
        else:
            dur_str = "-"

        lines = [
            f"제목         : {item.name}",
            f"BBC ID       : {item.id}",
            f"출처 URL     : {item.url}",
            f"미디어 URL   : {item.download_url}",
            f"길이         : {dur_str}",
            f"녹음일자     : {ex.get('recorded_date', '')[:10] or '-'}",
            f"카테고리     : {ex.get('category', '') or '-'}",
            f"녹음자       : {item.username or '-'}",
            f"위치         : {ex.get('location', '') or '-'}",
            f"서식지       : {ex.get('habitat', '') or '-'}",
            f"세부 설명    : {ex.get('band_description', '') or '-'}",
            f"사용 메모    : {ex.get('usage', '') or '-'}",
            f"태그         : {', '.join(item.tags) if item.tags else '-'}",
            f"라이선스     : {item.license}",
            "",
            "※ BBC RemArc License: 개인/교육/연구 목적의 무료 사용 허용, 상업적",
            "  사용은 별도 라이선스 필요. 자세한 내용은 아래 페이지 참조:",
            "  https://sound-effects.bbcrewind.co.uk/licensing",
        ]
        with open(sidecar, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
