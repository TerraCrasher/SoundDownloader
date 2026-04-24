# Sound Downloader — 프로젝트 인계 문서

> 이 문서는 다른 LLM/개발자가 처음 프로젝트를 보았을 때
> **즉시 작업을 이어받을 수 있도록** 모든 맥락을 담은 “프로젝트 백서”입니다.
>
> - 마지막 업데이트: 2026-04-24
> - 운영체제: Windows 11
> - 셸: `cmd.exe`
> - Python: 임베디드 3.13 (`./python/python.exe`)

---

## 0. 한 줄 요약

**Windows용 단일 zip 배포형 통합 사운드 다운로더.**
Freesound(검색/다운로드)와 YouTube(yt-dlp 래핑)를 하나의 한국어 CLI 메뉴에서 사용한다.
사용자는 zip 해제 → `setup.bat` → `run.bat` 순서로만 실행하면 된다.

---

## 1. 디렉토리 구조

```
SoundDownloader/
├── setup.bat            ← 최초 설치 (사용자가 처음 실행)
├── setup.py             ← 설치 로직 (pip 설치, requests 설치, bin 체크 등)
├── run.bat              ← 앱 실행 (사용자가 평소 실행)
├── regen.bat / regen.py ← 개발자용: templates/ → ROOT 로 코드 동기화
├── files_data.py        ← regen 의 실제 복사 로직 (제외 규칙 포함)
├── config.json          ← 사용자 설정 (API key, 저장 경로 등)
├── PROJECT.md           ← (이 파일)
│
├── python/              ← 임베디드 Python 3.13 (zip에 포함되어 배포됨)
├── packages/            ← pip 으로 설치된 third-party (requests, urllib3, ...)
│   └── bin/             ← (자동) pip 가 만든 스크립트
├── bin/                 ← yt-dlp.exe / ffmpeg.exe / ffprobe.exe (배포 전 사용자가 직접 배치)
│   └── README.txt
├── downloads/           ← 다운로드 결과 (provider 별로 하위 폴더 분리)
│   ├── freesound/
│   └── youtube/
│
├── templates/           ← *마스터 소스* (실제 편집은 여기에서!)
│   ├── run.bat
│   ├── bin/README.txt
│   └── app/
│       ├── main.py
│       ├── cli/
│       │   ├── __init__.py
│       │   └── app.py        ← CLI 메뉴 + 서브커맨드 (메인)
│       ├── core/
│       │   ├── __init__.py
│       │   ├── downloader_base.py   ← DownloaderBase, SoundItem, SortOption
│       │   └── manager.py           ← provider 등록
│       └── providers/
│           ├── __init__.py
│           ├── freesound.py
│           └── youtube.py
│
└── app/                 ← templates/ 에서 regen 으로 복사된 사본 (실제 import 대상)
    ├── main.py
    ├── cli/  core/  providers/  ...
```

> **⚠️ 핵심 규칙: 코드 수정은 `templates/` 에서만 하고, `python regen.py` (또는 `regen.bat`) 으로 ROOT 의 `app/`, `run.bat`, `bin/README.txt` 를 갱신한다.** ROOT 쪽 사본을 직접 고치면 다음 regen 때 덮어써진다.

---

## 2. 실행 흐름

### 사용자 시나리오 (zip 배포)
1. zip 해제
2. `setup.bat` 더블클릭
   - 이미 모든 게 들어있어 "이미 설치됨" 으로 스킵 → 마지막 단계인 `templates/` → `ROOT` 복사만 수행.
3. `run.bat` 더블클릭 → 메인 메뉴

### Contributor 시나리오 (git clone)
1. `git clone ...`
2. `setup.bat` 더블클릭
   - **시스템 Python 으로 부트스트랩** (없으면 안내). `setup.bat` 가 `py -3` / `python` 을 자동 탐지.
   - 임베디드 Python 자동 다운로드 → `python/`
   - `._pth` 활성화, pip 설치, `requests` 를 `packages/` 에 설치
   - `bin/yt-dlp.exe` 자동 다운로드 (GitHub releases latest)
   - `bin/ffmpeg.exe` + `bin/ffprobe.exe` 자동 다운로드 (gyan.dev essentials zip → 두 exe만 추출)
   - `templates/` → `ROOT` 복사
