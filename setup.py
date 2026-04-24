# -*- coding: utf-8 -*-
"""
Sound Downloader - 최초 환경 설치

다음을 자동으로 준비합니다 (이미 있는 항목은 건너뜁니다):
  1) 임베디드 Python (python/)
  2) ._pth 의 import site 활성화
  3) pip + requests 패키지 설치 (packages/)
  4) bin/yt-dlp.exe          (GitHub releases latest)
  5) bin/ffmpeg.exe / ffprobe.exe  (gyan.dev essentials)
  6) templates/ -> ROOT 앱 파일 복사

오프라인 모드:
  - "setup.bat --no-download"  또는
  - 환경변수 SOUND_DOWNLOADER_OFFLINE=1
  으로 외부 다운로드를 건너뛰고 존재 여부만 점검합니다.
"""
import os
import re
import sys
import zipfile
import shutil
import subprocess
import urllib.request
import urllib.error

# 콘솔 인코딩 보정 (cp949 콘솔에서도 안 깨지게)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# stderr 만 두 개의 단계 함수에서 활용 (가독성용)
ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON_DIR = os.path.join(ROOT, "python")
PYTHON_EXE = os.path.join(PYTHON_DIR, "python.exe")
PACKAGES_DIR = os.path.join(ROOT, "packages")
GET_PIP = os.path.join(PYTHON_DIR, "get-pip.py")
BIN_DIR = os.path.join(ROOT, "bin")
TMP_DIR = os.path.join(ROOT, ".setup_tmp")

# ---------------------------------------------------------------------------
# 다운로드 URL
# ---------------------------------------------------------------------------
EMBED_PY_URL = "https://www.python.org/ftp/python/3.13.1/python-3.13.1-embed-amd64.zip"
GET_PIP_URL  = "https://bootstrap.pypa.io/get-pip.py"
YT_DLP_URL   = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
# gyan.dev 의 'release-essentials' 빌드 (가벼움, ffmpeg+ffprobe 포함)
FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def step(n, total, msg):
    print(f"\n[{n}/{total}] {msg}")


def is_offline():
    if os.environ.get("SOUND_DOWNLOADER_OFFLINE") == "1":
        return True
    return ("--no-download" in sys.argv) or ("--offline" in sys.argv)


# ---------------------------------------------------------------------------
# 다운로드 헬퍼 (진행률 표시)
# ---------------------------------------------------------------------------
def _human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:6.1f} {unit}"
        n /= 1024
    return f"{n:6.1f} TB"


