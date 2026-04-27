# 🎵 Sound Downloader

**Freesound**, **YouTube**, **OpenGameArt**, **BBC Sound Effects** 사운드를 한 번에 받을 수 있는 윈도우용 도구입니다.
설치도 사용도 더블클릭 두 번이면 끝.

> 대상: Windows 10 / 11
> 별도 Python 설치 필요 없음 (압축 안에 다 들어있어요)

---

## 🚀 빠른 시작 (3분)

1. **압축 해제** — 받은 zip 파일을 원하는 위치에 풀어주세요. (예: `D:\Tools\SoundDownloader`)
2. **`setup.bat` 더블클릭** — 처음 한 번만 실행하면 됩니다. (1~2분 소요)
3. **`run.bat` 더블클릭** — 메뉴가 뜹니다. 끝!

> 압축 해제 위치 경로에 한글이 들어가도 괜찮습니다.

> **개발자/Github 에서 클론한 경우:** zip 본 안에 들어있던 큰 파일들(임베디드 Python, yt-dlp, ffmpeg)은 git 저장소에 없습니다. 시스템에 [Python 3](https://www.python.org/downloads/) 만 설치되어 있으면 `setup.bat` 가 알아서 모두 자동 다운로드합니다. 인터넷 차단 환경이라면 `setup.bat --no-download` 로 실행하세요.

---

## 🎯 무엇을 할 수 있나요?

```
  ╔══════════════════════════════════════════════╗
  ║ 🎵  Sound Downloader                         ║
  ╚══════════════════════════════════════════════╝

     1. 🔍  Freesound 검색 & 다운로드
     2. 🎬  YouTube 다운로드 (yt-dlp)
     3. 🎮  OpenGameArt 검색 & 다운로드
     4. 📻  BBC Sound Effects 검색 & 다운로드
     5. ⚙️  설정 (Freesound API Key)
     6. 📁  다운로드 폴더 열기
     0. 🚪  종료
```

### 1️⃣ Freesound 검색 & 다운로드
- 키워드로 음원 검색 → 다운로드 많은순/평점순/짧은순/긴순 등으로 정렬 → 상위 N개 일괄 다운로드.
- 효과음/앰비언스 찾을 때 강력합니다.
- 결과 폴더: `downloads/freesound/`

### 2️⃣ YouTube 다운로드 (yt-dlp)
- **단일 링크 다운로드**: 링크 하나만 붙여넣으면 됩니다.
- **`youtube_links.csv` 일괄 다운로드**: 여러 링크를 한꺼번에.
- 포맷 선택: **MP3 320kbps** / **FLAC** / **WAV** / **Opus**
- 결과 폴더: `downloads/youtube/`

### 3️⃣ OpenGameArt 검색 & 다운로드
- **API Key 불필요** — 바로 사용 가능.
- 카테고리: **음악(Music)** / **효과음(Sound Effect)** / **둘 다**
- 정렬: **인기순(즐겨찾기)** / **최신순** / **관련도순**
- 한 게시물 = 한 폴더 정책. 게시물 안의 모든 첨부 파일을 받고 `README.txt` 에 출처/작성자/태그/라이선스 안내를 자동 기록합니다.
- 결과 폴더: `downloads/opengameart/<게시물제목>/`
- ⚠️ OGA 게시물의 라이선스는 다양합니다(CC0/CC-BY/GPL/OGA-BY 등). 상업 이용 시 각 게시물의 출처 페이지에서 라이선스를 반드시 확인하세요.

### 4️⃣ BBC Sound Effects 검색 & 다운로드
- **API Key 불필요** — 영국 BBC 가 공개한 33,000+ 효과음/필드 레코딩 라이브러리.
- 정렬: **관련도순** / **녹음일자 최신순** / **짧은 길이순** / **긴 길이순**
- 길이 필터 지원 (15초/30초/45초/1분/2분/3분/제한없음).
- 트랙별로 mp3 1개 + 동일 이름 `.txt` 메타파일(녹음일/위치/녹음자/태그/라이선스) 자동 생성.
- 결과 폴더: `downloads/bbc/`
- ⚠️ **BBC RemArc License**: **개인/교육/연구 목적만 무료**. 상업 이용은 별도 라이선스가 필요합니다.
- 검색은 영문으로 (예: `rain`, `forest`, `train`).
- 본 도구는 mp3(약 128kbps) 만 지원합니다. 원본 wav 가 필요하면 [BBC 사이트](https://sound-effects.bbcrewind.co.uk/)에서 직접 받으세요.

### 5️⃣ 설정
- Freesound API Key / OAuth Token 입력.

### 6️⃣ 다운로드 폴더 열기
- 탐색기로 `downloads/` 폴더를 엽니다.

---

## 🔑 처음에 한 번만 — Freesound API Key 받기

Freesound 검색 기능을 쓰려면 무료 API Key가 필요합니다.
(YouTube 다운로드는 키 없이도 가능합니다.)

1. https://freesound.org 회원가입 후 로그인
2. https://freesound.org/apiv2/apply/ 접속
3. "Create new API credential" 클릭
4. 아무 이름이나 입력하고 발급
5. 발급받은 **Client secret/Api key** 를 복사
6. 앱 메뉴 **5번 → 설정** 에서 붙여넣기 후 저장

> 더 고품질의 원본 파일(WAV/AIFF)을 받고 싶다면 OAuth Token도 동일한 페이지에서 발급받아 같은 메뉴에 입력하세요. 보통은 API Key만으로 충분합니다.

---

## 🎬 YouTube 일괄 다운로드 사용법

1. 메뉴 **2번 → YouTube 다운로드 → 2번 (youtube_links.csv 일괄 다운로드)** 선택
2. CSV 파일이 없으면 자동으로 생성되고 메모장이 열립니다.
3. 아래처럼 한 줄에 하나씩 입력하고 저장:

   ```csv
   접두사,링크
   1,https://www.youtube.com/watch?v=dQw4w9WgXcQ
   2,https://youtu.be/oHg5SJYRHA0
   ,https://youtu.be/...     ← 접두사는 비워둬도 됩니다
   ```

   - `#` 으로 시작하는 줄은 메모로 무시되니 마음껏 적어두셔도 돼요.
   - 접두사를 적으면 파일명 앞에 붙습니다 (예: `1_원래제목.mp3`).

4. 다시 메뉴 2번을 실행 → 포맷 선택 → 자동으로 전부 다운로드됩니다.
5. 어떤 게 성공/실패했는지는 `downloads/youtube/youtube_log.csv` 에 기록됩니다.

---

## 📁 폴더 구조

```
SoundDownloader/
├── setup.bat            ← 처음 한 번만 더블클릭
├── run.bat              ← 평소엔 이걸 더블클릭
├── config.json          ← 내 설정 (API Key 등)
│
├── bin/                 ← yt-dlp / ffmpeg (이미 들어있어요)
├── downloads/           ← 다운로드한 파일이 여기 쌓입니다
│   ├── freesound/
│   ├── youtube/
│   ├── opengameart/
│   └── bbc/
└── youtube_links.csv    ← (자동 생성) YouTube 일괄용 링크 목록
```

> `python/`, `packages/`, `app/`, `templates/` 폴더는 프로그램 동작에 필요하니 건드리지 마세요.

---

## ❓ 자주 묻는 질문

### Q. 매번 `setup.bat` 을 실행해야 하나요?
**아뇨**, **처음 한 번만** 실행하면 됩니다. 그다음부터는 `run.bat` 만 더블클릭하세요.

### Q. 인터넷 없이도 되나요?
- Freesound / YouTube 모두 인터넷이 필요합니다.
- 단, 한 번 받은 파일은 오프라인에서 그대로 사용 가능.

### Q. 어떤 포맷으로 받는 게 좋나요?
| 용도 | 추천 |
|------|------|
| 그냥 듣기 / 휴대폰에 옮기기 | **MP3** (가벼움) |
| 영상 편집 / DAW 작업 | **WAV** (편집용 표준) |
| 무손실 보관 | **FLAC** (용량 절약 + 무손실) |
| 디스코드/스트리밍 | **Opus** (작은 용량, 좋은 음질) |

### Q. yt-dlp 가 갑자기 안 돼요!
YouTube가 사양을 자주 바꿔서 그렇습니다. 메뉴 **2번 → YouTube → 3번 (yt-dlp 업데이트)** 를 한 번 눌러보세요. 보통 해결됩니다.

### Q. 검색 결과가 너무 적어요 / 없어요
- 영문 키워드를 시도해보세요 (`비` → `rain`, `발걸음` → `footstep`).
- 정렬을 "관련도순"으로 바꿔보세요.
- 길이 제한을 "제한 없음"으로.

### Q. 다운로드한 파일은 상업적으로 써도 되나요?
- **Freesound**: 음원마다 라이선스가 다릅니다 (CC0 / CC-BY 등). 다운로드 후 원본 페이지의 라이선스를 꼭 확인하세요.
- **YouTube**: 저작권자가 명시적으로 허락한 경우가 아니면 개인 감상 목적으로만 사용하세요.
- **OpenGameArt**: 게시물마다 다릅니다 (CC0/CC-BY/GPL/OGA-BY 등). 각 게시물 폴더에 자동 생성되는 `README.txt` 의 출처 URL 에서 정확한 라이선스를 확인하세요.
- **BBC Sound Effects**: BBC RemArc License — 개인/교육/연구 목적은 무료, **상업 이용은 별도 라이선스 필요**. mp3 옆 `.txt` 파일에 자동 명시됩니다. 자세한 사항은 [BBC 라이선스 페이지](https://sound-effects.bbcrewind.co.uk/licensing) 참고.

---

## 🛟 문제가 생겼을 때

### "yt-dlp / ffmpeg 가 준비되지 않았습니다"
- `bin/` 폴더에 `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe` 가 모두 있는지 확인.
- 메뉴 **2번 → YouTube → 4번 (bin / 환경 상태 보기)** 로 진단 가능.

### "API Key가 설정되지 않았습니다"
- 메뉴 **5번 → 설정** 에서 Freesound API Key를 입력하세요. (위 “API Key 받기” 참고)

### 글자가 깨져 보여요 (한글이 `???` 로)
- `run.bat` 으로 실행하면 보통 정상입니다.
- 그래도 깨진다면 압축 해제할 때 경로에 한자/특수문자가 들어있지 않은지 확인.

### 그 외 에러 메시지가 떠요
1. 화면을 캡처합니다.
2. 에러 메시지에 `Traceback` 이 있다면 그 부분 전체를 같이 첨부.
3. 배포자에게 보내주세요.

---

## 💡 빠른 명령어 (선택, 고급)

`run.bat` 에 인자를 줘서 메뉴 없이 바로 실행할 수도 있습니다. CMD 창에서:

```bat
:: Freesound: "rain" 검색 → 인기순 상위 10개 자동 다운로드
run.bat search "rain" --top 10 -y

:: YouTube: 단일 링크 → MP3
run.bat youtube https://youtu.be/dQw4w9WgXcQ --format mp3

:: YouTube: CSV 일괄 → FLAC
run.bat youtube youtube_links.csv --format flac

:: yt-dlp 업데이트 후 다운로드
run.bat youtube --update https://youtu.be/...

:: OpenGameArt: "ambient" 음악 검색 → 인기순 상위 5개 자동 다운로드
run.bat oga "ambient" --category music --top 5 -y

:: OpenGameArt: 효과음 카테고리 전체 브라우징 → 최신순 상위 10개
run.bat oga --category sfx --sort newest --top 10 -y

:: BBC Sound Effects: "rain" 검색 → 짧은 길이순 상위 10개 자동 다운로드
run.bat bbc "rain" --sort duration_short --top 10 -y

:: BBC Sound Effects: "forest" 검색 → 30초 이하 상위 5개
run.bat bbc "forest" --duration-max 30 --top 5 -y
```

---

## 📜 라이선스

이 프로그램은 다음 오픈소스 도구를 활용합니다.

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — Unlicense
- [ffmpeg](https://ffmpeg.org/) — LGPL/GPL
- [Freesound API](https://freesound.org/docs/api/) — Freesound 정책
- [Python](https://www.python.org/) — PSF License
- [requests](https://github.com/psf/requests) — Apache 2.0

각 음원/영상의 저작권은 원저작자에게 있습니다.
다운로드한 콘텐츠의 사용 책임은 사용자에게 있습니다.

---

즐겁게 사용하세요! 🎶