3. `run.bat` 실행

> 모든 단계는 **멱등** — 이미 있는 항목은 건너뛴다. 사용자가 손으로 넣어둔 yt-dlp/ffmpeg 도 덮어쓰지 않음.
> 오프라인 환경에서는 `setup.bat --no-download` 또는 `set SOUND_DOWNLOADER_OFFLINE=1` 로 다운로드를 끌 수 있다 (체크만).

### 개발자 시나리오
1. `templates/...` 수정
2. `regen.bat` (또는 `python regen.py`) 실행 → ROOT 갱신
3. `run.bat` 으로 동작 확인

---

## 3. 주요 명령어

### CLI 서브커맨드 (run.bat 인자로 사용 가능)

```bat
run.bat                                                     :: 인터랙티브 메뉴
run.bat search "rain" --top 10 --sort downloads -y          :: Freesound
run.bat config --api-key XXX                                :: API Key 저장
run.bat youtube https://youtu.be/XXX --format mp3           :: YouTube 단일
run.bat youtube youtube_links.csv --format flac             :: YouTube 일괄
run.bat youtube --update https://youtu.be/XXX               :: yt-dlp 업데이트 후 다운로드
```

---

## 4. 핵심 인터페이스

### `DownloaderBase` (`templates/app/core/downloader_base.py`)
```python
class DownloaderBase(ABC):
    NAME = "Unknown"
    REQUIRES_AUTH = False
    SUPPORTED_SORTS = [SortOption.RELEVANCE]

    def search(self, query, max_results=50, sort=..., duration_max=None, duration_min=None) -> list[SoundItem]
    def download(self, item: SoundItem, save_dir, progress_cb=None) -> str   # 저장 경로
```

### `SoundItem` (dataclass)
```python
id, name, url, download_url
duration, filesize, downloads, rating, username, license
tags: list, extra: dict   # provider 별 추가 메타
```

### `SortOption`
`DOWNLOADS, RATING, DURATION_SHORT, DURATION_LONG, NEWEST, RELEVANCE`

### `DownloaderManager`
- 생성 시 모든 provider 자동 등록 (`Freesound`, `YouTube`)
- `manager.get("Freesound") / .get("YouTube")`

---

## 5. Provider 별 상세

### 5.1 Freesound (`providers/freesound.py`)
- Freesound API v2 사용. `requests` 필요.
- `freesound_api_key` 가 필수, OAuth 토큰이 있으면 원본 다운로드 URL 사용.
- 길이 필터: `duration:[min TO max]` Lucene 문법.
- 정렬 매핑: downloads_desc, rating_desc, duration_asc/desc, created_desc, score.

### 5.2 YouTube (`providers/youtube.py`) — yt-dlp 래퍼
- **`yt-dlp.exe`** 와 **`ffmpeg.exe`** 를 외부 프로세스로 호출.
- 탐색 우선순위:
  1. `config.json` 의 `youtube_bin_dir`
  2. 프로젝트 루트의 `bin/`
  3. 시스템 PATH (`shutil.which`)
- 검색 미지원 — `search()` 는 `NotImplementedError`.
- 메서드:
  - `download_url(url, save_dir, format_key, prefix)` → 단일
  - `download_csv(csv_path, save_dir, format_key, log_path, on_item)` → 일괄
  - `update_ytdlp()` → `yt-dlp -U`
  - `is_ready()`, `status_text()` → bin 진단
- 포맷 프리셋 (`FORMAT_PRESETS`):
  - `mp3` (320kbps, 썸네일/메타 임베드)
  - `flac` (무손실 압축, 썸네일/메타)
  - `wav` (무손실 비압축, 메타만)
  - `opus` (작은 용량, 썸네일/메타)
- 항상 다음 옵션 사용:
  `--no-playlist`, `--restrict-filenames`, `--newline`, `--ffmpeg-location <bin_dir>`