def download(url, dst, label=None):
    """url -> dst 다운로드. 진행률을 한 줄로 표시. 실패 시 예외."""
    label = label or os.path.basename(dst)
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    print(f"  - 다운로드: {label}")
    print(f"    URL: {url}")

    req = urllib.request.Request(url, headers={"User-Agent": "SoundDownloader-Setup/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            written = 0
            chunk = 64 * 1024
            with open(dst + ".part", "wb") as f:
                while True:
                    buf = resp.read(chunk)
                    if not buf:
                        break
                    f.write(buf)
                    written += len(buf)
                    if total:
                        pct = written / total * 100
                        bar_w = 24
                        filled = int(bar_w * written / total)
                        bar = "#" * filled + "-" * (bar_w - filled)
                        print(f"\r    [{bar}] {pct:5.1f}%  {_human_size(written)} / {_human_size(total)}",
                              end="", flush=True)
                    else:
                        print(f"\r    {_human_size(written)} ...", end="", flush=True)
        os.replace(dst + ".part", dst)
        print()  # 줄바꿈
    except Exception:
        # 정리
        try:
            if os.path.exists(dst + ".part"):
                os.remove(dst + ".part")
        except Exception:
            pass
        raise


# ---------------------------------------------------------------------------
# 1) 임베디드 Python
# ---------------------------------------------------------------------------
def ensure_embedded_python():
    if os.path.exists(PYTHON_EXE):
        print("  - 이미 설치됨")
        return True

    if is_offline():
        print("  [ERROR] python\\python.exe 가 없습니다 (오프라인 모드).")
        print("    https://www.python.org/downloads/windows/ 에서")
        print("    'Windows embeddable package (64-bit)' 을 받아 python\\ 폴더에 압축 해제하세요.")
        return False

    os.makedirs(TMP_DIR, exist_ok=True)
    zip_path = os.path.join(TMP_DIR, "python-embed.zip")
    try:
        download(EMBED_PY_URL, zip_path, label="Python 3.13 embedded")
    except Exception as e:
        print(f"  [ERROR] Python 다운로드 실패: {e}")
        return False

    print("  - 압축 해제 중...")
    os.makedirs(PYTHON_DIR, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(PYTHON_DIR)
    except Exception as e:
        print(f"  [ERROR] 압축 해제 실패: {e}")
        return False

    return os.path.exists(PYTHON_EXE)


# ---------------------------------------------------------------------------
# 2) ._pth 수정
# ---------------------------------------------------------------------------
def fix_pth():
    if not os.path.isdir(PYTHON_DIR):
        print("  [WARN] python 폴더 없음 → 건너뜀")
        return
    pth_files = [f for f in os.listdir(PYTHON_DIR) if re.match(r"python\d+\._pth$", f)]
    if not pth_files:
        print("  [WARN] ._pth 파일을 찾을 수 없음")
        return
    for fname in pth_files:
        path = os.path.join(PYTHON_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        new_content = re.sub(r"#\s*import site", "import site", content)
        if new_content != content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"  - {fname} 수정됨")
        else:
            print(f"  - {fname} 이미 설정됨")


# ---------------------------------------------------------------------------
# 3) pip + requests
# ---------------------------------------------------------------------------
def install_pip():
    pip_exe = os.path.join(PYTHON_DIR, "Scripts", "pip.exe")
    if os.path.exists(pip_exe):
        print("  - pip 이미 설치됨")
        return True

    if is_offline() and not os.path.exists(GET_PIP):
        print("  [ERROR] pip 미설치 + 오프라인 모드 → 설치 불가")
        return False

    if not os.path.exists(GET_PIP):
        try:
            download(GET_PIP_URL, GET_PIP, label="get-pip.py")
        except Exception as e:
            print(f"  [ERROR] get-pip.py 다운로드 실패: {e}")
            return False

    print("  - pip 설치 중...")
    rc = subprocess.run(
        [PYTHON_EXE, GET_PIP, "--no-warn-script-location"],
        cwd=ROOT,
    ).returncode
    return rc == 0


def install_requests():
    # 이미 설치돼 있으면 스킵
    marker = os.path.join(PACKAGES_DIR, "requests")
    if os.path.isdir(marker):
        print("  - requests 이미 설치됨")
        return True

    if is_offline():
        print("  [ERROR] requests 미설치 + 오프라인 모드 → 설치 불가")
        return False

    print("  - requests 패키지 설치 중...")
    rc = subprocess.run(
        [PYTHON_EXE, "-m", "pip", "install",
         "--target", PACKAGES_DIR, "requests",
         "--no-warn-script-location", "--upgrade"],
        cwd=ROOT,
    ).returncode
    return rc == 0


# ---------------------------------------------------------------------------
# 4) yt-dlp
# ---------------------------------------------------------------------------
def ensure_ytdlp():
    dst = os.path.join(BIN_DIR, "yt-dlp.exe")
    if os.path.isfile(dst):
        print(f"  - 이미 있음 ({_human_size(os.path.getsize(dst))})")
        return True
    if is_offline():
        print("  [WARN] yt-dlp.exe 누락 (오프라인 모드)")
        print("    https://github.com/yt-dlp/yt-dlp/releases/latest 에서 받아 bin\\ 에 두세요.")
        return False
    try:
        download(YT_DLP_URL, dst, label="yt-dlp.exe")
        return True
    except Exception as e:
        print(f"  [ERROR] yt-dlp 다운로드 실패: {e}")
        return False


# ---------------------------------------------------------------------------
# 5) ffmpeg / ffprobe (essentials zip → 두 exe 만 추출)
# ---------------------------------------------------------------------------
def ensure_ffmpeg():
    ffmpeg = os.path.join(BIN_DIR, "ffmpeg.exe")
    ffprobe = os.path.join(BIN_DIR, "ffprobe.exe")

    have_f = os.path.isfile(ffmpeg)
    have_p = os.path.isfile(ffprobe)
    if have_f and have_p:
        print(f"  - 이미 있음  (ffmpeg={_human_size(os.path.getsize(ffmpeg))}, "
              f"ffprobe={_human_size(os.path.getsize(ffprobe))})")
        return True

    if is_offline():
        print("  [WARN] ffmpeg/ffprobe 누락 (오프라인 모드)")
        print("    https://www.gyan.dev/ffmpeg/builds/ 에서 'release essentials' 를 받아")
        print("    내부 bin/ 의 ffmpeg.exe / ffprobe.exe 를 본 프로젝트의 bin\\ 에 복사하세요.")
        return False

    os.makedirs(TMP_DIR, exist_ok=True)
    zip_path = os.path.join(TMP_DIR, "ffmpeg-essentials.zip")
    try:
        download(FFMPEG_ZIP_URL, zip_path, label="ffmpeg-release-essentials.zip")
    except Exception as e:
        print(f"  [ERROR] ffmpeg 다운로드 실패: {e}")
        return False

    print("  - 압축에서 ffmpeg.exe / ffprobe.exe 추출 중...")
    os.makedirs(BIN_DIR, exist_ok=True)
    extracted = {"ffmpeg.exe": False, "ffprobe.exe": False}
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.namelist():
                base = os.path.basename(member).lower()
                if base in extracted and not extracted[base]:
                    target = os.path.join(BIN_DIR, base)
                    # 덮어쓰기는 하지 않음 (사용자 버전 보호)
                    if os.path.isfile(target):
                        extracted[base] = True
                        continue
                    with z.open(member) as src, open(target, "wb") as dst_f:
                        shutil.copyfileobj(src, dst_f)
                    extracted[base] = True
                if all(extracted.values()):
                    break
    except Exception as e:
        print(f"  [ERROR] 압축 해제 실패: {e}")
        return False

    if not all(extracted.values()):
        missing = [k for k, v in extracted.items() if not v]
        print(f"  [ERROR] zip 안에서 다음을 찾지 못했습니다: {missing}")
        return False
    return True


# ---------------------------------------------------------------------------
# 6) 앱 파일 생성
# ---------------------------------------------------------------------------
def generate_files():
    sys.path.insert(0, ROOT)
    try:
        import files_data
        files_data.write_files()
        return True
    except Exception as e:
        print(f"  [ERROR] 파일 생성 실패: {e}")
        return False


def cleanup_tmp():
    if os.path.isdir(TMP_DIR):
        try:
            shutil.rmtree(TMP_DIR)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    print("=" * 50)
    print("  Sound Downloader 최초 설치")
    if is_offline():
        print("  (오프라인 모드: 외부 다운로드 안 함)")
    print("=" * 50)

    total = 7

    step(1, total, "임베디드 Python 확인 / 다운로드")
    if not ensure_embedded_python():
        sys.exit(1)

    step(2, total, "._pth 파일 설정")
    fix_pth()

    step(3, total, "pip 설치")
    if not install_pip():
        print("  [ERROR] pip 설치 실패")
        sys.exit(1)

    step(4, total, "requests 패키지 설치")
    if not install_requests():
        print("  [ERROR] requests 설치 실패")
        sys.exit(1)

    step(5, total, "bin/yt-dlp.exe 확인 / 다운로드")
    ok_yt = ensure_ytdlp()

    step(6, total, "bin/ffmpeg.exe / ffprobe.exe 확인 / 다운로드")
    ok_ff = ensure_ffmpeg()

    step(7, total, "앱 파일 생성")
    if not generate_files():
        sys.exit(1)

    cleanup_tmp()

    print("\n" + "=" * 50)
    print("  [OK] 설치 완료!")
    print("  run.bat 을 더블클릭하여 실행하세요.")
    print("=" * 50)

    if not (ok_yt and ok_ff):
        print()
        print("  [알림] YouTube 다운로드 기능에 필요한 파일이 부족합니다.")
        print("  네트워크가 가능해지면 setup.bat 을 다시 실행하세요.")
        print("  (Freesound 검색/다운로드 기능은 정상 동작합니다.)")


if __name__ == "__main__":
    main()
