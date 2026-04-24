# -*- coding: utf-8 -*-
"""
YouTube 다운로더 (yt-dlp 래퍼)
- yt-dlp.exe / ffmpeg.exe 를 외부 프로세스로 호출합니다.
- 검색 기능은 제공하지 않으며(URL 입력 기반), DownloaderBase 의 search() 는
  명시적으로 NotImplementedError 를 발생시킵니다.

bin 위치 탐색 우선순위:
  1) config.json 의 "youtube_bin_dir"
  2) 프로젝트 루트의 bin/   (예: <ROOT>/bin/yt-dlp.exe)
  3) PATH 의 yt-dlp / ffmpeg
"""
import csv
import os
import shutil
import subprocess
import sys

from core.downloader_base import DownloaderBase, SoundItem


# ---------------------------------------------------------------------------
# 포맷 프리셋
# ---------------------------------------------------------------------------
# key: 사용자 노출용 짧은 이름
# args: yt-dlp 에 추가될 인자 리스트
# ext: 결과 파일 확장자(설명용)
FORMAT_PRESETS = {
    "mp3":  {
        "label": "MP3 320kbps (감상용 추천)",
        "ext": "mp3",
        "args": ["-x", "--audio-format", "mp3", "--audio-quality", "0",
                 "--embed-thumbnail", "--embed-metadata"],
    },
    "flac": {
        "label": "FLAC (무손실 압축)",
        "ext": "flac",
        "args": ["-x", "--audio-format", "flac",
                 "--embed-thumbnail", "--embed-metadata"],
    },
    "wav":  {
        "label": "WAV (무손실 비압축, 편집용)",
        "ext": "wav",
        "args": ["-x", "--audio-format", "wav", "--embed-metadata"],
    },
    "opus": {
        "label": "Opus (작은 용량, 고음질)",
        "ext": "opus",
        "args": ["-x", "--audio-format", "opus",
                 "--embed-thumbnail", "--embed-metadata"],
    },
}
DEFAULT_FORMAT = "mp3"


def _is_youtube_url(url):
    if not url:
        return False
    u = url.strip().lower()
    return ("youtube.com/" in u) or ("youtu.be/" in u) or ("music.youtube.com/" in u)