#### YouTube 일괄용 CSV (`youtube_links.csv`)
```csv
접두사,링크
# '#' 으로 시작하는 라인은 자동 무시 (예시 주석)
# 1,https://www.youtube.com/watch?v=AAAAAAAAAAA
1,https://youtu.be/REAL1
2,https://www.youtube.com/watch?v=REAL2
,https://youtu.be/REAL3   # 접두사 비워둬도 OK
```
- 인코딩 자동 감지: utf-8-sig → utf-8 → cp949
- 헤더 자동 스킵 (`접두사`, `prefix`, `name`, `title`)
- 결과 로그: `<save_dir>/youtube_log.csv` (utf-8-sig)

---

## 6. 설정 (`config.json`)

| 키 | 기본값 | 설명 |
|----|--------|------|
| `freesound_api_key` | `""` | Freesound v2 API key (필수) |
| `freesound_oauth_token` | `""` | OAuth 토큰(있으면 원본 wav/aiff 다운로드 가능) |
| `save_dir` | `"downloads"` | 베이스 다운로드 폴더 |
| `freesound_save_dir` | `"downloads/freesound"` | (없으면 `<save_dir>/freesound`) |
| `youtube_save_dir` | `"downloads/youtube"` | (없으면 `<save_dir>/youtube`) |
| `youtube_links_csv` | `"youtube_links.csv"` | 일괄 다운로드용 CSV 기본 경로 |
| `youtube_bin_dir` | `""` | yt-dlp/ffmpeg 가 있는 폴더 직접 지정 (비어있으면 ROOT/bin 사용) |

> CLI 의 `cli/app.py` 에 `freesound_default_dir(cfg)` / `youtube_default_dir(cfg)` 헬퍼가 있어 위 폴백 규칙이 일관되게 적용된다.

---

## 7. 인코딩 정책 (중요!)

Windows 코드페이지가 **CP949** 라서 한글/이모지/박스문자 출력에서 죽는 사고가 있었다.
다음 정책을 모두 지킨다.

1. **모든 `.py` 는 UTF-8 (BOM 없음) 으로 저장.**
   - 과거에 `downloader_base.py` 가 메모장 ANSI 저장으로 CP949가 되어 SyntaxError 발생.
   - 검출/변환 절차는 PowerShell 스니펫(아래 `12. 트러블슈팅` 참고).

2. **`run.bat` / `regen.bat` / `setup.bat`** 은 모두
   ```bat
   chcp 65001 > nul
   set PYTHONIOENCODING=utf-8
   set PYTHONUTF8=1
   ```
   를 둔다.

3. **각 파이썬 진입점(`app/main.py`, `setup.py`, `regen.py`)** 에서 stdout/stderr를 한 번 더 reconfigure:
   ```python
   try:
       sys.stdout.reconfigure(encoding="utf-8", errors="replace")
       sys.stderr.reconfigure(encoding="utf-8", errors="replace")
   except Exception:
       pass
   ```
   (`chcp` 만으로는 임베디드 Python 의 stdout 이 CP949 로 잡히는 경우가 있음)

4. **개발자 콘솔용 출력은 ASCII 친화적으로.**
   - `files_data.py`, `setup.py` 등 `chcp` 가 없는 환경에서도 도는 스크립트는 `✅` 같은 이모지를 쓰지 않는다 → `[OK]`, `[ERROR]` 같은 라벨로 대체.
   - `app/...` 쪽은 `run.bat` 이 chcp 65001 + reconfigure 를 보장하므로 이모지/박스문자 자유.

5. CSV/로그 파일 쓰기는 `utf-8-sig` (BOM) — Excel 한글 호환.

---

## 8. files_data.py 의 제외 규칙

`templates/` → `ROOT` 복사 시 다음은 **자동 제외**:
- 폴더: `__pycache__`, `.git`, `.idea`, `.vscode`
- 확장자: `.pyc`, `.pyo`, `.bak`, `.tmp`, `.swp`
- 파일: `.DS_Store`, `Thumbs.db`

→ 과거에 `downloader_base.py.bak` 까지 같이 복사돼서 import 시 부작용이 날 뻔한 사례가 있어 추가됨.

---

## 9. 배포 절차

### A. zip 배포 (일반 사용자용 — 가장 빠른 경로)
1. ROOT 에서 `python regen.py` → templates/ → ROOT 동기화.
2. `python/`, `packages/`, `bin/yt-dlp.exe`, `bin/ffmpeg.exe`, `bin/ffprobe.exe` 가 모두 들어있는지 확인.
3. `downloads/`, `config.json` 의 개인 데이터 정리.
4. `__pycache__/` 정리 (선택).
5. zip 으로 묶어 전달.
6. 사용자: 압축 해제 → `setup.bat` → `run.bat`. 이미 모두 들어있어 setup 은 "이미 설치됨" 으로 즉시 통과.

### B. git push (개발 / 공개)
1. `git add . && git commit && git push`.
   `.gitignore` 가 큰 바이너리(`python/`, `packages/`, `bin/*` 단 README 제외)와 `config.json`, `downloads/`, `app/`(자동 생성 사본), `run.bat`(자동 생성) 모두 제외.
2. clone 한 사람이 `setup.bat` 을 실행하면 v2.5 자동 다운로드가 모든 외부 의존성을 채워준다.
   - 시스템에 Python 3 만 있으면 됨 (없으면 `setup.bat` 가 안내).

---

## 10. 새 Provider 추가 절차 (예: SoundCloud)

1. `templates/app/providers/soundcloud.py` 작성.
   - `class SoundCloudDownloader(DownloaderBase):`
   - `NAME = "SoundCloud"`, `SUPPORTED_SORTS`, `search()`, `download()` 구현
   - 검색 결과는 `SoundItem` 리스트로 반환
2. `templates/app/core/manager.py` 의 `_register_defaults` 에 `self.register(SoundCloudDownloader(self.config))` 추가.
3. `templates/app/cli/app.py`:
   - 메인 메뉴에 항목 추가
   - 필요하면 `<provider>_default_dir(cfg)` 헬퍼 추가 (downloads/<provider>)
   - 인터랙티브/CLI 서브커맨드 함수 추가
4. `config.json` 기본값에 `<provider>_save_dir` 등 추가
5. `regen.bat` 후 `run.bat` 으로 검증

---

## 11. 변경 이력 (요약)

> 의사결정 근거를 남겨둠. 다른 LLM 이 “왜 이렇게 되어 있지?” 라고 의문을 가질 때 참고.

### v1: 초기
- Freesound 단일 provider, 한국어 CLI, 임베디드 Python + zip 배포 모델.

### v2: YouTube 통합 (이번 작업)
- 사용자 결정: **A안 — Python CLI 통합형** (병렬 BAT 안 / 하이브리드 안 거부).
- `providers/youtube.py` 신규. 검색은 미지원. yt-dlp.exe 외부 프로세스 호출.
- 메인 메뉴에 “🎬 YouTube 다운로드” 추가 + CLI 서브커맨드 `youtube` 추가.
- 4종 포맷 프리셋(MP3/FLAC/WAV/Opus).
- bin 위치는 `config.youtube_bin_dir` → `ROOT/bin/` → PATH 순.

### v2.1: 인코딩 정책 정비
- `templates/app/core/downloader_base.py` 가 CP949 로 저장돼 import 실패 → UTF-8(no BOM) 재저장.
- `regen.py` / `files_data.py` 의 이모지(`✅`)가 cp949 콘솔에서 죽음 → ASCII 라벨로 교체.
- `app/main.py`, `setup.py`, `regen.py` 에 stdout reconfigure 추가.
- `run.bat` / `templates/run.bat` 에 `PYTHONIOENCODING=utf-8` + `PYTHONUTF8=1`.

### v2.2: setup.py 정책 변경
- 사용자 요청: bin 자동 다운로드 X, **존재 체크만**.
- 이유: 패키지 만든 사람이 zip 안에 미리 yt-dlp/ffmpeg 를 넣어 배포할 것.
- `setup.py.check_bin()` 이 누락 항목만 안내.