class YouTubeDownloader(DownloaderBase):
    NAME = "YouTube"
    REQUIRES_AUTH = False
    SUPPORTED_SORTS = []  # 검색 미지원

    def __init__(self, config):
        super().__init__(config)
        self.bin_dir = self._resolve_bin_dir(config)
        self.ytdlp_path = self._resolve_exe("yt-dlp")
        self.ffmpeg_path = self._resolve_exe("ffmpeg")

    # ------------------------------------------------------------------
    # 환경 탐색
    # ------------------------------------------------------------------
    def _project_root(self):
        # providers/youtube.py -> providers -> app -> ROOT
        return os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

    def _resolve_bin_dir(self, config):
        cfg_dir = config.get("youtube_bin_dir")
        if cfg_dir and os.path.isdir(cfg_dir):
            return os.path.abspath(cfg_dir)
        default_dir = os.path.join(self._project_root(), "bin")
        return os.path.abspath(default_dir)

    def _resolve_exe(self, name):
        """bin_dir 우선 → PATH 검색."""
        candidates = []
        if sys.platform == "win32":
            candidates.append(os.path.join(self.bin_dir, name + ".exe"))
        candidates.append(os.path.join(self.bin_dir, name))
        for c in candidates:
            if os.path.isfile(c):
                return c
        # PATH
        which = shutil.which(name)
        return which  # None 가능

    def is_ready(self):
        """yt-dlp / ffmpeg 둘 다 발견되면 True."""
        return bool(self.ytdlp_path) and bool(self.ffmpeg_path)

    def status_text(self):
        ok_ytdlp = "OK" if self.ytdlp_path else "없음"
        ok_ffmpeg = "OK" if self.ffmpeg_path else "없음"
        return (f"yt-dlp: {ok_ytdlp}  |  ffmpeg: {ok_ffmpeg}\n"
                f"  bin_dir: {self.bin_dir}\n"
                f"  yt-dlp 경로: {self.ytdlp_path or '-'}\n"
                f"  ffmpeg 경로: {self.ffmpeg_path or '-'}")

    # ------------------------------------------------------------------
    # DownloaderBase 인터페이스
    # ------------------------------------------------------------------
    def search(self, query, max_results=50, sort=None,
               duration_max=None, duration_min=None):
        raise NotImplementedError(
            "YouTube provider는 검색을 지원하지 않습니다. URL을 직접 입력하세요."
        )

    def download(self, item, save_dir, progress_cb=None):
        """SoundItem(url 또는 download_url 만 사용)을 받아 다운로드.
        item.extra 에서 옵션을 읽음:
          - format_key: 'mp3'|'flac'|'wav'|'opus'  (기본 mp3)
          - prefix:     파일명 접두사 (옵션)
        """
        url = item.download_url or item.url
        if not _is_youtube_url(url):
            raise RuntimeError(f"유효한 YouTube URL이 아닙니다: {url}")

        fmt_key = (item.extra or {}).get("format_key", DEFAULT_FORMAT)
        prefix = (item.extra or {}).get("prefix", "")
        return self.download_url(url, save_dir,
                                 format_key=fmt_key, prefix=prefix,
                                 progress_cb=progress_cb)

    # ------------------------------------------------------------------
    # YouTube 전용 메서드 (CLI 에서 직접 호출)
    # ------------------------------------------------------------------
    def download_url(self, url, save_dir, format_key=DEFAULT_FORMAT,
                     prefix="", progress_cb=None):
        """단일 URL 다운로드. 결과 코드/메시지를 반환하지 않고 예외로 알림.
        반환값: (returncode:int, last_lines:str)
        """
        if not self.is_ready():
            missing = []
            if not self.ytdlp_path:
                missing.append("yt-dlp")
            if not self.ffmpeg_path:
                missing.append("ffmpeg")
            raise RuntimeError(
                "필수 실행파일을 찾을 수 없습니다: "
                + ", ".join(missing)
                + f"\n  bin_dir: {self.bin_dir}\n"
                "  bin 폴더에 yt-dlp.exe / ffmpeg.exe 를 배치하거나 PATH 에 추가하세요."
            )

        os.makedirs(save_dir, exist_ok=True)
        preset = FORMAT_PRESETS.get(format_key) or FORMAT_PRESETS[DEFAULT_FORMAT]

        if prefix:
            out_pattern = os.path.join(save_dir, f"{prefix}_%(title)s.%(ext)s")
        else:
            out_pattern = os.path.join(save_dir, "%(title)s.%(ext)s")

        cmd = [
            self.ytdlp_path,
            "--ffmpeg-location", os.path.dirname(self.ffmpeg_path) or self.ffmpeg_path,
            "-o", out_pattern,
            "--no-playlist",
            "--restrict-filenames",
            "--newline",
        ] + preset["args"] + [url]

        # 실행
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        last_lines = []
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            if progress_cb:
                try:
                    progress_cb(line)
                except Exception:
                    pass
            else:
                # 간단히 그대로 출력
                print("    " + line)
            last_lines.append(line)
            if len(last_lines) > 30:
                last_lines.pop(0)
        rc = proc.wait()
        return rc, "\n".join(last_lines)

    def download_csv(self, csv_path, save_dir, format_key=DEFAULT_FORMAT,
                     log_path=None, on_item=None):
        """links.csv 일괄 다운로드.
        CSV 형식:
            접두사,링크
            1,https://...
            2,https://...

        on_item(idx, total, prefix, url, status, filename, message) 콜백을
        라인 단위로 호출. status 는 'ok'|'fail'|'skip'.
        반환값: dict(success=int, fail=int, skip=int, total=int)
        """
        rows = self._read_links_csv(csv_path)
        total = len(rows)
        os.makedirs(save_dir, exist_ok=True)

        log_rows = [("접두사", "참조 링크", "파일명", "결과", "비고")]
        success = fail = skip = 0

        for i, (prefix, url) in enumerate(rows, 1):
            prefix = (prefix or "").strip()
            url = (url or "").strip()
            if not url:
                skip += 1
                if on_item:
                    on_item(i, total, prefix, url, "skip", "-", "링크 없음")
                log_rows.append((prefix, url, "-", "건너뜀", "링크 없음"))
                continue
            if not _is_youtube_url(url):
                fail += 1
                if on_item:
                    on_item(i, total, prefix, url, "fail", "-", "유효하지 않은 YouTube URL")
                log_rows.append((prefix, url, "-", "실패", "잘못된 링크"))
                continue

            try:
                rc, _ = self.download_url(url, save_dir,
                                          format_key=format_key,
                                          prefix=prefix)
                if rc == 0:
                    fname = self._guess_recent_file(save_dir, prefix)
                    success += 1
                    if on_item:
                        on_item(i, total, prefix, url, "ok", fname, "")
                    log_rows.append((prefix, url, fname, "성공", ""))
                else:
                    fail += 1
                    if on_item:
                        on_item(i, total, prefix, url, "fail", "-",
                                f"yt-dlp 종료코드 {rc}")
                    log_rows.append((prefix, url, "-", "실패",
                                     f"yt-dlp rc={rc}"))
            except Exception as e:
                fail += 1
                if on_item:
                    on_item(i, total, prefix, url, "fail", "-", str(e))
                log_rows.append((prefix, url, "-", "실패", str(e)))

        if log_path:
            try:
                with open(log_path, "w", encoding="utf-8-sig", newline="") as f:
                    csv.writer(f).writerows(log_rows)
            except Exception:
                pass

        return {"success": success, "fail": fail, "skip": skip, "total": total}

    def update_ytdlp(self):
        """yt-dlp.exe -U 실행. 반환값 returncode."""
        if not self.ytdlp_path:
            raise RuntimeError(f"yt-dlp 를 찾을 수 없습니다. bin_dir: {self.bin_dir}")
        proc = subprocess.Popen(
            [self.ytdlp_path, "-U"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in proc.stdout:
            print("    " + line.rstrip())
        return proc.wait()

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------
    @staticmethod
    def _read_links_csv(path):
        """첫 줄(헤더) 스킵, '접두사,링크' 형식. 빈 줄 무시."""
        if not os.path.isfile(path):
            raise FileNotFoundError(f"CSV 파일이 없습니다: {path}")
        # BOM 가능성 → utf-8-sig 시도, 실패시 cp949 fallback
        text = None
        for enc in ("utf-8-sig", "utf-8", "cp949"):
            try:
                with open(path, "r", encoding=enc, newline="") as f:
                    text = f.read()
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            raise RuntimeError(f"CSV 인코딩을 인식할 수 없습니다: {path}")

        reader = csv.reader(text.splitlines())
        rows = []
        header_consumed = False
        for row in reader:
            if not row:
                continue
            # '#' 주석 라인 무시 (자동 생성된 예시 주석 등)
            if row[0].lstrip().startswith("#"):
                continue
            if not header_consumed:
                header_consumed = True
                head0 = row[0].strip().lower() if row else ""
                # 헤더가 '접두사' / 'prefix' / 'name' / 'title' 이면 스킵
                if head0 in ("접두사", "prefix", "name", "title"):
                    continue
            # 컬럼이 1개뿐이면 url만 있는 것으로 간주
            if len(row) == 1:
                rows.append(("", row[0]))
            else:
                rows.append((row[0], row[1] if len(row) > 1 else ""))
        return rows

    @staticmethod
    def _guess_recent_file(save_dir, prefix):
        """접두사로 시작하는 파일 중 최신 1개의 이름 반환."""
        try:
            cands = []
            for f in os.listdir(save_dir):
                full = os.path.join(save_dir, f)
                if not os.path.isfile(full):
                    continue
                if prefix and not f.startswith(prefix + "_"):
                    continue
                cands.append((os.path.getmtime(full), f))
            if not cands:
                return "-"
            cands.sort(reverse=True)
            return cands[0][1]
        except Exception:
            return "-"