### v2.3: 다운로드 폴더 분리
- 사용자 요청: provider 별로 하위 폴더로 구분.
- 결과: `downloads/freesound/`, `downloads/youtube/` 자동 사용.
- `freesound_default_dir(cfg)` / `youtube_default_dir(cfg)` 헬퍼로 일관 처리.
- 메인 메뉴 “📁 다운로드 폴더 열기” 는 베이스(`downloads`) 를 연다.

### v2.4: CSV 명명 + 가이드 주석
- 사용자 요청: `links.csv` → 용도가 분명한 `youtube_links.csv` 로 변경.
- 자동 생성 시 `#` 주석으로 사용 예시 포함.
- 파서가 `#` 라인 자동 무시하도록 `_read_links_csv` 보강.

### v2.5: GitHub 공개 + setup 자동 다운로드 (정책 재변경)
- 사용자 요청: git 으로 공개하고 싶다 → 큰 바이너리(`python/`, `bin/yt-dlp.exe`, `bin/ffmpeg.exe` 등)는 git 에 못 올림.
- 동시에 "git clone 한 사람도 setup.bat 한 번이면 끝나야 함" 요구.
- 결정: **v2.2 의 '체크만' 정책을 뒤집어 자동 다운로드 + 멱등 + 오프라인 옵션** 으로 재설계.
  - `ensure_embedded_python()` — python.org 공식 embedded zip 자동 다운로드.
  - `ensure_ytdlp()` — GitHub releases latest 직접 다운로드.
  - `ensure_ffmpeg()` — gyan.dev essentials zip → `ffmpeg.exe`/`ffprobe.exe` 만 추출 (덮어쓰기 X).
  - 모두 **이미 있으면 스킵** (zip 배포 사용자에게도 안전).
  - **오프라인**: `setup.bat --no-download` 또는 `set SOUND_DOWNLOADER_OFFLINE=1`.
- `setup.bat` 부트스트랩: `python\python.exe` → `py -3` → `python` 순으로 자동 탐지.
- `.gitignore`: 큰 바이너리 / 자동 생성 사본 / 사용자 데이터 모두 제외.
  `bin/README.txt`, `templates/`, 빌드 스크립트만 추적. 개인 설정은 `config.example.json` 으로 분리.

---

## 12. 트러블슈팅 메모

### "UnicodeEncodeError: 'cp949' codec can't encode character ..."
- 원인: stdout 이 CP949. `run.bat` 의 `PYTHONIOENCODING=utf-8` 와 진입점의 `sys.stdout.reconfigure` 가 빠진 경우.
- 해결: 7장 인코딩 정책 항목 4개 모두 적용.

### "SyntaxError: (unicode error) ..." 가 import 에서 발생
- 원인: `.py` 파일이 CP949 로 저장됨.
- 검출 (PowerShell):
  ```powershell
  $strict = New-Object System.Text.UTF8Encoding $false, $true
  Get-ChildItem templates -Recurse -Filter *.py | ForEach-Object {
      try { $null = $strict.GetString([IO.File]::ReadAllBytes($_.FullName)); "OK   $($_.FullName)" }
      catch { "BAD  $($_.FullName)" }
  }
  ```
- 변환 (CP949 → UTF-8 no BOM):
  ```powershell
  $b = [IO.File]::ReadAllBytes($p)
  $t = [Text.Encoding]::GetEncoding(949).GetString($b)
  [IO.File]::WriteAllText($p, $t, (New-Object Text.UTF8Encoding $false))
  ```

### "yt-dlp / ffmpeg 를 찾을 수 없습니다"
- `bin/` 에 두 exe 가 있는지 확인 (메뉴: YouTube → "🔎 bin / 환경 상태 보기").
- 또는 `config.json` 의 `youtube_bin_dir` 절대경로 지정.
- PATH 에 이미 있으면 그쪽도 자동 사용됨.

### regen.bat 실행 시 `\u2705` 등 인코딩 오류
- v2.1 에서 해결됨. 그래도 발생 시 `regen.py` / `files_data.py` 의 `print` 에 이모지가 추가되었는지 확인.

---

## 13. 자주 쓰는 검증 명령

```bat
:: 1) 모든 templates *.py 가 UTF-8 인지
python\python.exe -c "import sys, os; from pathlib import Path; bad=[]; [bad.append(str(p)) for p in Path('templates').rglob('*.py') if (lambda b: not _try(b))(open(p,'rb').read())]" 

:: 2) 앱 import 테스트
python\python.exe -c "import sys, os; sys.path.insert(0, os.path.join(os.getcwd(),'app')); sys.path.insert(0, os.path.join(os.getcwd(),'packages')); from cli.app import main; from core.manager import DownloaderManager; import json; m=DownloaderManager(json.load(open('config.json',encoding='utf-8'))); print(m.list_providers())"

:: 3) YouTube provider 환경 진단
python\python.exe -c "import sys, os; sys.path.insert(0, os.path.join(os.getcwd(),'app')); from providers.youtube import YouTubeDownloader; import json; print(YouTubeDownloader(json.load(open('config.json',encoding='utf-8'))).status_text())"

:: 4) 메뉴 첫 화면이 죽지 않는지
echo 0| python\python.exe app\main.py
```

---

## 14. 알려진 한계 / TODO 후보

- **YouTube 검색 미지원** — yt-dlp 의 `ytsearch:` 를 활용하면 가능하지만, `SoundItem` 모델과 잘 안 맞아서 일부러 빼둠. 필요하면 별도 메뉴로.
- **playlist 일괄 다운로드** — 현재 `--no-playlist` 강제. 옵션화 가능.
- **GUI** — 없음. 콘솔 메뉴 only.
- **국제화** — 한국어 고정. 메시지 분리는 필요 시 `cli/i18n.py` 에 모으기.
- **테스트** — 자동화 테스트 없음. 수동 검증 명령은 13장 참고.
- **`downloads/` 의 기존 파일** — provider 분리 도입 후 기존 파일은 자동 이동되지 않는다. 수동 정리 필요.

---

## 15. 라이선스/외부 도구

- 본 코드: 사용자 내부 도구 (라이선스 미정).
- `yt-dlp`: Unlicense / public domain. https://github.com/yt-dlp/yt-dlp
- `ffmpeg`: LGPL/GPL (빌드에 따라 다름). https://www.gyan.dev/ffmpeg/builds/
- Freesound API: https://freesound.org/docs/api/ (개인 API key 필요)
- Python: PSF License.
- `requests` 등 third-party: 각각의 라이선스(`packages/<pkg>.dist-info/`) 참고.

---

## 16. 다른 LLM 에게 — “시작 전 반드시 읽어야 할 5가지”

1. **편집은 `templates/` 에서만, 그리고 끝나면 `python regen.py`.** ROOT 의 `app/...` 를 직접 고치지 말 것.
2. **모든 `.py` 는 UTF-8 (BOM 없음).** Windows 메모장으로 한글 저장하면 CP949 로 깨질 수 있음.
3. **사용자에게 이모지/박스문자 출력은 OK, 단 `app/...` 안에서만.** `setup.py` / `files_data.py` / `regen.py` 같은 “설치/개발자 진입점” 에서는 ASCII 친화적으로.
4. **`bin/` 의 yt-dlp/ffmpeg 와 `python/` 임베디드 런타임은 v2.5 부터 `setup.py` 가 자동 다운로드한다.**
   단, **이미 있으면 절대 덮어쓰지 않는다 (멱등)**. 오프라인 환경은 `setup.bat --no-download` 또는 `set SOUND_DOWNLOADER_OFFLINE=1` 로 자동 다운로드를 끈다(체크만).
   git 저장소는 큰 바이너리를 갖지 않고 `.gitignore` 로 제외해 둠.
5. **다운로드 경로는 헬퍼(`<provider>_default_dir`)를 통해 결정.** 새 provider 추가 시 같은 패턴을 따라 `downloads/<provider>/` 를 기본값으로.
